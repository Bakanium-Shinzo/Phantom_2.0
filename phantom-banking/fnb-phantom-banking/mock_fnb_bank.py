#!/usr/bin/env python3

# mock_fnb_bank.py
"""
Mock FNB Bank - Core Banking System Simulation
Simulates FNB's core banking operations for Phantom Banking integration

This mock service simulates:
- Account creation and management
- Transaction processing and settlement
- Balance inquiries and updates
- Payment notifications and webhooks
- KYC and compliance checking
- Mobile money integration (Orange Money, MyZaka)

Architecture: RESTful API service that can run standalone or integrated
"""

from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api, Resource, fields, Namespace
from datetime import datetime, timedelta
import uuid
import json
import secrets
import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from werkzeug.security import generate_password_hash

# ==========================================
# MOCK FNB CONFIGURATION
# ==========================================


class FNBConfig:
    """Mock FNB Bank Configuration"""

    SECRET_KEY = secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = "sqlite:///mock_fnb_bank.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Bank Configuration
    BANK_CODE = "250655"
    BANK_NAME = "First National Bank"
    SWIFT_CODE = "FIRNBWGX"

    # Account Number Ranges
    CHEQUE_ACCOUNT_PREFIX = "62"
    SAVINGS_ACCOUNT_PREFIX = "63"
    BUSINESS_ACCOUNT_PREFIX = "64"

    # Transaction Limits
    DAILY_TRANSACTION_LIMIT = 100000.0
    SINGLE_TRANSACTION_LIMIT = 50000.0

    # Webhook Configuration
    PHANTOM_BANKING_WEBHOOK = "http://localhost:5000/webhooks/fnb"


# ==========================================
# MOCK FNB APPLICATION SETUP
# ==========================================

fnb_app = Flask(__name__)
fnb_app.config.from_object(FNBConfig)

fnb_db = SQLAlchemy(fnb_app)

fnb_api = Api(
    fnb_app,
    version="1.0",
    title="FNB Mock Banking API",
    description="Mock FNB Core Banking System for Integration Testing",
    doc="/api/docs/",
    prefix="/api/v1",
)

# ==========================================
# MOCK FNB DATA MODELS
# ==========================================


