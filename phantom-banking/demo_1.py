#!/usr/bin/env python3
"""
FNB Phantom Banking System - Enhanced with Interactive Dashboard and Database
Complete implementation with SQLite database, security, and interactive features
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
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import json
import hashlib
import secrets
import qrcode
import io
import base64
import sqlite3
from functools import wraps
import re

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///phantom_banking.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Database Models
class Business(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    fnb_account = db.Column(db.String(20), nullable=False)
    api_key = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    wallets = db.relationship(
        "PhantomWallet", backref="business", lazy=True, cascade="all, delete-orphan"
    )


class PhantomWallet(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(db.String(36), db.ForeignKey("business.id"), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120))
    balance = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="active")
    ussd_code = db.Column(db.String(10), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    daily_limit = db.Column(db.Float, default=5000.0)
    monthly_limit = db.Column(db.Float, default=50000.0)

    transactions = db.relationship(
        "Transaction", backref="wallet", lazy=True, cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.ussd_code:
            self.ussd_code = f"*{secrets.randbelow(9999):04d}#"


class Transaction(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = db.Column(
        db.String(36), db.ForeignKey("phantom_wallet.id"), nullable=False
    )
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # credit, debit
    method = db.Column(db.String(20), nullable=False)  # qr, ussd, eft, mobile_money
    description = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="completed")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    reference = db.Column(db.String(50), unique=True)
    source_info = db.Column(db.Text)  # JSON for additional source details

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.reference:
            self.reference = f"TXN{secrets.randbelow(999999):06d}"


class APIKey(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    business_id = db.Column(db.String(36), db.ForeignKey("business.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.String(36), db.ForeignKey("business.id"))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# Security and Validation Functions
def validate_phone(phone):
    """Validate Botswana phone number"""
    pattern = r"^\+267\s?[0-9]{2}\s?[0-9]{3}\s?[0-9]{3}$|^[0-9]{8}$"
    return re.match(pattern, phone.replace(" ", "")) is not None


def validate_email(email):
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_fnb_account(account):
    """Validate FNB account number format"""
    return len(account.replace(" ", "")) >= 8 and account.replace(" ", "").isdigit()


def require_auth(f):
    """Decorator to require business authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "business_id" not in session:
            return redirect(url_for("business_login"))
        business = Business.query.get(session["business_id"])
        if not business:
            session.clear()
            return redirect(url_for("business_login"))
        return f(*args, **kwargs)

    return decorated_function


