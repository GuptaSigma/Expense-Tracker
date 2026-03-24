import os
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Load environment variables from .env file
_ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(_ROOT_DIR / '.env')
load_dotenv(find_dotenv(usecwd=True))


def _as_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _as_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _normalize_db_url(value):
    if not value:
        return None

    cleaned = value.strip().strip('"').strip("'")
    lowered = cleaned.lower()

    # Recover from accidental prefixes like "Value =postgresql://...".
    for prefix in ('postgresql://', 'postgres://', 'mysql+pymysql://', 'mysql://'):
        idx = lowered.find(prefix)
        if idx != -1:
            cleaned = cleaned[idx:]
            lowered = cleaned.lower()
            break

    if lowered.startswith('postgres://'):
        return cleaned.replace('postgres://', 'postgresql+psycopg2://', 1)
    if lowered.startswith('postgresql://'):
        return cleaned.replace('postgresql://', 'postgresql+psycopg2://', 1)
    return cleaned


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-me')

    _db_candidates = [
        os.getenv('NEON_DATABASE_URL'),
        os.getenv('POSTGRES_URL'),
        os.getenv('DATABASE_URL'),
        os.getenv('VALUE'),
        os.getenv('Value'),
    ]
    _db_url = next(
        (
            _normalize_db_url(value)
            for value in _db_candidates
            if value and _normalize_db_url(value).lower().startswith('postgresql+psycopg2://')
        ),
        None,
    )
    if not _db_url:
        _db_url = next(
            (
                _normalize_db_url(value)
                for value in _db_candidates
                if value and value.strip()
            ),
            None,
        )
    if not _db_url:
        raise RuntimeError(
            'No PostgreSQL database URL found. Set DATABASE_URL (preferred), '
            'or NEON_DATABASE_URL, or POSTGRES_URL.'
        )

    if _db_url.startswith('mysql://') or _db_url.startswith('mysql+pymysql://'):
        raise RuntimeError(
            'MySQL URL detected, but this app is configured for Neon PostgreSQL. '
            'Update DATABASE_URL to your Neon Postgres connection string.'
        )
    SQLALCHEMY_DATABASE_URI = _db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

    DEBUG = _as_bool('FLASK_DEBUG', False)
    AUTO_CREATE_TABLES = _as_bool('AUTO_CREATE_TABLES', False)
    RUN_MIGRATIONS = _as_bool('RUN_MIGRATIONS', False)

    # Cookie and CSRF security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _as_bool('SESSION_COOKIE_SECURE', not DEBUG)
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
    WTF_CSRF_TIME_LIMIT = None

    # Rate limit defaults
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '200 per day;50 per hour')

    # OpenRouter API Configuration - For AI Suggestions & Investment Advice
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')

    # MetalPriceAPI Configuration (primary for gold/silver rates)
    METALPRICEAPI_API_KEY = os.getenv('METALPRICEAPI_API_KEY')
    METALPRICEAPI_API_URL = os.getenv('METALPRICEAPI_API_URL', 'https://api.metalpriceapi.com/v1')

    # GoldAPI Configuration (fallback for gold/silver rates)
    GOLDAPI_API_KEY = os.getenv('GOLDAPI_API_KEY') or os.getenv('METALPRICE_API_KEY')
    GOLDAPI_API_URL = os.getenv('GOLDAPI_API_URL', 'https://www.goldapi.io/api')

    # Twelve Data Configuration (used for market watch / stock quotes)
    TWELVEDATA_API_KEY = os.getenv('TWELVEDATA_API_KEY')
    TWELVEDATA_API_URL = os.getenv('TWELVEDATA_API_URL', 'https://api.twelvedata.com')

    # CoinGecko Configuration (used for crypto prices)
    COINGECKO_API_URL = os.getenv('COINGECKO_API_URL', 'https://api.coingecko.com/api/v3')

    # Gemini API Configuration - For Chatbox
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = (os.getenv('GOOGLE_REDIRECT_URI') or '').strip() or None

    # Resend API Configuration (for OTP email delivery)
    RESEND_API_KEY = os.getenv('RESEND_API_KEY')
    RESEND_FROM_EMAIL = os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')
    RESEND_TIMEOUT = _as_int('RESEND_TIMEOUT', 15)
    
    # Google Apps Script Configuration (Alternative to Resend)
    APPS_SCRIPT_URL = os.getenv('APPS_SCRIPT_URL')
    
    # Flask-Mail Configuration (Gmail SMTP - Alternative method)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = _as_int('MAIL_PORT', 587)
    MAIL_USE_TLS = _as_bool('MAIL_USE_TLS', True)
    MAIL_USE_SSL = _as_bool('MAIL_USE_SSL', False)
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

    # OTP Settings
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    OTP_DEV_MODE = _as_bool('OTP_DEV_MODE', False)

    # Market Data Settings
    MARKET_UPDATE_INTERVAL = 30  # seconds
