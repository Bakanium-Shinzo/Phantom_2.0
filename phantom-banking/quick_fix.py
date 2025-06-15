"""
Quick Fix Script for FNB Phantom Banking Streamlit Issues
Run this to fix the KeyError and missing submit button issues
"""

import sqlite3
import hashlib
import os

def quick_fix():
    """Quick fix for immediate issues"""
    print("🔧 FNB Phantom Banking - Quick Fix")
    print("=" * 40)
    
    # Check if database exists
    db_path = "phantom_banking.db"
    if not os.path.exists(db_path):
        print("❌ Database not found. Please run: python api_server.py")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("1. 🔍 Checking demo merchant...")
        
        # Check if main demo merchant exists
        cursor.execute("""
            SELECT id, business_name, email FROM merchants 
            WHERE email = 'admin@kgalagadi.store'
        """)
        
        main_merchant = cursor.fetchone()
        
        if not main_merchant:
            print("   Creating main demo merchant...")
            # Create the main demo merchant with consistent ID
            api_key = "pk_live_demo_key_12345"
            password_hash = hashlib.sha256("admin123".encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO merchants (id, business_name, email, phone, location, 
                                     business_type, fnb_account, password_hash, api_key, balance, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (
                'merchant_0918cd8a',
                'Kgalagadi General Store',
                'admin@kgalagadi.store',
                '+267 75 123 456',
                'Gaborone, Botswana',
                'General Store',
                '62012345678',
                password_hash,
                api_key,
                0.0
            ))
            print("   ✅ Created main demo merchant")
        else:
            print(f"   ✅ Found merchant: {main_merchant[1]} (ID: {main_merchant[0]})")
        
        print("2. 🔍 Checking demo customer...")
        
        # Check if main demo customer exists
        cursor.execute("""
            SELECT wallet_id, customer_name, customer_phone, balance FROM wallets 
            WHERE customer_phone = '+267 71 123 456'
        """)
        
        main_customer = cursor.fetchone()
        
        if not main_customer:
            print("   Creating main demo customer...")
            # Create main demo customer
            cursor.execute("""
                INSERT INTO wallets (wallet_id, business_id, customer_name, customer_phone,
                                   customer_email, balance, ussd_code, customer_pin, status, daily_limit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """, (
                'pw_bw_2024_12345678',
                'merchant_0918cd8a',
                'Thabo Molefe',
                '+267 71 123 456',
                'thabo@example.com',
                250.0,
                '*167*DEMO#',
                '1234',
                5000.0
            ))
            print("   ✅ Created main demo customer")
        else:
            print(f"   ✅ Found customer: {main_customer[1]} (Wallet: {main_customer[0]}, Balance: P{main_customer[3]:.2f})")
        
        print("3. 🔧 Ensuring all wallets have PINs...")
        
        # Ensure all wallets have PINs
        cursor.execute("UPDATE wallets SET customer_pin = '1234' WHERE customer_pin IS NULL")
        updated_pins = cursor.rowcount
        
        if updated_pins > 0:
            print(f"   ✅ Updated {updated_pins} wallets with default PIN")
        else:
            print("   ✅ All wallets already have PINs")
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Quick fix completed!")
        print("\n🔐 **Test Credentials:**")
        print("Merchant:")
        print("   Email: admin@kgalagadi.store")
        print("   Password: admin123")
        print("   Merchant ID: merchant_0918cd8a")
        print()
        print("Customer:")
        print("   Phone: +267 71 123 456")
        print("   PIN: 1234")
        print("   Wallet ID: pw_bw_2024_12345678")
        print()
        print("🚀 Now restart Streamlit:")
        print("   streamlit run streamlit_app.py")
        
    except Exception as e:
        print(f"❌ Error during quick fix: {e}")

if __name__ == "__main__":
    quick_fix()