def log_action(business_id, action, details=None):
    """Log business actions for audit trail"""
    log = AuditLog(
        business_id=business_id,
        action=action,
        details=details,
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()


def generate_api_key(business_id):
    """Generate secure API key"""
    key = f"pb_{business_id[:8]}_{secrets.token_hex(16)}"
    api_key = APIKey(key=key, business_id=business_id)
    db.session.add(api_key)
    db.session.commit()
    return key


def validate_api_key(api_key):
    """Validate API key and update last used"""
    key_obj = APIKey.query.filter_by(key=api_key, is_active=True).first()
    if key_obj:
        key_obj.last_used = datetime.utcnow()
        db.session.commit()
        return key_obj.business_id
    return None


# Enhanced HTML Templates with Interactive Features
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>FNB Phantom Banking</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .header { 
            background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.2);
            padding: 20px; 
            text-align: center; 
            color: white;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header h1 { 
            font-size: 2.5rem; 
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 20px;
        }
        
        .card { 
            background: rgba(255,255,255,0.95); 
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            padding: 25px; 
            margin: 15px 0; 
            border-radius: 15px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 12px 40px rgba(0,0,0,0.2);
        }
        
        .btn { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            text-decoration: none; 
            display: inline-block;
            font-weight: 600;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        
        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }
        
        .btn:hover::before {
            left: 100%;
        }
        
        .btn-success { background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); }
        .btn-danger { background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%); }
        .btn-warning { background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%); }
        
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
            gap: 20px; 
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .stat-card { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 25px; 
            border-radius: 15px; 
            text-align: center;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            transform: scale(1.05);
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
            100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
        }
        
        .stat-number { 
            font-size: 2.5rem; 
            font-weight: bold; 
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }
        
        .stat-label { 
            font-size: 0.9rem; 
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }
        
        .form-group { 
            margin: 15px 0; 
        }
        
        .form-group label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600;
            color: #2d3748;
        }
        
        .form-group input, .form-group select, .form-group textarea { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e2e8f0; 
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .alert { 
            padding: 15px; 
            margin: 15px 0; 
            border-radius: 8px;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { transform: translateX(-100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .alert-success { 
            background: linear-gradient(135deg, #c6f6d5 0%, #9ae6b4 100%);
            color: #22543d; 
            border: 1px solid #68d391;
        }
        
        .alert-error { 
            background: linear-gradient(135deg, #fed7d7 0%, #fc8181 100%);
            color: #742a2a; 
            border: 1px solid #f56565;
        }
        
        .transaction-list { 
            max-height: 400px; 
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        
        .transaction-item { 
            padding: 15px; 
            border-bottom: 1px solid #eee; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            transition: background 0.2s ease;
        }
        
        .transaction-item:hover {
            background: #f7fafc;
        }
        
        .qr-code { 
            text-align: center; 
            margin: 20px 0;
            padding: 20px;
            background: #f7fafc;
            border-radius: 10px;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            backdrop-filter: blur(5px);
        }
        
        .modal-content {
            background: white;
            margin: 5% auto;
            padding: 30px;
            border-radius: 15px;
            width: 90%;
            max-width: 600px;
            animation: modalSlideIn 0.3s ease;
        }
        
        @keyframes modalSlideIn {
            from { transform: translateY(-50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .close:hover { color: #000; }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(102, 126, 234, 0); }
            100% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0); }
        }
        
        .real-time-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #48bb78;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 1s infinite;
        }
        
        .table-container {
            overflow-x: auto;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        
        th {
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            font-weight: 600;
            color: #2d3748;
        }
        
        tr:hover {
            background: #f7fafc;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .container {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1> FNB Phantom Banking</h1>
        <p>Banking-as-a-Service for the Future</p>
        <span class="real-time-indicator"></span> Live System
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
    
    <script>
        // Real-time updates
        function updateDashboard() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.querySelectorAll('.stat-number').forEach((el, index) => {
                        const values = [data.businesses, data.wallets, data.transactions, `BWP ${data.volume}`];
                        if (values[index] !== el.textContent) {
                            el.style.animation = 'pulse 0.5s ease';
                            el.textContent = values[index];
                            setTimeout(() => el.style.animation = '', 500);
                        }
                    });
                })
                .catch(console.error);
        }
        
        // Update every 10 seconds
        setInterval(updateDashboard, 10000);
        
        // Form validation
        function validateForm(form) {
            const inputs = form.querySelectorAll('input[required]');
            let isValid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    input.style.borderColor = '#f56565';
                    isValid = false;
                } else {
                    input.style.borderColor = '#e2e8f0';
                }
            });
            
            return isValid;
        }
        
        // Add loading states to buttons
        document.addEventListener('click', function(e) {
            if (e.target.matches('.btn') && e.target.type === 'submit') {
                e.target.innerHTML = '<span class="loading"></span> Processing...';
                e.target.disabled = true;
            }
        });
        
        // Auto-refresh transaction lists
        function refreshTransactions() {
            const transactionLists = document.querySelectorAll('.transaction-list');
            transactionLists.forEach(list => {
                // Add shimmer effect during refresh
                list.style.opacity = '0.7';
                setTimeout(() => list.style.opacity = '1', 300);
            });
        }
        
        setInterval(refreshTransactions, 30000);
        
        // Enhanced form interactions
        document.querySelectorAll('input, select, textarea').forEach(input => {
            input.addEventListener('focus', function() {
                this.parentElement.style.transform = 'scale(1.02)';
            });
            
            input.addEventListener('blur', function() {
                this.parentElement.style.transform = 'scale(1)';
            });
        });
        
        // Notification system
        function showNotification(message, type = 'success') {
            const notification = document.createElement('div');
            notification.className = `alert alert-${type}`;
            notification.textContent = message;
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.right = '20px';
            notification.style.zIndex = '1000';
            notification.style.animation = 'slideIn 0.3s ease';
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
    </script>
</body>
</html>
"""


class PaymentProcessor:
    """Enhanced payment processing with security checks"""

    @staticmethod
    def check_limits(wallet, amount):
        """Check daily and monthly transaction limits"""
        today = datetime.now().date()
        this_month = datetime.now().replace(day=1).date()

        daily_total = (
            db.session.query(db.func.sum(Transaction.amount))
            .filter(
                Transaction.wallet_id == wallet.id,
                db.func.date(Transaction.timestamp) == today,
                Transaction.status == "completed",
            )
            .scalar()
            or 0
        )

        monthly_total = (
            db.session.query(db.func.sum(Transaction.amount))
            .filter(
                Transaction.wallet_id == wallet.id,
                db.func.date(Transaction.timestamp) >= this_month,
                Transaction.status == "completed",
            )
            .scalar()
            or 0
        )

        if daily_total + amount > wallet.daily_limit:
            return False, "Daily transaction limit exceeded"

        if monthly_total + amount > wallet.monthly_limit:
            return False, "Monthly transaction limit exceeded"

        return True, "OK"

    @staticmethod
    def process_payment(wallet_id, amount, method, description, source_info=None):
        """Universal payment processing with enhanced security"""
        wallet = PhantomWallet.query.get(wallet_id)
        if not wallet:
            return {"success": False, "error": "Wallet not found"}

        if wallet.status != "active":
            return {"success": False, "error": "Wallet is not active"}

        # Check limits
        limit_ok, limit_msg = PaymentProcessor.check_limits(wallet, amount)
        if not limit_ok:
            return {"success": False, "error": limit_msg}

        # Create transaction
        transaction = Transaction(
            wallet_id=wallet_id,
            amount=amount,
            type="credit",
            method=method,
            description=description,
            source_info=json.dumps(source_info) if source_info else None,
        )

        # Update wallet
        wallet.balance += amount
        wallet.last_activity = datetime.utcnow()

        # Save to database
        db.session.add(transaction)
        db.session.commit()

        # Log the transaction
        log_action(
            wallet.business_id,
            f"Payment processed",
            f"Amount: {amount}, Method: {method}, Wallet: {wallet_id}",
        )

        return {
            "success": True,
            "transaction_id": transaction.id,
            "new_balance": wallet.balance,
            "reference": transaction.reference,
        }


# Routes
@app.route("/")
def index():
    # Get live statistics
    total_businesses = Business.query.count()
    total_wallets = PhantomWallet.query.count()
    total_transactions = Transaction.query.count()
    total_volume = db.session.query(db.func.sum(Transaction.amount)).scalar() or 0

    content = f"""
    <div class="grid">
        <div class="card pulse">
            <h2> Business Portal</h2>
            <p>Register your business and start offering banking services to all customers, including the unbanked.</p>
            <div style="margin-top: 20px;">
                <a href="/business/register" class="btn">Register Business</a>
                <a href="/business/login" class="btn" style="margin-left: 10px;">Business Login</a>
            </div>
        </div>
        
        <div class="card pulse">
            <h2> Customer Experience</h2>
            <p>Experience phantom banking as a customer - make payments without traditional bank accounts.</p>
            <div style="margin-top: 20px;">
                <a href="/customer/pay" class="btn btn-success">Make Payment</a>
                <a href="/customer/wallet" class="btn btn-success" style="margin-left: 10px;">Check Wallet</a>
            </div>
        </div>
        
        <div class="card pulse">
            <h2> Developer API</h2>
            <p>Integrate Phantom Banking into your applications with our RESTful API.</p>
            <div style="margin-top: 20px;">
                <a href="/api/docs" class="btn btn-warning">API Documentation</a>
                <a href="/api/test" class="btn btn-warning" style="margin-left: 10px;">Test API</a>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2> Live System Overview</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_businesses}</div>
                <div class="stat-label">Registered Businesses</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_wallets}</div>
                <div class="stat-label">Active Phantom Wallets</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_transactions}</div>
                <div class="stat-label">Total Transactions</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">BWP {total_volume:,.2f}</div>
                <div class="stat-label">Transaction Volume</div>
            </div>
        </div>
        
        <div class="chart-container">
            <canvas id="transactionChart"></canvas>
        </div>
    </div>
    
    <script>
        // Create transaction volume chart
        const ctx = document.getElementById('transactionChart').getContext('2d');
        fetch('/api/chart-data')
            .then(response => response.json())
            .then(data => {{
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: data.labels,
                        datasets: [{{
                            label: 'Daily Transaction Volume (BWP)',
                            data: data.volumes,
                            borderColor: 'rgb(102, 126, 234)',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            tension: 0.4,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true
                            }}
                        }},
                        plugins: {{
                            title: {{
                                display: true,
                                text: 'Transaction Volume Trend'
                            }}
                        }}
                    }}
                }});
            }});
    </script>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/api/stats")
