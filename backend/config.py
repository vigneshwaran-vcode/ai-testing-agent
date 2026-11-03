import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-testing-agent-secret-2024')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'ai_testing.db'))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    SANDBOX_FOLDER = os.path.join(BASE_DIR, 'sandbox')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0

    # Provider API Keys (loaded from .env or set via Settings UI)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    CUSTOM_API_URL = os.environ.get('CUSTOM_API_URL', '')
    CUSTOM_API_KEY = os.environ.get('CUSTOM_API_KEY', '')

    # Test execution settings
    DEFAULT_TIMEOUT = int(os.environ.get('DEFAULT_TIMEOUT', '120'))
    CODE_SANDBOX_TIMEOUT = int(os.environ.get('CODE_SANDBOX_TIMEOUT', '10'))
    MAX_TEST_CASES = int(os.environ.get('MAX_TEST_CASES', '50'))

    # Reliability thresholds
    RELIABILITY_HIGH = 80
    RELIABILITY_MEDIUM = 50
