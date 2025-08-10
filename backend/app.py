from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from database import db, CaseQuery, CaseDocument
from scraper import DelhiHighCourtScraper
from utils import validate_case_input, log_scraping_attempt
from config import Config
import json
import logging
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Initialize scraper
    scraper = DelhiHighCourtScraper(timeout=Config.SCRAPING_TIMEOUT)
    
    with app.app_context():
        db.create_all()
        
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/api/case-types', methods=['GET'])
    def get_case_types():
        """Get available case types from the court website"""
        try:
            case_types = scraper.get_available_case_types()
            formatted_types = [
                {'value': value, 'label': label} 
                for label, value in case_types.items()
            ]
            
            return jsonify({
                'success': True,
                'case_types': formatted_types
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching case types: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to fetch case types',
                'message': str(e)
            }), 500
    
    @app.route('/api/search', methods=['POST'])
    def search_case():
        """Search for case data"""
        try:
            data = request.get_json()
            
            case_type = data.get('case_type', '').strip()
            case_number = data.get('case_number', '').strip()
            filing_year = int(data.get('filing_year', 0))
            
            is_valid, error_message = validate_case_input(case_type, case_number, filing_year)
            if not is_valid:
                return jsonify({
                    'success': False,
                    'error': 'Invalid input',
                    'message': error_message
                }), 400
            
            existing_case = CaseQuery.query.filter_by(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year
            ).first()
            
            if existing_case and existing_case.status == 'success':
                documents = [doc.to_dict() for doc in existing_case.documents]
                return jsonify({
                    'success': True,
                    'cached': True,
                    'case_data': existing_case.to_dict(),
                    'documents': documents
                }), 200
            
            success, scraped_data, error_msg = scraper.search_case(case_type, case_number, filing_year)
            
            # Improved success check - consider it successful if we have meaningful data
            actual_success = success and (scraped_data.get('parties_names') or scraped_data.get('case_status'))
            
            case_query = CaseQuery(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year,
                status='success' if actual_success else 'failed',
                error_message=error_msg if not actual_success else None
            )
            
            if actual_success:
                case_query.parties_names = scraped_data.get('parties_names', '')
                case_query.filing_date = scraped_data.get('filing_date', '')
                case_query.next_hearing_date = scraped_data.get('next_hearing_date', '')
                case_query.raw_response = json.dumps(scraped_data)
            
            db.session.add(case_query)
            db.session.commit()
            
            documents = []
            if actual_success and scraped_data.get('documents'):
                for doc_data in scraped_data['documents']:
                    document = CaseDocument(
                        case_query_id=case_query.id,
                        document_type=doc_data.get('type', 'order'),
                        document_title=doc_data.get('title', ''),
                        pdf_url=doc_data.get('url', ''),
                        document_date=doc_data.get('date', '')
                    )
                    db.session.add(document)
                    documents.append(document.to_dict())
                
                db.session.commit()
            
            log_scraping_attempt(case_type, case_number, filing_year, actual_success, error_msg)
            
            if actual_success:
                return jsonify({
                    'success': True,
                    'cached': False,
                    'case_data': case_query.to_dict(),
                    'documents': documents
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Case not found or scraping failed',
                    'message': error_msg or 'No case data found'
                }), 400
                
        except Exception as e:
            logger.error(f"Search endpoint error: {str(e)}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }), 500
    
    @app.route('/api/history', methods=['GET'])
    def get_search_history():
        """Get search history with pagination"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            queries = CaseQuery.query.order_by(CaseQuery.query_timestamp.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            history = []
            for query in queries.items:
                query_dict = query.to_dict()
                query_dict['documents_count'] = len(query.documents)
                history.append(query_dict)
            
            return jsonify({
                'success': True,
                'history': history,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': queries.total,
                    'pages': queries.pages
                }
            }), 200
            
        except Exception as e:
            logger.error(f"History endpoint error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to fetch history',
                'message': str(e)
            }), 500

    @app.route('/api/extract-pdf-url', methods=['POST'])
    def extract_pdf_url():
        """Extract direct PDF URL from case details page"""
        try:
            data = request.get_json()
            case_details_url = data.get('case_details_url')
            
            if not case_details_url:
                return jsonify({
                    'success': False,
                    'error': 'Case details URL is required'
                }), 400
            
            # Use the scraper method to extract PDF URL
            pdf_url = scraper._extract_direct_pdf_from_case_page(case_details_url)
            
            if pdf_url:
                return jsonify({
                    'success': True,
                    'pdf_url': pdf_url,
                    'message': 'PDF URL extracted successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Could not extract PDF URL',
                    'message': 'No PDF link found on the page'
                }), 404
                
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'PDF extraction failed',
                'message': str(e)
            }), 500
        
    @app.route('/api/download/<int:document_id>', methods=['GET'])
    def download_document(document_id):
        """Download document by ID - fetches and serves the PDF directly"""
        try:
            document = CaseDocument.query.get_or_404(document_id)
            
            # Check if the URL is already a direct PDF URL with showlogo
            if 'showlogo' in document.pdf_url and '.pdf' in document.pdf_url:
                # This is already a direct PDF URL
                return jsonify({
                    'success': True,
                    'download_url': document.pdf_url,
                    'document_title': document.document_title,
                    'message': 'Document ready for download',
                    'direct_download': True
                }), 200
            
            # If the URL points to case details page, extract the direct PDF link
            elif 'case-type-status-details' in document.pdf_url:
                try:
                    # Extract direct PDF URL from the case details page
                    direct_pdf_url = scraper._extract_direct_pdf_from_case_page(document.pdf_url)
                    
                    if direct_pdf_url:
                        logger.info(f"Extracted direct PDF URL: {direct_pdf_url}")
                        return jsonify({
                            'success': True,
                            'download_url': direct_pdf_url,
                            'document_title': document.document_title,
                            'message': 'Document ready for download',
                            'direct_download': True
                        }), 200
                    else:
                        # Fallback to original URL
                        return jsonify({
                            'success': True,
                            'download_url': document.pdf_url,
                            'document_title': document.document_title,
                            'message': 'Original URL returned',
                            'direct_download': False
                        }), 200
                            
                except Exception as e:
                    logger.error(f"Error extracting PDF URL: {str(e)}")
                    # Return the original URL as fallback
                    return jsonify({
                        'success': True,
                        'download_url': document.pdf_url,
                        'document_title': document.document_title,
                        'message': 'Fallback URL returned',
                        'direct_download': False
                    }), 200
            else:
                # For other URLs, return as-is
                return jsonify({
                    'success': True,
                    'download_url': document.pdf_url,
                    'document_title': document.document_title,
                    'message': 'Document ready for download',
                    'direct_download': True
                }), 200
                    
        except Exception as e:
            logger.error(f"Download endpoint error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Download failed',
                'message': str(e)
            }), 500

    @app.route('/api/stats', methods=['GET'])
    def get_statistics():
        """Get application statistics"""
        try:
            total_queries = CaseQuery.query.count()
            successful_queries = CaseQuery.query.filter_by(status='success').count()
            failed_queries = CaseQuery.query.filter_by(status='failed').count()
            total_documents = CaseDocument.query.count()
            
            # Fix deprecated datetime.utcnow() usage
            recent_queries = CaseQuery.query.filter(
                CaseQuery.query_timestamp > datetime.now(timezone.utc) - timedelta(days=1)
            ).count()
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_queries': total_queries,
                    'successful_queries': successful_queries,
                    'failed_queries': failed_queries,
                    'success_rate': round((successful_queries / total_queries * 100) if total_queries > 0 else 0, 2),
                    'total_documents': total_documents,
                    'recent_queries_24h': recent_queries
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Stats endpoint error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to fetch statistics',
                'message': str(e)
            }), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
    
    return app

# Create the Flask application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)