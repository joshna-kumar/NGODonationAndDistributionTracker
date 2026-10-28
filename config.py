import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ngo-ledger-super-secret-key-2026-lavender')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///ngo_tracker.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    BLOCKCHAIN_RPC_URL = os.environ.get('BLOCKCHAIN_RPC_URL', '')
    BLOCKCHAIN_PRIVATE_KEY = os.environ.get('BLOCKCHAIN_PRIVATE_KEY', '')
    BLOCKCHAIN_CONTRACT_ADDRESS = os.environ.get('BLOCKCHAIN_CONTRACT_ADDRESS', '')
    UPI_ID = os.environ.get('UPI_ID', 'ngo.support@upi')
    CASHFREE_APP_ID = os.environ.get('CASHFREE_APP_ID', '')
    CASHFREE_SECRET_KEY = os.environ.get('CASHFREE_SECRET_KEY', '')
    CASHFREE_ENVIRONMENT = os.environ.get('CASHFREE_ENVIRONMENT', 'sandbox').lower()
    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', '')
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
