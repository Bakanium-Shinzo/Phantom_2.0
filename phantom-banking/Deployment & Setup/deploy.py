"""
FNB Phantom Banking - Deployment & Setup Script
Automated setup, dependency installation, and environment configuration
"""

import os
import sys
import subprocess
import platform
import sqlite3
import json
import time
from pathlib import Path
import shutil


class PhantomBankingDeployer:
    """Handles deployment and setup of Phantom Banking system"""

    def __init__(self):
        self.project_dir = Path.cwd()
        self.python_executable = sys.executable
        self.platform = platform.system()
        self.setup_log = []

    def log(self, message, level="INFO"):
        """Log setup messages"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.setup_log.append(log_entry)

    def check_python_version(self):
        """Check if Python version is compatible"""
        self.log("Checking Python version...")

        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.log(
                "Python 3.8+ required. Current version: {}.{}.{}".format(
                    version.major, version.minor, version.micro
                ),
                "ERROR",
            )
            return False

        self.log(f"Python {version.major}.{version.minor}.{version.micro} - OK")
        return True

    def check_required_files(self):
        """Check if all required files are present"""
        self.log("Checking required files...")

        required_files = [
            "database.py",
            "api_server.py",
            "streamlit_app.py",
            "config.py",
            "requirements.txt",
        ]

        missing_files = []
        for file in required_files:
            if not (self.project_dir / file).exists():
                missing_files.append(file)

        if missing_files:
            self.log(f"Missing files: {', '.join(missing_files)}", "ERROR")
            return False

        self.log("All required files present")
        return True

    def install_dependencies(self):
        """Install Python dependencies"""
        self.log("Installing dependencies...")

        try:
            # Check if pip is available
            subprocess.run(
                [self.python_executable, "-m", "pip", "--version"],
                check=True,
                capture_output=True,
            )

            # Install requirements
            requirements_file = self.project_dir / "requirements.txt"
            if requirements_file.exists():
                cmd = [
                    self.python_executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_file),
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    self.log("Dependencies installed successfully")
                    return True
                else:
                    self.log(
                        f"Failed to install dependencies: {result.stderr}", "ERROR"
                    )
                    return False
            else:
                self.log("requirements.txt not found", "ERROR")
                return False

        except subprocess.CalledProcessError:
            self.log("pip not available", "ERROR")
            return False

    def setup_database(self):
        """Initialize database with demo data"""
        self.log("Setting up database...")

        try:
            # Import and initialize database
            sys.path.append(str(self.project_dir))
            from database import PhantomBankingDB

            db = PhantomBankingDB()
            self.log("Database initialized with demo data")

            # Verify database setup
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM wallets")
            wallet_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM transactions")
            transaction_count = cursor.fetchone()[0]

            conn.close()

            self.log(
                f"Demo data: {wallet_count} wallets, {transaction_count} transactions"
            )
            return True

        except Exception as e:
            self.log(f"Database setup failed: {str(e)}", "ERROR")
            return False

    def create_environment_file(self):
        """Create environment configuration file"""
        self.log("Creating environment configuration...")

        env_content = """# FNB Phantom Banking Environment Configuration
# Copy this to .env and customize for your environment

# Environment
FLASK_ENV=hackathon
LOG_LEVEL=INFO

# Database
DATABASE_PATH=phantom_banking.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=5000
API_DEBUG=True
SECRET_KEY=phantom-banking-secret-key-2025

# Streamlit Configuration  
STREAMLIT_HOST=0.0.0.0
STREAMLIT_PORT=8501

# Integration APIs (Production)
ORANGE_MONEY_API_KEY=your_orange_api_key_here
MYZAKA_API_KEY=your_myzaka_api_key_here
USSD_API_KEY=your_ussd_api_key_here

# Security (Change in production)
JWT_SECRET=phantom-jwt-secret-2025
ENCRYPTION_KEY=phantom-encryption-2025

# Business Configuration
BUSINESS_NAME=Kgalagadi General Store
BUSINESS_ID=kgalagadi_store
"""

        env_file = self.project_dir / ".env.example"
        try:
            with open(env_file, "w") as f:
                f.write(env_content)
            self.log("Environment file created: .env.example")
            return True
        except Exception as e:
            self.log(f"Failed to create environment file: {str(e)}", "ERROR")
            return False

    def create_startup_scripts(self):
        """Create convenient startup scripts"""
        self.log("Creating startup scripts...")

        # Windows batch file
        if self.platform == "Windows":
            batch_content = f"""@echo off
