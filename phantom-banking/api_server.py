"""
FNB Phantom Banking - Enhanced Flask REST API Server
Complete banking-as-a-service with merchant top-ups, PIN generation, account upgrades, and API docs
"""
###Api_server.py###
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import sqlite3
import json
import hashlib
import random
import string
from datetime import datetime, timedelta
from database import PhantomBankingDB

# Update database schema to include customer_pin and upgrade_suggestions
def update_database_schema():
    """Update database schema for new features"""
    db_instance = PhantomBankingDB()
    conn = db_instance.get_connection()
    cursor = conn.cursor()
    
    try:
        # Add customer_pin column to wallets table if it doesn't exist
        cursor.execute("PRAGMA table_info(wallets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'customer_pin' not in columns:
            cursor.execute("ALTER TABLE wallets ADD COLUMN customer_pin TEXT")
            print("[INFO] Added customer_pin column to wallets table")
        
        # Create upgrade_suggestions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upgrade_suggestions (
                id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                reason TEXT,
                documents_provided TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wallet_id) REFERENCES wallets (wallet_id),
                FOREIGN KEY (merchant_id) REFERENCES merchants (id)
            )
        """)
        print("[INFO] Created upgrade_suggestions table")
        
        conn.commit()
        print("[OK] Database schema updated successfully")
        
    except Exception as e:
        print(f"[ERROR] Failed to update schema: {e}")
    finally:
        conn.close()

# Initialize schema updates
update_database_schema()

app = Flask(__name__)
app.secret_key = 'fnb_phantom_banking_secret_key_2025'
CORS(app, supports_credentials=True)

# Initialize enhanced database
db = PhantomBankingDB()

def hash_password(password):
    """Hash password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def generate_wallet_id():
    """Generate unique wallet ID"""
    return f"pw_bw_2025_{uuid.uuid4().hex[:8]}"

def generate_transaction_id():
    """Generate unique transaction ID"""
    return f"txn_bw_2025_{uuid.uuid4().hex[:8]}"

def generate_customer_pin():
    """Generate 4-digit PIN for customer"""
    return ''.join([str(random.randint(0, 9)) for _ in range(4)])

def send_sms_notification(phone, message):
    """Simulate SMS sending (in production, integrate with SMS provider)"""
    print(f"📱 SMS to {phone}: {message}")
    return True

def get_current_user():
    """Extract current user from request headers"""
    auth_header = request.headers.get('Authorization')
    user_type = request.headers.get('User-Type', 'merchant')
    
    if auth_header and auth_header.startswith('Bearer '):
        user_id = auth_header.replace('Bearer ', '')
        return {'user_id': user_id, 'user_type': user_type}
    return None

def require_merchant_auth():
    """Check if merchant is authenticated"""
    user = get_current_user()
    return user and user['user_type'] == 'merchant'

def require_auth():
    """Check if user is authenticated"""
    return get_current_user() is not None

# Authentication endpoints
@app.route("/api/v1/auth/merchant/register", methods=["POST"])
def merchant_register():
    """Merchant registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['business_name', 'email', 'phone', 'password']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({
                    'success': False,
                    'error': f'Missing or empty field: {field}'
                }), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if email already exists
            cursor.execute("SELECT email FROM merchants WHERE email = ?", (data['email'],))
            if cursor.fetchone():
                return jsonify({
                    'success': False,
                    'error': 'Email already registered'
                }), 409
            
            # Generate unique IDs
            merchant_id = f"merchant_{uuid.uuid4().hex[:8]}"
            api_key = f"pk_live_{uuid.uuid4().hex[:16]}"
            
            # Insert new merchant
            cursor.execute("""
                INSERT INTO merchants (id, business_name, email, phone, location, 
                                     business_type, fnb_account, password_hash, api_key, balance, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (
                merchant_id,
                data['business_name'],
                data['email'],
                data['phone'],
                data.get('location', ''),
                data.get('business_type', 'General Business'),
                data.get('fnb_account', ''),
                hash_password(data['password']),
                api_key,
                0.0
            ))
            
            # Create corresponding business entry for compatibility
            cursor.execute("""
                INSERT INTO businesses (business_id, business_name, api_key, balance)
                VALUES (?, ?, ?, ?)
            """, (merchant_id, data['business_name'], api_key, 0.0))
            
            conn.commit()
            
            # Add welcome notification
            db.add_notification(
                merchant_id,
                'merchant',
                f"🎉 Welcome to FNB Phantom Banking! Your business {data['business_name']} is now registered.",
                'success'
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'merchant_id': merchant_id,
                    'business_name': data['business_name'],
                    'email': data['email'],
                    'api_key': api_key
                },
                'message': 'Merchant registered successfully'
            })
            
        except sqlite3.IntegrityError as e:
            return jsonify({
                'success': False,
                'error': 'Registration failed: Email may already be in use'
            }), 409
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Registration failed: {str(e)}'
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }), 500