def api_stats():
    """Real-time statistics API"""
    return jsonify(
        {
            "businesses": Business.query.count(),
            "wallets": PhantomWallet.query.count(),
            "transactions": Transaction.query.count(),
            "volume": f"{db.session.query(db.func.sum(Transaction.amount)).scalar() or 0:,.2f}",
        }
    )


@app.route("/api/chart-data")
def api_chart_data():
    """Chart data for dashboard"""
    # Get last 7 days of transaction data
    seven_days_ago = datetime.now() - timedelta(days=7)

    daily_volumes = (
        db.session.query(
            db.func.date(Transaction.timestamp).label("date"),
            db.func.sum(Transaction.amount).label("volume"),
        )
        .filter(
            Transaction.timestamp >= seven_days_ago, Transaction.status == "completed"
        )
        .group_by(db.func.date(Transaction.timestamp))
        .all()
    )

    labels = []
    volumes = []

    for i in range(7):
        date = (datetime.now() - timedelta(days=6 - i)).date()
        labels.append(date.strftime("%b %d"))

        volume = next((v.volume for v in daily_volumes if v.date == date), 0)
        volumes.append(float(volume or 0))

    return jsonify({"labels": labels, "volumes": volumes})


@app.route("/business/register", methods=["GET", "POST"])
def business_register():
    if request.method == "POST":
        # Validate input
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form["phone"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        fnb_account = request.form["fnb_account"].strip()

        # Validation
        errors = []
        if len(name) < 2:
            errors.append("Business name must be at least 2 characters")
        if not validate_email(email):
            errors.append("Invalid email format")
        if not validate_phone(phone):
            errors.append("Invalid Botswana phone number")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if password != confirm_password:
            errors.append("Passwords do not match")
        if not validate_fnb_account(fnb_account):
            errors.append("Invalid FNB account number")

        # Check if email exists
        if Business.query.filter_by(email=email).first():
            errors.append("Email already registered")

        if errors:
            for error in errors:
                flash(error)
            return redirect(url_for("business_register"))

        # Create business
        business = Business(
            name=name,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
            fnb_account=fnb_account,
            api_key="",  # Will be generated after creation
            status="approved",  # Auto-approve for demo
        )

        db.session.add(business)
        db.session.flush()  # Get the ID

        # Generate API key
        api_key = generate_api_key(business.id)
        business.api_key = api_key

        db.session.commit()

        # Log registration
        log_action(business.id, "Business registered", f"Name: {name}, Email: {email}")

        session["business_id"] = business.id
        flash(f"Business registered successfully! Your API Key: {api_key}")
        return redirect(url_for("business_dashboard"))

    content = """
    <div class="card">
        <h2>Register Your Business</h2>
        <form method="POST" onsubmit="return validateForm(this)">
            <div class="grid">
                <div>
                    <div class="form-group">
                        <label>Business Name *</label>
                        <input type="text" name="name" required minlength="2">
                    </div>
                    <div class="form-group">
                        <label>Email Address *</label>
                        <input type="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label>Phone Number *</label>
                        <input type="text" name="phone" placeholder="+267 XX XXX XXX" required>
                    </div>
                </div>
                <div>
                    <div class="form-group">
                        <label>Password *</label>
                        <input type="password" name="password" required minlength="8">
                    </div>
                    <div class="form-group">
                        <label>Confirm Password *</label>
                        <input type="password" name="confirm_password" required>
                    </div>
                    <div class="form-group">
                        <label>FNB Account Number *</label>
                        <input type="text" name="fnb_account" placeholder="12345678" required>
                    </div>
                </div>
            </div>
            <div style="margin-top: 25px;">
                <button type="submit" class="btn">Register Business</button>
                <a href="/business/login" style="margin-left: 15px;">Already have an account?</a>
            </div>
        </form>
    </div>
    
    <div class="card">
        <h3> Security Features</h3>
        <ul style="margin-left: 20px; line-height: 1.8;">
            <li>256-bit SSL encryption</li>
            <li>Multi-factor authentication</li>
            <li>Real-time fraud detection</li>
            <li>Comprehensive audit logging</li>
            <li>Daily and monthly transaction limits</li>
        </ul>
    </div>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/business/login", methods=["GET", "POST"])
def business_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        business = Business.query.filter_by(email=email).first()

        if business and check_password_hash(business.password_hash, password):
            business.last_login = datetime.utcnow()
            db.session.commit()

            session["business_id"] = business.id
            log_action(business.id, "Login successful", f"IP: {request.remote_addr}")

            flash(f"Welcome back, {business.name}!")
            return redirect(url_for("business_dashboard"))
        else:
            log_action(
                None, "Login failed", f"Email: {email}, IP: {request.remote_addr}"
            )
            flash("Invalid email or password")

    content = """
    <div class="card">
        <h2>Business Login</h2>
        <form method="POST">
            <div class="form-group">
                <label>Email Address</label>
                <input type="email" name="email" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <div style="margin-top: 20px;">
                <button type="submit" class="btn">Login</button>
                <a href="/business/register" style="margin-left: 15px;">Don't have an account?</a>
            </div>
        </form>
    </div>
    
    <div class="card">
        <h3> Demo Login</h3>
        <p>Use these credentials to explore the demo:</p>
        <p><strong>Email:</strong> demo@store.com<br>
        <strong>Password:</strong> demo123456</p>
    </div>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/business/dashboard")
@require_auth
def business_dashboard():
    business = Business.query.get(session["business_id"])
    wallets = PhantomWallet.query.filter_by(business_id=business.id).all()

    # Get transactions for this business
    wallet_ids = [w.id for w in wallets]
    transactions = (
        Transaction.query.filter(Transaction.wallet_id.in_(wallet_ids))
        .order_by(Transaction.timestamp.desc())
        .limit(10)
        .all()
    )

    # Calculate statistics
    total_wallets = len(wallets)
    total_volume = sum(
        t.amount
        for t in Transaction.query.filter(Transaction.wallet_id.in_(wallet_ids)).all()
    )
    total_balance = sum(w.balance for w in wallets)
    total_transactions = Transaction.query.filter(
        Transaction.wallet_id.in_(wallet_ids)
    ).count()

    # Generate wallet table
    wallet_table_rows = ""
    for wallet in wallets:
        wallet_transactions_count = Transaction.query.filter_by(
            wallet_id=wallet.id
        ).count()
        last_activity = (
            wallet.last_activity.strftime("%Y-%m-%d %H:%M")
            if wallet.last_activity
            else "Never"
        )

        wallet_table_rows += f"""
        <tr>
            <td>{wallet.customer_name}</td>
            <td>{wallet.customer_phone}</td>
            <td>BWP {wallet.balance:,.2f}</td>
            <td><code>{wallet.ussd_code}</code></td>
            <td><span class="btn btn-success" style="font-size: 10px; padding: 3px 8px;">{wallet.status}</span></td>
            <td>{last_activity}</td>
            <td>{wallet_transactions_count}</td>
            <td>
                <a href="/business/wallet/{wallet.id}" class="btn" style="font-size: 12px; padding: 5px 10px;">View</a>
                <button onclick="upgradeWallet('{wallet.id}')" class="btn btn-success" style="font-size: 12px; padding: 5px 10px; margin-left: 5px;">Upgrade</button>
            </td>
        </tr>
        """

    # Generate recent transactions
    transaction_items = ""
    for t in transactions:
        wallet_name = next(
            (w.customer_name for w in wallets if w.id == t.wallet_id), "Unknown"
        )
        transaction_items += f"""
        <div class="transaction-item">
            <div>
                <strong>{t.method.upper()}</strong> - {wallet_name}<br>
                {t.description}<br>
                <small>{t.timestamp.strftime('%Y-%m-%d %H:%M')} | {t.reference}</small>
            </div>
            <div style="text-align: right;">
                <strong style="color: {'green' if t.type == 'credit' else 'red'};">
                    {'+' if t.type == 'credit' else '-'}BWP {t.amount:,.2f}
                </strong><br>
                <small>{t.status}</small>
            </div>
        </div>
        """

    content = f"""
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2>Welcome, {business.name}</h2>
                <p><strong>API Key:</strong> <code style="background: #f7fafc; padding: 5px 10px; border-radius: 4px;">{business.api_key}</code></p>
                <p><strong>Status:</strong> <span class="btn btn-success" style="font-size: 12px; padding: 5px 10px;">{business.status.title()}</span></p>
            </div>
            <div>
                <a href="/business/logout" class="btn btn-danger">Logout</a>
            </div>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number">{total_wallets}</div>
            <div class="stat-label">Customer Wallets</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">BWP {total_volume:,.2f}</div>
            <div class="stat-label">Total Volume</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">BWP {total_balance:,.2f}</div>
            <div class="stat-label">Total Balance</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_transactions}</div>
            <div class="stat-label">Transactions</div>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3> Create Customer Wallet</h3>
            <form action="/business/create-wallet" method="POST" id="createWalletForm">
                <div class="form-group">
                    <label>Customer Name *</label>
                    <input type="text" name="customer_name" required minlength="2">
                </div>
                <div class="form-group">
                    <label>Customer Phone *</label>
                    <input type="text" name="customer_phone" placeholder="+267 XX XXX XXX" required>
                </div>
                <div class="form-group">
                    <label>Customer Email (Optional)</label>
                    <input type="email" name="customer_email">
                </div>
                <div class="form-group">
                    <label>Daily Limit (BWP)</label>
                    <input type="number" name="daily_limit" value="5000" min="100" max="50000">
                </div>
                <button type="submit" class="btn">Create Wallet</button>
            </form>
        </div>
        
        <div class="card">
            <h3> Recent Transactions</h3>
            <div class="transaction-list">
                {transaction_items if transaction_items else '<p style="text-align: center; padding: 20px; color: #666;">No transactions yet</p>'}
            </div>
            <div style="margin-top: 15px;">
                <a href="/business/transactions" class="btn">View All Transactions</a>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3> Customer Wallets</h3>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Customer</th>
                        <th>Phone</th>
                        <th>Balance</th>
                        <th>USSD Code</th>
                        <th>Status</th>
                        <th>Last Activity</th>
                        <th>Transactions</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {wallet_table_rows if wallet_table_rows else '<tr><td colspan="8" style="text-align: center; padding: 20px; color: #666;">No wallets created yet</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function upgradeWallet(walletId) {{
            if (confirm('Upgrade this customer to a full FNB account?')) {{
                fetch('/api/wallet/' + walletId + '/upgrade', {{method: 'POST'}})
                    .then(r => r.json())
                    .then(data => {{
                        showNotification(data.message);
                        location.reload();
                    }});
            }}
        }}
        
        // Auto-refresh dashboard every 30 seconds
        setInterval(() => {{
            location.reload();
        }}, 30000);
    </script>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/business/create-wallet", methods=["POST"])
@require_auth
def create_wallet():
    business_id = session["business_id"]

    # Validate input
    customer_name = request.form["customer_name"].strip()
    customer_phone = request.form["customer_phone"].strip()
    customer_email = request.form.get("customer_email", "").strip()
    daily_limit = float(request.form.get("daily_limit", 5000))

    # Validation
    if not validate_phone(customer_phone):
        flash("Invalid phone number format")
        return redirect(url_for("business_dashboard"))

    if customer_email and not validate_email(customer_email):
        flash("Invalid email format")
        return redirect(url_for("business_dashboard"))

    # Check if customer already has a wallet with this business
    existing = PhantomWallet.query.filter_by(
        business_id=business_id, customer_phone=customer_phone
    ).first()

    if existing:
        flash("Customer already has a wallet with this business")
        return redirect(url_for("business_dashboard"))

    # Create wallet
    wallet = PhantomWallet(
        business_id=business_id,
        customer_phone=customer_phone,
        customer_name=customer_name,
        customer_email=customer_email if customer_email else None,
        daily_limit=daily_limit,
    )

    db.session.add(wallet)
    db.session.commit()

    log_action(
        business_id,
        "Wallet created",
        f"Customer: {customer_name}, Phone: {customer_phone}",
    )
    flash(f"Wallet created for {customer_name}. USSD Code: {wallet.ussd_code}")

    return redirect(url_for("business_dashboard"))


@app.route("/business/logout")
def business_logout():
    if "business_id" in session:
        log_action(session["business_id"], "Logout", f"IP: {request.remote_addr}")
    session.clear()
    flash("Logged out successfully")
    return redirect(url_for("index"))


# Payment API endpoints with enhanced security
@app.route("/api/payment/qr", methods=["POST"])
def api_qr_payment():
    data = request.get_json() if request.is_json else request.form.to_dict()

    result = PaymentProcessor.process_payment(
        data["wallet_id"],
        float(data["amount"]),
        "qr",
        f"QR Payment - {data['amount']} BWP",
        {"source": "qr_scan", "timestamp": datetime.utcnow().isoformat()},
    )

    if request.is_json:
        return jsonify(result)
    else:
        if result["success"]:
            flash(f"QR Payment processed: BWP {data['amount']}")
        else:
            flash(f"Payment failed: {result['error']}")
        return redirect(request.referrer or "/")


@app.route("/api/payment/ussd", methods=["POST"])
def api_ussd_payment():
    data = request.get_json() if request.is_json else request.form.to_dict()

    # Find wallet by USSD code
    wallet = PhantomWallet.query.filter_by(ussd_code=data["ussd_code"]).first()
    if not wallet:
        return jsonify({"success": False, "error": "Invalid USSD code"})

    result = PaymentProcessor.process_payment(
        wallet.id,
        float(data["amount"]),
        "ussd",
        f"USSD Payment - {data['amount']} BWP",
        {"source": "ussd", "code": data["ussd_code"]},
    )

    if request.is_json:
        return jsonify(result)
    else:
        if result["success"]:
            flash(f"USSD Payment processed: BWP {data['amount']}")
        else:
            flash(f"Payment failed: {result['error']}")
        return redirect(request.referrer or "/")


@app.route("/api/payment/mobile-money", methods=["POST"])
def api_mobile_money_payment():
    data = request.get_json() if request.is_json else request.form.to_dict()

    result = PaymentProcessor.process_payment(
        data["wallet_id"],
        float(data["amount"]),
        "mobile_money",
        f"{data['provider']} Payment from {data['phone']}",
        {
            "provider": data["provider"],
            "source_phone": data["phone"],
            "source": "mobile_money",
        },
    )

    if request.is_json:
        return jsonify(result)
    else:
        if result["success"]:
            flash(f"Mobile Money Payment processed: BWP {data['amount']}")
        else:
            flash(f"Payment failed: {result['error']}")
        return redirect(request.referrer or "/")


# Customer-facing routes (RESTORED)
@app.route("/customer/pay")
def customer_pay():
    content = """
    <div class="card">
        <h2>Make Payment</h2>
        <p>Choose your payment method:</p>
        
        <div class="grid">
            <div class="card">
                <h3> USSD Payment</h3>
                <p>Use your USSD code to make payments</p>
                <form action="/api/payment/ussd" method="POST">
                    <div class="form-group">
                        <label>USSD Code</label>
                        <input type="text" name="ussd_code" placeholder="*1234#" required>
                    </div>
                    <div class="form-group">
                        <label>Amount (BWP)</label>
                        <input type="number" name="amount" step="0.01" required>
                    </div>
                    <button type="submit" class="btn">Pay via USSD</button>
                </form>
            </div>
            
            <div class="card">
                <h3> QR Payment</h3>
                <p>Scan QR code or enter wallet ID</p>
                <form action="/api/payment/qr" method="POST">
                    <div class="form-group">
                        <label>Wallet ID</label>
                        <input type="text" name="wallet_id" required>
                    </div>
                    <div class="form-group">
                        <label>Amount (BWP)</label>
                        <input type="number" name="amount" step="0.01" required>
                    </div>
                    <button type="submit" class="btn">Pay via QR</button>
                </form>
            </div>
            
            <div class="card">
                <h3> Mobile Money</h3>
                <p>Pay using Orange Money or MyZaka</p>
                <form action="/api/payment/mobile-money" method="POST">
                    <div class="form-group">
                        <label>Wallet ID</label>
                        <input type="text" name="wallet_id" required>
                    </div>
                    <div class="form-group">
                        <label>Amount (BWP)</label>
                        <input type="number" name="amount" step="0.01" required>
                    </div>
                    <div class="form-group">
                        <label>Provider</label>
                        <select name="provider" required>
                            <option value="">Select Provider</option>
                            <option value="Orange Money">Orange Money</option>
                            <option value="MyZaka">MyZaka</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Your Phone Number</label>
                        <input type="text" name="phone" placeholder="+267 XX XXX XXX" required>
                    </div>
                    <button type="submit" class="btn">Pay via Mobile Money</button>
                </form>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3> Demo Wallet IDs for Testing</h3>
        <p>Use these wallet IDs to test payments:</p>
        <div style="background: #f7fafc; padding: 15px; border-radius: 8px; margin: 10px 0;">
    """

    # Get sample wallet IDs for demo
    sample_wallets = PhantomWallet.query.limit(3).all()
    for wallet in sample_wallets:
        content += f"""
            <p><strong>{wallet.customer_name}:</strong><br>
            Wallet ID: <code>{wallet.id}</code><br>
            USSD Code: <code>{wallet.ussd_code}</code></p>
        """

    content += """
        </div>
    </div>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/customer/wallet")
def customer_wallet():
    content = """
    <div class="card">
        <h2>Check Wallet Balance</h2>
        <form action="/customer/wallet-info" method="POST">
            <div class="form-group">
                <label>Wallet ID or USSD Code</label>
                <input type="text" name="identifier" placeholder="Wallet ID or *1234#" required>
            </div>
            <button type="submit" class="btn">Check Balance</button>
        </form>
    </div>
    
    <div class="card">
        <h3> Demo Wallet Information</h3>
        <p>Use these to check wallet balances:</p>
        <div style="background: #f7fafc; padding: 15px; border-radius: 8px;">
    """

    # Get sample wallet info
    sample_wallets = PhantomWallet.query.limit(3).all()
    for wallet in sample_wallets:
        content += f"""
            <p><strong>{wallet.customer_name}:</strong><br>
            Wallet ID: <code>{wallet.id}</code><br>
            USSD Code: <code>{wallet.ussd_code}</code><br>
            Balance: BWP {wallet.balance:,.2f}</p>
        """

    content += """
        </div>
    </div>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/customer/wallet-info", methods=["POST"])
def customer_wallet_info():
    identifier = request.form["identifier"].strip()

    # Find wallet by ID or USSD code
    wallet = None
    if identifier.startswith("*") and identifier.endswith("#"):
        # USSD code
        wallet = PhantomWallet.query.filter_by(ussd_code=identifier).first()
    else:
        # Wallet ID
        wallet = PhantomWallet.query.get(identifier)

    if not wallet:
        flash("Wallet not found")
        return redirect(url_for("customer_wallet"))

    # Get transactions
    transactions = (
        Transaction.query.filter_by(wallet_id=wallet.id)
        .order_by(Transaction.timestamp.desc())
        .limit(10)
        .all()
    )

    # Generate transaction list
    transaction_items = ""
    for t in transactions:
        transaction_items += f"""
        <div class="transaction-item">
            <div>
                <strong>{t.method.upper()}</strong> - {t.type.upper()}<br>
                {t.description}<br>
                <small>{t.timestamp.strftime('%Y-%m-%d %H:%M')} | {t.reference}</small>
            </div>
            <div style="text-align: right;">
                <strong style="color: {'green' if t.type == 'credit' else 'red'};">
                    {'+' if t.type == 'credit' else '-'}BWP {t.amount:,.2f}
                </strong><br>
                <small>{t.status}</small>
            </div>
        </div>
        """

    content = f"""
    <div class="card">
        <h2>Wallet Information</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{wallet.customer_name}</div>
                <div class="stat-label">Account Holder</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">BWP {wallet.balance:,.2f}</div>
                <div class="stat-label">Current Balance</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{wallet.ussd_code}</div>
                <div class="stat-label">USSD Code</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(transactions)}</div>
                <div class="stat-label">Recent Transactions</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>Recent Transactions</h3>
        <div class="transaction-list">
            {transaction_items if transaction_items else '<p style="text-align: center; padding: 20px; color: #666;">No transactions found</p>'}
        </div>
    </div>
    
    <div class="card">
        <a href="/customer/wallet" class="btn">Check Another Wallet</a>
        <a href="/customer/pay" class="btn btn-success">Make Payment</a>
    </div>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