echo Starting FNB Phantom Banking Demo...
echo.

REM Start API Server
echo Starting API Server on port 5000...
start "Phantom Banking API" {self.python_executable} api_server.py

REM Wait for API to start
timeout /t 3 > nul

REM Start Streamlit Frontend
echo Starting Streamlit Frontend on port 8501...
start "Phantom Banking Frontend" {self.python_executable} -m streamlit run streamlit_app.py

echo.
echo Demo started successfully!
echo Frontend: http://localhost:8501
echo API: http://localhost:5000
echo.
echo Press any key to continue...
pause > nul
"""

            batch_file = self.project_dir / "start_demo.bat"
            try:
                with open(batch_file, "w") as f:
                    f.write(batch_content)
                self.log("Windows startup script created: start_demo.bat")
            except Exception as e:
                self.log(f"Failed to create batch file: {str(e)}", "ERROR")

        # Unix shell script
        shell_content = f"""#!/bin/bash

echo "🏦 Starting FNB Phantom Banking Demo..."
echo "🇧🇼 Banking-as-a-Service for Botswana's Unbanked"
echo

# Function to check if port is in use
check_port() {{
    if lsof -i:$1 >/dev/null 2>&1; then
        echo "⚠️  Port $1 is already in use"
        return 1
    fi
    return 0
}}

# Check ports
if ! check_port 5000; then
    echo "Please stop the service using port 5000 and try again"
    exit 1
fi

if ! check_port 8501; then
    echo "Please stop the service using port 8501 and try again"  
    exit 1
fi

# Start API Server
echo "🚀 Starting API Server on port 5000..."
{self.python_executable} api_server.py &
API_PID=$!

# Wait for API to start
sleep 3

# Check if API started successfully
if ! curl -s http://localhost:5000/api/v1/health >/dev/null; then
    echo "❌ Failed to start API server"
    kill $API_PID 2>/dev/null
    exit 1
fi

echo "✅ API Server started successfully"

# Start Streamlit Frontend
echo "🌐 Starting Streamlit Frontend on port 8501..."
{self.python_executable} -m streamlit run streamlit_app.py --server.headless=true &
STREAMLIT_PID=$!

# Wait for Streamlit to start
sleep 5

echo
echo "🎉 Demo started successfully!"
echo "📊 Frontend Dashboard: http://localhost:8501"
echo "🔧 Backend API: http://localhost:5000"
echo "📖 API Health: http://localhost:5000/api/v1/health"
echo
echo "💡 Press Ctrl+C to stop the demo"

# Function to cleanup on exit
cleanup() {{
    echo
    echo "🛑 Stopping services..."
    kill $API_PID $STREAMLIT_PID 2>/dev/null
    echo "✅ Demo stopped"
    exit 0
}}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Keep script running
wait
"""

        shell_file = self.project_dir / "start_demo.sh"
        try:
            with open(shell_file, "w") as f:
                f.write(shell_content)

            # Make executable on Unix systems
            if self.platform in ["Linux", "Darwin"]:
                os.chmod(shell_file, 0o755)

            self.log("Shell startup script created: start_demo.sh")
        except Exception as e:
            self.log(f"Failed to create shell script: {str(e)}", "ERROR")

    def run_tests(self):
        """Run basic tests to verify setup"""
        self.log("Running verification tests...")

        try:
            # Test database connection
            from database import PhantomBankingDB

            db = PhantomBankingDB(":memory:")
            conn = db.get_connection()
            conn.close()
            self.log("Database test passed")

            # Test configuration
            from config import get_config

            config = get_config("hackathon")
            self.log("Configuration test passed")

            # Test API imports
            from api_server import app

            self.log("API server test passed")

            return True

        except Exception as e:
            self.log(f"Tests failed: {str(e)}", "ERROR")
            return False

    def create_readme_quick_start(self):
        """Create a quick start guide"""
        self.log("Creating quick start guide...")

        quick_start = """# 🚀 FNB Phantom Banking - Quick Start

## Instant Demo Setup

### 1. Run the Demo
```bash
# Option 1: All-in-one runner
python run_demo.py

# Option 2: Use startup scripts
./start_demo.sh          # Linux/Mac
start_demo.bat           # Windows

# Option 3: Manual startup
python api_server.py     # Terminal 1
streamlit run streamlit_app.py  # Terminal 2
```

