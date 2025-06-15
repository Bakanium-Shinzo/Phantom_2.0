"""
FNB Phantom Banking - Enhanced Database Setup (Windows Compatible)
Handles SQLite database initialization with authentication and demo data seeding
"""
'database.py'
import sqlite3
import uuid
import hashlib
from datetime import datetime, timedelta
import json
import random


class PhantomBankingDB:
    def __init__(self, db_path="phantom_banking.db"):
        self.db_path = db_path
        self.init_database()
        self.seed_demo_data()

    def hash_password(self, password):
        """Hash password for storage"""
        return hashlib.sha256(password.encode()).hexdigest()

    def init_database(self):
        """Initialize database tables with enhanced schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Drop existing tables to ensure clean schema
        print("[INFO] Recreating database tables with enhanced schema...")
        cursor.execute("DROP TABLE IF EXISTS notifications")
        cursor.execute("DROP TABLE IF EXISTS transactions")
        cursor.execute("DROP TABLE IF EXISTS wallets")
        cursor.execute("DROP TABLE IF EXISTS merchants")
        cursor.execute("DROP TABLE IF EXISTS businesses")

        # Create merchants table for business authentication
        cursor.execute("""
            CREATE TABLE merchants (
                id TEXT PRIMARY KEY,
                business_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                location TEXT,
                business_type TEXT,
                fnb_account TEXT,
                password_hash TEXT NOT NULL,
                api_key TEXT NOT NULL,
                balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)

        # Enhanced wallets table with business relationship and PIN security
        cursor.execute("""
            CREATE TABLE wallets (
                wallet_id TEXT PRIMARY KEY,
                business_id TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_email TEXT,
                balance REAL DEFAULT 0,
                daily_limit REAL DEFAULT 5000.0,
                ussd_code TEXT UNIQUE,
                customer_pin TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (business_id) REFERENCES merchants (id)
            )
        """)

        # Enhanced transactions table
        cursor.execute("""
            CREATE TABLE transactions (
                transaction_id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL,
                recipient_wallet_id TEXT,
                from_wallet TEXT,
                to_wallet TEXT,
                amount REAL NOT NULL,
                fee REAL DEFAULT 0,
                channel TEXT NOT NULL,
                status TEXT DEFAULT 'completed',
                description TEXT,
                external_reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wallet_id) REFERENCES wallets (wallet_id)
            )
        """)

        # Notifications table for real-time alerts
        cursor.execute("""
            CREATE TABLE notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_type TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Keep original businesses table for compatibility
        cursor.execute("""
            CREATE TABLE businesses (
                business_id TEXT PRIMARY KEY,
                business_name TEXT NOT NULL,
                api_key TEXT NOT NULL,
                balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        print("[OK] Enhanced database tables initialized")

    def seed_demo_data(self):
        """Populate database with comprehensive demo data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        print("[INFO] Seeding comprehensive demo data...")

        # Create demo merchants with authentication
        demo_merchants = [
            {
                'id': 'merchant_001',
                'business_name': 'Kgalagadi General Store',
                'email': 'admin@kgalagadi.store',
                'phone': '+267 75 123 456',
                'location': 'Gaborone, Botswana',
                'business_type': 'General Store',
                'fnb_account': '62012345678',
                'password': 'admin123',
                'api_key': 'pk_test_kgalagadi_1234567890'
            },
            {
                'id': 'merchant_002',
                'business_name': 'Motswana Hair Salon',
                'email': 'info@motswana.salon',
                'phone': '+267 75 234 567',
                'location': 'Francistown, Botswana',
                'business_type': 'Hair Salon',
                'fnb_account': '62023456789',
                'password': 'salon123',
                'api_key': 'pk_test_motswana_9876543210'
            },
            {
                'id': 'merchant_003',
                'business_name': 'Serowe Electronics',
                'email': 'contact@serowe.electronics',
                'phone': '+267 75 345 678',
                'location': 'Serowe, Botswana',
                'business_type': 'Electronics Shop',
                'fnb_account': '62034567890',
                'password': 'electronics123',
                'api_key': 'pk_test_serowe_1122334455'
            }
        ]

        for merchant in demo_merchants:
            cursor.execute("""
                INSERT INTO merchants (id, business_name, email, phone, location, 
                                     business_type, fnb_account, password_hash, api_key, balance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                merchant['id'],
                merchant['business_name'],
                merchant['email'],
                merchant['phone'],
                merchant['location'],
                merchant['business_type'],
                merchant['fnb_account'],
                self.hash_password(merchant['password']),
                merchant['api_key'],
                random.uniform(50000, 250000)
            ))

            # Create corresponding business entry for compatibility
            cursor.execute("""
                INSERT INTO businesses (business_id, business_name, api_key, balance)
                VALUES (?, ?, ?, ?)
            """, (
                merchant['id'],
                merchant['business_name'],
                merchant['api_key'],
                random.uniform(50000, 250000)
            ))

        print(f"[OK] Created {len(demo_merchants)} demo merchants")

        # Create comprehensive customer wallets
        demo_customers = [
            {'name': 'Thabo Molefe', 'phone': '+267 71 123 456', 'email': 'thabo.molefe@gmail.com', 'balance': 1245.50},
            {'name': 'Neo Kgomotso', 'phone': '+267 72 234 567', 'email': 'neo.kgomotso@gmail.com', 'balance': 890.00},
            {'name': 'Kabo Seretse', 'phone': '+267 73 345 678', 'email': 'kabo.seretse@gmail.com', 'balance': 0.00},
            {'name': 'Mpho Tebogo', 'phone': '+267 74 456 789', 'email': 'mpho.tebogo@gmail.com', 'balance': 3567.25},
            {'name': 'Lesego Bogatsu', 'phone': '+267 75 567 890', 'email': 'lesego.bogatsu@gmail.com', 'balance': 234.75},
            {'name': 'Keabetswe Motse', 'phone': '+267 76 678 901', 'email': 'keabetswe.motse@gmail.com', 'balance': 1567.00},
            {'name': 'Boitumelo Segwabe', 'phone': '+267 77 789 012', 'email': 'boitumelo.segwabe@gmail.com', 'balance': 789.25},
            {'name': 'Tshepiso Ramaboa', 'phone': '+267 78 890 123', 'email': 'tshepiso.ramaboa@gmail.com', 'balance': 2134.50},
            {'name': 'Gaone Mokgosi', 'phone': '+267 79 901 234', 'email': 'gaone.mokgosi@gmail.com', 'balance': 567.75},
            {'name': 'Phenyo Setlhare', 'phone': '+267 70 012 345', 'email': 'phenyo.setlhare@gmail.com', 'balance': 1823.00},
        ]

        merchant_ids = [m['id'] for m in demo_merchants]
        statuses = ['active', 'active', 'active', 'active', 'active', 'dormant', 'active', 'upgraded']

        for i, customer in enumerate(demo_customers):
            wallet_id = f"pw_bw_2024_{uuid.uuid4().hex[:8]}"
            ussd_code = f"*167*{uuid.uuid4().hex[:4].upper()}#"
            business_id = merchant_ids[i % len(merchant_ids)]
            status = statuses[i % len(statuses)]
            
            cursor.execute("""
                INSERT INTO wallets (wallet_id, business_id, customer_name, customer_phone,
                                   customer_email, balance, ussd_code, status, daily_limit,
                                   created_at, last_activity, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wallet_id,
                business_id,
                customer['name'],
                customer['phone'],
                customer['email'],
                customer['balance'],
                ussd_code,
                status,
                random.choice([1000, 2500, 5000, 7500, 10000]),
                datetime.now() - timedelta(days=random.randint(1, 90)),
                datetime.now() - timedelta(hours=random.randint(1, 72)),
                json.dumps({
                    'preferred_language': random.choice(['en', 'tn', 'fr']),
                    'notification_preferences': {'sms': True, 'email': True},
                    'created_via': 'merchant_dashboard'
                })
            ))

            # Create realistic transaction history for each wallet
            num_transactions = random.randint(5, 15)
            channels = ['orange_money', 'myzaka', 'phantom_wallet', 'ussd', 'qr_code']
            descriptions = [
                'Payment for groceries', 'Top-up from mobile money', 'Transfer to friend',
                'Bill payment - electricity', 'Transport fare', 'Airtime purchase',
                'Rent payment', 'Medical consultation', 'School fees', 'Shopping',
                'Fuel payment', 'Restaurant payment', 'Market purchase'
            ]

            for j in range(num_transactions):
                txn_id = f"txn_bw_2024_{uuid.uuid4().hex[:8]}"
                amount = round(random.uniform(25, 750), 2)
                channel = random.choice(channels)
                
                # Calculate realistic fees
                fee_schedule = {
                    'phantom_wallet': 0.0,
                    'orange_money': 2.50,
                    'myzaka': 3.00,
                    'ussd': 1.50,
                    'qr_code': 0.0
                }
                fee = fee_schedule.get(channel, 2.50)
                
                # Mix of incoming and outgoing transactions
                is_incoming = random.choice([True, False])
                
                cursor.execute("""
                    INSERT INTO transactions (transaction_id, wallet_id, from_wallet, to_wallet,
                                            amount, fee, channel, status, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    txn_id,
                    wallet_id,
                    None if is_incoming else wallet_id,
                    wallet_id if is_incoming else None,
                    amount,
                    0 if is_incoming else fee,
                    channel,
                    random.choice(['completed', 'completed', 'completed', 'pending']),
                    random.choice(descriptions),
                    datetime.now() - timedelta(
                        days=random.randint(0, 30),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                ))

        print(f"[OK] Created {len(demo_customers)} customer wallets with realistic transaction history")

        # Create demo notifications
        demo_notifications = [
            {
                'user_id': 'merchant_001',
                'user_type': 'merchant',
                'message': '🎉 New customer wallet created for Thabo Molefe',
                'type': 'success'
            },
            {
                'user_id': 'merchant_001',
                'user_type': 'merchant',
                'message': '💳 Payment of P450 received from Neo Kgomotso',
                'type': 'info'
            },
            {
                'user_id': '+267 71 123 456',
                'user_type': 'customer',
                'message': '💰 Your wallet has been created! Welcome to FNB Phantom Banking',
                'type': 'success'
            },
            {
                'user_id': '+267 72 234 567',
                'user_type': 'customer',
                'message': '✅ Payment of P125 sent successfully via Orange Money',
                'type': 'success'
            },
            {
                'user_id': 'merchant_002',
                'user_type': 'merchant',
                'message': '📊 Monthly transaction volume increased by 18%',
                'type': 'info'
            }
        ]

        for notif in demo_notifications:
            cursor.execute("""
                INSERT INTO notifications (id, user_id, user_type, message, type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                notif['user_id'],
                notif['user_type'],
                notif['message'],
                notif['type'],
                datetime.now() - timedelta(minutes=random.randint(5, 1440))
            ))

        print(f"[OK] Created {len(demo_notifications)} demo notifications")

        conn.commit()
        conn.close()
        
        print("\n🎉 Enhanced demo data seeded successfully!")
        print("\n📋 **Sample Login Credentials:**")
        print("=" * 50)
        print("🏪 **Merchants:**")
        for merchant in demo_merchants:
            print(f"   Email: {merchant['email']}")
            print(f"   Password: {merchant['password']}")
            print(f"   Business: {merchant['business_name']}")
            print()
        
        print("📱 **Customers:**")
        for customer in demo_customers[:3]:
            print(f"   Phone: {customer['phone']}")
            print(f"   Name: {customer['name']}")
            print(f"   PIN: 1234 (default for demo)")
            print()
        
        print("💡 **Features Included:**")
        print("   ✅ Merchant authentication system")
        print("   ✅ Customer wallet management")
        print("   ✅ Realistic transaction history")
        print("   ✅ Multi-channel payment support")
        print("   ✅ Real-time notifications")
        print("   ✅ Business analytics data")
        print("\n🚀 Database ready for interactive banking demo!")

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def add_notification(self, user_id, user_type, message, notif_type="info"):
        """Add notification to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO notifications (id, user_id, user_type, message, type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                user_id,
                user_type,
                message,
                notif_type,
                datetime.now()
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding notification: {e}")
            return False
        finally:
            conn.close()

    def get_merchant_by_email(self, email):
        """Get merchant by email for authentication"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, business_name, password_hash, status
                FROM merchants WHERE email = ?
            """, (email,))
            return cursor.fetchone()
        finally:
            conn.close()

    def get_wallet_by_phone(self, phone):
        """Get wallet by phone for customer authentication"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT wallet_id, customer_name, balance, status
                FROM wallets WHERE customer_phone = ? AND status = 'active'
            """, (phone,))
            return cursor.fetchone()
        finally:
            conn.close()


if __name__ == "__main__":
    # Initialize database for testing
    print("🏦 Initializing FNB Phantom Banking Database...")
    db = PhantomBankingDB()
    print("✅ FNB Phantom Banking Database initialized and ready!")
    print("💡 Run 'python api_server.py' and 'streamlit run streamlit_app.py' to start the demo!")