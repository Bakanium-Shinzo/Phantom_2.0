"""
FNB Phantom Banking - Configuration Management
Centralized configuration for different environments (development, production, testing)
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class"""

    # Database Configuration
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "phantom_banking.db")

    # API Configuration
    API_HOST = os.environ.get("API_HOST", "0.0.0.0")
    API_PORT = int(os.environ.get("API_PORT", 5000))
    API_DEBUG = os.environ.get("API_DEBUG", "True").lower() == "true"
    SECRET_KEY = os.environ.get("SECRET_KEY", "phantom-banking-secret-key-2025")

    # Streamlit Configuration
    STREAMLIT_HOST = os.environ.get("STREAMLIT_HOST", "0.0.0.0")
    STREAMLIT_PORT = int(os.environ.get("STREAMLIT_PORT", 8501))

    # Business Configuration
    BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "Kgalagadi General Store")
    BUSINESS_ID = os.environ.get("BUSINESS_ID", "kgalagadi_store")

    # Fee Structure (in BWP)
    FEE_STRUCTURE = {
        "phantom_wallet": 0.00,  # FREE - Our competitive advantage
        "orange_money": 2.50,  # Much lower than actual P92 fee
        "myzaka": 3.00,  # Much lower than actual P99 fee
        "ussd": 1.50,  # Standard USSD fee
        "qr_code": 0.00,  # FREE for QR payments
        "bank_transfer": 5.00,  # Standard bank transfer fee
        "eft": 5.00,  # Standard EFT fee
    }

    # Transaction Limits
    TRANSACTION_LIMITS = {
        "daily_limit": 10000.00,  # P10,000 daily limit
        "monthly_limit": 50000.00,  # P50,000 monthly limit
        "single_transaction": 5000.00,  # P5,000 per transaction
        "minimum_transaction": 1.00,  # P1 minimum
    }

    # Botswana Market Data
    MARKET_DATA = {
        "total_population": 2650000,
        "unbanked_population": 636000,
        "unbanked_percentage": 24,
        "mobile_money_users": 1800000,
        "mobile_money_adoption": 69.5,
        "annual_mobile_money_volume": 26500000000,  # P26.5 billion
        "orange_money_market_share": 53,
        "myzaka_market_share": 36,
        "median_age": 23.4,
    }

    # Integration URLs (for production)
    INTEGRATION_URLS = {
        "orange_money_api": os.environ.get(
            "ORANGE_MONEY_API", "https://api.orange.co.bw"
        ),
        "myzaka_api": os.environ.get("MYZAKA_API", "https://api.mascom.bw"),
        "bob_api": os.environ.get("BOB_API", "https://api.bankofbotswana.bw"),
        "ussd_gateway": os.environ.get("USSD_GATEWAY", "https://ussd.btc.bw"),
    }

    # API Keys (use environment variables in production)
    API_KEYS = {
        "orange_money": os.environ.get("ORANGE_MONEY_API_KEY", "demo_orange_key"),
        "myzaka": os.environ.get("MYZAKA_API_KEY", "demo_myzaka_key"),
        "ussd_gateway": os.environ.get("USSD_API_KEY", "demo_ussd_key"),
        "qr_service": os.environ.get("QR_API_KEY", "demo_qr_key"),
    }

    # Security Configuration
    SECURITY = {
        "jwt_secret": os.environ.get("JWT_SECRET", "phantom-jwt-secret-2025"),
        "jwt_expiry": timedelta(hours=24),
        "rate_limit": "100/hour",
        "encryption_key": os.environ.get("ENCRYPTION_KEY", "phantom-encryption-2025"),
    }

    # Logging Configuration
    LOGGING = {
        "level": os.environ.get("LOG_LEVEL", "INFO"),
        "file": os.environ.get("LOG_FILE", "phantom_banking.log"),
        "max_bytes": 10485760,  # 10MB
        "backup_count": 5,
    }


class DevelopmentConfig(Config):
    """Development environment configuration"""

    DEBUG = True
    TESTING = False

    # Use local SQLite for development
    DATABASE_PATH = "phantom_banking_dev.db"

    # Relaxed security for development
    API_DEBUG = True

    # Development-specific settings
    DEMO_MODE = True
    SEED_DEMO_DATA = True

    # Lower transaction limits for testing
    TRANSACTION_LIMITS = {
        "daily_limit": 1000.00,
        "monthly_limit": 5000.00,
        "single_transaction": 500.00,
        "minimum_transaction": 0.01,
    }