class FNBCustomer(fnb_db.Model):
    """FNB Customer Entity"""

    __tablename__ = "fnb_customers"

    id = fnb_db.Column(
        fnb_db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    customer_number = fnb_db.Column(fnb_db.String(20), unique=True, nullable=False)

    # Personal Information
    first_name = fnb_db.Column(fnb_db.String(50), nullable=False)
    last_name = fnb_db.Column(fnb_db.String(50), nullable=False)
    id_number = fnb_db.Column(fnb_db.String(20), unique=True)
    phone = fnb_db.Column(fnb_db.String(20), nullable=False)
    email = fnb_db.Column(fnb_db.String(120))

    # Address Information
    address_line1 = fnb_db.Column(fnb_db.String(100))
    address_line2 = fnb_db.Column(fnb_db.String(100))
    city = fnb_db.Column(fnb_db.String(50))
    postal_code = fnb_db.Column(fnb_db.String(10))

    # Banking Information
    branch_code = fnb_db.Column(fnb_db.String(10), default=FNBConfig.BANK_CODE)
    customer_type = fnb_db.Column(
        fnb_db.String(20), default="INDIVIDUAL"
    )  # INDIVIDUAL, BUSINESS
    risk_rating = fnb_db.Column(fnb_db.String(10), default="LOW")  # LOW, MEDIUM, HIGH

    # KYC and Compliance
    kyc_status = fnb_db.Column(
        fnb_db.String(20), default="PENDING"
    )  # PENDING, VERIFIED, REJECTED
    kyc_date = fnb_db.Column(fnb_db.DateTime)
    compliance_status = fnb_db.Column(
        fnb_db.String(20), default="CLEAR"
    )  # CLEAR, FLAGGED, BLOCKED

    # Status and Timestamps
    status = fnb_db.Column(
        fnb_db.String(20), default="ACTIVE"
    )  # ACTIVE, INACTIVE, SUSPENDED, CLOSED
    created_at = fnb_db.Column(fnb_db.DateTime, default=datetime.utcnow)
    updated_at = fnb_db.Column(
        fnb_db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    accounts = fnb_db.relationship(
        "FNBAccount", backref="customer", lazy=True, cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.customer_number:
            self.customer_number = self._generate_customer_number()

    def _generate_customer_number(self) -> str:
        """Generate unique customer number"""
        return f"FNBC{secrets.randbelow(9999999):07d}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class FNBAccount(fnb_db.Model):
    """FNB Account Entity"""

    __tablename__ = "fnb_accounts"

    id = fnb_db.Column(
        fnb_db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_number = fnb_db.Column(fnb_db.String(20), unique=True, nullable=False)
    customer_id = fnb_db.Column(
        fnb_db.String(36), fnb_db.ForeignKey("fnb_customers.id"), nullable=False
    )

    # Account Details
    account_type = fnb_db.Column(
        fnb_db.String(20), nullable=False
    )  # CHEQUE, SAVINGS, BUSINESS, PHANTOM_LINK
    product_code = fnb_db.Column(fnb_db.String(10))
    account_name = fnb_db.Column(fnb_db.String(100))
    branch_code = fnb_db.Column(fnb_db.String(10), default=FNBConfig.BANK_CODE)

    # Financial Information
    balance = fnb_db.Column(fnb_db.Float, default=0.0, nullable=False)
    available_balance = fnb_db.Column(fnb_db.Float, default=0.0, nullable=False)
    overdraft_limit = fnb_db.Column(fnb_db.Float, default=0.0)

    # Limits and Settings
    daily_transaction_limit = fnb_db.Column(
        fnb_db.Float, default=FNBConfig.DAILY_TRANSACTION_LIMIT
    )
    monthly_transaction_limit = fnb_db.Column(fnb_db.Float, default=300000.0)

    # Status and Timestamps
    status = fnb_db.Column(
        fnb_db.String(20), default="ACTIVE"
    )  # ACTIVE, INACTIVE, SUSPENDED, CLOSED
    opened_date = fnb_db.Column(fnb_db.DateTime, default=datetime.utcnow)
    last_transaction_date = fnb_db.Column(fnb_db.DateTime)

    # Phantom Banking Integration
    phantom_wallet_id = fnb_db.Column(fnb_db.String(36))  # Link to phantom wallet
    phantom_business_id = fnb_db.Column(fnb_db.String(36))  # Link to phantom business

    # Relationships
    transactions = fnb_db.relationship("FNBTransaction", backref="account", lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.account_number:
            self.account_number = self._generate_account_number()
        self.available_balance = self.balance  # Initialize available balance

    def _generate_account_number(self) -> str:
        """Generate account number based on type"""
        if self.account_type == "CHEQUE":
            prefix = FNBConfig.CHEQUE_ACCOUNT_PREFIX
        elif self.account_type == "SAVINGS":
            prefix = FNBConfig.SAVINGS_ACCOUNT_PREFIX
        elif self.account_type in ["BUSINESS", "PHANTOM_LINK"]:
            prefix = FNBConfig.BUSINESS_ACCOUNT_PREFIX
        else:
            prefix = FNBConfig.CHEQUE_ACCOUNT_PREFIX

        return f"{prefix}{secrets.randbelow(99999999):08d}"

    def update_balance(self, amount: float, transaction_type: str):
        """Update account balance"""
        if transaction_type == "CREDIT":
            self.balance += amount
            self.available_balance += amount
        elif transaction_type == "DEBIT":
            if self.available_balance >= amount:
                self.balance -= amount
                self.available_balance -= amount
            else:
                raise ValueError("Insufficient funds")

        self.last_transaction_date = datetime.utcnow()


class FNBTransaction(fnb_db.Model):
    """FNB Transaction Entity"""

    __tablename__ = "fnb_transactions"

    id = fnb_db.Column(
        fnb_db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    transaction_number = fnb_db.Column(fnb_db.String(20), unique=True, nullable=False)
    account_id = fnb_db.Column(
        fnb_db.String(36), fnb_db.ForeignKey("fnb_accounts.id"), nullable=False
    )

    # Transaction Details
    transaction_type = fnb_db.Column(fnb_db.String(10), nullable=False)  # CREDIT, DEBIT
    amount = fnb_db.Column(fnb_db.Float, nullable=False)
    balance_after = fnb_db.Column(fnb_db.Float, nullable=False)

    # Transaction Classification
    transaction_code = fnb_db.Column(fnb_db.String(10))  # Internal transaction codes
    description = fnb_db.Column(fnb_db.String(255), nullable=False)
    reference = fnb_db.Column(fnb_db.String(100))

    # Source/Destination Information
    counterparty_account = fnb_db.Column(fnb_db.String(20))
    counterparty_name = fnb_db.Column(fnb_db.String(100))
    counterparty_bank = fnb_db.Column(fnb_db.String(50))

    # Channel Information
    channel = fnb_db.Column(fnb_db.String(20))  # ATM, INTERNET, MOBILE, PHANTOM, BRANCH
    device_id = fnb_db.Column(fnb_db.String(50))

    # Status and Processing
    status = fnb_db.Column(
        fnb_db.String(20), default="COMPLETED"
    )  # PENDING, COMPLETED, FAILED, REVERSED
    processing_date = fnb_db.Column(fnb_db.DateTime, default=datetime.utcnow)
    value_date = fnb_db.Column(fnb_db.DateTime, default=datetime.utcnow)

    # Phantom Banking Integration
    phantom_transaction_id = fnb_db.Column(
        fnb_db.String(36)
    )  # Link to phantom transaction
    phantom_wallet_id = fnb_db.Column(fnb_db.String(36))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.transaction_number:
            self.transaction_number = self._generate_transaction_number()

    def _generate_transaction_number(self) -> str:
        """Generate unique transaction number"""
        timestamp = int(time.time())
        random_part = secrets.randbelow(99999)
        return f"FNB{timestamp}{random_part:05d}"


class FNBWebhookLog(fnb_db.Model):
    """Webhook delivery tracking"""

    __tablename__ = "fnb_webhook_logs"

    id = fnb_db.Column(
        fnb_db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    webhook_url = fnb_db.Column(fnb_db.String(255), nullable=False)
    event_type = fnb_db.Column(fnb_db.String(50), nullable=False)
    payload = fnb_db.Column(fnb_db.Text, nullable=False)

    # Delivery Information
    http_status = fnb_db.Column(fnb_db.Integer)
    response_body = fnb_db.Column(fnb_db.Text)
    delivery_attempts = fnb_db.Column(fnb_db.Integer, default=0)

    # Timestamps
    created_at = fnb_db.Column(fnb_db.DateTime, default=datetime.utcnow)
    delivered_at = fnb_db.Column(fnb_db.DateTime)
    next_retry_at = fnb_db.Column(fnb_db.DateTime)


# ==========================================
# MOCK FNB SERVICES
# ==========================================


class FNBAccountService:
    """FNB Account Management Service"""

    @staticmethod
    def create_customer_and_account(
        customer_data: Dict, account_type: str = "CHEQUE"
    ) -> Dict:
        """Create customer and associated account"""
        try:
            # Parse customer name
            name_parts = customer_data.get("customer_name", "").split(" ", 1)
            first_name = name_parts[0] if name_parts else "Unknown"
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Create customer
            customer = FNBCustomer(
                first_name=first_name,
                last_name=last_name,
                phone=customer_data.get("customer_phone"),
                email=customer_data.get("customer_email"),
                kyc_status="VERIFIED",  # Auto-verify for phantom integration
                kyc_date=datetime.utcnow(),
            )

            fnb_db.session.add(customer)
            fnb_db.session.flush()

            # Create account
            account = FNBAccount(
                customer_id=customer.id,
                account_type=account_type,
                account_name=f"{customer.full_name} - {account_type}",
                balance=customer_data.get("initial_balance", 0.0),
                phantom_wallet_id=customer_data.get("phantom_wallet_id"),
                phantom_business_id=customer_data.get("phantom_business_id"),
            )
            account.available_balance = account.balance

            fnb_db.session.add(account)
            fnb_db.session.commit()

            return {
                "success": True,
                "customer_id": customer.id,
                "customer_number": customer.customer_number,
                "account_id": account.id,
                "account_number": account.account_number,
                "account_type": account.account_type,
                "branch_code": account.branch_code,
                "balance": account.balance,
            }

        except Exception as e:
            fnb_db.session.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_account_balance(account_number: str) -> Dict:
        """Get account balance"""
        account = FNBAccount.query.filter_by(account_number=account_number).first()
        if not account:
            return {"success": False, "error": "Account not found"}

        return {
            "success": True,
            "account_number": account.account_number,
            "balance": account.balance,
            "available_balance": account.available_balance,
            "account_type": account.account_type,
            "status": account.status,
        }

    @staticmethod
    def process_transaction(transaction_data: Dict) -> Dict:
        """Process account transaction"""
        try:
            account = FNBAccount.query.filter_by(
                account_number=transaction_data["account_number"]
            ).first()

            if not account:
                return {"success": False, "error": "Account not found"}

            if account.status != "ACTIVE":
                return {"success": False, "error": "Account is not active"}

            # Validate transaction limits
            amount = float(transaction_data["amount"])
            if amount > FNBConfig.SINGLE_TRANSACTION_LIMIT:
                return {"success": False, "error": "Transaction amount exceeds limit"}

            # Update account balance
            old_balance = account.balance
            account.update_balance(amount, transaction_data["transaction_type"])

            # Create transaction record
            transaction = FNBTransaction(
                account_id=account.id,
                transaction_type=transaction_data["transaction_type"],
                amount=amount,
                balance_after=account.balance,
                transaction_code=transaction_data.get("transaction_code", "PHANTOM"),
                description=transaction_data.get(
                    "description", "Phantom Banking Transaction"
                ),
                reference=transaction_data.get("reference"),
                channel="PHANTOM",
                phantom_transaction_id=transaction_data.get("phantom_transaction_id"),
                phantom_wallet_id=transaction_data.get("phantom_wallet_id"),
            )

            fnb_db.session.add(transaction)
            fnb_db.session.commit()

            return {
                "success": True,
                "transaction_id": transaction.id,
                "transaction_number": transaction.transaction_number,
                "old_balance": old_balance,
                "new_balance": account.balance,
                "reference": transaction.reference,
            }

        except Exception as e:
            fnb_db.session.rollback()
            return {"success": False, "error": str(e)}


class FNBWebhookService:
    """FNB Webhook Service for external notifications"""

    @staticmethod
    def send_webhook(event_type: str, payload: Dict, webhook_url: str = None):
        """Send webhook notification"""
        if not webhook_url:
            webhook_url = FNBConfig.PHANTOM_BANKING_WEBHOOK

        # Create webhook log
        webhook_log = FNBWebhookLog(
            webhook_url=webhook_url, event_type=event_type, payload=json.dumps(payload)
        )

        def _send_async():
            try:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-FNB-Event-Type": event_type,
                        "X-FNB-Signature": "mock-signature",
                        "User-Agent": "FNB-Webhook/1.0",
                    },
                    timeout=30,
                )

                webhook_log.http_status = response.status_code
                webhook_log.response_body = response.text[:1000]  # Limit response size
                webhook_log.delivered_at = datetime.utcnow()
                webhook_log.delivery_attempts = 1

                print(
                    f"[FNB WEBHOOK] {event_type} sent to {webhook_url} - Status: {response.status_code}"
                )

            except Exception as e:
                webhook_log.http_status = 0
                webhook_log.response_body = str(e)
                webhook_log.delivery_attempts = 1
                webhook_log.next_retry_at = datetime.utcnow() + timedelta(minutes=5)

                print(
                    f"[FNB WEBHOOK] Failed to send {event_type} to {webhook_url}: {e}"
                )

            finally:
                fnb_db.session.add(webhook_log)
                fnb_db.session.commit()

        # Send webhook asynchronously
        threading.Thread(target=_send_async).start()


class MobileMoneyService:
    """Mobile Money Integration Service (Orange Money, MyZaka)"""

    PROVIDERS = {
        "orange_money": {
            "name": "Orange Money",
            "prefix": "OM",
            "fee_rate": 0.02,  # 2% fee
        },
        "myzaka": {"name": "MyZaka", "prefix": "MZ", "fee_rate": 0.015},  # 1.5% fee
    }

    @staticmethod
    def process_mobile_money_deposit(
        provider: str, amount: float, source_phone: str, target_account: str
    ) -> Dict:
        """Process mobile money deposit to FNB account"""
        try:
            if provider not in MobileMoneyService.PROVIDERS:
                return {"success": False, "error": "Unsupported provider"}

            provider_info = MobileMoneyService.PROVIDERS[provider]
            fee = amount * provider_info["fee_rate"]
            net_amount = amount - fee

            # Find target account
            account = FNBAccount.query.filter_by(account_number=target_account).first()
            if not account:
                return {"success": False, "error": "Target account not found"}

            # Process deposit
            account.update_balance(net_amount, "CREDIT")

            # Create transaction record
            transaction = FNBTransaction(
                account_id=account.id,
                transaction_type="CREDIT",
                amount=net_amount,
                balance_after=account.balance,
                transaction_code="MOBMONEY",
                description=f"{provider_info['name']} deposit from {source_phone}",
                reference=f"{provider_info['prefix']}{secrets.randbelow(999999):06d}",
                channel="MOBILE_MONEY",
                counterparty_name=source_phone,
                counterparty_bank=provider_info["name"],
            )

            fnb_db.session.add(transaction)
            fnb_db.session.commit()

            return {
                "success": True,
                "transaction_number": transaction.transaction_number,
                "amount_received": net_amount,
                "fee_charged": fee,
                "provider": provider_info["name"],
                "reference": transaction.reference,
            }

        except Exception as e:
            fnb_db.session.rollback()
            return {"success": False, "error": str(e)}


# ==========================================
# MOCK FNB API ENDPOINTS
# ==========================================

# API Namespaces
account_ns = Namespace("accounts", description="Account management operations")
transaction_ns = Namespace("transactions", description="Transaction processing")
customer_ns = Namespace("customers", description="Customer management")
webhook_ns = Namespace("webhooks", description="Webhook management")
mobile_money_ns = Namespace("mobile-money", description="Mobile money integration")

fnb_api.add_namespace(account_ns)
fnb_api.add_namespace(transaction_ns)
fnb_api.add_namespace(customer_ns)
fnb_api.add_namespace(webhook_ns)
fnb_api.add_namespace(mobile_money_ns)

# API Models
customer_model = fnb_api.model(
    "Customer",
    {
        "customer_name": fields.String(required=True, description="Full customer name"),
        "customer_phone": fields.String(required=True, description="Phone number"),
        "customer_email": fields.String(description="Email address"),
        "initial_balance": fields.Float(description="Initial account balance"),
        "phantom_wallet_id": fields.String(description="Associated phantom wallet ID"),
        "phantom_business_id": fields.String(
            description="Associated phantom business ID"
        ),
    },
)

account_model = fnb_api.model(
    "Account",
    {
        "account_number": fields.String(description="FNB account number"),
        "account_type": fields.String(description="Account type"),
        "balance": fields.Float(description="Current balance"),
        "status": fields.String(description="Account status"),
    },
)

transaction_model = fnb_api.model(
    "Transaction",
    {
        "account_number": fields.String(required=True, description="Account number"),
        "amount": fields.Float(required=True, description="Transaction amount"),
        "transaction_type": fields.String(required=True, description="CREDIT or DEBIT"),
        "description": fields.String(description="Transaction description"),
        "reference": fields.String(description="Transaction reference"),
        "phantom_transaction_id": fields.String(description="Phantom transaction ID"),
        "phantom_wallet_id": fields.String(description="Phantom wallet ID"),
    },
)


# Account Management Endpoints
@account_ns.route("/create")
class CreateAccount(Resource):
    @account_ns.doc("create_account")
    @account_ns.expect(customer_model)
    def post(self):
        """Create new FNB customer and account"""
        result = FNBAccountService.create_customer_and_account(
            request.json, request.json.get("account_type", "CHEQUE")
        )

        if result["success"]:
            return result, 201
        else:
            return {"error": result["error"]}, 400


@account_ns.route("/<string:account_number>/balance")
class AccountBalance(Resource):
    @account_ns.doc("get_balance")
    def get(self, account_number):
        """Get account balance"""
        result = FNBAccountService.get_account_balance(account_number)

        if result["success"]:
            return result
        else:
            return {"error": result["error"]}, 404


@account_ns.route("/list")
class AccountList(Resource):
    @account_ns.doc("list_accounts")
    def get(self):
        """List all accounts (for testing)"""
        accounts = FNBAccount.query.filter_by(status="ACTIVE").all()

        return {
            "accounts": [
                {
                    "account_number": acc.account_number,
                    "account_type": acc.account_type,
                    "customer_name": acc.customer.full_name
                    if acc.customer
                    else "Unknown",
                    "balance": acc.balance,
                    "status": acc.status,
                    "phantom_wallet_id": acc.phantom_wallet_id,
                }
                for acc in accounts
            ]
        }


# Transaction Processing Endpoints
@transaction_ns.route("/process")
class ProcessTransaction(Resource):
    @transaction_ns.doc("process_transaction")
    @transaction_ns.expect(transaction_model)
    def post(self):
        """Process account transaction"""
        result = FNBAccountService.process_transaction(request.json)

        if result["success"]:
            # Send webhook notification
            webhook_payload = {
                "event_type": "transaction_processed",
                "transaction_id": result["transaction_id"],
                "account_number": request.json["account_number"],
                "amount": request.json["amount"],
                "transaction_type": request.json["transaction_type"],
                "new_balance": result["new_balance"],
                "timestamp": datetime.utcnow().isoformat(),
                "phantom_transaction_id": request.json.get("phantom_transaction_id"),
            }

            FNBWebhookService.send_webhook("transaction_processed", webhook_payload)

            return result, 200
        else:
            return {"error": result["error"]}, 400


@transaction_ns.route("/<string:account_number>/history")
class TransactionHistory(Resource):
    @transaction_ns.doc("transaction_history")
    def get(self, account_number):
        """Get transaction history for account"""
        account = FNBAccount.query.filter_by(account_number=account_number).first()
        if not account:
            return {"error": "Account not found"}, 404

        transactions = (
            FNBTransaction.query.filter_by(account_id=account.id)
            .order_by(FNBTransaction.processing_date.desc())
            .limit(50)
            .all()
        )

        return {
            "account_number": account_number,
            "transactions": [
                {
                    "transaction_number": t.transaction_number,
                    "amount": t.amount,
                    "transaction_type": t.transaction_type,
                    "description": t.description,
                    "reference": t.reference,
                    "balance_after": t.balance_after,
                    "processing_date": t.processing_date.isoformat(),
                    "status": t.status,
                    "phantom_transaction_id": t.phantom_transaction_id,
                }
                for t in transactions
            ],
        }


# Mobile Money Endpoints
@mobile_money_ns.route("/deposit")
class MobileMoneyDeposit(Resource):
    @mobile_money_ns.doc("mobile_money_deposit")
    @mobile_money_ns.expect(
        fnb_api.model(
            "MobileMoneyDeposit",
            {
                "provider": fields.String(
                    required=True, description="orange_money or myzaka"
                ),
                "amount": fields.Float(required=True, description="Deposit amount"),
                "source_phone": fields.String(
                    required=True, description="Source phone number"
                ),
                "target_account": fields.String(
                    required=True, description="Target FNB account"
                ),
            },
        )
    )
    def post(self):
        """Process mobile money deposit"""
        data = request.json
        result = MobileMoneyService.process_mobile_money_deposit(
            data["provider"],
            data["amount"],
            data["source_phone"],
            data["target_account"],
        )

        if result["success"]:
            return result, 200
        else:
            return {"error": result["error"]}, 400


# Webhook Management
@webhook_ns.route("/test")
class WebhookTest(Resource):
    @webhook_ns.doc("test_webhook")
    def post(self):
        """Test webhook delivery"""
        test_payload = {
            "event_type": "webhook_test",
            "message": "This is a test webhook from FNB Mock Bank",
            "timestamp": datetime.utcnow().isoformat(),
            "test_data": {
                "account_number": "6212345678",
                "amount": 100.00,
                "status": "completed",
            },
        }

        webhook_url = request.json.get("webhook_url", FNBConfig.PHANTOM_BANKING_WEBHOOK)
        FNBWebhookService.send_webhook("webhook_test", test_payload, webhook_url)

        return {"message": "Test webhook sent", "webhook_url": webhook_url}


@webhook_ns.route("/logs")
class WebhookLogs(Resource):
    @webhook_ns.doc("webhook_logs")
    def get(self):
        """Get webhook delivery logs"""
        logs = (
            FNBWebhookLog.query.order_by(FNBWebhookLog.created_at.desc())
            .limit(50)
            .all()
        )

        return {
            "webhook_logs": [
                {
                    "id": log.id,
                    "event_type": log.event_type,
                    "webhook_url": log.webhook_url,
                    "http_status": log.http_status,
                    "delivery_attempts": log.delivery_attempts,
                    "created_at": log.created_at.isoformat(),
                    "delivered_at": log.delivered_at.isoformat()
                    if log.delivered_at
                    else None,
                }
                for log in logs
            ]
        }


# ==========================================
# MOCK FNB WEB INTERFACE
# ==========================================

FNB_ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>FNB Mock Bank - Admin Console</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
        }
        
        .header { 
            background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(20px);
            padding: 20px; 
            color: white;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 30px;
        }
        
        .card { 
            background: rgba(255,255,255,0.95); 
            border-radius: 15px; 
            padding: 25px; 
            margin: 20px 0; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .stat-card { 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; 
            padding: 25px; 
            border-radius: 15px; 
            text-align: center;
        }
        
        .stat-number { 
            font-size: 2.5rem; 
            font-weight: bold; 
            margin-bottom: 10px;
        }
        
        .btn { 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            text-decoration: none; 
            display: inline-block;
            font-weight: 600;
            margin: 5px;
            transition: all 0.3s ease;
        }
        
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(30, 60, 114, 0.4);
        }
        
        .btn-success { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); }
        .btn-warning { background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
        }
        
        .status-active { color: #28a745; font-weight: bold; }
        .status-inactive { color: #dc3545; font-weight: bold; }
        
        .form-group { margin: 15px 0; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 600; }
        .form-group input, .form-group select { 
            width: 100%; 
            padding: 10px; 
            border: 1px solid #ddd; 
            border-radius: 6px;
        }
        
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
            gap: 20px; 
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏦 FNB Mock Bank</h1>
        <p>Core Banking System Simulation for Phantom Banking Integration</p>
    </div>
    
    <div class="container">
        {{ content|safe }}
    </div>
    
    <script>
        function refreshData() {
            location.reload();
        }
        
        setInterval(refreshData, 30000); // Refresh every 30 seconds
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    print("🏦 Starting FNB Mock Bank System...")
    print("🔧 Initializing database...")

    with fnb_app.app_context():
        init_fnb_db()

    print("📊 Mock bank ready for integration testing")
    print("🌐 FNB Mock Bank URLs:")
    print("   Admin Console: http://localhost:5001")
    print("   API Docs: http://localhost:5001/api/docs/")
    print("   API Base: http://localhost:5001/api/v1/")

    print("\n🔗 Integration Test Commands:")
    print("   Test Account Creation:")
    print("   curl -X POST http://localhost:5001/api/v1/accounts/create \\")
    print("        -H 'Content-Type: application/json' \\")
    print(
        '        -d \'{"customer_name":"Test User","customer_phone":"+267 75 555 555"}\''
    )

    fnb_app.run(debug=True, port=5001, host="0.0.0.0")
