import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'recoverai.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_SECURE = os.environ.get('APP_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')

    LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'openai')

    MAX_AUTOMATIC_ACTION_AMOUNT = int(os.environ.get('MAX_AUTOMATIC_ACTION_AMOUNT', 10000))
    MAX_AUTOMATIC_RETRY_COUNT = int(os.environ.get('MAX_AUTOMATIC_RETRY_COUNT', 1))

    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5000')
    BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:5000')

    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5000').split(',')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    MAX_CSV_SIZE = 10 * 1024 * 1024
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100