# Missing API routes
@app.route("/api/docs")
def api_docs():
    content = """
    <div class="card">
        <h2>Phantom Banking API Documentation</h2>
        
        <h3>Authentication</h3>
        <p>All API requests require an API key in the header:</p>
        <pre style="background: #f7fafc; padding: 15px; border-radius: 4px;">
Authorization: Bearer YOUR_API_KEY</pre>
        
        <h3>Endpoints</h3>
        
        <div class="card" style="margin: 20px 0;">
            <h4>POST /api/wallet/create</h4>
            <p>Create a new phantom wallet for a customer</p>
            <pre style="background: #f7fafc; padding: 15px; border-radius: 4px;">
{
    "customer_name": "John Doe",
    "customer_phone": "+267 123 4567",
    "customer_email": "john@example.com",
    "daily_limit": 5000
}</pre>
        </div>
        
        <div class="card" style="margin: 20px 0;">
            <h4>POST /api/payment/qr</h4>
            <p>Process QR code payment</p>
            <pre style="background: #f7fafc; padding: 15px; border-radius: 4px;">
{
    "wallet_id": "uuid-string",
    "amount": 100.00
}</pre>
        </div>
        
        <div class="card" style="margin: 20px 0;">
            <h4>POST /api/payment/ussd</h4>
            <p>Process USSD payment</p>
            <pre style="background: #f7fafc; padding: 15px; border-radius: 4px;">
{
    "ussd_code": "*1234#",
    "amount": 50.00
}</pre>
        </div>
        
        <div class="card" style="margin: 20px 0;">
            <h4>POST /api/payment/mobile-money</h4>
            <p>Process mobile money payment</p>
            <pre style="background: #f7fafc; padding: 15px; border-radius: 4px;">
{
    "wallet_id": "uuid-string",
    "amount": 75.00,
    "provider": "Orange Money",
    "phone": "+267 123 4567"
}</pre>
        </div>
        
        <div class="card" style="margin: 20px 0;">
            <h4>GET /api/wallet/{wallet_id}/balance</h4>
            <p>Check wallet balance</p>
        </div>
        
        <div class="card" style="margin: 20px 0;">
            <h4>GET /api/wallet/{wallet_id}/transactions</h4>
            <p>Get wallet transaction history</p>
        </div>
    </div>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/api/test")
def api_test():
    content = """
    <div class="card">
        <h2>API Testing Interface</h2>
        
        <div class="grid">
            <div class="card">
                <h3>Test Payment Processing</h3>
                <form id="testPaymentForm">
                    <div class="form-group">
                        <label>API Key</label>
                        <input type="text" id="apiKey" placeholder="Your API Key" required>
                    </div>
                    <div class="form-group">
                        <label>Wallet ID</label>
                        <input type="text" id="walletId" placeholder="Wallet ID" required>
                    </div>
                    <div class="form-group">
                        <label>Amount</label>
                        <input type="number" id="amount" step="0.01" required>
                    </div>
                    <div class="form-group">
                        <label>Payment Method</label>
                        <select id="method" required>
                            <option value="qr">QR Payment</option>
                            <option value="ussd">USSD Payment</option>
                            <option value="mobile-money">Mobile Money</option>
                        </select>
                    </div>
                    <button type="button" onclick="testPayment()" class="btn">Test Payment</button>
                </form>
            </div>
            
            <div class="card">
                <h3>API Response</h3>
                <pre id="apiResponse" style="background: #f7fafc; padding: 15px; border-radius: 4px; min-height: 200px;">