class ProductionConfig(Config):
    """Production environment configuration"""

    DEBUG = False
    TESTING = False

    # Use environment variables for production database
    DATABASE_PATH = os.environ.get("DATABASE_URL", "phantom_banking_prod.db")

    # Strict security for production
    API_DEBUG = False

    # Production-specific settings
    DEMO_MODE = False
    SEED_DEMO_DATA = False

    # Enhanced security
    SECURITY = {
        **Config.SECURITY,
        "rate_limit": "50/hour",  # Stricter rate limiting
        "require_https": True,
        "session_timeout": timedelta(minutes=30),
    }

    # Production logging
    LOGGING = {
        **Config.LOGGING,
        "level": "WARNING",
        "file": "/var/log/phantom_banking/app.log",
    }


class TestingConfig(Config):
    """Testing environment configuration"""

    DEBUG = True
    TESTING = True

    # Use in-memory database for testing
    DATABASE_PATH = ":memory:"

    # Testing-specific settings
    DEMO_MODE = True
    SEED_DEMO_DATA = True

    # Minimal transaction limits for testing
    TRANSACTION_LIMITS = {
        "daily_limit": 100.00,
        "monthly_limit": 500.00,
        "single_transaction": 50.00,
        "minimum_transaction": 0.01,
    }

    # Fast JWT expiry for testing
    SECURITY = {**Config.SECURITY, "jwt_expiry": timedelta(minutes=5)}


class HackathonConfig(DevelopmentConfig):
    """Special configuration for hackathon demo"""

    # Enhanced demo features
    DEMO_MODE = True
    SEED_DEMO_DATA = True
    SHOW_MARKET_DATA = True
    ENABLE_LIVE_DEMO = True

    # Hackathon-specific branding
    BUSINESS_NAME = "Kgalagadi General Store (Demo)"
    DEMO_MESSAGE = "FNB Botswana Hackathon 2025 - Banking the Unbanked"

    # Pre-populated demo scenarios
    DEMO_SCENARIOS = {
        "rural_store": {
            "business_name": "Kgalagadi General Store",
            "location": "Ghanzi, Botswana",
            "customers": 2456,
            "monthly_revenue": 12890.50,
        },
        "agricultural_payments": {
            "business_name": "Botswana Beef Exports",
            "farmers_served": 1200,
            "monthly_volume": 850000.00,
        },
        "youth_inclusion": {
            "target_age": "18-25",
            "wallet_adoption": "89%",
            "upgrade_rate": "15%",
        },
    }


# Configuration factory
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "hackathon": HackathonConfig,
    "default": HackathonConfig,  # Use hackathon config as default for demo
}


def get_config(env=None):
    """Get configuration for specified environment"""
    if env is None:
        env = os.environ.get("FLASK_ENV", "default")

    return config.get(env, config["default"])


# Current configuration
current_config = get_config()


# Utility functions
def is_development():
    """Check if running in development mode"""
    return current_config.DEBUG


def is_production():
    """Check if running in production mode"""
    return not current_config.DEBUG and not current_config.TESTING


def is_testing():
    """Check if running in testing mode"""
    return current_config.TESTING


def get_fee(channel):
    """Get transaction fee for specific channel"""
    return current_config.FEE_STRUCTURE.get(channel, 0.00)


def validate_transaction_amount(amount):
    """Validate transaction amount against limits"""
    limits = current_config.TRANSACTION_LIMITS

    if amount < limits["minimum_transaction"]:
        return False, f"Amount below minimum of P{limits['minimum_transaction']}"

    if amount > limits["single_transaction"]:
        return (
            False,
            f"Amount exceeds single transaction limit of P{limits['single_transaction']}",
        )

    return True, "Amount valid"


if __name__ == "__main__":
    # Test configuration
    print("🔧 FNB Phantom Banking - Configuration Test")
    print("=" * 50)

    config_env = get_config()
    print(f"Environment: {os.environ.get('FLASK_ENV', 'default')}")
    print(f"Debug Mode: {config_env.DEBUG}")
    print(f"Database Path: {config_env.DATABASE_PATH}")
    print(f"Business Name: {config_env.BUSINESS_NAME}")

    print("\n💰 Fee Structure:")
    for channel, fee in config_env.FEE_STRUCTURE.items():
        print(f"  {channel}: P{fee:.2f}")

    print("\n🎯 Market Data:")
    market = config_env.MARKET_DATA
    print(
        f"  Unbanked Population: {market['unbanked_population']:,} ({market['unbanked_percentage']}%)"
    )
    print(
        f"  Mobile Money Users: {market['mobile_money_users']:,} ({market['mobile_money_adoption']}%)"
    )

    print("\n✅ Configuration loaded successfully!")