### 2. Access the Demo
- 🌐 **Frontend:** http://localhost:8501
- 🔧 **API:** http://localhost:5000
- 📊 **Health Check:** http://localhost:5000/api/v1/health

### 3. Demo Features
- 🏪 **Business Dashboard** - Wallet management & analytics
- 📱 **Mobile Interface** - Customer experience mockup
- 🔧 **API Documentation** - Live testing & integration

### 4. Hackathon Highlights
- 🎯 **Target:** 636,000 unbanked Botswanans (24% of population)
- 💰 **Savings:** 67% lower fees vs traditional mobile money  
- 🚀 **Integration:** 15-minute API setup for businesses
- 🌍 **Impact:** Banking-as-a-Service for financial inclusion

### 5. Test Scenarios
```python
# Create a customer wallet
import requests

response = requests.post('http://localhost:5000/api/v1/wallets/create', json={
    'customer_name': 'Thabo Molefe',
    'customer_phone': '+26772345678'
})

wallet_id = response.json()['data']['wallet_id']
print(f"Wallet created: {wallet_id}")
```

### 6. Market Impact
- **FREE transfers** vs P92-99 mobile money fees
- **Multi-channel** integration (Orange Money, MyZaka, USSD)
- **Youth focus** (median age 23.4 years)
- **Rural access** via USSD codes (*167#)

---
**🏦 Ready to revolutionize banking in Botswana! 🇧🇼**
"""

        quick_start_file = self.project_dir / "QUICK_START.md"
        try:
            with open(quick_start_file, "w") as f:
                f.write(quick_start)
            self.log("Quick start guide created: QUICK_START.md")
        except Exception as e:
            self.log(f"Failed to create quick start guide: {str(e)}", "ERROR")

    def deploy(self):
        """Run complete deployment process"""
        print("🏦 FNB Phantom Banking - Deployment Script")
        print("=" * 60)
        print("🇧🇼 Setting up Banking-as-a-Service for Botswana's Unbanked")
        print("=" * 60)

        success = True

        # Pre-flight checks
        if not self.check_python_version():
            return False

        if not self.check_required_files():
            return False

        # Installation steps
        steps = [
            ("Installing dependencies", self.install_dependencies),
            ("Setting up database", self.setup_database),
            ("Creating environment config", self.create_environment_file),
            ("Creating startup scripts", self.create_startup_scripts),
            ("Running verification tests", self.run_tests),
            ("Creating quick start guide", self.create_readme_quick_start),
        ]

        for step_name, step_func in steps:
            self.log(f"\n📋 {step_name}...")
            if not step_func():
                success = False
                break

        # Final status
        print("\n" + "=" * 60)
        if success:
            print("🎉 Deployment completed successfully!")
            print("\n📋 Next Steps:")
            print("1. Run the demo: python run_demo.py")
            print("2. Open browser: http://localhost:8501")
            print("3. Test API: http://localhost:5000/api/v1/health")
            print("\n🎯 Ready for FNB Botswana Hackathon!")
            print("💳 Serving 636,000 unbanked Botswanans with 67% cost savings!")
        else:
            print("❌ Deployment failed!")
            print("📋 Check the error messages above and try again.")

        print("=" * 60)

        # Save setup log
        log_file = self.project_dir / "setup.log"
        try:
            with open(log_file, "w") as f:
                f.write("\n".join(self.setup_log))
            print(f"📄 Setup log saved: {log_file}")
        except:
            pass

        return success


def main():
    """Main deployment entry point"""
    deployer = PhantomBankingDeployer()

    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # Run quick test
            print("🧪 Running Quick Test...")
            return deployer.run_tests()
        elif sys.argv[1] == "--reset":
            # Reset database
            print("🔄 Resetting Database...")
            db_file = Path("phantom_banking.db")
            if db_file.exists():
                db_file.unlink()
                print("✅ Database reset")
            return deployer.setup_database()
        elif sys.argv[1] == "--help":
            print(
                """
🏦 FNB Phantom Banking Deployment Script

Usage:
  python deploy.py           # Full deployment
  python deploy.py --test    # Run verification tests
  python deploy.py --reset   # Reset database
  python deploy.py --help    # Show this help

After deployment:
  python run_demo.py         # Start complete demo
  ./start_demo.sh           # Use startup script (Unix)
  start_demo.bat            # Use startup script (Windows)
            """
            )
            return True

    # Run full deployment
    return deployer.deploy()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
