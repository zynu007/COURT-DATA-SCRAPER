from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class CaseQuery(db.Model):
    """
    Model to store each court case query and response for audit trail
    """
    __tablename__ = 'case_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    case_type = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(100), nullable=False)
    filing_year = db.Column(db.Integer, nullable=False)
    
    raw_response = db.Column(db.Text, nullable=True)
    
    parties_names = db.Column(db.Text, nullable=True)
    filing_date = db.Column(db.String(50), nullable=True)
    next_hearing_date = db.Column(db.String(50), nullable=True)
    
    query_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'case_type': self.case_type,
            'case_number': self.case_number,
            'filing_year': self.filing_year,
            'parties_names': self.parties_names,
            'filing_date': self.filing_date,
            'next_hearing_date': self.next_hearing_date,
            'query_timestamp': self.query_timestamp.isoformat() if self.query_timestamp else None,
            'status': self.status,
            'error_message': self.error_message
        }

class CaseDocument(db.Model):
    """
    Model to store PDF links and order/judgment details
    """
    __tablename__ = 'case_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    case_query_id = db.Column(db.Integer, db.ForeignKey('case_queries.id'), nullable=False)
    
    document_type = db.Column(db.String(50), nullable=False)
    document_title = db.Column(db.String(200), nullable=True)
    document_date = db.Column(db.String(50), nullable=True)
    pdf_url = db.Column(db.Text, nullable=False)
    
    case_query = db.relationship('CaseQuery', backref=db.backref('documents', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_type': self.document_type,
            'document_title': self.document_title,
            'document_date': self.document_date,
            'pdf_url': self.pdf_url
        }