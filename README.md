# Delhi High Court Case Data Scraper 🏛️

A comprehensive web scraping solution for extracting case data and documents from the Delhi High Court portal, built with Flask, Vue.js, and Playwright.

## 📋 Table of Contents
- [Overview](#overview)
- [Why Delhi High Court?](#why-delhi-high-court)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation & Setup](#installation--setup)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [Rate Limiting & Security](#rate-limiting--security)
- [Technical Implementation](#technical-implementation)
- [Docker Deployment](#docker-deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

This project automates the process of retrieving case information and downloading legal documents from the Delhi High Court's online portal. It handles CAPTCHA validation, form submission, and document extraction with a user-friendly web interface.

**Live Demo**: [Add your deployed URL here]

## 🏛️ Why Delhi High Court?

After evaluating multiple court websites across India, I chose Delhi High Court for several strategic reasons:

### 1. **Superior CAPTCHA Implementation**
- **Text-based CAPTCHA**: Unlike other courts that use complex image-based CAPTCHAs, Delhi HC uses simple 4-digit numeric CAPTCHAs
- **HTML-embedded**: The CAPTCHA solution is stored as plain text in HTML tags (`<span id="captcha-code">`), discoverable through DOM inspection
- **No Third-party APIs**: This eliminates the need for expensive CAPTCHA-solving services like 2captcha or Anti-Captcha
- **Consistent Format**: Always 4 digits, making validation predictable and reliable

### 2. **Clean & Accessible UI**
- Modern, responsive design with clear form elements
- Consistent HTML structure across different case types
- Well-organized data tables with predictable patterns
- Minimal JavaScript interference with scraping operations

### 3. **Robust Document Access**
- Direct PDF links with consistent URL patterns (`/app/showlogo/...`)
- Structured case detail pages with tabular data
- Multiple document types (orders, judgments, notices)
- Reliable document availability and accessibility

### 4. **Technical Advantages**
```python
# Example: How we extract CAPTCHA from Delhi HC
captcha_span = page.wait_for_selector('span#captcha-code')
captcha_solution = captcha_span.text_content().strip()
# No image processing or external APIs needed!
```

## ✨ Key Features

### Core Functionality
- **Intelligent Case Search**: Support for multiple case types (CWP, CRL.A., BAIL APPLN., etc.)
- **Automated CAPTCHA Handling**: Smart text extraction and validation
- **Document Discovery**: Automatic extraction of PDF links and case documents
- **Real-time Processing**: Live status updates during scraping operations
- **Data Caching**: SQLite-based caching to avoid redundant requests

### User Experience
- **Modern Web Interface**: Clean, responsive Vue.js frontend
- **Progress Indicators**: Real-time feedback during long operations
- **Error Handling**: Comprehensive error messages with troubleshooting tips
- **Search History**: Track and revisit previous searches
- **One-click Downloads**: Direct access to legal documents

### Technical Features
- **Rate Limiting**: Built-in protection against server overload
- **Session Management**: Proper cookie and CSRF token handling
- **Retry Logic**: Automatic retry with exponential backoff
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Vue.js SPA    │────│   Flask API      │────│  Playwright Engine  │
│   (Frontend)    │    │   (Backend)      │    │   (Web Scraper)     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                       │                         │
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│  Static Assets  │    │  SQLite Database │    │  Delhi HC Portal    │
│   CSS/JS/HTML   │    │   (Data Cache)   │    │  (Target Website)   │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

### Technology Stack
- **Frontend**: Vue.js 3, Tailwind CSS, Lucide Icons
- **Backend**: Python Flask, SQLAlchemy ORM
- **Scraping**: Playwright (Chromium automation)
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Containerization**: Docker & Docker Compose

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ (for frontend development, optional)
- Docker & Docker Compose (for containerized deployment)

### Option 1: Local Development Setup

#### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/delhi-hc-scraper.git
cd delhi-hc-scraper
```

#### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

#### Step 3: Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Install Playwright Browsers
```bash
# Install Playwright and browser dependencies
playwright install chromium
playwright install-deps
```

#### Step 5: Environment Configuration
Create a `.env` file in the root directory:
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///court_data.db
SCRAPING_TIMEOUT=90
MAX_RETRIES=3
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=3600
```

#### Step 6: Initialize Database
```bash
python -c "from app import create_app; from database import db; app = create_app(); app.app_context().push(); db.create_all()"
```

#### Step 7: Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Option 2: Docker Deployment (Recommended)

#### Quick Start with Docker Compose
```bash
# Clone and navigate to project
git clone https://github.com/yourusername/delhi-hc-scraper.git
cd delhi-hc-scraper

# Build and run with Docker Compose
docker-compose up --build -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Manual Docker Build
```bash
# Build the image
docker build -t delhi-hc-scraper .

# Run the container
docker run -d \
  --name court-scraper \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e FLASK_ENV=production \
  delhi-hc-scraper
```

## 📖 Usage Guide

### Web Interface

1. **Access the Application**: Open `http://localhost:5000` in your browser

2. **Search for Cases**:
   - Select case type from dropdown (e.g., "Criminal Appeal" → CRL.A.)
   - Enter case number (e.g., "1626")
   - Select filing year (e.g., "2025")
   - Click "Search Case"

3. **View Results**:
   - Case information displays in organized cards
   - Documents section shows available PDFs
   - Click "Download" to access documents in new tabs

4. **Quick Test Cases**:
   - Use provided test buttons for immediate testing
   - Examples: CRL.A. 798/2025, BAIL APPLN. 1626/2025

### API Usage

#### Search for Case Data
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "case_type": "CRL.A.",
    "case_number": "1626",
    "filing_year": 2025
  }'
```

#### Get Available Case Types
```bash
curl http://localhost:5000/api/case-types
```

#### Download Document
```bash
curl http://localhost:5000/api/download/1
```

## 📚 API Documentation

### Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/api/case-types` | Fetch available case types | None |
| POST | `/api/search` | Search for case data | `case_type`, `case_number`, `filing_year` |
| GET | `/api/history` | Get search history | `page`, `per_page` (optional) |
| GET | `/api/download/<id>` | Download document by ID | Document ID in URL |
| POST | `/api/extract-pdf-url` | Extract PDF from case page | `case_details_url` |
| GET | `/api/stats` | Get application statistics | None |

### Response Format
```json
{
  "success": true,
  "cached": false,
  "case_data": {
    "case_type": "CRL.A.",
    "case_number": "1626",
    "filing_year": 2025,
    "parties_names": "VINAY SHARMA VS. STATE GOVT. OF NCT OF DELHI",
    "filing_date": "01/08/2025",
    "status": "success"
  },
  "documents": [
    {
      "id": 1,
      "title": "Latest Order - CRL.A. 1626/2025",
      "url": "https://delhihighcourt.nic.in/app/showlogo/...",
      "type": "order",
      "date": "01/08/2025"
    }
  ]
}
```

## 🛡️ Rate Limiting & Security

### Implemented Rate Limiting
To protect the Delhi High Court servers and ensure responsible scraping:

```python
# Rate limiting configuration in config.py
RATE_LIMIT_REQUESTS = 30  # Maximum requests per window
RATE_LIMIT_WINDOW = 3600  # Time window in seconds (1 hour)
SCRAPING_TIMEOUT = 90     # Maximum time per request
MAX_RETRIES = 3           # Retry attempts on failure
```

### Security Features
- **Request Throttling**: Maximum 30 requests per hour per IP
- **Timeout Protection**: 90-second maximum per scraping operation
- **CSRF Token Validation**: Proper token handling for court website
- **User Agent Rotation**: Mimics legitimate browser requests
- **Session Management**: Maintains proper cookie states

### Best Practices Implemented
- Respectful crawling delays between requests
- Proper error handling to avoid server stress
- Caching to minimize redundant requests
- Graceful failure handling

## 🔧 Technical Implementation

### CAPTCHA Handling Deep Dive

The Delhi High Court CAPTCHA implementation is uniquely accessible:

```python
def _handle_captcha(self, page) -> Optional[str]:
    """Extract CAPTCHA directly from HTML - No image processing needed!"""
    try:
        # Wait for CAPTCHA to load
        captcha_span = page.wait_for_selector('span#captcha-code', timeout=10000)
        captcha_solution = captcha_span.text_content().strip()
        logger.info(f"CAPTCHA extracted: {captcha_solution}")
        
        # Get CSRF token for validation
        csrf_token = self._get_csrf_token(page)
        
        # Validate CAPTCHA via API call
        response = page.request.post(
            self.captcha_validate_url,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': '*/*',
                'Referer': self.case_status_url
            },
            data=f"_token={csrf_token}&captchaInput={captcha_solution}"
        )
        
        if response.ok and response.json().get("success"):
            return captcha_solution
            
    except Exception as e:
        logger.error(f"CAPTCHA handling failed: {str(e)}")
        return None
```

### Why This Approach Works
1. **No Image Recognition**: CAPTCHA text is in DOM, not rendered as image
2. **Consistent Pattern**: Always 4 digits, making validation predictable
3. **Server Validation**: Proper API call mimics browser behavior
4. **CSRF Compliance**: Includes required security tokens

### Document Extraction Process

```python
def _extract_direct_pdf_from_case_page(self, case_page_url: str) -> Optional[str]:
    """Navigate to case details and extract direct PDF URLs"""
    # 1. Load the case details page
    # 2. Wait for table to load completely  
    # 3. Find PDF links with 'showlogo' pattern
    # 4. Return first (latest) PDF URL
    
    pdf_selectors = [
        'table a[href*="showlogo"]',      # Primary PDF links
        'tbody a[href*="showlogo"]',      # Table body links
        'tr a[href*="showlogo"]',         # Table row links  
        'a[href*="showlogo"][href*=".pdf"]' # Explicit PDF links
    ]
```

### Database Schema

```sql
-- Case queries table
CREATE TABLE case_query (
    id INTEGER PRIMARY KEY,
    case_type VARCHAR(50) NOT NULL,
    case_number VARCHAR(20) NOT NULL,
    filing_year INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    parties_names TEXT,
    filing_date VARCHAR(20),
    next_hearing_date VARCHAR(20),
    query_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_response TEXT,
    error_message TEXT
);

-- Documents table
CREATE TABLE case_document (
    id INTEGER PRIMARY KEY,
    case_query_id INTEGER NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    document_title VARCHAR(200),
    pdf_url TEXT NOT NULL,
    document_date VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_query_id) REFERENCES case_query (id)
);
```


## 🔍 Troubleshooting

### Common Issues and Solutions

#### 1. CAPTCHA Validation Fails
```bash
# Check if CAPTCHA element exists
Error: CAPTCHA span not found

Solution:
- Verify Delhi HC website is accessible
- Check if site structure hasn't changed
- Increase timeout values in config
```

#### 2. Playwright Browser Issues
```bash
# Browser not found error
playwright install chromium
playwright install-deps
```

#### 3. Database Initialization Issues
```bash
# Reset database
rm court_data.db
python -c "from app import create_app; from database import db; app = create_app(); app.app_context().push(); db.create_all()"
```

#### 4. Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000
# Kill the process
kill -9 <PID>
```

### Performance Optimization

#### 1. Database Indexing
```sql
-- Add indexes for better performance
CREATE INDEX idx_case_lookup ON case_query(case_type, case_number, filing_year);
CREATE INDEX idx_query_timestamp ON case_query(query_timestamp);
```

#### 2. Caching Strategy
- SQLite caching for repeated queries
- 1-hour cache expiry for fresh data
- Background cache warming for popular cases

#### 3. Resource Management
```python
# Playwright resource cleanup
browser.close()  # Always close browsers
context.clear_cookies()  # Clear session data
```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use ESLint for JavaScript
- Add docstrings for all functions
- Include unit tests for new features

### Testing
```bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=. tests/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚖️ Legal Disclaimer

This tool is designed for educational and research purposes only. Users are responsible for:
- Complying with the Delhi High Court's Terms of Service
- Respecting rate limits and server resources
- Using scraped data appropriately and legally
- Ensuring compliance with applicable laws and regulations

## 📞 Support

- **Email**: sainudheen.dev@gmail.com

---

**Built with ❤️ for the legal tech community**

*Last updated: 10/08/2025*
