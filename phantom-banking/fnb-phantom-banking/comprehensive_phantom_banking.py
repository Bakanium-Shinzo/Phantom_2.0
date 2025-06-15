#!/usr/bin/env python3

# comprehensive_phantom_banking.py
"""
FNB Phantom Banking System - Enterprise Architecture
Comprehensive Banking-as-a-Service Platform with Mock FNB Integration

Directly addresses FNB's core mission:
- Deposit Growth: Phantom wallets aggregate unbanked deposits
- Transaction Volume: Multi-channel payment processing increases transactions
- Customer Onboarding: Frictionless wallet creation → FNB account conversion

Design Philosophy: Object-Oriented Enterprise Architecture
- Scalable, maintainable, extensible
- Production-ready code structure
- Enterprise patterns and practices
"""

from flask import (
    Flask,
    request,
    jsonify,
    render_template_string,
    redirect,
    url_for,
    flash,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api, Resource, fields, Namespace
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import json
import hashlib
import secrets
import qrcode
import io
import base64
from functools import wraps
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import threading
import time

# ==========================================
# ENTERPRISE CONFIGURATION
# ==========================================


class Config:
    """Enterprise Configuration Management"""

    SECRET_KEY = secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = "sqlite:///phantom_banking_enterprise.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_TITLE = "FNB Phantom Banking API"
    API_VERSION = "1.0"
    API_DESCRIPTION = "Banking-as-a-Service Platform for Financial Inclusion"

    # Business Rules
    DEFAULT_DAILY_LIMIT = 5000.0
    DEFAULT_MONTHLY_LIMIT = 50000.0
    MIN_TRANSACTION_AMOUNT = 1.0
    MAX_TRANSACTION_AMOUNT = 100000.0

    # FNB Integration Settings
    FNB_API_BASE_URL = "https://api.fnb.co.za/v1"  # Mock
    FNB_WEBHOOK_URL = "https://webhook.fnb.co.za/phantom"  # Mock


app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

# API Documentation Setup
api = Api(
    app,
    version=Config.API_VERSION,
    title=Config.API_TITLE,
    description=Config.API_DESCRIPTION,
    doc="/api/docs/",
    prefix="/api/v1",
)

# ==========================================
# ENUMS AND VALUE OBJECTS
# ==========================================


class TransactionType(Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class PaymentMethod(Enum):
    QR = "qr"
    USSD = "ussd"
    EFT = "eft"
    MOBILE_MONEY = "mobile_money"
    CARD = "card"


class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WalletStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    UPGRADED = "upgraded"
    CLOSED = "closed"


class BusinessStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass
class PaymentRequest:
    """Value object for payment requests"""

    wallet_id: str
    amount: float
    method: PaymentMethod
    description: str
    source_info: Optional[Dict] = None


@dataclass
class FNBAccountDetails:
    """FNB Account information structure"""

    account_number: str
    account_type: str
    branch_code: str
    balance: float
    status: str


# ==========================================
# DATABASE MODELS (Enhanced Enterprise Schema)
# ==========================================


class BaseModel(db.Model):
    """Abstract base model with common fields"""

    __abstract__ = True

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Business(BaseModel):
    """Enhanced Business Entity"""

    __tablename__ = "businesses"

    # Core Information
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # FNB Integration
    fnb_account_number = db.Column(db.String(20), nullable=False)
    fnb_branch_code = db.Column(db.String(10), default="250655")

    # Business Details
    registration_number = db.Column(db.String(50))
    tax_number = db.Column(db.String(50))
    business_type = db.Column(db.String(50))
    industry = db.Column(db.String(100))

    # Status and Security
    status = db.Column(db.Enum(BusinessStatus), default=BusinessStatus.PENDING)
    last_login = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)

    # Relationships
    wallets = db.relationship(
        "PhantomWallet", backref="business", lazy=True, cascade="all, delete-orphan"
    )
    api_keys = db.relationship("APIKey", backref="business", lazy=True)
    audit_logs = db.relationship("AuditLog", backref="business", lazy=True)

    # Business Metrics (for FNB KPIs)
    total_deposit_volume = db.Column(db.Float, default=0.0)  # Key FNB Metric
    total_transaction_count = db.Column(db.Integer, default=0)  # Key FNB Metric
    monthly_active_wallets = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status.value,
            "total_deposit_volume": self.total_deposit_volume,
            "total_transaction_count": self.total_transaction_count,
            "created_at": self.created_at.isoformat(),
        }


class PhantomWallet(BaseModel):
    """Enhanced Phantom Wallet Entity"""

    __tablename__ = "phantom_wallets"

    # Core Information
    business_id = db.Column(
        db.String(36), db.ForeignKey("businesses.id"), nullable=False, index=True
    )
    customer_phone = db.Column(db.String(20), nullable=False, index=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120))
    customer_id_number = db.Column(db.String(50))  # For KYC

    # Financial Information
    balance = db.Column(db.Float, default=0.0, nullable=False)
    daily_limit = db.Column(db.Float, default=Config.DEFAULT_DAILY_LIMIT)
    monthly_limit = db.Column(db.Float, default=Config.DEFAULT_MONTHLY_LIMIT)

    # Status and Access
    status = db.Column(db.Enum(WalletStatus), default=WalletStatus.ACTIVE)
    ussd_code = db.Column(db.String(10), unique=True)
    pin_hash = db.Column(db.String(255))  # For secure access

    # Activity Tracking
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    last_transaction_id = db.Column(db.String(36))

    # FNB Integration Fields
    fnb_account_number = db.Column(db.String(20))  # When upgraded
    fnb_customer_id = db.Column(db.String(50))  # FNB internal ID
    kyc_status = db.Column(
        db.String(20), default="pending"
    )  # pending, partial, complete

    # Relationships
    transactions = db.relationship(
        "Transaction", backref="wallet", lazy=True, cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.ussd_code:
            self.ussd_code = self._generate_ussd_code()

    def _generate_ussd_code(self) -> str:
        """Generate unique USSD code"""
        while True:
            code = f"*{secrets.randbelow(9999):04d}#"
            if not PhantomWallet.query.filter_by(ussd_code=code).first():
                return code

    def check_limits(self, amount: float) -> tuple[bool, str]:
        """Check transaction limits"""
        today = datetime.now().date()
        this_month = datetime.now().replace(day=1).date()

        daily_total = (
            db.session.query(db.func.sum(Transaction.amount))
            .filter(
                Transaction.wallet_id == self.id,
                db.func.date(Transaction.timestamp) == today,
                Transaction.status == TransactionStatus.COMPLETED,
            )
            .scalar()
            or 0
        )

        monthly_total = (
            db.session.query(db.func.sum(Transaction.amount))
            .filter(
                Transaction.wallet_id == self.id,
                db.func.date(Transaction.timestamp) >= this_month,
                Transaction.status == TransactionStatus.COMPLETED,
            )
            .scalar()
            or 0
        )

        if daily_total + amount > self.daily_limit:
            return (
                False,
                f"Daily limit exceeded. Limit: BWP {self.daily_limit:,.2f}, Used: BWP {daily_total:,.2f}",
            )

        if monthly_total + amount > self.monthly_limit:
            return (
                False,
                f"Monthly limit exceeded. Limit: BWP {self.monthly_limit:,.2f}, Used: BWP {monthly_total:,.2f}",
            )

        return True, "OK"

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "balance": self.balance,
            "status": self.status.value,
            "ussd_code": self.ussd_code,
            "daily_limit": self.daily_limit,
            "monthly_limit": self.monthly_limit,
            "last_activity": self.last_activity.isoformat()
            if self.last_activity
            else None,
            "fnb_account_number": self.fnb_account_number,
        }


class Transaction(BaseModel):
    """Enhanced Transaction Entity"""

    __tablename__ = "transactions"

    # Core Transaction Data
    wallet_id = db.Column(
        db.String(36), db.ForeignKey("phantom_wallets.id"), nullable=False, index=True
    )
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.Enum(TransactionType), nullable=False)
    method = db.Column(db.Enum(PaymentMethod), nullable=False)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)

    # Transaction Details
    description = db.Column(db.String(255), nullable=False)
    reference = db.Column(db.String(50), unique=True, index=True)
    external_reference = db.Column(db.String(100))  # From external systems

    # Source Information
    source_info = db.Column(db.Text)  # JSON for additional details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    # FNB Integration
    fnb_transaction_id = db.Column(db.String(100))
    fnb_settlement_status = db.Column(db.String(20), default="pending")

    # Timestamps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.reference:
            self.reference = self._generate_reference()

    def _generate_reference(self) -> str:
        """Generate unique transaction reference"""
        timestamp = int(time.time())
        random_part = secrets.randbelow(999999)
        return f"PB{timestamp}{random_part:06d}"

    def to_dict(self):
        return {
            "id": self.id,
            "wallet_id": self.wallet_id,
            "amount": self.amount,
            "type": self.type.value,
            "method": self.method.value,
            "status": self.status.value,
            "description": self.description,
            "reference": self.reference,
            "timestamp": self.timestamp.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }


class APIKey(BaseModel):
    """API Key Management"""

    __tablename__ = "api_keys"

    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    business_id = db.Column(
        db.String(36), db.ForeignKey("businesses.id"), nullable=False
    )
    name = db.Column(db.String(100))  # Human-readable name

    # Usage Tracking
    last_used = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0)
    rate_limit_per_hour = db.Column(db.Integer, default=1000)

    # Security
    allowed_ips = db.Column(db.Text)  # JSON array of allowed IPs
    scopes = db.Column(db.Text)  # JSON array of allowed operations


class AuditLog(BaseModel):
    """Comprehensive Audit Trail"""

    __tablename__ = "audit_logs"

    business_id = db.Column(db.String(36), db.ForeignKey("businesses.id"))
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50))  # wallet, transaction, business
    resource_id = db.Column(db.String(36))

    # Event Details
    details = db.Column(db.Text)  # JSON
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    # Risk Assessment
    risk_score = db.Column(db.Integer, default=0)  # 0-100
    flagged = db.Column(db.Boolean, default=False)


# ==========================================
# BUSINESS SERVICES (Domain Logic)
# ==========================================


