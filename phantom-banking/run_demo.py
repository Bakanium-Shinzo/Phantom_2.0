"""
FNB Phantom Banking - Demo Runner (Windows Compatible)
Orchestrates the complete demo by running both backend API and frontend interface
"""

import subprocess
import sys
import time
import threading
import webbrowser
import os
import signal
from pathlib import Path


class PhantomBankingDemo:
    def __init__(self):
        self.api_process = None
        self.streamlit_process = None
        self.running = False

    def check_dependencies(self):
        """Check if all required dependencies are installed"""
        print("Checking dependencies...")

        required_packages = [
            "streamlit",
            "flask",
            "flask-cors",
            "pandas",
            "plotly",
            "requests",
        ]

        missing_packages = []

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            print(f"[ERROR] Missing packages: {', '.join(missing_packages)}")
            print(f"Install with: pip install {' '.join(missing_packages)}")
            return False

        print("[OK] All dependencies installed")
        return True

    def check_files(self):
        """Check if all required files exist"""
        print("Checking required files...")

        required_files = ["database.py", "api_server.py", "streamlit_app.py"]

        missing_files = []

        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)

        if missing_files:
            print(f"[ERROR] Missing files: {', '.join(missing_files)}")
            print("Make sure all Python files are in the same directory")
            return False

        print("[OK] All required files found")
        return True

    def start_api_server(self):
        """Start the Flask API server"""
        print("Starting Flask API server...")
        try:
            self.api_process = subprocess.Popen(
                [sys.executable, "api_server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            # Wait a moment and check if process started successfully
            time.sleep(3)
            if self.api_process.poll() is None:
                print("[OK] API server started successfully (port 5000)")
                return True
            else:
                stdout, stderr = self.api_process.communicate()
                print(f"[ERROR] API server failed to start")
                print(f"Error: {stderr}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to start API server: {e}")
            return False

    def start_streamlit_app(self):
        """Start the Streamlit frontend"""
        print("Starting Streamlit frontend...")
        try:
            self.streamlit_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "streamlit_app.py",
                    "--server.headless=true",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            # Wait for Streamlit to start
            time.sleep(5)
            if self.streamlit_process.poll() is None:
                print("[OK] Streamlit frontend started successfully (port 8501)")
                return True
            else:
                stdout, stderr = self.streamlit_process.communicate()
                print(f"[ERROR] Streamlit failed to start")
                print(f"Error: {stderr}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to start Streamlit: {e}")
            return False

    def open_browser(self):
        """Open the demo in browser"""
        print("Opening demo in browser...")
        try:
            time.sleep(3)  # Give Streamlit time to fully start
            webbrowser.open("http://localhost:8501")
            print("[OK] Demo opened in browser")
        except Exception as e:
            print(f"[WARNING] Could not open browser automatically: {e}")
            print("Please open http://localhost:8501 manually")

    def cleanup(self):
        """Clean up processes"""
        print("\nCleaning up...")

        if self.api_process and self.api_process.poll() is None:
            print("Stopping API server...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=5)
                print("[OK] API server stopped")
            except subprocess.TimeoutExpired:
                self.api_process.kill()
                print("[OK] API server force-stopped")

        if self.streamlit_process and self.streamlit_process.poll() is None:
            print("Stopping Streamlit...")
            self.streamlit_process.terminate()
            try:
                self.streamlit_process.wait(timeout=5)
                print("[OK] Streamlit stopped")
            except subprocess.TimeoutExpired:
                self.streamlit_process.kill()
                print("[OK] Streamlit force-stopped")

        self.running = False
        print("[OK] Cleanup completed")

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\nReceived signal {signum}")
        self.cleanup()
        sys.exit(0)

    def run(self):
        """Run the complete demo"""
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        print("FNB Phantom Banking - Complete Demo")
        print("=" * 60)
        print("Banking-as-a-Service for Botswana's 636,000 Unbanked Citizens")
        print("=" * 60)

        # Pre-flight checks
        if not self.check_dependencies():
            return False

        if not self.check_files():
            return False

        # Start services
        if not self.start_api_server():
            return False

        if not self.start_streamlit_app():
            self.cleanup()
            return False

        self.running = True

        # Open browser
        browser_thread = threading.Thread(target=self.open_browser)
        browser_thread.daemon = True
        browser_thread.start()

        # Show access information
        print("\n" + "=" * 60)
        print("FNB Phantom Banking Demo is now running!")
        print("=" * 60)
        print("Frontend Dashboard: http://localhost:8501")
        print("Backend API:       http://localhost:5000")
        print("API Health Check:  http://localhost:5000/api/v1/health")
        print("=" * 60)
        print("\nDemo Features:")
        print("   Business Dashboard - Wallet management and analytics")
        print("   Mobile Interface  - Customer experience mockup")
        print("   API Documentation - Live testing and integration guide")
        print("\nMarket Impact:")
        print("   Target: 636,000 unbanked Botswanans (24% of population)")
        print("   Savings: 67% lower fees vs traditional mobile money")
        print("   Growth: 69.5% mobile money adoption ready for integration")
        print("\nPress Ctrl+C to stop the demo")
        print("=" * 60)

        # Keep running until interrupted
        try:
            while self.running:
                time.sleep(1)

                # Check if processes are still running
                if self.api_process.poll() is not None:
                    print("[WARNING] API server stopped unexpectedly")
                    break

                if self.streamlit_process.poll() is not None:
                    print("[WARNING] Streamlit stopped unexpectedly")
                    break

        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
        finally:
            self.cleanup()

        return True


def main():
    """Main entry point"""
    demo = PhantomBankingDemo()

    try:
        success = demo.run()
        if success:
            print("\n[OK] Demo completed successfully!")
        else:
            print("\n[ERROR] Demo failed to start properly")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        demo.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