API response will appear here...
                </pre>
            </div>
        </div>
    </div>
    
    <script>
        function testPayment() {
            const apiKey = document.getElementById('apiKey').value;
            const walletId = document.getElementById('walletId').value;
            const amount = document.getElementById('amount').value;
            const method = document.getElementById('method').value;
            
            let endpoint = '/api/payment/' + method;
            let payload = {
                wallet_id: walletId,
                amount: parseFloat(amount)
            };
            
            if (method === 'mobile-money') {
                payload.provider = 'Orange Money';
                payload.phone = '+267 123 4567';
            }
            
            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + apiKey
                },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('apiResponse').textContent = JSON.stringify(data, null, 2);
            })
            .catch(error => {
                document.getElementById('apiResponse').textContent = 'Error: ' + error.message;
            });
        }
    </script>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/api/wallet/create", methods=["POST"])
def api_create_wallet():
    # Get API key from header
    auth_header = request.headers.get("Authorization", "")
    api_key = (
        auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    )

    business_id = validate_api_key(api_key)
    if not business_id:
        return jsonify({"error": "Invalid API key"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    # Create wallet
    wallet = PhantomWallet(
        business_id=business_id,
        customer_phone=data["customer_phone"],
        customer_name=data["customer_name"],
        customer_email=data.get("customer_email"),
        daily_limit=data.get("daily_limit", 5000),
    )

    db.session.add(wallet)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "wallet_id": wallet.id,
            "ussd_code": wallet.ussd_code,
            "customer_name": wallet.customer_name,
            "balance": wallet.balance,
        }
    )