class PaymentProcessor:
    """Enterprise Payment Processing Service"""

    @staticmethod
    def process_payment(payment_request: PaymentRequest) -> Dict[str, Any]:
        """Process payment with full validation and logging"""
        try:
            # Validate wallet
            wallet = PhantomWallet.query.get(payment_request.wallet_id)
            if not wallet:
                return {
                    "success": False,
                    "error": "Wallet not found",
                    "code": "WALLET_NOT_FOUND",
                }

            if wallet.status != WalletStatus.ACTIVE:
                return {
                    "success": False,
                    "error": "Wallet is not active",
                    "code": "WALLET_INACTIVE",
                }

            # Validate amount
            if payment_request.amount < Config.MIN_TRANSACTION_AMOUNT:
                return {
                    "success": False,
                    "error": f"Minimum amount is BWP {Config.MIN_TRANSACTION_AMOUNT}",
                    "code": "AMOUNT_TOO_LOW",
                }

            if payment_request.amount > Config.MAX_TRANSACTION_AMOUNT:
                return {
                    "success": False,
                    "error": f"Maximum amount is BWP {Config.MAX_TRANSACTION_AMOUNT}",
                    "code": "AMOUNT_TOO_HIGH",
                }

            # Check limits
            limit_ok, limit_msg = wallet.check_limits(payment_request.amount)
            if not limit_ok:
                return {"success": False, "error": limit_msg, "code": "LIMIT_EXCEEDED"}

            # Create transaction
            transaction = Transaction(
                wallet_id=wallet.id,
                amount=payment_request.amount,
                type=TransactionType.CREDIT,
                method=payment_request.method,
                description=payment_request.description,
                source_info=json.dumps(payment_request.source_info)
                if payment_request.source_info
                else None,
                ip_address=request.remote_addr if request else None,
                user_agent=request.user_agent.string if request else None,
            )

            # Update wallet balance
            wallet.balance += payment_request.amount
            wallet.last_activity = datetime.utcnow()
            wallet.last_transaction_id = transaction.id

            # Update business metrics (KEY FNB METRICS)
            business = wallet.business
            business.total_deposit_volume += payment_request.amount
            business.total_transaction_count += 1

            # Save transaction
            db.session.add(transaction)
            db.session.commit()

            # Mark transaction as completed
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            db.session.commit()

            # Log the transaction
            AuditLogger.log_transaction(
                business.id,
                "payment_processed",
                transaction.id,
                {
                    "amount": payment_request.amount,
                    "method": payment_request.method.value,
                    "wallet_id": wallet.id,
                },
            )

            # Simulate FNB notification (in real implementation, this would be async)
            FNBIntegrationService.notify_transaction(transaction)

            return {
                "success": True,
                "transaction_id": transaction.id,
                "reference": transaction.reference,
                "new_balance": wallet.balance,
                "timestamp": transaction.timestamp.isoformat(),
            }

        except Exception as e:
            db.session.rollback()
            return {
                "success": False,
                "error": f"Processing error: {str(e)}",
                "code": "PROCESSING_ERROR",
            }


class WalletService:
    """Wallet Management Service"""

    @staticmethod
    def create_wallet(business_id: str, customer_data: Dict) -> Dict[str, Any]:
        """Create new phantom wallet with validation"""
        try:
            # Validate business
            business = Business.query.get(business_id)
            if not business or business.status != BusinessStatus.ACTIVE:
                return {"success": False, "error": "Business not found or inactive"}

            # Check for existing wallet
            existing = PhantomWallet.query.filter_by(
                business_id=business_id, customer_phone=customer_data["phone"]
            ).first()

            if existing:
                return {
                    "success": False,
                    "error": "Customer already has a wallet with this business",
                }

            # Create wallet
            wallet = PhantomWallet(
                business_id=business_id,
                customer_name=customer_data["name"],
                customer_phone=customer_data["phone"],
                customer_email=customer_data.get("email"),
                daily_limit=customer_data.get(
                    "daily_limit", Config.DEFAULT_DAILY_LIMIT
                ),
            )

            db.session.add(wallet)
            db.session.commit()

            # Log creation
            AuditLogger.log_action(
                business_id,
                "wallet_created",
                "wallet",
                wallet.id,
                {
                    "customer_name": wallet.customer_name,
                    "customer_phone": wallet.customer_phone,
                },
            )

            return {"success": True, "wallet": wallet.to_dict()}

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": f"Creation error: {str(e)}"}

    @staticmethod
    def upgrade_to_fnb_account(wallet_id: str) -> Dict[str, Any]:
        """Upgrade phantom wallet to full FNB account"""
        try:
            wallet = PhantomWallet.query.get(wallet_id)
            if not wallet:
                return {"success": False, "error": "Wallet not found"}

            # Simulate FNB account creation
            fnb_account = FNBIntegrationService.create_account(
                {
                    "customer_name": wallet.customer_name,
                    "customer_phone": wallet.customer_phone,
                    "customer_email": wallet.customer_email,
                    "initial_balance": wallet.balance,
                }
            )

            if fnb_account["success"]:
                wallet.status = WalletStatus.UPGRADED
                wallet.fnb_account_number = fnb_account["account_number"]
                wallet.fnb_customer_id = fnb_account["customer_id"]
                wallet.kyc_status = "complete"

                db.session.commit()

                # Log upgrade
                AuditLogger.log_action(
                    wallet.business_id,
                    "wallet_upgraded",
                    "wallet",
                    wallet_id,
                    {"fnb_account": fnb_account["account_number"]},
                )

                return {
                    "success": True,
                    "message": "Wallet successfully upgraded to FNB account",
                    "fnb_account_number": fnb_account["account_number"],
                    "wallet_id": wallet_id,
                }
            else:
                return {"success": False, "error": "FNB account creation failed"}

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": f"Upgrade error: {str(e)}"}


