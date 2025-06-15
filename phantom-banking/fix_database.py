"""
Database Fix Script for FNB Phantom Banking
Run this script to update your existing database with the customer_pin column
"""

import sqlite3
import sys
import os

def fix_database():
    """Fix the database schema to include customer_pin column"""
    db_path = "phantom_banking.db"
    
    if not os.path.exists(db_path):
        print("❌ Database file not found. Creating fresh database...")
        # Import and initialize the database properly
        try:
            from database import PhantomBankingDB
            db = PhantomBankingDB()
            print("✅ Fresh database created successfully!")
            return
        except ImportError:
            print("❌ Could not import database module. Make sure database.py is in the same directory.")
            return
    
    print(f"🔧 Fixing database schema in {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(wallets)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current wallets table columns: {columns}")
        
        schema_updated = False
        
        # Add customer_pin column if missing
        if 'customer_pin' not in columns:
            print("➕ Adding customer_pin column...")
            cursor.execute("ALTER TABLE wallets ADD COLUMN customer_pin TEXT")
            # Set default PIN for existing wallets
            cursor.execute("UPDATE wallets SET customer_pin = '1234' WHERE customer_pin IS NULL")
            print("✅ Added customer_pin column with default PIN '1234'")
            schema_updated = True
        else:
            print("✅ customer_pin column already exists")
        
        # Check if upgrade_suggestions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='upgrade_suggestions'")
        if not cursor.fetchone():
            print("➕ Creating upgrade_suggestions table...")
            cursor.execute("""
                CREATE TABLE upgrade_suggestions (
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
            print("✅ Created upgrade_suggestions table")
            schema_updated = True
        else:
            print("✅ upgrade_suggestions table already exists")
        
        # Commit changes
        if schema_updated:
            conn.commit()
            print("💾 Changes saved to database")
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(wallets)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Updated wallets table columns: {updated_columns}")
        
        if 'customer_pin' in updated_columns:
            print("🎉 Database fix completed successfully!")
            print("✅ You can now create wallets with PIN security")
        else:
            print("❌ Database fix failed - customer_pin column still missing")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        print("💡 Try deleting the phantom_banking.db file and restart the API server to create a fresh database")

if __name__ == "__main__":
    print("🏦 FNB Phantom Banking - Database Fix Utility")
    print("=" * 50)
    
    fix_database()
    
    print("\n" + "=" * 50)
    print("🚀 Next steps:")
    print("1. Restart the API server: python api_server.py")
    print("2. Restart Streamlit: streamlit run streamlit_app.py")
    print("3. Try creating a customer wallet again")