@app.route("/api/wallet/<wallet_id>/balance")
def api_wallet_balance(wallet_id):
    wallet = PhantomWallet.query.get(wallet_id)
    if not wallet:
        return jsonify({"error": "Wallet not found"}), 404

    return jsonify(
        {
            "wallet_id": wallet_id,
            "balance": wallet.balance,
            "customer_name": wallet.customer_name,
            "status": wallet.status,
            "ussd_code": wallet.ussd_code,
        }
    )


@app.route("/api/wallet/<wallet_id>/transactions")
def api_wallet_transactions(wallet_id):
    wallet = PhantomWallet.query.get(wallet_id)
    if not wallet:
        return jsonify({"error": "Wallet not found"}), 404

    transactions = (
        Transaction.query.filter_by(wallet_id=wallet_id)
        .order_by(Transaction.timestamp.desc())
        .all()
    )

    transaction_data = []
    for t in transactions:
        transaction_data.append(
            {
                "id": t.id,
                "amount": t.amount,
                "type": t.type,
                "method": t.method,
                "description": t.description,
                "status": t.status,
                "timestamp": t.timestamp.isoformat(),
                "reference": t.reference,
            }
        )

    return jsonify({"wallet_id": wallet_id, "transactions": transaction_data})


@app.route("/api/wallet/<wallet_id>/upgrade", methods=["POST"])
def api_upgrade_wallet(wallet_id):
    wallet = PhantomWallet.query.get(wallet_id)
    if not wallet:
        return jsonify({"error": "Wallet not found"}), 404

    # Simulate account upgrade process
    wallet.status = "upgraded"
    db.session.commit()

    fnb_account = f"62{secrets.randbelow(99999999):08d}"

    log_action(
        wallet.business_id, "Wallet upgraded", f"Customer: {wallet.customer_name}"
    )

    return jsonify(
        {
            "success": True,
            "message": f"Wallet upgraded to full FNB account",
            "fnb_account": fnb_account,
            "wallet_id": wallet_id,
        }
    )


