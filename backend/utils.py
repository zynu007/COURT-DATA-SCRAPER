# utils.py - Utility functions for the Court Data Fetcher
import re
import os
from typing import Tuple
from datetime import datetime

def validate_case_input(case_type: str, case_number: str, filing_year: int) -> Tuple[bool, str]:
    """
    Validate case search input parameters
    
    Args:
        case_type: Type of case (e.g., "CWP", "RFA")
        case_number: Case number (numeric or alphanumeric)
        filing_year: Year when case was filed
    
    Returns:
        Tuple of (is_valid : bool, error_message: str)
    """
    
    # Validate case type
    if not case_type or len(case_type.strip()) < 2:
        return False, "Case type is required and must be at least 2 characters"
    
    if len(case_type) > 20:
        return False, "Case type cannot exceed 20 characters"
    
    # Validate case number
    if not case_number or len(case_number.strip()) < 1:
        return False, "Case number is required"
        
    if len(case_number) > 50:
        return False, "Case number cannot exceed 50 characters"
    
    # Case number should contain at least one digit
    if not re.search(r'\d', case_number):
        return False, "Case number must contain at least one digit"
    
    # Validate filing year
    current_year = datetime.now().year
    
    if not filing_year:
        return False, "Filing year is required"
    
    try:
        year = int(filing_year)
        if year < 1950:  # Reasonable lower bound
            return False, "Filing year cannot be before 1950"
        
        if year > current_year:
            return False, f"Filing year cannot be in the future (current year: {current_year})"
            
    except (ValueError, TypeError):
        return False, "Filing year must be a valid number"
    
    return True, ""

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file operations
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "document"
    
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized

def format_case_display(case_type: str, case_number: str, filing_year: int) -> str:
    """
    Format case information for display
    
    Args:
        case_type: Type of case
        case_number: Case number
        filing_year: Filing year
        
    Returns:
        Formatted case string
    """
    return f"{case_type} {case_number}/{filing_year}"

def extract_year_from_date(date_string: str) -> int:
    """
    Extract year from various date formats
    
    Args:
        date_string: Date in various formats
        
    Returns:
        Year as integer, or current year if extraction fails
    """
    if not date_string:
        return datetime.now().year
    
    # Try to extract 4-digit year
    year_match = re.search(r'\b(19|20)\d{2}\b', date_string)
    if year_match:
        return int(year_match.group())
    
    # Try to extract 2-digit year and convert
    year_match = re.search(r'\b(\d{2})\b', date_string)
    if year_match:
        year = int(year_match.group())
        # Assume 00-30 is 2000-2030, 31-99 is 1931-1999
        if year <= 30:
            return 2000 + year
        else:
            return 1900 + year
    
    return datetime.now().year

def is_valid_pdf_url(url: str) -> bool:
    """
    Check if URL appears to be a valid PDF link
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL appears to be a PDF link
    """
    if not url:
        return False
    
    # Check for PDF extension or PDF-related keywords
    pdf_indicators = ['.pdf', 'download', 'document', 'order', 'judgment']
    url_lower = url.lower()
    
    return any(indicator in url_lower for indicator in pdf_indicators)

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified length with ellipsis
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def parse_indian_date(date_string: str) -> str:
    """
    Parse and normalize Indian date formats
    
    Args:
        date_string: Date string in various Indian formats
        
    Returns:
        Normalized date string in DD-MM-YYYY format
    """
    if not date_string:
        return ""
    
    # Common Indian date patterns
    patterns = [
        r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})',  # DD-MM-YYYY or DD/MM/YYYY
        r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})',      # DD.MM.YYYY
        r'(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})',   # DD MM YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_string)
        if match:
            day, month, year = match.groups()
            
            # Convert 2-digit year to 4-digit
            if len(year) == 2:
                year_int = int(year)
                year = str(2000 + year_int if year_int <= 30 else 1900 + year_int)
            
            # Ensure day and month are 2 digits
            day = day.zfill(2)
            month = month.zfill(2)
            
            return f"{day}-{month}-{year}"
    
    return date_string  # Return original if no pattern matches

def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB, or 0 if file doesn't exist
    """
    try:
        if os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            return round(size_bytes / (1024 * 1024), 2)
    except Exception:
        pass
    
    return 0.0

def log_scraping_attempt(case_type: str, case_number: str, filing_year: int, 
                        success: bool, error_message: str = ""):
    """
    Log scraping attempts for monitoring and debugging
    
    Args:
        case_type: Type of case
        case_number: Case number
        filing_year: Filing year
        success: Whether scraping was successful
        error_message: Error message if failed
    """
    import logging
    logger = logging.getLogger(__name__)
    
    log_message = (f"Scraping attempt: {case_type} {case_number}/{filing_year} - "
                  f"{'SUCCESS' if success else 'FAILED'}")
    
    if not success and error_message:
        log_message += f" - {error_message}"
    
    if success:
        logger.info(log_message)
    else:
        logger.warning(log_message)

def clean_extracted_text(text: str) -> str:
    """
    Clean and normalize extracted text from web scraping
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text.
        
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters that might cause issues
    cleaned = re.sub(r'[^\w\s\-.,():/]', '', cleaned)
    
    # Remove duplicate punctuation
    cleaned = re.sub(r'([.,:])\1+', r'\1', cleaned)
    
    return cleaned

def generate_cache_key(case_type: str, case_number: str, filing_year: int) -> str:
    """
    Generate a cache key for storing scraped data
    
    Args:
        case_type: Type of case
        case_number: Case number
        filing_year: Filing year
        
    Returns:
        Cache key string
    """
    return f"case_{case_type}_{case_number}_{filing_year}".replace(' ', '_').lower()

# Constants for the application
SUPPORTED_CASE_TYPES = [
    'CWP',   # Civil Writ Petition
    'CrWP',  # Criminal Writ Petition
    'RFA',   # Regular First Appeal
    'CM(M)', # Civil Miscellaneous Main
    'CrA',   # Criminal Appeal
    'FAO',   # First Appeal from Order
    'CS',    # Civil Suit
    'CrR',   # Criminal Revision
]

FILE_TYPES = {
    'order': 'Order',
    'judgment': 'Judgment',
    'notice': 'Notice',
    'misc': 'Miscellaneous'
}

MAX_RETRY_ATTEMPTS = 5
DEFAULT_TIMEOUT = 120  # seconds
MAX_CACHE_AGE_HOURS = 24