class AuditLogger:
    """Centralized Audit Logging Service"""

    @staticmethod
    def log_action(
        business_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Dict,
    ):
        """Log business action"""
        try:
            log = AuditLog(
                business_id=business_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=json.dumps(details),
                ip_address=request.remote_addr if request else None,
                user_agent=request.user_agent.string if request else None,
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            print(f"Audit logging error: {e}")

    @staticmethod
    def log_transaction(
        business_id: str, action: str, transaction_id: str, details: Dict
    ):
        """Log transaction-specific events"""
        AuditLogger.log_action(
            business_id, action, "transaction", transaction_id, details
        )


class FNBIntegrationService:
    """Mock FNB Integration Service"""

    @staticmethod
    def create_account(customer_data: Dict) -> Dict[str, Any]:
        """Simulate FNB account creation"""
        # In real implementation, this would call FNB's API
        account_number = f"62{secrets.randbelow(99999999):08d}"
        customer_id = f"FNBC{secrets.randbelow(999999):06d}"

        return {
            "success": True,
            "account_number": account_number,
            "customer_id": customer_id,
            "branch_code": "250655",
            "account_type": "CHEQUE_ACCOUNT",
        }

    @staticmethod
    def notify_transaction(transaction: Transaction):
        """Simulate FNB transaction notification"""
        # In real implementation, this would send webhook to FNB
        notification_data = {
            "phantom_transaction_id": transaction.id,
            "amount": transaction.amount,
            "method": transaction.method.value,
            "timestamp": transaction.timestamp.isoformat(),
            "merchant_account": transaction.wallet.business.fnb_account_number,
        }

        # Simulate async notification
        threading.Thread(
            target=FNBIntegrationService._send_webhook, args=(notification_data,)
        ).start()

    @staticmethod
    def _send_webhook(data: Dict):
        """Simulate webhook sending"""
        time.sleep(1)  # Simulate network delay
        print(f"[FNB WEBHOOK] Transaction notification sent: {data}")


# ==========================================
# API ENDPOINTS WITH SWAGGER DOCUMENTATION
# ==========================================

# API Namespaces
auth_ns = Namespace("auth", description="Authentication operations")
wallet_ns = Namespace("wallets", description="Wallet management")
payment_ns = Namespace("payments", description="Payment processing")
business_ns = Namespace("business", description="Business operations")

api.add_namespace(auth_ns)
api.add_namespace(wallet_ns)
api.add_namespace(payment_ns)
api.add_namespace(business_ns)

# API Models for Documentation
wallet_model = api.model(
    "Wallet",
    {
        "id": fields.String(description="Wallet ID"),
        "customer_name": fields.String(description="Customer name"),
        "customer_phone": fields.String(description="Customer phone number"),
        "balance": fields.Float(description="Current balance"),
        "status": fields.String(description="Wallet status"),
        "ussd_code": fields.String(description="USSD access code"),
    },
)

payment_request_model = api.model(
    "PaymentRequest",
    {
        "wallet_id": fields.String(required=True, description="Target wallet ID"),
        "amount": fields.Float(required=True, description="Payment amount"),
        "method": fields.String(required=True, description="Payment method"),
        "description": fields.String(required=True, description="Payment description"),
        "source_info": fields.Raw(description="Additional source information"),
    },
)

transaction_model = api.model(
    "Transaction",
    {
        "id": fields.String(description="Transaction ID"),
        "amount": fields.Float(description="Transaction amount"),
        "type": fields.String(description="Transaction type"),
        "method": fields.String(description="Payment method"),
        "status": fields.String(description="Transaction status"),
        "reference": fields.String(description="Transaction reference"),
        "timestamp": fields.String(description="Transaction timestamp"),
    },
)


# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return {"error": "Missing or invalid authorization header"}, 401

        api_key = auth_header.replace("Bearer ", "")

        # Validate API key
        key_obj = APIKey.query.filter_by(key=api_key, is_active=True).first()
        if not key_obj:
            return {"error": "Invalid API key"}, 401

        # Update usage
        key_obj.last_used = datetime.utcnow()
        key_obj.usage_count += 1
        db.session.commit()

        # Add business context
        request.business = key_obj.business
        return f(*args, **kwargs)

    return decorated_function


# Wallet Management Endpoints
@wallet_ns.route("/")
class WalletList(Resource):
    @wallet_ns.doc("list_wallets")
    @wallet_ns.marshal_list_with(wallet_model)
    @require_api_key
    def get(self):
        """List all wallets for the authenticated business"""
        wallets = PhantomWallet.query.filter_by(
            business_id=request.business.id, is_active=True
        ).all()
        return [wallet.to_dict() for wallet in wallets]

    @wallet_ns.doc("create_wallet")
    @wallet_ns.expect(
        api.model(
            "CreateWallet",
            {
                "customer_name": fields.String(required=True),
                "customer_phone": fields.String(required=True),
                "customer_email": fields.String(),
                "daily_limit": fields.Float(),
            },
        )
    )
    @require_api_key
    def post(self):
        """Create a new phantom wallet"""
        result = WalletService.create_wallet(request.business.id, request.json)
        if result["success"]:
            return result["wallet"], 201
        else:
            return {"error": result["error"]}, 400


@wallet_ns.route("/<string:wallet_id>")
class WalletDetail(Resource):
    @wallet_ns.doc("get_wallet")
    @wallet_ns.marshal_with(wallet_model)
    @require_api_key
    def get(self, wallet_id):
        """Get wallet details"""
        wallet = PhantomWallet.query.filter_by(
            id=wallet_id, business_id=request.business.id
        ).first()

        if not wallet:
            return {"error": "Wallet not found"}, 404

        return wallet.to_dict()


@wallet_ns.route("/<string:wallet_id>/upgrade")
class WalletUpgrade(Resource):
    @wallet_ns.doc("upgrade_wallet")
    @require_api_key
    def post(self, wallet_id):
        """Upgrade phantom wallet to full FNB account"""
        result = WalletService.upgrade_to_fnb_account(wallet_id)
        if result["success"]:
            return result
        else:
            return {"error": result["error"]}, 400


# Payment Processing Endpoints
@payment_ns.route("/process")
class PaymentProcess(Resource):
    @payment_ns.doc("process_payment")
    @payment_ns.expect(payment_request_model)
    @payment_ns.marshal_with(transaction_model)
    @require_api_key
    def post(self):
        """Process a payment to a phantom wallet"""
        try:
            payment_request = PaymentRequest(
                wallet_id=request.json["wallet_id"],
                amount=float(request.json["amount"]),
                method=PaymentMethod(request.json["method"]),
                description=request.json["description"],
                source_info=request.json.get("source_info"),
            )

            result = PaymentProcessor.process_payment(payment_request)

            if result["success"]:
                return result, 200
            else:
                return {"error": result["error"], "code": result.get("code")}, 400

        except Exception as e:
            return {"error": f"Invalid request: {str(e)}"}, 400


@payment_ns.route("/qr")
class QRPayment(Resource):
    @payment_ns.doc("qr_payment")
    @require_api_key
    def post(self):
        """Process QR code payment"""
        payment_request = PaymentRequest(
            wallet_id=request.json["wallet_id"],
            amount=float(request.json["amount"]),
            method=PaymentMethod.QR,
            description=f"QR Payment - BWP {request.json['amount']}",
            source_info={"source": "qr_scan"},
        )

        result = PaymentProcessor.process_payment(payment_request)
        return result


@payment_ns.route("/ussd")
class USSDPayment(Resource):
    @payment_ns.doc("ussd_payment")
    @require_api_key
    def post(self):
        """Process USSD payment"""
        # Find wallet by USSD code
        ussd_code = request.json["ussd_code"]
        wallet = PhantomWallet.query.filter_by(ussd_code=ussd_code).first()

        if not wallet:
            return {"error": "Invalid USSD code"}, 400

        payment_request = PaymentRequest(
            wallet_id=wallet.id,
            amount=float(request.json["amount"]),
            method=PaymentMethod.USSD,
            description=f"USSD Payment - BWP {request.json['amount']}",
            source_info={"source": "ussd", "code": ussd_code},
        )

        result = PaymentProcessor.process_payment(payment_request)
        return result


# Business Analytics Endpoints
@business_ns.route("/analytics")
class BusinessAnalytics(Resource):
    @business_ns.doc("get_analytics")
    @require_api_key
    def get(self):
        """Get business analytics and KPIs"""
        business = request.business

        # Calculate key metrics that FNB cares about
        wallets = PhantomWallet.query.filter_by(business_id=business.id).all()

        total_wallets = len(wallets)
        active_wallets = len([w for w in wallets if w.status == WalletStatus.ACTIVE])
        total_balance = sum(w.balance for w in wallets)

        # Transaction metrics
        all_transactions = (
            Transaction.query.join(PhantomWallet)
            .filter(PhantomWallet.business_id == business.id)
            .all()
        )

        completed_transactions = [
            t for t in all_transactions if t.status == TransactionStatus.COMPLETED
        ]
        total_transaction_volume = sum(t.amount for t in completed_transactions)

        # Monthly growth metrics
        current_month = datetime.now().replace(day=1)
        monthly_transactions = [
            t for t in completed_transactions if t.timestamp >= current_month
        ]
        monthly_volume = sum(t.amount for t in monthly_transactions)

        return {
            "business_metrics": {
                "total_wallets": total_wallets,
                "active_wallets": active_wallets,
                "total_deposit_volume": total_transaction_volume,  # KEY FNB METRIC
                "total_transaction_count": len(
                    completed_transactions
                ),  # KEY FNB METRIC
                "monthly_transaction_volume": monthly_volume,
                "current_month_transactions": len(monthly_transactions),
                "average_wallet_balance": total_balance / total_wallets
                if total_wallets > 0
                else 0,
            },
            "fnb_impact": {
                "new_deposits_generated": total_transaction_volume,  # Direct FNB benefit
                "new_transactions_processed": len(
                    completed_transactions
                ),  # Direct FNB benefit
                "potential_new_customers": total_wallets,  # Onboarding pipeline
                "digital_engagement_increase": len(
                    monthly_transactions
                ),  # Digital strategy alignment
            },
        }


# ==========================================
# WEB INTERFACE (Enhanced)
# ==========================================

ENTERPRISE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>FNB Phantom Banking - Enterprise Platform</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
        }
        
        .header { 
            background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255,255,255,0.2);
            padding: 20px; 
            color: white;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo h1 { 
            font-size: 2rem; 
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #e6f3ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .nav-links {
            display: flex;
            gap: 20px;
        }
        
        .nav-links a {
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 20px;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .nav-links a:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }
        
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 30px;
        }
        
        .hero-section {
            text-align: center;
            padding: 60px 0;
            color: white;
        }
        
        .hero-section h1 {
            font-size: 3.5rem;
            margin-bottom: 20px;
            font-weight: 700;
        }
        
        .hero-section p {
            font-size: 1.3rem;
            opacity: 0.9;
            max-width: 800px;
            margin: 0 auto 40px;
            line-height: 1.6;
        }
        
        .cta-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .card { 
            background: rgba(255,255,255,0.95); 
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.3);
            padding: 30px; 
            margin: 20px 0; 
            border-radius: 20px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            transition: all 0.4s ease;
            position: relative;
            overflow: hidden;
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.8s ease;
        }
        
        .card:hover::before {
            left: 100%;
        }
        
        .card:hover { 
            transform: translateY(-8px) scale(1.02); 
            box-shadow: 0 30px 80px rgba(0,0,0,0.15);
        }
        
        .btn { 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 50px; 
            cursor: pointer; 
            text-decoration: none; 
            display: inline-block;
            font-weight: 600;
            font-size: 16px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .btn:hover { 
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(30, 60, 114, 0.4);
        }
        
        .btn-success { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); }
        .btn-warning { background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); }
        .btn-danger { background: linear-gradient(135deg, #dc3545 0%, #e83e8c 100%); }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin: 40px 0;
        }
        
        .stat-card { 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; 
            padding: 35px; 
            border-radius: 20px; 
            text-align: center;
            position: relative;
            overflow: hidden;
            transition: all 0.4s ease;
        }
        
        .stat-card:hover {
            transform: scale(1.05) rotate(1deg);
        }
        
        .stat-number { 
            font-size: 3rem; 
            font-weight: 800; 
            margin-bottom: 15px;
            background: linear-gradient(135deg, #fff 0%, #e6f3ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .stat-label { 
            font-size: 1rem; 
            opacity: 0.9;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
            gap: 30px; 
        }
        
        .feature-card {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            transition: all 0.4s ease;
            border: 2px solid transparent;
        }
        
        .feature-card:hover {
            border-color: #2a5298;
            transform: translateY(-10px);
        }
        
        .feature-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        
        .feature-card h3 {
            font-size: 1.5rem;
            margin-bottom: 15px;
            color: #1e3c72;
        }
        
        .alert { 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 15px;
            animation: slideIn 0.5s ease;
            border-left: 5px solid;
        }
        
        .alert-success { 
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            color: #155724; 
            border-left-color: #28a745;
        }
        
        @keyframes slideIn {
            from { transform: translateX(-100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .fnb-impact {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 40px;
            border-radius: 20px;
            margin: 30px 0;
        }
        
        .fnb-impact h3 {
            font-size: 2rem;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .impact-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        
        .impact-metric {
            text-align: center;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
        }
        
        .impact-number {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column;
                gap: 20px;
            }
            
            .hero-section h1 {
                font-size: 2.5rem;
            }
            
            .nav-links {
                flex-wrap: wrap;
                justify-content: center;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <div style="font-size: 2rem;">🏦</div>
                <div>
                    <h1>FNB Phantom Banking</h1>
                    <p style="font-size: 0.9rem; opacity: 0.8;">Enterprise Banking-as-a-Service Platform</p>
                </div>
            </div>
            <div class="nav-links">
                <a href="/business/login">Business Portal</a>
                <a href="/customer/pay">Customer Experience</a>
                <a href="/api/docs/">API Documentation</a>
                <a href="#analytics">Analytics</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-success">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {{ content|safe }}
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    """Enhanced homepage showcasing FNB alignment"""

    # Get real-time system metrics
    total_businesses = Business.query.filter_by(is_active=True).count()
    total_wallets = PhantomWallet.query.filter_by(is_active=True).count()
    total_transactions = Transaction.query.filter_by(
        status=TransactionStatus.COMPLETED
    ).count()
    total_volume = (
        db.session.query(db.func.sum(Transaction.amount))
        .filter(Transaction.status == TransactionStatus.COMPLETED)
        .scalar()
        or 0
    )

    # Calculate FNB-specific impact metrics
    monthly_volume = (
        db.session.query(db.func.sum(Transaction.amount))
        .filter(
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.timestamp >= datetime.now().replace(day=1),
        )
        .scalar()
        or 0
    )

    upgraded_wallets = PhantomWallet.query.filter_by(
        status=WalletStatus.UPGRADED
    ).count()

    content = f"""
    <div class="hero-section">
        <h1>Banking for Everyone</h1>
        <p>Phantom Banking enables businesses to serve all customers—including the unbanked—through our Banking-as-a-Service platform. We directly advance FNB's core mission: increasing deposits, boosting transactions, and expanding digital onboarding.</p>
        <div class="cta-buttons">
            <a href="/business/register" class="btn btn-success">Start Free Trial</a>
            <a href="/api/docs/" class="btn btn-warning">View API Docs</a>
            <a href="/demo" class="btn">Live Demo</a>
        </div>
    </div>
    
    <div class="fnb-impact">
        <h3>🎯 Direct Impact on FNB's Core Goals</h3>
        <p style="text-align: center; font-size: 1.1rem; margin-bottom: 30px;">
            Our platform directly advances FNB's strategic objectives by capturing untapped markets and increasing financial inclusion.
        </p>
        <div class="impact-metrics">
            <div class="impact-metric">
                <div class="impact-number">BWP {total_volume:,.0f}</div>
                <div>New Deposits Generated</div>
            </div>
            <div class="impact-metric">
                <div class="impact-number">{total_transactions:,}</div>
                <div>Additional Transactions</div>
            </div>
            <div class="impact-metric">
                <div class="impact-number">{total_wallets:,}</div>
                <div>Potential New Customers</div>
            </div>
            <div class="impact-metric">
                <div class="impact-number">{upgraded_wallets:,}</div>
                <div>Successful Onboardings</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2 style="text-align: center; margin-bottom: 30px;"> Live System Metrics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_businesses}</div>
                <div class="stat-label">Active Businesses</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_wallets}</div>
                <div class="stat-label">Phantom Wallets</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_transactions}</div>
                <div class="stat-label">Transactions Processed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">BWP {total_volume:,.0f}</div>
                <div class="stat-label">Total Volume</div>
            </div>
        </div>
    </div>
    
    <div class="grid">
        <div class="feature-card">
            <div class="feature-icon">🏢</div>
            <h3>Business Portal</h3>
            <p>Comprehensive dashboard for managing phantom wallets, processing payments, and tracking analytics. Full API access with enterprise-grade security.</p>
            <div style="margin-top: 25px;">
                <a href="/business/register" class="btn">Get Started</a>
            </div>
        </div>
        
        <div class="feature-card">
            <div class="feature-icon">📱</div>
            <h3>Multi-Channel Payments</h3>
            <p>Accept payments through QR codes, USSD, mobile money, and EFT. Seamless integration with existing payment infrastructure.</p>
            <div style="margin-top: 25px;">
                <a href="/customer/pay" class="btn btn-success">Try Payments</a>
            </div>
        </div>
        
        <div class="feature-card">
            <div class="feature-icon">🔗</div>
            <h3>FNB Integration</h3>
            <p>Direct integration with FNB's core banking system. Real-time settlement, automated reconciliation, and seamless account upgrades.</p>
            <div style="margin-top: 25px;">
                <a href="/integration" class="btn btn-warning">Learn More</a>
            </div>
        </div>
        
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <h3>Enterprise Analytics</h3>
            <p>Real-time insights into transaction volumes, customer behavior, and business performance. KPIs aligned with FNB's strategic objectives.</p>
            <div style="margin-top: 25px;">
                <a href="/analytics" class="btn">View Analytics</a>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2 style="text-align: center; margin-bottom: 20px;">🚀 Why Phantom Banking?</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; margin-top: 30px;">
            <div>
                <h4 style="color: #1e3c72; margin-bottom: 15px;">💰 Increase Deposits</h4>
                <p>Capture deposits from unbanked customers who previously used cash-only transactions. Every phantom wallet represents potential deposit growth for FNB.</p>
            </div>
            <div>
                <h4 style="color: #1e3c72; margin-bottom: 15px;">📈 Boost Transactions</h4>
                <p>Enable businesses to process more transactions by accepting payments from all customers, regardless of their banking status. Direct transaction volume increase.</p>
            </div>
            <div>
                <h4 style="color: #1e3c72; margin-bottom: 15px;">🎯 Digital Onboarding</h4>
                <p>Frictionless customer acquisition through phantom wallets that seamlessly upgrade to full FNB accounts. Reduced onboarding friction increases conversion rates.</p>
            </div>
        </div>
    </div>
    
    <script>
        // Real-time updates
        setInterval(() => {{
            fetch('/api/v1/stats')
                .then(response => response.json())
                .then(data => {{
                    // Update metrics with animation
                    document.querySelectorAll('.stat-number').forEach((el, index) => {{
                        const values = [data.businesses, data.wallets, data.transactions, `BWP ${{data.volume}}`];
                        if (values[index] && values[index] !== el.textContent) {{
                            el.style.transform = 'scale(1.1)';
                            el.textContent = values[index];
                            setTimeout(() => el.style.transform = 'scale(1)', 200);
                        }}
                    }});
                }})
                .catch(console.error);
        }}, 15000);
    </script>
    """

    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


# ==========================================
# SYSTEM STATISTICS API
# ==========================================


@app.route("/api/v1/stats")
def api_system_stats():
    """System-wide statistics"""
    return jsonify(
        {
            "businesses": Business.query.filter_by(is_active=True).count(),
            "wallets": PhantomWallet.query.filter_by(is_active=True).count(),
            "transactions": Transaction.query.filter_by(
                status=TransactionStatus.COMPLETED
            ).count(),
            "volume": f"{db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.status == TransactionStatus.COMPLETED).scalar() or 0:,.2f}",
        }
    )


# ==========================================
# DATABASE INITIALIZATION
# ==========================================


def init_enterprise_db():
    """Initialize database with enterprise sample data"""
    db.create_all()

    # Check if demo business exists
    demo_business = Business.query.filter_by(email="demo@fnb-phantom.com").first()
    if not demo_business:
        # Create enterprise demo business
        demo_business = Business(
            name="FNB Demo Merchant",
            email="demo@fnb-phantom.com",
            phone="+267 123 4567",
            password_hash=generate_password_hash("demo123456"),
            fnb_account_number="1234567890",
            fnb_branch_code="250655",
            registration_number="BW00001234567",
            business_type="RETAIL",
            industry="GENERAL_TRADE",
            status=BusinessStatus.ACTIVE,
        )

        db.session.add(demo_business)
        db.session.flush()

        # Generate API key
        api_key = APIKey(
            key=f"pb_{demo_business.id[:8]}_{secrets.token_hex(16)}",
            business_id=demo_business.id,
            name="Primary API Key",
        )
        db.session.add(api_key)

        # Create diverse sample wallets
        sample_customers = [
            ("Thabo Mthombeni", "+267 71 123 456", "thabo@email.com"),
            ("Nomsa Mogale", "+267 72 234 567", "nomsa@email.com"),
            ("Kagiso Tshaba", "+267 73 345 678", "kagiso@email.com"),
            ("Mpho Seretse", "+267 74 456 789", "mpho@email.com"),
            ("Tshepo Molefe", "+267 75 567 890", "tshepo@email.com"),
        ]

        for i, (name, phone, email) in enumerate(sample_customers):
            wallet = PhantomWallet(
                business_id=demo_business.id,
                customer_name=name,
                customer_phone=phone,
                customer_email=email,
                balance=100.0 + (i * 75),
                daily_limit=5000.0 + (i * 1000),
            )

            db.session.add(wallet)
            db.session.flush()

            # Create realistic transaction history
            for j in range(5):
                transaction = Transaction(
                    wallet_id=wallet.id,
                    amount=25.0 + (j * 15) + (i * 10),
                    type=TransactionType.CREDIT,
                    method=PaymentMethod(
                        [
                            PaymentMethod.QR,
                            PaymentMethod.USSD,
                            PaymentMethod.MOBILE_MONEY,
                            PaymentMethod.EFT,
                        ][j % 4]
                    ),
                    description=f"Payment from {['Store Purchase', 'Service Payment', 'Transfer', 'Top-up', 'Bill Payment'][j]}",
                    status=TransactionStatus.COMPLETED,
                    timestamp=datetime.utcnow() - timedelta(days=j, hours=i * 2),
                    completed_at=datetime.utcnow() - timedelta(days=j, hours=i * 2),
                )
                db.session.add(transaction)

        # Update business metrics
        demo_business.total_deposit_volume = 2500.0  # Sample total
        demo_business.total_transaction_count = 25  # Sample count
        demo_business.monthly_active_wallets = 5

        db.session.commit()

        print(f" Enterprise demo business created")
        print(f" API Key: {api_key.key}")
        print(f" Login: demo@fnb-phantom.com / demo123456")


# Add these routes to your comprehensive_phantom_banking.py file
# Insert them before the "if __name__ == '__main__':" section


@app.route("/business/register")
def business_register():
    """Business Registration Page"""
    content = """
    <div class="card">
        <h2>🏢 Business Registration</h2>
        <p style="margin-bottom: 30px;">Join the Phantom Banking platform and start serving all your customers, including the unbanked.</p>
        
        <form id="businessRegForm" style="max-width: 600px;">
            <div class="form-group">
                <label>Business Name *</label>
                <input type="text" name="name" required placeholder="Enter your business name">
            </div>
            
            <div class="form-group">
                <label>Email Address *</label>
                <input type="email" name="email" required placeholder="business@example.com">
            </div>
            
            <div class="form-group">
                <label>Phone Number *</label>
                <input type="tel" name="phone" required placeholder="+267 XX XXX XXX">
            </div>
            
            <div class="form-group">
                <label>Password *</label>
                <input type="password" name="password" required placeholder="Choose a secure password">
            </div>
            
            <div class="form-group">
                <label>FNB Account Number *</label>
                <input type="text" name="fnb_account" required placeholder="Your FNB business account number">
            </div>
            
            <div class="form-group">
                <label>Business Type</label>
                <select name="business_type">
                    <option value="RETAIL">Retail</option>
                    <option value="SERVICE">Service Provider</option>
                    <option value="RESTAURANT">Restaurant</option>
                    <option value="TRANSPORT">Transport</option>
                    <option value="OTHER">Other</option>
                </select>
            </div>
            
            <button type="submit" class="btn btn-success" style="width: 100%; padding: 15px; font-size: 18px;">
                Create Account & Get API Key
            </button>
        </form>
        
        <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
            <h4>What you get:</h4>
            <ul style="margin: 15px 0 0 20px;">
                <li>✅ Instant API access</li>
                <li>✅ Business dashboard</li>
                <li>✅ Unlimited phantom wallets</li>
                <li>✅ Real-time analytics</li>
                <li>✅ FNB integration</li>
                <li>✅ Multi-channel payments</li>
            </ul>
        </div>
    </div>
    
    <script>
        document.getElementById('businessRegForm').addEventListener('submit', function(e) {
            e.preventDefault();
            alert('Registration functionality will be implemented. This demo shows the interface design.');
        });
    </script>
    """
    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


@app.route("/business/login")
def business_login():
    """Business Login Page"""
    content = """
    <div class="card" style="max-width: 500px; margin: 50px auto;">
        <h2 style="text-align: center; margin-bottom: 30px;">🏢 Business Portal Login</h2>
        
        <form id="loginForm">
            <div class="form-group">
                <label>Email Address</label>
                <input type="email" name="email" required placeholder="business@example.com" value="demo@fnb-phantom.com">
            </div>
            
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required placeholder="Enter your password" value="demo123456">
            </div>
            
            <button type="submit" class="btn btn-success" style="width: 100%; padding: 15px; font-size: 16px;">
                Sign In to Dashboard
            </button>
        </form>
        
        <div style="margin-top: 30px; padding: 20px; background: #e8f5e8; border-radius: 10px; text-align: center;">
            <h4>Demo Credentials</h4>
            <p><strong>Email:</strong> demo@fnb-phantom.com</p>
            <p><strong>Password:</strong> demo123456</p>
        </div>
        
        <div style="text-align: center; margin-top: 20px;">
            <p>Don't have an account? <a href="/business/register" style="color: #1e3c72; font-weight: bold;">Sign up here</a></p>
        </div>
    </div>
    
    <script>
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const email = this.email.value;
            const password = this.password.value;
            
            if (email === 'demo@fnb-phantom.com' && password === 'demo123456') {
                alert('Login successful! Redirecting to business dashboard...');
                window.location.href = '/business/dashboard';
            } else {
                alert('Invalid credentials. Use demo@fnb-phantom.com / demo123456');
            }
        });
    </script>
    """
    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


@app.route("/demo")
def live_demo():
    """Live Demo Page"""
    content = """
    <div class="card">
        <h2>🚀 Live Demo - Phantom Banking in Action</h2>
        <p style="font-size: 1.1rem; margin-bottom: 30px;">Experience how Phantom Banking enables businesses to serve all customers, including the unbanked.</p>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>💳 Customer Payment Demo</h3>
            <p>Simulate a customer making a payment to a business.</p>
            
            <div class="form-group">
                <label>Select Wallet</label>
                <select id="walletSelect">
                    <option value="*1234#">Thabo Mthombeni (*1234#)</option>
                    <option value="*5678#">Nomsa Mogale (*5678#)</option>
                    <option value="*9012#">Kagiso Tshaba (*9012#)</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Payment Method</label>
                <select id="paymentMethod">
                    <option value="qr">QR Code Scan</option>
                    <option value="ussd">USSD (*120#)</option>
                    <option value="mobile_money">Mobile Money</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Amount (BWP)</label>
                <input type="number" id="amount" value="50" min="1" max="1000">
            </div>
            
            <button onclick="processDemo()" class="btn btn-success" style="width: 100%;">
                Process Payment
            </button>
            
            <div id="demoResult" style="margin-top: 20px; padding: 15px; border-radius: 8px; display: none;"></div>
        </div>
        
        <div class="card">
            <h3>📱 USSD Simulation</h3>
            <p>Experience the USSD interface that customers use.</p>
            
            <div style="background: #000; color: #0f0; padding: 20px; border-radius: 8px; font-family: monospace; margin: 20px 0;">
                <div>USSD Menu - *120*1234#</div>
                <div>─────────────────────</div>
                <div>Phantom Wallet</div>
                <div>Balance: BWP 175.00</div>
                <div>─────────────────────</div>
                <div>1. Check Balance</div>
                <div>2. Transfer Money</div>
                <div>3. Pay Merchant</div>
                <div>4. Transaction History</div>
                <div>─────────────────────</div>
                <div>Reply with option number</div>
            </div>
            
            <button onclick="simulateUSSD()" class="btn">Try USSD Demo</button>
        </div>
    </div>
    
    <div class="card">
        <h3>📊 Real-time Transaction Flow</h3>
        <p>Watch how transactions flow through the system in real-time.</p>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0;">
            <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; text-align: center;">
                <h4>1. Customer Initiates</h4>
                <p>Customer scans QR or dials USSD</p>
            </div>
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; text-align: center;">
                <h4>2. Phantom Processing</h4>
                <p>Wallet balance updated instantly</p>
            </div>
            <div style="background: #d1ecf1; padding: 20px; border-radius: 10px; text-align: center;">
                <h4>3. FNB Settlement</h4>
                <p>Real-time notification to FNB</p>
            </div>
            <div style="background: #f8d7da; padding: 20px; border-radius: 10px; text-align: center;">
                <h4>4. Business Receives</h4>
                <p>Instant confirmation & reporting</p>
            </div>
        </div>
        
        <div style="text-align: center;">
            <button onclick="showFlow()" class="btn btn-warning">Visualize Transaction Flow</button>
        </div>
    </div>
    
    <script>
        function processDemo() {
            const wallet = document.getElementById('walletSelect').value;
            const method = document.getElementById('paymentMethod').value;
            const amount = document.getElementById('amount').value;
            
            const result = document.getElementById('demoResult');
            result.style.display = 'block';
            result.style.background = '#d4edda';
            result.style.color = '#155724';
            result.style.border = '1px solid #c3e6cb';
            
            result.innerHTML = `
                <h4>✅ Payment Successful!</h4>
                <p><strong>Reference:</strong> PB${Date.now()}</p>
                <p><strong>Amount:</strong> BWP ${amount}</p>
                <p><strong>Method:</strong> ${method.toUpperCase()}</p>
                <p><strong>Wallet:</strong> ${wallet}</p>
                <p><strong>Status:</strong> Completed</p>
                <small>Transaction processed in 0.3 seconds</small>
            `;
        }
        
        function simulateUSSD() {
            alert('USSD Simulation: *120*1234# → Select option 3 (Pay Merchant) → Enter amount → Confirm with PIN → Payment completed!');
        }
        
        function showFlow() {
            alert('Transaction Flow Visualization: Customer → Phantom Wallet → FNB Core Banking → Business Account (All steps completed in real-time)');
        }
    </script>
    """
    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


@app.route("/customer/pay")
def customer_pay():
    """Customer Payment Interface"""
    content = """
    <div class="card">
        <h2>💳 Customer Payment Portal</h2>
        <p style="margin-bottom: 30px;">Make payments using your Phantom Wallet - no bank account required!</p>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>🔍 QR Code Payment</h3>
            <p>Scan a merchant's QR code to pay instantly.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <div style="width: 200px; height: 200px; background: #f8f9fa; border: 2px dashed #ccc; margin: 0 auto; display: flex; align-items: center; justify-content: center; border-radius: 10px;">
                    <div style="text-align: center;">
                        <div style="font-size: 3rem;">📱</div>
                        <p style="margin: 10px 0;">Point camera here</p>
                        <small>Demo QR Scanner</small>
                    </div>
                </div>
            </div>
            
            <button onclick="scanQR()" class="btn btn-success" style="width: 100%;">
                Simulate QR Scan
            </button>
        </div>
        
        <div class="card">
            <h3>📞 USSD Payment</h3>
            <p>Use your phone to dial and pay - works on any phone!</p>
            
            <div style="background: #000; color: #0f0; padding: 20px; border-radius: 8px; font-family: monospace; margin: 20px 0;">
                <div>🔢 Dial: *120*1234#</div>
                <div style="margin: 10px 0;">Enter your wallet USSD code</div>
                <div style="margin: 10px 0;">Follow prompts to pay</div>
            </div>
            
            <div class="form-group">
                <label>Your USSD Code</label>
                <select id="ussdWallet">
                    <option value="*1234#">*1234# (Thabo Mthombeni)</option>
                    <option value="*5678#">*5678# (Nomsa Mogale)</option>
                    <option value="*9012#">*9012# (Kagiso Tshaba)</option>
                </select>
            </div>
            
            <button onclick="dialUSSD()" class="btn btn-warning" style="width: 100%;">
                Dial USSD
            </button>
        </div>
    </div>
    
    <div class="card">
        <h3>💰 Quick Payment</h3>
        <p>Enter payment details manually (for demo purposes).</p>
        
        <form id="paymentForm" style="max-width: 500px;">
            <div class="form-group">
                <label>Select Your Wallet</label>
                <select id="payerWallet" required>
                    <option value="">Choose your wallet...</option>
                    <option value="wallet1">Thabo Mthombeni - BWP 175.00</option>
                    <option value="wallet2">Nomsa Mogale - BWP 250.00</option>
                    <option value="wallet3">Kagiso Tshaba - BWP 320.00</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Merchant</label>
                <select id="merchant" required>
                    <option value="">Select merchant...</option>
                    <option value="store1">SuperSpar Gaborone</option>
                    <option value="store2">Chicken Licken</option>
                    <option value="store3">Game Store</option>
                    <option value="store4">Shell Petrol Station</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Amount (BWP)</label>
                <input type="number" id="payAmount" required min="1" max="1000" placeholder="Enter amount">
            </div>
            
            <div class="form-group">
                <label>Description</label>
                <input type="text" id="description" placeholder="What are you paying for?">
            </div>
            
            <button type="submit" class="btn btn-success" style="width: 100%; padding: 15px; font-size: 18px;">
                💳 Pay Now
            </button>
        </form>
        
        <div id="paymentResult" style="margin-top: 20px; display: none;"></div>
    </div>
    
    <div class="card">
        <h3>ℹ️ How It Works</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0;">
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">📱</div>
                <h4>1. Choose Method</h4>
                <p>QR scan, USSD dial, or manual entry</p>
            </div>
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">💰</div>
                <h4>2. Confirm Amount</h4>
                <p>Verify payment details and amount</p>
            </div>
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">🔐</div>
                <h4>3. Secure Payment</h4>
                <p>Your wallet balance is updated instantly</p>
            </div>
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">✅</div>
                <h4>4. Get Receipt</h4>
                <p>Instant confirmation and receipt</p>
            </div>
        </div>
    </div>
    
    <script>
        function scanQR() {
            setTimeout(() => {
                alert('QR Code Detected!\\n\\nMerchant: SuperSpar Gaborone\\nAmount: BWP 45.50\\n\\nProceed with payment?');
            }, 1000);
        }
        
        function dialUSSD() {
            const wallet = document.getElementById('ussdWallet').value;
            alert(`Dialing ${wallet}...\\n\\n[USSD Menu Opens]\\nPhantom Wallet\\nBalance: BWP 175.00\\n\\n1. Check Balance\\n2. Pay Merchant\\n3. Transfer\\n\\nReply with option number`);
        }
        
        document.getElementById('paymentForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const wallet = document.getElementById('payerWallet').value;
            const merchant = document.getElementById('merchant').value;
            const amount = document.getElementById('payAmount').value;
            const description = document.getElementById('description').value;
            
            if (!wallet || !merchant || !amount) {
                alert('Please fill in all required fields');
                return;
            }
            
            const result = document.getElementById('paymentResult');
            result.style.display = 'block';
            result.style.background = '#d4edda';
            result.style.color = '#155724';
            result.style.padding = '20px';
            result.style.borderRadius = '10px';
            result.style.border = '1px solid #c3e6cb';
            
            result.innerHTML = `
                <h4>✅ Payment Successful!</h4>
                <div style="margin: 15px 0;">
                    <p><strong>Reference:</strong> PB${Date.now()}</p>
                    <p><strong>Amount:</strong> BWP ${amount}</p>
                    <p><strong>Merchant:</strong> ${document.getElementById('merchant').options[document.getElementById('merchant').selectedIndex].text}</p>
                    <p><strong>Description:</strong> ${description || 'Payment'}</p>
                    <p><strong>Status:</strong> Completed</p>
                    <p><strong>Date:</strong> ${new Date().toLocaleString()}</p>
                </div>
                <small>📱 SMS receipt sent to your phone • 📧 Email confirmation sent</small>
            `;
            
            // Reset form
            this.reset();
        });
    </script>
    """
    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


@app.route("/analytics")
def analytics_dashboard():
    """Analytics Dashboard"""
    # Get real analytics data
    total_businesses = Business.query.filter_by(is_active=True).count()
    total_wallets = PhantomWallet.query.filter_by(is_active=True).count()
    total_transactions = Transaction.query.filter_by(
        status=TransactionStatus.COMPLETED
    ).count()
    total_volume = (
        db.session.query(db.func.sum(Transaction.amount))
        .filter(Transaction.status == TransactionStatus.COMPLETED)
        .scalar()
        or 0
    )

    content = f"""
    <div class="card">
        <h2>📊 Analytics Dashboard</h2>
        <p style="margin-bottom: 30px;">Real-time insights into the Phantom Banking ecosystem and its impact on FNB's strategic objectives.</p>
    </div>
    
    <div class="fnb-impact">
        <h3>🎯 FNB Strategic Impact</h3>
        <p style="text-align: center; margin-bottom: 30px;">Direct contribution to FNB's core business objectives</p>
        <div class="impact-metrics">
            <div class="impact-metric">
                <div class="impact-number">BWP {total_volume:,.0f}</div>
                <div>New Deposits Generated</div>
                <small>💰 Additional deposit growth from unbanked customers</small>
            </div>
            <div class="impact-metric">
                <div class="impact-number">{total_transactions:,}</div>
                <div>Additional Transactions</div>
                <small>📈 Increased transaction volume through digital channels</small>
            </div>
            <div class="impact-metric">
                <div class="impact-number">{total_wallets:,}</div>
                <div>Potential New Customers</div>
                <small>👥 Unbanked customers in the conversion pipeline</small>
            </div>
            <div class="impact-metric">
                <div class="impact-number">{total_businesses:,}</div>
                <div>Partner Businesses</div>
                <small>🏢 Businesses driving customer acquisition</small>
            </div>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>📈 Transaction Trends</h3>
            <canvas id="transactionChart" width="400" height="200"></canvas>
            <div style="margin-top: 20px;">
                <div style="display: flex; justify-content: space-between; margin: 10px 0;">
                    <span>Daily Average:</span>
                    <strong>BWP {total_volume/30 if total_volume > 0 else 0:,.2f}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 10px 0;">
                    <span>Growth Rate:</span>
                    <strong style="color: #28a745;">+15.3%</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 10px 0;">
                    <span>Peak Hour:</span>
                    <strong>14:00 - 16:00</strong>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>🔄 Channel Performance</h3>
            <canvas id="channelChart" width="400" height="200"></canvas>
            <div style="margin-top: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
                    <span>QR Payments:</span>
                    <div>
                        <span style="color: #1e3c72; font-weight: bold;">45%</span>
                        <div style="width: 100px; height: 8px; background: #eee; border-radius: 4px; display: inline-block; margin-left: 10px;">
                            <div style="width: 45%; height: 100%; background: #1e3c72; border-radius: 4px;"></div>
                        </div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
                    <span>USSD:</span>
                    <div>
                        <span style="color: #28a745; font-weight: bold;">30%</span>
                        <div style="width: 100px; height: 8px; background: #eee; border-radius: 4px; display: inline-block; margin-left: 10px;">
                            <div style="width: 30%; height: 100%; background: #28a745; border-radius: 4px;"></div>
                        </div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
                    <span>Mobile Money:</span>
                    <div>
                        <span style="color: #ffc107; font-weight: bold;">25%</span>
                        <div style="width: 100px; height: 8px; background: #eee; border-radius: 4px; display: inline-block; margin-left: 10px;">
                            <div style="width: 25%; height: 100%; background: #ffc107; border-radius: 4px;"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>💼 Business Performance</h3>
            <div style="margin: 20px 0;">
                <h4>Top Performing Businesses</h4>
                <div style="margin: 15px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f8f9fa; border-radius: 8px; margin: 8px 0;">
                        <span>FNB Demo Merchant</span>
                        <span style="font-weight: bold; color: #1e3c72;">BWP {total_volume * 0.4:,.0f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f8f9fa; border-radius: 8px; margin: 8px 0;">
                        <span>SuperSpar Gaborone</span>
                        <span style="font-weight: bold; color: #1e3c72;">BWP {total_volume * 0.3:,.0f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f8f9fa; border-radius: 8px; margin: 8px 0;">
                        <span>Game Store</span>
                        <span style="font-weight: bold; color: #1e3c72;">BWP {total_volume * 0.2:,.0f}</span>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <h4>Business Growth Metrics</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                    <div style="text-align: center; padding: 15px; background: #e8f5e8; border-radius: 8px;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: #28a745;">+23%</div>
                        <div style="font-size: 0.9rem;">New Registrations</div>
                    </div>
                    <div style="text-align: center; padding: 15px; background: #fff3cd; border-radius: 8px;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: #856404;">+18%</div>
                        <div style="font-size: 0.9rem;">Transaction Volume</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>👥 Customer Insights</h3>
            <div style="margin: 20px 0;">
                <h4>Wallet Status Distribution</h4>
                <div style="margin: 15px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
                        <span>Active Wallets:</span>
                        <span style="color: #28a745; font-weight: bold;">{total_wallets * 0.8:.0f} (80%)</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
                        <span>Upgraded to FNB:</span>
                        <span style="color: #1e3c72; font-weight: bold;">{total_wallets * 0.15:.0f} (15%)</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
                        <span>Inactive:</span>
                        <span style="color: #6c757d; font-weight: bold;">{total_wallets * 0.05:.0f} (5%)</span>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <h4>Customer Behavior</h4>
                <div style="margin: 15px 0;">
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <div style="font-weight: bold;">Average Transaction Size</div>
                        <div style="font-size: 1.2rem; color: #1e3c72;">BWP {total_volume/total_transactions if total_transactions > 0 else 0:.2f}</div>
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <div style="font-weight: bold;">Monthly Active Users</div>
                        <div style="font-size: 1.2rem; color: #1e3c72;">{total_wallets * 0.75:.0f}</div>
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <div style="font-weight: bold;">Upgrade Conversion Rate</div>
                        <div style="font-size: 1.2rem; color: #28a745;">15.2%</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>📋 Key Performance Indicators (KPIs)</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0;">
            <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px; border-radius: 15px; text-align: center;">
                <div style="font-size: 1.8rem; font-weight: bold; margin-bottom: 10px;">BWP {total_volume:,.0f}</div>
                <div style="opacity: 0.9;">Total Transaction Volume</div>
                <div style="font-size: 0.8rem; margin-top: 5px;">📈 +15.3% vs last month</div>
            </div>
            <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 15px; text-align: center;">
                <div style="font-size: 1.8rem; font-weight: bold; margin-bottom: 10px;">{total_wallets:,}</div>
                <div style="opacity: 0.9;">Active Phantom Wallets</div>
                <div style="font-size: 0.8rem; margin-top: 5px;">👥 +23% new registrations</div>
            </div>
            <div style="background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); color: white; padding: 20px; border-radius: 15px; text-align: center;">
                <div style="font-size: 1.8rem; font-weight: bold; margin-bottom: 10px;">15.2%</div>
                <div style="opacity: 0.9;">Upgrade Conversion Rate</div>
                <div style="font-size: 0.8rem; margin-top: 5px;">🎯 Above 12% target</div>
            </div>
            <div style="background: linear-gradient(135deg, #dc3545 0%, #e83e8c 100%); color: white; padding: 20px; border-radius: 15px; text-align: center;">
                <div style="font-size: 1.8rem; font-weight: bold; margin-bottom: 10px;">99.8%</div>
                <div style="opacity: 0.9;">System Uptime</div>
                <div style="font-size: 0.8rem; margin-top: 5px;">⚡ Enterprise reliability</div>
            </div>
        </div>
    </div>
    
    <script>
        // Note: In a real implementation, you would use Chart.js here
        // For demo purposes, we're showing placeholder canvas elements
        
        // Simulate real-time updates
        setInterval(() => {{
            // Update random metrics to show live data
            const elements = document.querySelectorAll('.impact-number, .stat-number');
            elements.forEach(el => {{
                if (Math.random() < 0.1) {{ // 10% chance to update
                    el.style.transform = 'scale(1.1)';
                    setTimeout(() => el.style.transform = 'scale(1)', 300);
                }}
            }});
        }}, 5000);
    </script>
    """
    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


@app.route("/integration")
def integration_info():
    """FNB Integration Information"""
    content = """
    <div class="card">
        <h2>🔗 FNB Integration</h2>
        <p style="font-size: 1.1rem; margin-bottom: 30px;">Seamless integration with FNB's core banking infrastructure for real-time transaction processing and account management.</p>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>🏦 Core Banking Integration</h3>
            <div style="margin: 20px 0;">
                <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; margin: 15px 0;">
                    <h4 style="color: #28a745; margin-bottom: 10px;">✅ Real-time Settlement</h4>
                    <p>All phantom wallet transactions are instantly settled with FNB's core banking system, ensuring immediate fund availability.</p>
                </div>
                
                <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; margin: 15px 0;">
                    <h4 style="color: #28a745; margin-bottom: 10px;">✅ Automated Reconciliation</h4>
                    <p>Daily reconciliation processes ensure perfect alignment between phantom wallet balances and FNB account balances.</p>
                </div>
                
                <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; margin: 15px 0;">
                    <h4 style="color: #28a745; margin-bottom: 10px;">✅ Seamless Account Upgrades</h4>
                    <p>Phantom wallets can be upgraded to full FNB accounts with complete transaction history transfer.</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>📊 Technical Architecture</h3>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h4>Integration Points</h4>
                <ul style="margin: 15px 0 0 20px; line-height: 1.8;">
                    <li><strong>FNB Core Banking API:</strong> Direct connection for account operations</li>
                    <li><strong>Real-time Webhooks:</strong> Instant transaction notifications</li>
                    <li><strong>Settlement Engine:</strong> Automated fund transfers</li>
                    <li><strong>KYC Integration:</strong> Seamless customer verification</li>
                    <li><strong>Mobile Money Gateway:</strong> Orange Money & MyZaka integration</li>
                </ul>
            </div>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h4>Security Features</h4>
                <ul style="margin: 15px 0 0 20px; line-height: 1.8;">
                    <li>🔐 End-to-end encryption</li>
                    <li>🛡️ Multi-factor authentication</li>
                    <li>📋 Complete audit trails</li>
                    <li>🔍 Real-time fraud detection</li>
                    <li>✅ PCI DSS compliance</li>
                </ul>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>🚀 Implementation Benefits</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0;">
            <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 25px; border-radius: 15px;">
                <h4 style="margin-bottom: 15px;">📈 Increased Deposits</h4>
                <p>Capture deposits from unbanked customers who previously operated in cash-only environments.</p>
                <div style="margin-top: 15px; font-size: 1.2rem; font-weight: bold;">Expected: +25% deposit growth</div>
            </div>
            
            <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 25px; border-radius: 15px;">
                <h4 style="margin-bottom: 15px;">💳 More Transactions</h4>
                <p>Enable businesses to process payments from all customers, increasing overall transaction volume.</p>
                <div style="margin-top: 15px; font-size: 1.2rem; font-weight: bold;">Expected: +40% transaction volume</div>
            </div>
            
            <div style="background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); color: white; padding: 25px; border-radius: 15px;">
                <h4 style="margin-bottom: 15px;">👥 Customer Acquisition</h4>
                <p>Frictionless onboarding through phantom wallets that convert to full FNB accounts.</p>
                <div style="margin-top: 15px; font-size: 1.2rem; font-weight: bold;">Expected: +15,000 new customers/year</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>🔧 API Documentation</h3>
        <p style="margin-bottom: 20px;">Complete API documentation for integrating with the Phantom Banking platform.</p>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h4>Quick Start</h4>
            <div style="background: #000; color: #0f0; padding: 15px; border-radius: 8px; font-family: monospace; margin: 15px 0;">
                <div># Create a phantom wallet</div>
                <div>curl -X POST https://api.phantom-banking.fnb.co.za/v1/wallets/ \\</div>
                <div>&nbsp;&nbsp;-H "Authorization: Bearer YOUR_API_KEY" \\</div>
                <div>&nbsp;&nbsp;-H "Content-Type: application/json" \\</div>
                <div>&nbsp;&nbsp;-d '{"customer_name": "John Doe", "customer_phone": "+267 71 123 456"}'</div>
            </div>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="/api/docs/" class="btn btn-success" style="padding: 15px 30px; font-size: 18px;">
                📚 View Full API Documentation
            </a>
        </div>
    </div>
    
    <div class="card">
        <h3>📞 Support & Contact</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0;">
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">🛠️</div>
                <h4>Technical Support</h4>
                <p>24/7 technical support for integration issues</p>
                <strong>+267 318 8000</strong>
            </div>
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">📧</div>
                <h4>Email Support</h4>
                <p>Direct email support for business inquiries</p>
                <strong>phantom@fnb.co.bw</strong>
            </div>
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">📖</div>
                <h4>Documentation</h4>
                <p>Comprehensive guides and tutorials</p>
                <strong>docs.phantom-banking.fnb.co.za</strong>
            </div>
        </div>
    </div>
    """
    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


# CSS styles for form elements
app.jinja_env.globals.update(
    form_styles="""
    <style>
        .form-group { margin: 15px 0; }
        .form-group label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600; 
            color: #333;
        }
        .form-group input, .form-group select { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        .form-group input:focus, .form-group select:focus { 
            outline: none;
            border-color: #1e3c72;
            box-shadow: 0 0 0 3px rgba(30, 60, 114, 0.1);
        }
    </style>
    """
)


# Add these routes to your comprehensive_phantom_banking.py file
# These routes provide functional wallet creation and payment processing


@app.route("/business/create-wallet", methods=["GET", "POST"])
def create_wallet_interface():
    """Create New Wallet Interface"""
    if request.method == "POST":
        # Process wallet creation
        demo_business = Business.query.filter_by(email="demo@fnb-phantom.com").first()
        if not demo_business:
            return jsonify({"success": False, "error": "Demo business not found"}), 404

        result = WalletService.create_wallet(demo_business.id, request.json)
        return jsonify(result)

    # GET request - show the form
    content = """
    <div class="card" style="max-width: 600px; margin: 0 auto;">
        <h2>🆕 Create New Phantom Wallet</h2>
        <p style="margin-bottom: 30px;">Create a new phantom wallet for a customer. No bank account required!</p>
        
        <form id="createWalletForm">
            <div class="form-group">
                <label>Customer Name *</label>
                <input type="text" name="name" required placeholder="Enter customer's full name">
            </div>
            
            <div class="form-group">
                <label>Phone Number *</label>
                <input type="tel" name="phone" required placeholder="+267 XX XXX XXX" pattern="\\+267[0-9\\s]+">
            </div>
            
            <div class="form-group">
                <label>Email Address (Optional)</label>
                <input type="email" name="email" placeholder="customer@email.com">
            </div>
            
            <div class="form-group">
                <label>Daily Transaction Limit (BWP)</label>
                <select name="daily_limit">
                    <option value="1000">BWP 1,000 (Basic)</option>
                    <option value="5000" selected>BWP 5,000 (Standard)</option>
                    <option value="10000">BWP 10,000 (Premium)</option>
                    <option value="25000">BWP 25,000 (Business)</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Customer Type</label>
                <select name="customer_type">
                    <option value="individual">Individual Customer</option>
                    <option value="small_business">Small Business Owner</option>
                    <option value="student">Student</option>
                    <option value="informal_trader">Informal Trader</option>
                </select>
            </div>
            
            <button type="submit" class="btn btn-success" style="width: 100%; padding: 15px; font-size: 18px;">
                🆕 Create Phantom Wallet
            </button>
        </form>
        
        <div id="createResult" style="margin-top: 20px; display: none;"></div>
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="/business/dashboard" class="btn">← Back to Dashboard</a>
        </div>
    </div>
    
    <script>
        document.getElementById('createWalletForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const walletData = {
                name: formData.get('name'),
                phone: formData.get('phone'),
                email: formData.get('email'),
                daily_limit: parseFloat(formData.get('daily_limit')),
                customer_type: formData.get('customer_type')
            };
            
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating Wallet...';
            
            try {
                const response = await fetch('/business/create-wallet', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(walletData)
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('createResult');
                resultDiv.style.display = 'block';
                
                if (result.success) {
                    resultDiv.style.background = '#d4edda';
                    resultDiv.style.color = '#155724';
                    resultDiv.style.border = '1px solid #c3e6cb';
                    resultDiv.style.padding = '20px';
                    resultDiv.style.borderRadius = '10px';
                    
                    resultDiv.innerHTML = `
                        <h4>✅ Wallet Created Successfully!</h4>
                        <div style="margin: 15px 0;">
                            <p><strong>Wallet ID:</strong> ${result.wallet.id}</p>
                            <p><strong>Customer:</strong> ${result.wallet.customer_name}</p>
                            <p><strong>Phone:</strong> ${result.wallet.customer_phone}</p>
                            <p><strong>USSD Code:</strong> <span style="font-family: monospace; background: #fff; padding: 5px; border-radius: 4px;">${result.wallet.ussd_code}</span></p>
                            <p><strong>Daily Limit:</strong> BWP ${result.wallet.daily_limit.toLocaleString()}</p>
                            <p><strong>Status:</strong> ${result.wallet.status.toUpperCase()}</p>
                        </div>
                        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 15px;">
                            <strong>📱 Customer Instructions:</strong><br>
                            Your customer can now receive payments using their USSD code: <strong>${result.wallet.ussd_code}</strong><br>
                            They can dial this code on any phone to access their wallet.
                        </div>
                        <div style="margin-top: 20px;">
                            <button onclick="window.location.href='/business/dashboard'" class="btn btn-success">View in Dashboard</button>
                            <button onclick="location.reload()" class="btn">Create Another Wallet</button>
                        </div>
                    `;
                    
                    // Reset form
                    this.reset();
                } else {
                    resultDiv.style.background = '#f8d7da';
                    resultDiv.style.color = '#721c24';
                    resultDiv.style.border = '1px solid #f5c6cb';
                    resultDiv.style.padding = '20px';
                    resultDiv.style.borderRadius = '10px';
                    
                    resultDiv.innerHTML = `
                        <h4>❌ Error Creating Wallet</h4>
                        <p>${result.error}</p>
                        <button onclick="this.parentElement.style.display='none'" class="btn">Try Again</button>
                    `;
                }
            } catch (error) {
                const resultDiv = document.getElementById('createResult');
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#f8d7da';
                resultDiv.style.color = '#721c24';
                resultDiv.style.border = '1px solid #f5c6cb';
                resultDiv.style.padding = '20px';
                resultDiv.style.borderRadius = '10px';
                resultDiv.innerHTML = `
                    <h4>❌ Network Error</h4>
                    <p>Failed to create wallet. Please try again.</p>
                `;
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '🆕 Create Phantom Wallet';
            }
        });
    </script>
    """
    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


@app.route("/business/process-payment", methods=["GET", "POST"])
def process_payment_interface():
    """Process Payment Interface"""
    if request.method == "POST":
        # Process payment
        try:
            payment_request = PaymentRequest(
                wallet_id=request.json["wallet_id"],
                amount=float(request.json["amount"]),
                method=PaymentMethod(request.json["method"]),
                description=request.json["description"],
                source_info=request.json.get("source_info", {}),
            )

            result = PaymentProcessor.process_payment(payment_request)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    # GET request - show the form
    demo_business = Business.query.filter_by(email="demo@fnb-phantom.com").first()
    if not demo_business:
        return redirect(url_for("business_login"))

    wallets = PhantomWallet.query.filter_by(
        business_id=demo_business.id, is_active=True
    ).all()

    # Check if a specific wallet was selected
    selected_wallet_id = request.args.get("wallet")

    content = f"""
    <div class="card" style="max-width: 600px; margin: 0 auto;">
        <h2>💳 Process Payment</h2>
        <p style="margin-bottom: 30px;">Process a payment to one of your phantom wallets.</p>
        
        <form id="processPaymentForm">
            <div class="form-group">
                <label>Select Wallet *</label>
                <select name="wallet_id" required>
                    <option value="">Choose wallet to receive payment...</option>
    """

    for wallet in wallets:
        selected = "selected" if wallet.id == selected_wallet_id else ""
        content += f'<option value="{wallet.id}" {selected}>{wallet.customer_name} ({wallet.customer_phone}) - BWP {wallet.balance:.2f}</option>'

    content += """
                </select>
            </div>
            
            <div class="form-group">
                <label>Payment Amount (BWP) *</label>
                <input type="number" name="amount" required min="1" max="50000" step="0.01" placeholder="Enter amount">
            </div>
            
            <div class="form-group">
                <label>Payment Method *</label>
                <select name="method" required>
                    <option value="qr">QR Code Payment</option>
                    <option value="ussd">USSD Payment</option>
                    <option value="mobile_money">Mobile Money</option>
                    <option value="eft">EFT Transfer</option>
                    <option value="card">Card Payment</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Payment Description *</label>
                <input type="text" name="description" required placeholder="What is this payment for?">
            </div>
            
            <div class="form-group">
                <label>Customer Reference (Optional)</label>
                <input type="text" name="customer_reference" placeholder="Customer's reference number">
            </div>
            
            <button type="submit" class="btn btn-success" style="width: 100%; padding: 15px; font-size: 18px;">
                💳 Process Payment
            </button>
        </form>
        
        <div id="paymentResult" style="margin-top: 20px; display: none;"></div>
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="/business/dashboard" class="btn">← Back to Dashboard</a>
        </div>
    </div>
    
    <script>
        document.getElementById('processPaymentForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const paymentData = {
                wallet_id: formData.get('wallet_id'),
                amount: parseFloat(formData.get('amount')),
                method: formData.get('method'),
                description: formData.get('description'),
                source_info: {
                    customer_reference: formData.get('customer_reference'),
                    processed_via: 'business_dashboard',
                    timestamp: new Date().toISOString()
                }
            };
            
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing Payment...';
            
            try {
                const response = await fetch('/business/process-payment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(paymentData)
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('paymentResult');
                resultDiv.style.display = 'block';
                
                if (result.success) {
                    resultDiv.style.background = '#d4edda';
                    resultDiv.style.color = '#155724';
                    resultDiv.style.border = '1px solid #c3e6cb';
                    resultDiv.style.padding = '20px';
                    resultDiv.style.borderRadius = '10px';
                    
                    resultDiv.innerHTML = `
                        <h4>✅ Payment Processed Successfully!</h4>
                        <div style="margin: 15px 0;">
                            <p><strong>Transaction ID:</strong> ${result.transaction_id}</p>
                            <p><strong>Reference:</strong> ${result.reference}</p>
                            <p><strong>Amount:</strong> BWP ${paymentData.amount.toLocaleString()}</p>
                            <p><strong>New Balance:</strong> BWP ${result.new_balance.toLocaleString()}</p>
                            <p><strong>Processed:</strong> ${new Date(result.timestamp).toLocaleString()}</p>
                        </div>
                        <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin-top: 15px;">
                            <strong>📊 Impact:</strong><br>
                            • Customer wallet balance updated instantly<br>
                            • Transaction recorded in FNB system<br>
                            • Business analytics updated<br>
                            • SMS/Email notifications sent
                        </div>
                        <div style="margin-top: 20px;">
                            <button onclick="window.location.href='/business/dashboard'" class="btn btn-success">View in Dashboard</button>
                            <button onclick="location.reload()" class="btn">Process Another Payment</button>
                        </div>
                    `;
                    
                    // Reset form
                    this.reset();
                } else {
                    resultDiv.style.background = '#f8d7da';
                    resultDiv.style.color = '#721c24';
                    resultDiv.style.border = '1px solid #f5c6cb';
                    resultDiv.style.padding = '20px';
                    resultDiv.style.borderRadius = '10px';
                    
                    resultDiv.innerHTML = `
                        <h4>❌ Payment Failed</h4>
                        <p><strong>Error:</strong> ${result.error}</p>
                        ${result.code ? `<p><strong>Code:</strong> ${result.code}</p>` : ''}
                        <button onclick="this.parentElement.style.display='none'" class="btn">Try Again</button>
                    `;
                }
            } catch (error) {
                const resultDiv = document.getElementById('paymentResult');
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#f8d7da';
                resultDiv.style.color = '#721c24';
                resultDiv.style.border = '1px solid #f5c6cb';
                resultDiv.style.padding = '20px';
                resultDiv.style.borderRadius = '10px';
                resultDiv.innerHTML = `
                    <h4>❌ Network Error</h4>
                    <p>Failed to process payment. Please try again.</p>
                `;
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '💳 Process Payment';
            }
        });
    </script>
    """
    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


# Update the business dashboard to have functional buttons and auto-refresh
@app.route("/business/dashboard")
def business_dashboard():
    """Enhanced Business Dashboard with Real Functionality"""
    demo_business = Business.query.filter_by(email="demo@fnb-phantom.com").first()
    if not demo_business:
        return redirect(url_for("business_login"))

    wallets = PhantomWallet.query.filter_by(business_id=demo_business.id).all()
    recent_transactions = (
        Transaction.query.join(PhantomWallet)
        .filter(PhantomWallet.business_id == demo_business.id)
        .order_by(Transaction.timestamp.desc())
        .limit(15)
        .all()
    )

    # Calculate real-time metrics
    total_balance = sum(w.balance for w in wallets)
    active_wallets = len([w for w in wallets if w.status.value == "active"])
    today = datetime.now().date()
    todays_transactions = [
        t for t in recent_transactions if t.timestamp.date() == today
    ]
    todays_volume = sum(
        t.amount for t in todays_transactions if t.status == TransactionStatus.COMPLETED
    )

    # Find the demo business API key
    api_key = APIKey.query.filter_by(business_id=demo_business.id).first()
    api_key_value = api_key.key if api_key else "pb_demo_key_1234567890abcdef"

    content = f"""
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div>
                <h2>📊 Business Dashboard - {demo_business.name}</h2>
                <p style="color: #666; margin: 5px 0;">Real-time phantom banking operations</p>
            </div>
            <div>
                <button onclick="refreshDashboard()" class="btn" style="margin-right: 10px;">🔄 Refresh</button>
                <span id="lastUpdated" style="font-size: 0.9rem; color: #666;">Last updated: {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="totalWallets">{len(wallets)}</div>
                <div class="stat-label">Total Wallets</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalBalance">BWP {total_balance:,.2f}</div>
                <div class="stat-label">Total Balance</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="todaysTransactions">{len(todays_transactions)}</div>
                <div class="stat-label">Today's Transactions</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="todaysVolume">BWP {todays_volume:,.2f}</div>
                <div class="stat-label">Today's Volume</div>
            </div>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>🚀 Quick Actions</h3>
            <div style="margin: 20px 0;">
                <a href="/business/create-wallet" class="btn btn-success" style="margin: 5px;">
                    🆕 Create New Wallet
                </a>
                <a href="/business/process-payment" class="btn btn-warning" style="margin: 5px;">
                    💳 Process Payment
                </a>
                <a href="/api/docs/" class="btn" style="margin: 5px;">
                    📚 API Docs
                </a>
            </div>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px;">
                <h4>🔄 Real-time Features</h4>
                <ul style="margin: 10px 0 0 20px; line-height: 1.8;">
                    <li>✅ Instant wallet creation</li>
                    <li>✅ Real-time payment processing</li>
                    <li>✅ Live balance updates</li>
                    <li>✅ Automatic FNB sync</li>
                </ul>
            </div>
        </div>
        
        <div class="card">
            <h3>🔑 API Integration</h3>
            <p>Your API key for system integration:</p>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; font-family: monospace; word-break: break-all; margin: 15px 0;">
                {api_key_value}
            </div>
            <button onclick="copyApiKey()" class="btn" style="margin-top: 10px;">📋 Copy API Key</button>
            
            <div style="margin-top: 20px;">
                <h4>📊 API Usage Today</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                    <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: #28a745;">{len(recent_transactions)}</div>
                        <div style="font-size: 0.9rem;">API Calls</div>
                    </div>
                    <div style="background: #fff3cd; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: #856404;">99.9%</div>
                        <div style="font-size: 0.9rem;">Uptime</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3>👥 Recent Wallets</h3>
            <div>
                <span style="color: #28a745; font-weight: bold;">{active_wallets} Active</span> | 
                <span style="color: #666;">{len(wallets)} Total</span>
            </div>
        </div>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="padding: 12px; text-align: left;">Customer</th>
                        <th style="padding: 12px; text-align: left;">Phone</th>
                        <th style="padding: 12px; text-align: left;">Balance</th>
                        <th style="padding: 12px; text-align: left;">Status</th>
                        <th style="padding: 12px; text-align: left;">USSD Code</th>
                        <th style="padding: 12px; text-align: left;">Actions</th>
                    </tr>
                </thead>
                <tbody id="walletsTable">
    """

    for wallet in wallets:
        status_color = "#28a745" if wallet.status.value == "active" else "#dc3545"
        content += f"""
                    <tr>
                        <td style="padding: 12px; border-bottom: 1px solid #eee;">{wallet.customer_name}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee;">{wallet.customer_phone}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee;">BWP {wallet.balance:.2f}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee; color: {status_color}; font-weight: bold;">{wallet.status.value.upper()}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee; font-family: monospace;">{wallet.ussd_code}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee;">
                            <button onclick="processPaymentFor('{wallet.id}')" class="btn" style="padding: 5px 10px; font-size: 12px; margin-right: 5px;">💳 Pay</button>
                            <button onclick="viewWalletDetails('{wallet.id}')" class="btn" style="padding: 5px 10px; font-size: 12px;">👁️ View</button>
                        </td>
                    </tr>
        """

    content += f"""
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="card">
        <h3>📈 Recent Transactions</h3>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="padding: 12px; text-align: left;">Time</th>
                        <th style="padding: 12px; text-align: left;">Customer</th>
                        <th style="padding: 12px; text-align: left;">Amount</th>
                        <th style="padding: 12px; text-align: left;">Method</th>
                        <th style="padding: 12px; text-align: left;">Status</th>
                        <th style="padding: 12px; text-align: left;">Reference</th>
                    </tr>
                </thead>
                <tbody id="transactionsTable">
    """

    for txn in recent_transactions[:10]:
        status_color = (
            "#28a745" if txn.status == TransactionStatus.COMPLETED else "#ffc107"
        )
        content += f"""
                    <tr>
                        <td style="padding: 12px; border-bottom: 1px solid #eee;">{txn.timestamp.strftime('%H:%M')}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee;">{txn.wallet.customer_name if txn.wallet else 'Unknown'}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee;">BWP {txn.amount:.2f}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee;">{txn.method.value.upper()}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee; color: {status_color}; font-weight: bold;">{txn.status.value.upper()}</td>
                        <td style="padding: 12px; border-bottom: 1px solid #eee; font-family: monospace;">{txn.reference}</td>
                    </tr>
        """

    content += (
        """
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function copyApiKey() {
            const apiKey = '"""
        + api_key_value
        + """';
            navigator.clipboard.writeText(apiKey).then(() => {
                alert('API key copied to clipboard!');
            });
        }
        
        function processPaymentFor(walletId) {
            window.location.href = `/business/process-payment?wallet=${walletId}`;
        }
        
        function viewWalletDetails(walletId) {
            alert(`Wallet details for ID: ${walletId}\\nThis would open a detailed wallet view.`);
        }
        
        function refreshDashboard() {
            location.reload();
        }
        
        // Auto-refresh dashboard every 30 seconds
        setInterval(() => {
            fetch('/api/v1/stats')
                .then(response => response.json())
                .then(data => {
                    // Update real-time stats
                    document.getElementById('lastUpdated').textContent = 
                        `Last updated: ${new Date().toLocaleTimeString()}`;
                })
                .catch(console.error);
        }, 30000);
        
        // Highlight new transactions with animation
        const rows = document.querySelectorAll('#transactionsTable tr');
        rows.forEach((row, index) => {
            if (index < 3) { // Highlight first 3 transactions as "new"
                row.style.backgroundColor = '#f0f8f0';
                row.style.transition = 'background-color 3s ease';
                setTimeout(() => {
                    row.style.backgroundColor = '';
                }, 3000);
            }
        });
    </script>
    """
    )

    return render_template_string(ENTERPRISE_TEMPLATE, content=content)


if __name__ == "__main__":
    print(" Starting FNB Phantom Banking Enterprise System...")
    print("  Initializing enterprise architecture...")

    with app.app_context():
        init_enterprise_db()

    print(" Enterprise database initialized")
    print(" Security features enabled")
    print(" Analytics dashboard ready")
    print(" FNB integration simulated")
    print("\n System URLs:")
    print("   Main Portal: http://localhost:5000")
    print("   API Docs: http://localhost:5000/api/docs/")
    print("   Business Portal: http://localhost:5000/business/login")
    print("\n Demo Login:")
    print("   Email: demo@fnb-phantom.com")
    print("   Password: demo123456")

    app.run(debug=True, port=5000, host="0.0.0.0")