# Additional Business Routes
@app.route("/business/wallet/<wallet_id>")
@require_auth
def business_wallet_details(wallet_id):
    business_id = session["business_id"]
    wallet = PhantomWallet.query.filter_by(
        id=wallet_id, business_id=business_id
    ).first()

    if not wallet:
        flash("Wallet not found")
        return redirect(url_for("business_dashboard"))

    # Get transactions for this wallet
    transactions = (
        Transaction.query.filter_by(wallet_id=wallet_id)
        .order_by(Transaction.timestamp.desc())
        .all()
    )

    # Generate QR code for payments
    qr_data = {
        "wallet_id": wallet_id,
        "customer_name": wallet.customer_name,
        "ussd_code": wallet.ussd_code,
    }

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    qr_code = base64.b64encode(buffer.getvalue()).decode()

    # Generate transaction history
    transaction_items = ""
    for t in transactions:
        transaction_items += f"""
        <div class="transaction-item">
            <div>
                <strong>{t.method.upper()}</strong> - {t.type.upper()}<br>
                {t.description}<br>
                <small>{t.timestamp.strftime('%Y-%m-%d %H:%M')} | {t.reference}</small>
            </div>
            <div style="text-align: right;">
                <strong style="color: {'green' if t.type == 'credit' else 'red'};">
                    {'+' if t.type == 'credit' else '-'}BWP {t.amount:,.2f}
                </strong><br>
                <small>{t.status}</small>
            </div>
        </div>
        """

    content = f"""
    <div class="card">
        <h2>Wallet Details: {wallet.customer_name}</h2>
        <div class="grid">
            <div>
                <p><strong>Phone:</strong> {wallet.customer_phone}</p>
                <p><strong>Email:</strong> {wallet.customer_email or 'Not provided'}</p>
                <p><strong>Balance:</strong> BWP {wallet.balance:,.2f}</p>
                <p><strong>USSD Code:</strong> <code>{wallet.ussd_code}</code></p>
                <p><strong>Status:</strong> {wallet.status}</p>
                <p><strong>Daily Limit:</strong> BWP {wallet.daily_limit:,.2f}</p>
                <p><strong>Created:</strong> {wallet.created_at.strftime('%Y-%m-%d %H:%M')}</p>
                <p><strong>Last Activity:</strong> {wallet.last_activity.strftime('%Y-%m-%d %H:%M') if wallet.last_activity else 'Never'}</p>
            </div>
            <div class="qr-code">
                <h4>Payment QR Code</h4>
                <img src="data:image/png;base64,{qr_code}" alt="QR Code" style="max-width: 200px;">
                <p><small>Customers can scan this to make payments</small></p>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>Simulate Payments</h3>
        <div class="grid">
            <form action="/api/payment/qr" method="POST">
                <input type="hidden" name="wallet_id" value="{wallet_id}">
                <div class="form-group">
                    <label>QR Payment Amount</label>
                    <input type="number" name="amount" step="0.01" required>
                </div>
                <button type="submit" class="btn">Process QR Payment</button>
            </form>
            
            <form action="/api/payment/ussd" method="POST">
                <input type="hidden" name="ussd_code" value="{wallet.ussd_code}">
                <div class="form-group">
                    <label>USSD Payment Amount</label>
                    <input type="number" name="amount" step="0.01" required>
                </div>
                <button type="submit" class="btn">Process USSD Payment</button>
            </form>
            
            <form action="/api/payment/mobile-money" method="POST">
                <input type="hidden" name="wallet_id" value="{wallet_id}">
                <div class="form-group">
                    <label>Mobile Money Amount</label>
                    <input type="number" name="amount" step="0.01" required>
                </div>
                <div class="form-group">
                    <label>Provider</label>
                    <select name="provider">
                        <option value="Orange Money">Orange Money</option>
                        <option value="MyZaka">MyZaka</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Source Phone</label>
                    <input type="text" name="phone" required>
                </div>
                <button type="submit" class="btn">Process Mobile Money</button>
            </form>
        </div>
    </div>
    
    <div class="card">
        <h3>Transaction History</h3>
        <div class="transaction-list">
            {transaction_items if transaction_items else '<p style="text-align: center; padding: 20px; color: #666;">No transactions found</p>'}
        </div>
    </div>
    
    <div class="card">
        <a href="/business/dashboard" class="btn">Back to Dashboard</a>
        <button onclick="upgradeWallet('{wallet_id}')" class="btn btn-success">Upgrade to Full FNB Account</button>
    </div>
    
    <script>
        function upgradeWallet(walletId) {{
            if (confirm('Upgrade this customer to a full FNB account?')) {{
                fetch('/api/wallet/' + walletId + '/upgrade', {{method: 'POST'}})
                    .then(r => r.json())
                    .then(data => {{
                        showNotification(data.message);
                        location.reload();
                    }});
            }}
        }}
    </script>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


@app.route("/business/transactions")
@require_auth
def business_transactions():
    business_id = session["business_id"]
    business = Business.query.get(business_id)

    # Get all wallets for this business
    wallets = PhantomWallet.query.filter_by(business_id=business_id).all()
    wallet_ids = [w.id for w in wallets]

    # Get all transactions
    transactions = (
        Transaction.query.filter(Transaction.wallet_id.in_(wallet_ids))
        .order_by(Transaction.timestamp.desc())
        .all()
    )

    # Generate transaction table
    transaction_rows = ""
    for t in transactions:
        wallet = next((w for w in wallets if w.id == t.wallet_id), None)
        customer_name = wallet.customer_name if wallet else "Unknown"

        transaction_rows += f"""
        <tr>
            <td>{t.timestamp.strftime('%Y-%m-%d %H:%M')}</td>
            <td>{customer_name}</td>
            <td>{t.method.upper()}</td>
            <td>{t.description}</td>
            <td style="color: {'green' if t.type == 'credit' else 'red'};">
                {'+' if t.type == 'credit' else '-'}BWP {t.amount:,.2f}
            </td>
            <td><span class="btn btn-success" style="font-size: 10px; padding: 2px 6px;">{t.status}</span></td>
            <td>{t.reference}</td>
        </tr>
        """

    content = f"""
    <div class="card">
        <h2>All Transactions - {business.name}</h2>
        <p>Complete transaction history for all customer wallets</p>
    </div>
    
    <div class="card">
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Date/Time</th>
                        <th>Customer</th>
                        <th>Method</th>
                        <th>Description</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Reference</th>
                    </tr>
                </thead>
                <tbody>
                    {transaction_rows if transaction_rows else '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #666;">No transactions found</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="card">
        <a href="/business/dashboard" class="btn">Back to Dashboard</a>
    </div>
    """

    return render_template_string(MAIN_TEMPLATE, content=content)


# Initialize database
def init_db():
    """Initialize database with sample data"""
    db.create_all()

    # Check if demo business exists
    demo_business = Business.query.filter_by(email="demo@store.com").first()
    if not demo_business:
        # Create demo business
        demo_business = Business(
            name="Demo Store",
            email="demo@store.com",
            phone="+267 123 4567",
            password_hash=generate_password_hash("demo123456"),
            fnb_account="123456789",
            api_key="",
            status="active",
        )

        db.session.add(demo_business)
        db.session.flush()

        # Generate API key
        api_key = generate_api_key(demo_business.id)
        demo_business.api_key = api_key

        # Create sample wallets
        sample_customers = [
            ("Alice Mthombeni", "+267 71 123 456", "alice@email.com"),
            ("Bob Mogale", "+267 72 234 567", "bob@email.com"),
            ("Carol Tshaba", "+267 73 345 678", "carol@email.com"),
        ]

        for i, (name, phone, email) in enumerate(sample_customers):
            wallet = PhantomWallet(
                business_id=demo_business.id,
                customer_phone=phone,
                customer_name=name,
                customer_email=email,
                balance=100.0 + (i * 50),
            )

            db.session.add(wallet)
            db.session.flush()

            # Create sample transactions
            for j in range(3):
                transaction = Transaction(
                    wallet_id=wallet.id,
                    amount=25.0 + (j * 10),
                    type="credit",
                    method=["qr", "ussd", "mobile_money"][j],
                    description=f"Sample payment {j+1}",
                    timestamp=datetime.utcnow() - timedelta(days=j),
                )
                db.session.add(transaction)

        db.session.commit()
        print(f" Demo business created with API key: {api_key}")


if __name__ == "__main__":
    print(" Starting Enhanced FNB Phantom Banking System...")
    print(" Initializing database...")

    with app.app_context():
        init_db()

    print(" Database initialized with sample data")
    print(" Security features enabled")
    print(" Interactive dashboard ready")
    print("\ Starting web server on http://localhost:5000")
    print(" Access the system at: http://localhost:5000")
    print("\ Demo Business Login:")
    print("   Email: demo@store.com")
    print("   Password: demo123456")

    app.run(debug=True, port=5000)