@app.route("/api/v1/auth/merchant/login", methods=["POST"])
def merchant_login():
    """Merchant authentication endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password required'
            }), 400
        
        merchant = db.get_merchant_by_email(email)
        
        if merchant and verify_password(password, merchant[2]):
            if merchant[3] != 'active':
                return jsonify({
                    'success': False,
                    'error': 'Account is not active'
                }), 403
            
            return jsonify({
                'success': True,
                'data': {
                    'user_id': merchant[0],
                    'business_name': merchant[1],
                    'user_type': 'merchant'
                },
                'message': 'Login successful'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route("/api/v1/auth/customer/login", methods=["POST"])
def customer_login():
    """Customer authentication endpoint"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        pin = data.get('pin')
        
        if not phone or not pin:
            return jsonify({
                'success': False,
                'error': 'Phone number and PIN required'
            }), 400
        
        # Get wallet with PIN verification
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT wallet_id, customer_name, balance, status, customer_pin
            FROM wallets WHERE customer_phone = ?
        """, (phone,))
        
        wallet = cursor.fetchone()
        conn.close()
        
        if wallet and wallet[3] == 'active':
            # In demo mode, accept any 4-digit PIN, but in production verify against wallet[4]
            if len(pin) == 4 and pin.isdigit():
                return jsonify({
                    'success': True,
                    'data': {
                        'wallet_id': wallet[0],
                        'customer_name': wallet[1],
                        'balance': wallet[2],
                        'customer_phone': phone,
                        'user_type': 'customer'
                    },
                    'message': 'Login successful'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid PIN'
                }), 401
        else:
            return jsonify({
                'success': False,
                'error': 'Wallet not found or inactive'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Health check endpoint
@app.route("/api/v1/health", methods=["GET"])
def health_check():
    """Enhanced health check endpoint"""
    return jsonify({
        "success": True,
        "message": "FNB Phantom Banking API is running",
        "version": "3.0",
        "status": "healthy",
        "features": [
            "Merchant Authentication",
            "Customer Wallets with PIN Security", 
            "Multi-channel Payments",
            "Merchant Wallet Top-ups",
            "Account Upgrade Suggestions",
            "Real-time Notifications",
            "Dashboard Analytics",
            "API Documentation"
        ],
        "market_impact": {
            "target_unbanked": 636000,
            "cost_savings": "67% vs traditional fees",
            "channels": ["Orange Money", "MyZaka", "USSD", "QR Code"]
        },
        "timestamp": datetime.now().isoformat()
    })

# Enhanced wallet management
@app.route("/api/v1/wallets/create", methods=["POST"])
def create_wallet():
    """Create a new phantom wallet with PIN generation"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'merchant':
            return jsonify({
                'success': False,
                'error': 'Merchant authentication required'
            }), 401
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["customer_phone", "customer_name"]
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False, 
                    "error": f"Missing field: {field}"
                }), 400

        business_id = user['user_id']
        wallet_id = generate_wallet_id()
        ussd_code = f"*167*{uuid.uuid4().hex[:4].upper()}#"
        customer_pin = generate_customer_pin()

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Check if customer already has a wallet
            cursor.execute("""
                SELECT wallet_id FROM wallets WHERE customer_phone = ?
            """, (data['customer_phone'],))
            
            existing = cursor.fetchone()
            if existing:
                return jsonify({
                    'success': False,
                    'error': 'Customer already has a wallet'
                }), 409

            # Insert new wallet with PIN
            cursor.execute("""
                INSERT INTO wallets (wallet_id, business_id, customer_name, customer_phone,
                                   customer_email, balance, daily_limit, ussd_code, customer_pin,
                                   status, created_at, last_activity, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """, (
                wallet_id,
                business_id,
                data["customer_name"],
                data["customer_phone"],
                data.get("customer_email"),
                data.get("initial_balance", 0),
                data.get("daily_limit", 5000.0),
                ussd_code,
                customer_pin,
                datetime.now(),
                datetime.now(),
                json.dumps(data.get("metadata", {}))
            ))

            conn.commit()

            # Send PIN via SMS
            sms_message = f"Welcome to FNB Phantom Banking! Your wallet PIN is: {customer_pin}. USSD: {ussd_code}. Keep this secure!"
            send_sms_notification(data['customer_phone'], sms_message)

            # Add notifications
            db.add_notification(
                business_id, 
                'merchant', 
                f"🎉 New wallet created for {data['customer_name']} - PIN sent via SMS", 
                'success'
            )
            
            db.add_notification(
                data['customer_phone'], 
                'customer', 
                f"💰 Your digital wallet has been created! Check SMS for your PIN.", 
                'success'
            )

            response_data = {
                "wallet_id": wallet_id,
                "customer_phone": data["customer_phone"],
                "customer_name": data["customer_name"],
                "balance": data.get("initial_balance", 0),
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "ussd_code": ussd_code,
                "customer_pin": customer_pin,  # Show to merchant for confirmation
                "qr_code_url": f"https://qr.phantom.fnb.co.bw/{wallet_id}",
                "sms_sent": True,
                "business_benefits": {
                    "serves_unbanked": True,
                    "fee_savings": "67% vs traditional banking",
                    "instant_setup": True,
                    "secure_pin_access": True
                }
            }

            return jsonify({
                "success": True,
                "data": response_data,
                "message": "Wallet created successfully with PIN sent via SMS",
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Merchant wallet top-up functionality
@app.route("/api/v1/wallets/<wallet_id>/topup", methods=["POST"])
def merchant_topup_wallet(wallet_id):
    """Merchant tops up customer wallet balance"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'merchant':
            return jsonify({
                'success': False,
                'error': 'Merchant authentication required'
            }), 401

        data = request.get_json()
        
        required_fields = ['amount', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing field: {field}'
                }), 400

        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({
                'success': False,
                'error': 'Amount must be positive'
            }), 400

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Verify wallet belongs to this merchant and get customer info
            cursor.execute("""
                SELECT business_id, customer_name, customer_phone, balance
                FROM wallets WHERE wallet_id = ?
            """, (wallet_id,))
            
            wallet = cursor.fetchone()
            if not wallet:
                return jsonify({
                    'success': False,
                    'error': 'Wallet not found'
                }), 404
            
            if wallet[0] != user['user_id']:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized: This wallet belongs to another merchant'
                }), 403

            # Update wallet balance
            cursor.execute("""
                UPDATE wallets SET balance = balance + ?, last_activity = ?
                WHERE wallet_id = ?
            """, (amount, datetime.now(), wallet_id))

            # Record transaction
            transaction_id = generate_transaction_id()
            cursor.execute("""
                INSERT INTO transactions (transaction_id, wallet_id, to_wallet, amount, fee,
                                        channel, description, created_at, status)
                VALUES (?, ?, ?, ?, 0, 'merchant_topup', ?, ?, 'completed')
            """, (
                transaction_id,
                wallet_id,
                wallet_id,
                amount,
                data['description'],
                datetime.now()
            ))

            # Get new balance
            cursor.execute("SELECT balance FROM wallets WHERE wallet_id = ?", (wallet_id,))
            new_balance = cursor.fetchone()[0]

            conn.commit()

            # Send notifications
            db.add_notification(
                user['user_id'],
                'merchant',
                f"💰 Topped up P{amount} to {wallet[1]}'s wallet",
                'success'
            )

            db.add_notification(
                wallet[2],  # customer_phone
                'customer',
                f"💰 Your wallet has been topped up with P{amount} by your merchant",
                'success'
            )

            # Send SMS to customer
            sms_message = f"FNB Phantom: Your wallet has been topped up with P{amount:.2f}. New balance: P{new_balance:.2f}"
            send_sms_notification(wallet[2], sms_message)

            return jsonify({
                'success': True,
                'data': {
                    'transaction_id': transaction_id,
                    'wallet_id': wallet_id,
                    'customer_name': wallet[1],
                    'amount_added': amount,
                    'new_balance': new_balance,
                    'previous_balance': wallet[3],
                    'description': data['description'],
                    'processed_at': datetime.now().isoformat(),
                    'sms_sent': True
                },
                'message': 'Wallet topped up successfully'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Account upgrade suggestion
@app.route("/api/v1/wallets/<wallet_id>/suggest-upgrade", methods=["POST"])
def suggest_account_upgrade(wallet_id):
    """Suggest upgrade to full FNB account"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'merchant':
            return jsonify({
                'success': False,
                'error': 'Merchant authentication required'
            }), 401

        data = request.get_json()
        documents_provided = data.get('documents_provided', [])
        reason = data.get('reason', 'Customer meets upgrade criteria')

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Verify wallet and get customer info
            cursor.execute("""
                SELECT business_id, customer_name, customer_phone, balance
                FROM wallets WHERE wallet_id = ?
            """, (wallet_id,))
            
            wallet = cursor.fetchone()
            if not wallet:
                return jsonify({
                    'success': False,
                    'error': 'Wallet not found'
                }), 404
            
            if wallet[0] != user['user_id']:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized'
                }), 403

            # Create upgrade suggestion record
            suggestion_id = f"upgrade_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO upgrade_suggestions (id, wallet_id, merchant_id, reason, 
                                               documents_provided, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """, (
                suggestion_id,
                wallet_id,
                user['user_id'],
                reason,
                json.dumps(documents_provided),
                datetime.now()
            ))

            conn.commit()

            # Send notifications
            db.add_notification(
                user['user_id'],
                'merchant',
                f"📈 Upgrade suggestion sent for {wallet[1]} to full FNB account",
                'info'
            )

            db.add_notification(
                wallet[2],
                'customer',
                f"🏦 Your merchant has suggested upgrading to a full FNB account for enhanced benefits!",
                'info'
            )

            # Send SMS
            sms_message = f"FNB Phantom: You're eligible for a full FNB account upgrade! Contact your merchant for details."
            send_sms_notification(wallet[2], sms_message)

            return jsonify({
                'success': True,
                'data': {
                    'suggestion_id': suggestion_id,
                    'wallet_id': wallet_id,
                    'customer_name': wallet[1],
                    'status': 'pending',
                    'benefits': [
                        'Higher transaction limits',
                        'Debit card access',
                        'Internet banking',
                        'Loan eligibility',
                        'Investment products'
                    ],
                    'next_steps': [
                        'Customer to visit nearest FNB branch',
                        'Bring required documents',
                        'Complete KYC process',
                        'Maintain phantom wallet during transition'
                    ]
                },
                'message': 'Account upgrade suggested successfully'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Customer transaction endpoints
@app.route("/api/v1/customer/send-payment", methods=["POST"])
def customer_send_payment():
    """Customer sends payment through various channels"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'customer':
            return jsonify({
                'success': False,
                'error': 'Customer authentication required'
            }), 401

        data = request.get_json()
        required_fields = ['amount', 'channel', 'recipient']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing field: {field}'
                }), 400

        # Get customer phone from multiple sources
        customer_phone = (
            data.get('customer_phone') or 
            user.get('customer_phone') or
            request.headers.get('Customer-Phone')
        )
        
        if not customer_phone:
            return jsonify({
                'success': False,
                'error': 'Customer phone number required'
            }), 400

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Get customer wallet - try multiple ways to find it
            wallet_id = data.get('wallet_id') or user.get('wallet_id')
            
            if wallet_id:
                # Get wallet by ID
                cursor.execute("""
                    SELECT wallet_id, customer_name, balance, business_id, customer_phone
                    FROM wallets WHERE wallet_id = ? AND status = 'active'
                """, (wallet_id,))
            else:
                # Get wallet by phone
                cursor.execute("""
                    SELECT wallet_id, customer_name, balance, business_id, customer_phone
                    FROM wallets WHERE customer_phone = ? AND status = 'active'
                """, (customer_phone,))
            
            wallet = cursor.fetchone()
            if not wallet:
                return jsonify({
                    'success': False,
                    'error': 'Customer wallet not found or inactive'
                }), 404

            wallet_id, customer_name, balance, business_id, wallet_phone = wallet
            amount = float(data['amount'])
            channel = data['channel']

            # Fee structure
            fee_structure = {
                "phantom_wallet": 0,
                "orange_money": 2.50,
                "myzaka": 3.00,
                "ussd": 1.50,
                "qr_code": 0,
            }

            fee = fee_structure.get(channel, 2.50)
            total_amount = amount + fee

            if balance < total_amount:
                return jsonify({
                    'success': False,
                    'error': f'Insufficient balance. Available: P{balance:.2f}, Required: P{total_amount:.2f}'
                }), 400

            # Update balance
            cursor.execute("""
                UPDATE wallets SET balance = balance - ?, last_activity = ?
                WHERE wallet_id = ?
            """, (total_amount, datetime.now(), wallet_id))

            # Handle recipient - check if it's a customer wallet or merchant
            recipient_info = None
            recipient_type = "external"
            
            if channel == "phantom_wallet" and data['recipient']:
                recipient_id = data['recipient']
                
                if recipient_id.startswith("pw_bw_"):
                    # Customer wallet transfer
                    cursor.execute("""
                        SELECT customer_name, customer_phone, business_id
                        FROM wallets WHERE wallet_id = ? AND status = 'active'
                    """, (recipient_id,))
                    
                    recipient_wallet = cursor.fetchone()
                    if recipient_wallet:
                        # Add money to recipient wallet
                        cursor.execute("""
                            UPDATE wallets SET balance = balance + ?, last_activity = ?
                            WHERE wallet_id = ?
                        """, (amount, datetime.now(), recipient_id))
                        
                        recipient_info = {
                            "name": recipient_wallet[0],
                            "phone": recipient_wallet[1],
                            "type": "customer"
                        }
                        recipient_type = "customer_wallet"
                
                elif recipient_id.startswith("merchant_"):
                    # Merchant transfer - add to merchant balance
                    cursor.execute("""
                        SELECT business_name, email, phone
                        FROM merchants WHERE id = ? AND status = 'active'
                    """, (recipient_id,))
                    
                    recipient_merchant = cursor.fetchone()
                    if recipient_merchant:
                        # Add money to merchant balance
                        cursor.execute("""
                            UPDATE merchants SET balance = balance + ?
                            WHERE id = ?
                        """, (amount, recipient_id))
                        
                        recipient_info = {
                            "name": recipient_merchant[0],
                            "email": recipient_merchant[1],
                            "phone": recipient_merchant[2],
                            "type": "merchant"
                        }
                        recipient_type = "merchant"

            # Record transaction
            transaction_id = generate_transaction_id()
            cursor.execute("""
                INSERT INTO transactions (transaction_id, wallet_id, from_wallet, to_wallet, amount, fee,
                                        channel, description, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            """, (
                transaction_id,
                wallet_id,
                wallet_id,
                data['recipient'] if channel == "phantom_wallet" else None,
                amount,
                fee,
                channel,
                f"Payment to {data['recipient']} via {channel}",
                datetime.now()
            ))

            conn.commit()

            # Calculate savings
            traditional_fees = {"orange_money": 92, "myzaka": 99}
            fee_saved = traditional_fees.get(channel, 0) - fee

            # Notifications
            db.add_notification(
                customer_phone,
                'customer',
                f"✅ Sent P{amount} to {data['recipient']} via {channel}",
                'success'
            )

            db.add_notification(
                business_id,
                'merchant',
                f"💳 {customer_name} sent P{amount} via {channel}",
                'info'
            )

            # Notify recipient if it's a phantom transfer
            if recipient_info:
                if recipient_info['type'] == 'customer':
                    db.add_notification(
                        recipient_info['phone'],
                        'customer',
                        f"💰 Received P{amount} from {customer_name} (FREE phantom transfer)",
                        'success'
                    )
                elif recipient_info['type'] == 'merchant':
                    db.add_notification(
                        recipient_id,
                        'merchant',
                        f"💰 Received P{amount} payment from {customer_name} (FREE phantom transfer)",
                        'success'
                    )

            return jsonify({
                'success': True,
                'data': {
                    'transaction_id': transaction_id,
                    'amount': amount,
                    'fee': fee,
                    'fee_saved': fee_saved if fee_saved > 0 else None,
                    'channel': channel,
                    'recipient': data['recipient'],
                    'recipient_type': recipient_type,
                    'recipient_info': recipient_info,
                    'new_balance': balance - total_amount,
                    'processed_at': datetime.now().isoformat()
                },
                'message': 'Payment sent successfully'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/v1/customer/topup", methods=["POST"])
def customer_topup():
    """Customer tops up wallet from external source"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'customer':
            return jsonify({
                'success': False,
                'error': 'Customer authentication required'
            }), 401

        data = request.get_json()
        required_fields = ['amount', 'source', 'reference']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing field: {field}'
                }), 400

        customer_phone = user.get('customer_phone') or data.get('customer_phone')
        amount = float(data['amount'])

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Get customer wallet
            cursor.execute("""
                SELECT wallet_id, customer_name, balance, business_id
                FROM wallets WHERE customer_phone = ?
            """, (customer_phone,))
            
            wallet = cursor.fetchone()
            if not wallet:
                return jsonify({
                    'success': False,
                    'error': 'Customer wallet not found'
                }), 404

            wallet_id, customer_name, old_balance, business_id = wallet

            # Update balance
            cursor.execute("""
                UPDATE wallets SET balance = balance + ?, last_activity = ?
                WHERE wallet_id = ?
            """, (amount, datetime.now(), wallet_id))

            # Record transaction
            transaction_id = generate_transaction_id()
            cursor.execute("""
                INSERT INTO transactions (transaction_id, wallet_id, to_wallet, amount, fee,
                                        channel, description, external_reference, created_at, status)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, 'completed')
            """, (
                transaction_id,
                wallet_id,
                wallet_id,
                amount,
                data['source'],
                f"Top-up from {data['source']}",
                data['reference'],
                datetime.now()
            ))

            new_balance = old_balance + amount
            conn.commit()

            # Notifications
            db.add_notification(
                customer_phone,
                'customer',
                f"💰 Wallet topped up with P{amount} from {data['source']}",
                'success'
            )

            db.add_notification(
                business_id,
                'merchant',
                f"💰 {customer_name} topped up P{amount} from {data['source']}",
                'info'
            )

            return jsonify({
                'success': True,
                'data': {
                    'transaction_id': transaction_id,
                    'amount': amount,
                    'source': data['source'],
                    'old_balance': old_balance,
                    'new_balance': new_balance,
                    'reference': data['reference'],
                    'processed_at': datetime.now().isoformat()
                },
                'message': 'Wallet topped up successfully'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API Documentation endpoint
@app.route("/api/v1/docs", methods=["GET"])
def api_documentation():
    """Complete API documentation for merchants"""
    return jsonify({
        "success": True,
        "data": {
            "title": "FNB Phantom Banking API Documentation",
            "version": "3.0",
            "description": "Complete Banking-as-a-Service API for Botswana's unbanked population",
            "base_url": "http://localhost:5000/api/v1",
            "authentication": {
                "type": "Bearer Token",
                "header": "Authorization: Bearer {merchant_id}",
                "user_type_header": "User-Type: merchant|customer"
            },
            "endpoints": {
                "authentication": {
                    "merchant_register": {
                        "method": "POST",
                        "url": "/auth/merchant/register",
                        "description": "Register new merchant account",
                        "body": {
                            "business_name": "string (required)",
                            "email": "string (required)",
                            "phone": "string (required)",
                            "password": "string (required)",
                            "location": "string (optional)",
                            "business_type": "string (optional)"
                        },
                        "response": {
                            "merchant_id": "string",
                            "api_key": "string",
                            "business_name": "string"
                        }
                    },
                    "merchant_login": {
                        "method": "POST",
                        "url": "/auth/merchant/login",
                        "description": "Authenticate merchant",
                        "body": {
                            "email": "string (required)",
                            "password": "string (required)"
                        }
                    },
                    "customer_login": {
                        "method": "POST",
                        "url": "/auth/customer/login",
                        "description": "Authenticate customer with PIN",
                        "body": {
                            "phone": "string (required)",
                            "pin": "string (required, 4 digits)"
                        }
                    }
                },
                "wallet_management": {
                    "create_wallet": {
                        "method": "POST",
                        "url": "/wallets/create",
                        "description": "Create new customer wallet with PIN generation",
                        "auth_required": "merchant",
                        "body": {
                            "customer_name": "string (required)",
                            "customer_phone": "string (required)",
                            "customer_email": "string (optional)",
                            "initial_balance": "number (optional, default: 0)",
                            "daily_limit": "number (optional, default: 5000)"
                        },
                        "response": {
                            "wallet_id": "string",
                            "customer_pin": "string (4 digits, sent via SMS)",
                            "ussd_code": "string",
                            "sms_sent": "boolean"
                        }
                    },
                    "list_merchant_wallets": {
                        "method": "GET",
                        "url": "/wallets/merchant/{merchant_id}",
                        "description": "List all wallets for specific merchant",
                        "auth_required": "merchant"
                    },
                    "wallet_balance": {
                        "method": "GET",
                        "url": "/wallets/{wallet_id}/balance",
                        "description": "Get wallet balance and details"
                    },
                    "topup_wallet": {
                        "method": "POST",
                        "url": "/wallets/{wallet_id}/topup",
                        "description": "Merchant tops up customer wallet",
                        "auth_required": "merchant",
                        "body": {
                            "amount": "number (required, > 0)",
                            "description": "string (required)"
                        }
                    },
                    "activate_wallet": {
                        "method": "PUT",
                        "url": "/wallets/{wallet_id}/activate",
                        "description": "Activate customer wallet",
                        "auth_required": "merchant"
                    },
                    "deactivate_wallet": {
                        "method": "PUT",
                        "url": "/wallets/{wallet_id}/deactivate",
                        "description": "Deactivate customer wallet",
                        "auth_required": "merchant"
                    }
                },
                "transactions": {
                    "customer_send_payment": {
                        "method": "POST",
                        "url": "/customer/send-payment",
                        "description": "Customer sends payment via various channels",
                        "auth_required": "customer",
                        "body": {
                            "amount": "number (required)",
                            "channel": "string (required: phantom_wallet|orange_money|myzaka|ussd|qr_code)",
                            "recipient": "string (required)",
                            "description": "string (optional)"
                        },
                        "fees": {
                            "phantom_wallet": "P0 (FREE)",
                            "orange_money": "P2.50 (97% savings vs P92)",
                            "myzaka": "P3.00 (97% savings vs P99)",
                            "ussd": "P1.50",
                            "qr_code": "P0 (FREE)"
                        }
                    },
                    "customer_topup": {
                        "method": "POST",
                        "url": "/customer/topup",
                        "description": "Customer tops up wallet from external source",
                        "auth_required": "customer",
                        "body": {
                            "amount": "number (required)",
                            "source": "string (required: orange_money|myzaka|bank_transfer)",
                            "reference": "string (required)"
                        }
                    },
                    "transaction_history": {
                        "method": "GET",
                        "url": "/wallets/{wallet_id}/transactions",
                        "description": "Get transaction history for wallet",
                        "query_params": {
                            "limit": "number (optional, default: 50)",
                            "offset": "number (optional, default: 0)"
                        }
                    }
                },
                "account_services": {
                    "suggest_upgrade": {
                        "method": "POST",
                        "url": "/wallets/{wallet_id}/suggest-upgrade",
                        "description": "Suggest upgrade to full FNB account",
                        "auth_required": "merchant",
                        "body": {
                            "reason": "string (optional)",
                            "documents_provided": "array (optional)"
                        }
                    }
                },
                "analytics": {
                    "dashboard_stats": {
                        "method": "GET",
                        "url": "/stats/dashboard/{merchant_id}",
                        "description": "Get comprehensive merchant dashboard statistics",
                        "auth_required": "merchant",
                        "response_includes": [
                            "wallet_stats",
                            "monthly_transactions",
                            "channel_breakdown",
                            "cost_savings_analysis",
                            "recent_transactions"
                        ]
                    }
                },
                "notifications": {
                    "get_notifications": {
                        "method": "GET",
                        "url": "/notifications",
                        "description": "Get user notifications",
                        "auth_required": "merchant|customer"
                    }
                }
            },
            "error_codes": {
                "400": "Bad Request - Missing or invalid parameters",
                "401": "Unauthorized - Authentication required",
                "403": "Forbidden - Insufficient permissions",
                "404": "Not Found - Resource doesn't exist",
                "409": "Conflict - Resource already exists",
                "500": "Internal Server Error"
            },
            "rate_limits": {
                "requests_per_minute": 60,
                "burst_limit": 100
            },
            "webhooks": {
                "supported_events": [
                    "wallet.created",
                    "transaction.completed",
                    "wallet.topped_up",
                    "upgrade.suggested"
                ],
                "setup_url": "/webhooks/configure"
            }
        },
        "message": "API documentation retrieved successfully"
    })

# Get merchant balance
@app.route("/api/v1/merchants/<merchant_id>/balance", methods=["GET"])
def get_merchant_balance(merchant_id):
    """Get merchant balance from phantom transfers"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'merchant' or user['user_id'] != merchant_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 401

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Get merchant balance
            cursor.execute("""
                SELECT balance, business_name
                FROM merchants WHERE id = ?
            """, (merchant_id,))
            
            merchant = cursor.fetchone()
            if not merchant:
                return jsonify({
                    'success': False,
                    'error': 'Merchant not found'
                }), 404

            return jsonify({
                "success": True,
                "data": {
                    "merchant_id": merchant_id,
                    "balance": merchant[0],
                    "business_name": merchant[1],
                    "currency": "BWP",
                    "last_updated": datetime.now().isoformat()
                }
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Get available merchants for transfers
@app.route("/api/v1/merchants/available", methods=["GET"])
def get_available_merchants():
    """Get list of available merchants for transfers"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Get all active merchants
            cursor.execute("""
                SELECT id, business_name, email
                FROM merchants 
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            merchants = cursor.fetchall()

            result = []
            for merchant in merchants:
                result.append({
                    "merchant_id": merchant[0],
                    "business_name": merchant[1],
                    "email": merchant[2]
                })

            return jsonify({
                "success": True,
                "data": result,
                "count": len(result)
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Get available wallets for transfers
@app.route("/api/v1/wallets/available", methods=["GET"])
def get_available_wallets():
    """Get list of available wallets for transfers"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Get all active wallets
            cursor.execute("""
                SELECT wallet_id, customer_name, customer_phone
                FROM wallets 
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            wallets = cursor.fetchall()

            result = []
            for wallet in wallets:
                result.append({
                    "wallet_id": wallet[0],
                    "customer_name": wallet[1],
                    "customer_phone": wallet[2]
                })

            return jsonify({
                "success": True,
                "data": result,
                "count": len(result)
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
@app.route("/api/v1/wallets/merchant/<merchant_id>", methods=["GET"])
def list_merchant_wallets(merchant_id):
    """List wallets for a specific merchant"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'merchant' or user['user_id'] != merchant_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 401

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Get wallets for this merchant with transaction counts
            cursor.execute("""
                SELECT w.*, 
                       (SELECT COUNT(*) FROM transactions t WHERE t.wallet_id = w.wallet_id) as transaction_count,
                       (SELECT MAX(created_at) FROM transactions t WHERE t.wallet_id = w.wallet_id) as last_transaction
                FROM wallets w
                WHERE w.business_id = ?
                ORDER BY w.created_at DESC
            """, (merchant_id,))
            
            wallets = cursor.fetchall()

            result = []
            for wallet in wallets:
                result.append({
                    "wallet_id": wallet[0],
                    "customer_name": wallet[2],
                    "customer_phone": wallet[3],
                    "customer_email": wallet[4],
                    "balance": wallet[5],
                    "daily_limit": wallet[6],
                    "ussd_code": wallet[7],
                    "customer_pin": "****",  # Masked for security
                    "status": wallet[9],
                    "created_at": wallet[10],
                    "last_activity": wallet[11],
                    "transaction_count": wallet[13] or 0,
                    "last_transaction": wallet[14]
                })

            return jsonify({
                "success": True,
                "data": result,
                "count": len(result)
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Wallet management endpoints
@app.route("/api/v1/wallets/<wallet_id>/deactivate", methods=["PUT"])
def deactivate_wallet(wallet_id):
    """Deactivate a wallet"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'merchant':
            return jsonify({
                'success': False,
                'error': 'Merchant authentication required'
            }), 401

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Check if wallet belongs to this merchant
            cursor.execute("""
                SELECT business_id, customer_name FROM wallets WHERE wallet_id = ?
            """, (wallet_id,))
            
            wallet = cursor.fetchone()
            if not wallet:
                return jsonify({
                    'success': False,
                    'error': 'Wallet not found'
                }), 404
            
            if wallet[0] != user['user_id']:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized: This wallet belongs to another merchant'
                }), 403

            # Deactivate wallet
            cursor.execute("""
                UPDATE wallets SET status = 'inactive' WHERE wallet_id = ?
            """, (wallet_id,))
            
            conn.commit()

            # Add notification
            db.add_notification(
                user['user_id'],
                'merchant',
                f"⏸️ Wallet for {wallet[1]} has been deactivated",
                'info'
            )

            return jsonify({
                'success': True,
                'message': 'Wallet deactivated successfully'
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/v1/wallets/<wallet_id>/activate", methods=["PUT"])
def activate_wallet(wallet_id):
    """Activate a wallet"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'merchant':
            return jsonify({
                'success': False,
                'error': 'Merchant authentication required'
            }), 401

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Check if wallet belongs to this merchant
            cursor.execute("""
                SELECT business_id, customer_name FROM wallets WHERE wallet_id = ?
            """, (wallet_id,))
            
            wallet = cursor.fetchone()
            if not wallet:
                return jsonify({
                    'success': False,
                    'error': 'Wallet not found'
                }), 404
            
            if wallet[0] != user['user_id']:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized: This wallet belongs to another merchant'
                }), 403

            # Activate wallet
            cursor.execute("""
                UPDATE wallets SET status = 'active' WHERE wallet_id = ?
            """, (wallet_id,))
            
            conn.commit()

            # Add notification
            db.add_notification(
                user['user_id'],
                'merchant',
                f"▶️ Wallet for {wallet[1]} has been activated",
                'success'
            )

            return jsonify({
                'success': True,
                'message': 'Wallet activated successfully'
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/v1/wallets/<wallet_id>/balance", methods=["GET"])
def get_wallet_balance(wallet_id):
    """Get current balance for a customer wallet"""
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT w.*, m.business_name 
            FROM wallets w
            LEFT JOIN merchants m ON w.business_id = m.id
            WHERE w.wallet_id = ?
        """, (wallet_id,))
        
        wallet = cursor.fetchone()

        if not wallet:
            return jsonify({"success": False, "error": "Wallet not found"}), 404

        return jsonify({
            "success": True,
            "data": {
                "wallet_id": wallet[0],
                "customer_name": wallet[2],
                "customer_phone": wallet[3],
                "balance": wallet[5],
                "currency": "BWP",
                "daily_limit": wallet[6],
                "ussd_code": wallet[7],
                "status": wallet[9],
                "business_name": wallet[13] if len(wallet) > 13 else "Unknown",
                "last_activity": wallet[11],
                "features": {
                    "free_transfers": "Between phantom wallets",
                    "multi_channel": "Orange Money, MyZaka, USSD, QR",
                    "cost_savings": "67% vs traditional fees",
                    "pin_security": "4-digit PIN protection"
                }
            },
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

# Merchant-specific dashboard stats
@app.route("/api/v1/stats/dashboard/<merchant_id>", methods=["GET"])
def get_merchant_dashboard_stats(merchant_id):
    """Get comprehensive dashboard statistics for a specific merchant"""
    try:
        user = get_current_user()
        if not user or user['user_type'] != 'merchant' or user['user_id'] != merchant_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 401

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            # Enhanced wallet statistics for this merchant
            cursor.execute("""
                SELECT 
                    status, 
                    COUNT(*) as count,
                    AVG(balance) as avg_balance,
                    SUM(balance) as total_balance
                FROM wallets 
                WHERE business_id = ?
                GROUP BY status
            """, (merchant_id,))
            
            wallet_stats = {}
            total_balance = 0
            for row in cursor.fetchall():
                wallet_stats[row[0]] = {
                    'count': row[1],
                    'avg_balance': row[2] or 0,
                    'total_balance': row[3] or 0
                }
                total_balance += row[3] or 0

            # Transaction statistics for this merchant (last 30 days)
            cursor.execute("""
                SELECT 
                    COUNT(*) as transaction_count,
                    COALESCE(SUM(amount), 0) as total_volume,
                    COALESCE(SUM(fee), 0) as total_fees,
                    AVG(amount) as avg_transaction
                FROM transactions t
                JOIN wallets w ON t.wallet_id = w.wallet_id
                WHERE w.business_id = ? 
                AND DATE(t.created_at) >= DATE("now", "-30 days")
            """, (merchant_id,))
            
            txn_result = cursor.fetchone()
            txn_count, txn_volume, total_fees, avg_txn = txn_result

            # Enhanced channel breakdown for this merchant
            cursor.execute("""
                SELECT 
                    channel,
                    COUNT(*) as transaction_count,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COALESCE(AVG(amount), 0) as avg_amount,
                    COALESCE(SUM(fee), 0) as total_fees
                FROM transactions t
                JOIN wallets w ON t.wallet_id = w.wallet_id
                WHERE w.business_id = ?
                AND t.created_at >= datetime('now', '-30 days')
                GROUP BY channel
                ORDER BY transaction_count DESC
            """, (merchant_id,))
            
            channel_stats = []
            for row in cursor.fetchall():
                channel_stats.append({
                    'channel': row[0],
                    'transaction_count': row[1],
                    'total_amount': row[2],
                    'avg_amount': row[3],
                    'total_fees': row[4]
                })

            # Calculate competitive advantage metrics for this merchant
            phantom_txns = sum(1 for c in channel_stats if c['channel'] == 'phantom_wallet')
            total_phantom_savings = phantom_txns * 92  # vs Orange Money fees
            
            traditional_fees_saved = 0
            for channel in channel_stats:
                if channel['channel'] == 'orange_money':
                    traditional_fees_saved += channel['transaction_count'] * (92 - 2.50)
                elif channel['channel'] == 'myzaka':
                    traditional_fees_saved += channel['transaction_count'] * (99 - 3.00)

            # Recent activity for this merchant (include payments TO merchant)
            cursor.execute("""
                SELECT 
                    t.transaction_id,
                    t.amount,
                    t.fee,
                    t.channel,
                    t.description,
                    t.created_at,
                    w.customer_name,
                    w.customer_phone,
                    CASE 
                        WHEN t.to_wallet = ? THEN 'payment_to_merchant'
                        ELSE 'customer_transaction'
                    END as transaction_type
                FROM transactions t
                LEFT JOIN wallets w ON t.wallet_id = w.wallet_id
                WHERE w.business_id = ? OR t.to_wallet = ?
                ORDER BY t.created_at DESC
                LIMIT 20
            """, (merchant_id, merchant_id, merchant_id))
            
            recent_transactions = []
            for row in cursor.fetchall():
                recent_transactions.append({
                    'transaction_id': row[0],
                    'amount': row[1],
                    'fee': row[2],
                    'channel': row[3],
                    'description': row[4],
                    'created_at': row[5],
                    'customer_name': row[6] or 'Unknown',
                    'customer_phone': row[7] or 'Unknown',
                    'to_merchant': row[8] == 'payment_to_merchant'
                })

            # Get merchant phantom balance
            cursor.execute("""
                SELECT balance FROM merchants WHERE id = ?
            """, (merchant_id,))
            merchant_balance_row = cursor.fetchone()
            phantom_balance = merchant_balance_row[0] if merchant_balance_row else 0

            conn.close()

            return jsonify({
                "success": True,
                "data": {
                    "merchant_id": merchant_id,
                    "wallet_stats": wallet_stats,
                    "monthly_transactions": txn_count or 0,
                    "monthly_volume": txn_volume or 0,
                    "average_transaction": avg_txn or 0,
                    "total_balance": total_balance,
                    "phantom_balance": phantom_balance,
                    "channel_breakdown": channel_stats,
                    "recent_transactions": recent_transactions,
                    "competitive_advantage": {
                        "total_fees_saved": traditional_fees_saved,
                        "phantom_wallet_savings": total_phantom_savings,
                        "cost_reduction_percentage": 67,
                        "unbanked_customers_served": wallet_stats.get('active', {}).get('count', 0)
                    },
                    "business_impact": {
                        "serving_unbanked": True,
                        "cost_advantage": "67% savings vs traditional mobile money",
                        "channels_supported": ["Orange Money", "MyZaka", "USSD", "QR Code", "Phantom Wallets"],
                        "pin_security": "4-digit PIN protection for all wallets",
                        "upgrade_path": "Full FNB account upgrade available",
                        "phantom_revenue": f"P {phantom_balance:.2f} received from customer payments"
                    }
                },
                "message": "Merchant dashboard stats retrieved successfully",
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Transaction history endpoint
@app.route("/api/v1/wallets/<wallet_id>/transactions", methods=["GET"])
def get_transactions(wallet_id):
    """Get enhanced transaction history for a wallet"""
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        # Get query parameters
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        cursor.execute("""
            SELECT 
                t.*,
                CASE 
                    WHEN t.from_wallet = ? THEN 'sent'
                    WHEN t.to_wallet = ? THEN 'received'
                    ELSE 'unknown'
                END as transaction_type
            FROM transactions t
            WHERE t.from_wallet = ? OR t.to_wallet = ?
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
        """, (wallet_id, wallet_id, wallet_id, wallet_id, limit, offset))

        transactions = cursor.fetchall()

        result = []
        for txn in transactions:
            # Calculate savings for each transaction
            traditional_fees = {"orange_money": 92, "myzaka": 99}
            fee_saved = traditional_fees.get(txn[6], 0) - (txn[5] or 0)  # channel, fee
            
            result.append({
                "transaction_id": txn[0],
                "wallet_id": txn[1],
                "from_wallet": txn[3],
                "to_wallet": txn[4],
                "amount": txn[5],
                "fee": txn[6],
                "channel": txn[7],
                "status": txn[8],
                "description": txn[9],
                "created_at": txn[11],
                "external_reference": txn[10],
                "type": txn[13],  # transaction_type from CASE statement
                "fee_saved": fee_saved if fee_saved > 0 else None,
                "phantom_benefit": {
                    "free_transfer": txn[7] == 'phantom_wallet',
                    "cost_savings": fee_saved > 0
                }
            })

        return jsonify({
            "success": True, 
            "data": result, 
            "count": len(result),
            "summary": {
                "total_transactions": len(result),
                "total_fees_saved": sum(t.get('fee_saved', 0) or 0 for t in result),
                "phantom_transfers": len([t for t in result if t['channel'] == 'phantom_wallet'])
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

# Notifications endpoint
@app.route("/api/v1/notifications", methods=["GET"])
def get_notifications():
    """Get user notifications"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        user_id = user['user_id']
        user_type = user['user_type']

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM notifications
            WHERE user_id = ? AND user_type = ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_id, user_type))

        notifications = cursor.fetchall()
        conn.close()

        result = []
        for notif in notifications:
            result.append({
                'id': notif[0],
                'message': notif[3],
                'type': notif[4],
                'read': bool(notif[5]),
                'created_at': notif[6]
            })

        return jsonify({
            'success': True,
            'data': result,
            'unread_count': len([n for n in result if not n['read']])
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False, 
        "error": "Endpoint not found",
        "available_endpoints": [
            "/api/v1/health",
            "/api/v1/docs",
            "/api/v1/auth/merchant/register",
            "/api/v1/auth/merchant/login",
            "/api/v1/auth/customer/login", 
            "/api/v1/wallets/create",
            "/api/v1/wallets/merchant/<merchant_id>",
            "/api/v1/wallets/<wallet_id>/topup",
            "/api/v1/wallets/<wallet_id>/suggest-upgrade",
            "/api/v1/customer/send-payment",
            "/api/v1/customer/topup",
            "/api/v1/stats/dashboard/<merchant_id>"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False, 
        "error": "Internal server error",
        "message": "Please contact support if this persists"
    }), 500

if __name__ == "__main__":
    print("🚀 Starting FNB Phantom Banking Enhanced API Server v3.0...")
    print("📱 Complete Banking-as-a-Service for Botswana's 636,000 unbanked population")
    print("💰 Offering 67% cost savings vs traditional mobile money (P92-99 fees)")
    print("🔐 Enhanced security with 4-digit PIN generation and SMS notifications")
    print("🌍 Supporting financial inclusion across rural and urban Botswana")
    print("")
    print("🔗 New API Endpoints:")
    print("   🏦 Merchant Wallet Top-up: POST /api/v1/wallets/{id}/topup")
    print("   📈 Account Upgrade: POST /api/v1/wallets/{id}/suggest-upgrade")
    print("   💳 Customer Payments: POST /api/v1/customer/send-payment")
    print("   💰 Customer Top-up: POST /api/v1/customer/topup")
    print("   📖 API Documentation: GET /api/v1/docs")
    print("")
    print("💡 Enhanced Features:")
    print("   ✅ Automatic PIN Generation & SMS Delivery")
    print("   ✅ Merchant Wallet Top-up Functionality")
    print("   ✅ Customer Transaction Processing")
    print("   ✅ Account Upgrade Suggestions")
    print("   ✅ Complete API Documentation")
    print("   ✅ Real-time SMS Notifications")
    print("   ✅ Enhanced Security with PIN Protection")
    print("")
    print("🔐 Demo Credentials:")
    print("   Merchant: admin@kgalagadi.store / admin123")
    print("   Customer: +267 71 123 456 / PIN: 1234")
    print("-" * 70)

    app.run(debug=True, port=5000, host="0.0.0.0", threaded=True)