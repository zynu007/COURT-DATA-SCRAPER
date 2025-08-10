import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Application configuration class
    """
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///court_data.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-please-change-in-production')
    
    # Court scraping configuration
    COURT_BASE_URL = 'https://delhihighcourt.nic.in'
    SCRAPING_TIMEOUT = 90  # Increased timeout to 90 seconds for robustness
    
    # Rate limiting (to be respectful to court servers)
    REQUESTS_PER_MINUTE = 10
    
    # Development settings
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    @staticmethod
    def validate_config():
        """Validate that all required configuration is present"""
        required_vars = ['SECRET_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars and not Config.DEBUG:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
