"""
FNB Phantom Banking - Comprehensive Test Suite
Tests API functionality, database operations, and integration scenarios
"""

import unittest
import requests
import json
import time
import sqlite3
from datetime import datetime
import subprocess
import sys
import os
from config import TestingConfig, get_fee, validate_transaction_amount


class TestPhantomBankingAPI(unittest.TestCase):
    """Test suite for Phantom Banking API"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost:5000/api/v1"
        cls.test_wallet_ids = []
        cls.test_transaction_ids = []

        # Check if API server is running
        try:
            response = requests.get(f"{cls.base_url}/health", timeout=5)
            if response.status_code != 200:
                raise Exception("API server not responding")
        except:
            print("⚠️  API server not running. Starting test server...")
            # Note: In a real test environment, you'd start the server here
            raise unittest.SkipTest("API server not available for testing")

    def setUp(self):
        """Set up each test"""
        self.start_time = time.time()

    def tearDown(self):
        """Clean up after each test"""
        elapsed = time.time() - self.start_time
        print(f"  ⏱️  Test completed in {elapsed:.3f}s")

    def test_01_health_check(self):
        """Test API health check endpoint"""
        print("🔍 Testing health check...")

        response = requests.get(f"{self.base_url}/health")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "FNB Phantom Banking API is running")
        self.assertEqual(data["version"], "1.0")

        print("  ✅ Health check passed")

    def test_02_create_wallet(self):
        """Test wallet creation"""
        print("🔍 Testing wallet creation...")

        wallet_data = {
            "customer_name": "Test User",
            "customer_phone": "+26771234567",
            "initial_balance": 100.0,
            "metadata": {
                "test_case": "test_02_create_wallet",
                "created_via": "AUTOMATED_TEST",
            },
        }

        response = requests.post(f"{self.base_url}/wallets/create", json=wallet_data)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("wallet_id", data["data"])
        self.assertIn("ussd_code", data["data"])
        self.assertIn("qr_code_url", data["data"])

        # Store wallet ID for later tests
        wallet_id = data["data"]["wallet_id"]
        self.test_wallet_ids.append(wallet_id)
        TestPhantomBankingAPI.test_wallet_ids.append(wallet_id)

        print(f"  ✅ Wallet created: {wallet_id}")

    def test_03_create_wallet_validation(self):
        """Test wallet creation validation"""
        print("🔍 Testing wallet creation validation...")

        # Test missing required fields
        invalid_data = {
            "customer_name": "Test User"
            # Missing customer_phone
        }

        response = requests.post(f"{self.base_url}/wallets/create", json=invalid_data)

        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Missing field", data["error"])

        print("  ✅ Validation working correctly")

    def test_04_get_wallet_balance(self):
        """Test wallet balance retrieval"""
        print("🔍 Testing wallet balance retrieval...")

        if not self.test_wallet_ids:
            self.skipTest("No test wallets available")

        wallet_id = self.test_wallet_ids[0]
        response = requests.get(f"{self.base_url}/wallets/{wallet_id}/balance")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("balance", data["data"])
        self.assertIn("currency", data["data"])
        self.assertEqual(data["data"]["currency"], "BWP")

        print(f"  ✅ Balance retrieved: P{data['data']['balance']}")

    def test_05_get_nonexistent_wallet(self):
        """Test retrieval of non-existent wallet"""
        print("🔍 Testing non-existent wallet retrieval...")

        fake_wallet_id = "pw_bw_2024_nonexistent"
        response = requests.get(f"{self.base_url}/wallets/{fake_wallet_id}/balance")

        self.assertEqual(response.status_code, 404)

        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("not found", data["error"])

        print("  ✅ Non-existent wallet handling correct")

    def test_06_send_payment_phantom_to_phantom(self):
        """Test phantom-to-phantom payment (FREE)"""
        print("🔍 Testing phantom-to-phantom payment...")

        # Create two test wallets
        wallet1_data = {
            "customer_name": "Sender Test",
            "customer_phone": "+26771111111",
            "initial_balance": 500.0,
        }

        wallet2_data = {
            "customer_name": "Receiver Test",
            "customer_phone": "+26772222222",
            "initial_balance": 0.0,
        }

        # Create sender wallet
        response1 = requests.post(f"{self.base_url}/wallets/create", json=wallet1_data)
        self.assertEqual(response1.status_code, 200)
        sender_wallet = response1.json()["data"]["wallet_id"]
        self.test_wallet_ids.append(sender_wallet)

        # Create receiver wallet
        response2 = requests.post(f"{self.base_url}/wallets/create", json=wallet2_data)
        self.assertEqual(response2.status_code, 200)
        receiver_wallet = response2.json()["data"]["wallet_id"]
        self.test_wallet_ids.append(receiver_wallet)

        # Send payment
        payment_data = {
            "from_wallet": sender_wallet,
            "to_wallet": receiver_wallet,
            "amount": 150.0,
            "channel": "phantom_wallet",
            "description": "Test phantom-to-phantom payment",
        }

        response = requests.post(f"{self.base_url}/payments/send", json=payment_data)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["amount"], 150.0)
        self.assertEqual(data["data"]["fee"], 0.0)  # FREE for phantom-to-phantom
        self.assertEqual(data["data"]["channel"], "phantom_wallet")

        transaction_id = data["data"]["transaction_id"]
        self.test_transaction_ids.append(transaction_id)

        print(f"  ✅ Payment sent: {transaction_id}, Fee: P{data['data']['fee']}")

    def test_07_send_payment_external_channel(self):
        """Test payment via external channel (with fee)"""
        print("🔍 Testing external channel payment...")

        if not self.test_wallet_ids:
            self.skipTest("No test wallets available")

        sender_wallet = self.test_wallet_ids[0]

        payment_data = {
            "from_wallet": sender_wallet,
            "amount": 50.0,
            "channel": "orange_money",
            "description": "Test Orange Money payment",
        }

        response = requests.post(f"{self.base_url}/payments/send", json=payment_data)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["amount"], 50.0)
        self.assertEqual(data["data"]["channel"], "orange_money")

        # Should have fee for external channel
        expected_fee = get_fee("orange_money")
        self.assertEqual(data["data"]["fee"], expected_fee)

        print(f"  ✅ External payment sent, Fee: P{data['data']['fee']} (Orange Money)")

    def test_08_insufficient_balance(self):
        """Test payment with insufficient balance"""
        print("🔍 Testing insufficient balance handling...")

        if not self.test_wallet_ids:
            self.skipTest("No test wallets available")

        sender_wallet = self.test_wallet_ids[0]

        # Try to send more than available balance
        payment_data = {
            "from_wallet": sender_wallet,
            "amount": 999999.0,  # Ridiculously high amount
            "channel": "phantom_wallet",
            "description": "Test insufficient balance",
        }

        response = requests.post(f"{self.base_url}/payments/send", json=payment_data)

        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Insufficient balance", data["error"])

        print("  ✅ Insufficient balance handled correctly")

    def test_09_accept_payment(self):
        """Test accepting payment from external channel"""
        print("🔍 Testing payment acceptance...")

        if not self.test_wallet_ids:
            self.skipTest("No test wallets available")

        wallet_id = self.test_wallet_ids[0]

        payment_data = {
            "wallet_id": wallet_id,
            "amount": 200.0,
            "channel": "orange_money",
            "description": "Test payment from Orange Money",
            "external_reference": "OM-TEST-12345",
        }

        response = requests.post(f"{self.base_url}/payments/accept", json=payment_data)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["amount"], 200.0)
        self.assertEqual(data["data"]["channel"], "orange_money")
        self.assertIn("wallet_balance", data["data"])

        print(f"  ✅ Payment accepted, New balance: P{data['data']['wallet_balance']}")

    def test_10_transaction_history(self):
        """Test transaction history retrieval"""
        print("🔍 Testing transaction history...")

        if not self.test_wallet_ids:
            self.skipTest("No test wallets available")

        wallet_id = self.test_wallet_ids[0]

        response = requests.get(f"{self.base_url}/wallets/{wallet_id}/transactions")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)
        self.assertIn("count", data)

        if data["data"]:
            transaction = data["data"][0]
            self.assertIn("transaction_id", transaction)
            self.assertIn("amount", transaction)
            self.assertIn("channel", transaction)
            self.assertIn("created_at", transaction)

        print(f"  ✅ Transaction history retrieved: {data['count']} transactions")

    def test_11_dashboard_stats(self):
        """Test dashboard statistics"""
        print("🔍 Testing dashboard statistics...")

        response = requests.get(f"{self.base_url}/stats/dashboard")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("wallet_stats", data["data"])
        self.assertIn("monthly_transactions", data["data"])
        self.assertIn("monthly_volume", data["data"])
        self.assertIn("cost_savings", data["data"])

        print("  ✅ Dashboard stats retrieved")

    def test_12_fee_calculation(self):
        """Test fee calculation logic"""
        print("🔍 Testing fee calculation...")

        # Test different channels
        channels_to_test = ["phantom_wallet", "orange_money", "myzaka", "ussd"]

        for channel in channels_to_test:
            fee = get_fee(channel)
            self.assertIsInstance(fee, (int, float))
            self.assertGreaterEqual(fee, 0)

            if channel == "phantom_wallet":
                self.assertEqual(fee, 0.0)  # Should be FREE

        print("  ✅ Fee calculation working correctly")

    def test_13_transaction_validation(self):
        """Test transaction amount validation"""
        print("🔍 Testing transaction validation...")

        # Test valid amount
        valid, message = validate_transaction_amount(100.0)
        self.assertTrue(valid)

        # Test amount too small
        valid, message = validate_transaction_amount(0.001)
        self.assertFalse(valid)
        self.assertIn("minimum", message)

        # Test amount too large
        valid, message = validate_transaction_amount(999999.0)
        self.assertFalse(valid)
        self.assertIn("exceeds", message)

        print("  ✅ Transaction validation working correctly")


class TestDatabaseOperations(unittest.TestCase):
    """Test database operations"""

    def test_database_connection(self):
        """Test database connection and tables"""
        print("🔍 Testing database connection...")

        from database import PhantomBankingDB

        # Create test database
        db = PhantomBankingDB(":memory:")
        conn = db.get_connection()
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        self.assertIn("wallets", tables)
        self.assertIn("transactions", tables)
        self.assertIn("businesses", tables)

        conn.close()

        print("  ✅ Database tables created successfully")


class TestConfigurationManager(unittest.TestCase):
    """Test configuration management"""

    def test_config_loading(self):
        """Test configuration loading"""
        print("🔍 Testing configuration loading...")

        from config import get_config, TestingConfig

        config = get_config("testing")
        self.assertEqual(config, TestingConfig)

        # Test fee structure
        self.assertIn("phantom_wallet", config.FEE_STRUCTURE)
        self.assertEqual(config.FEE_STRUCTURE["phantom_wallet"], 0.0)

        # Test market data
        self.assertIn("unbanked_population", config.MARKET_DATA)
        self.assertEqual(config.MARKET_DATA["unbanked_population"], 636000)

        print("  ✅ Configuration loaded correctly")


def run_performance_tests():
    """Run basic performance tests"""
    print("\n🚀 Running Performance Tests")
    print("=" * 40)

    base_url = "http://localhost:5000/api/v1"

    # Test API response times
    endpoints = ["/health", "/stats/dashboard"]

    for endpoint in endpoints:
        start_time = time.time()
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                print(f"  ✅ {endpoint}: {elapsed:.3f}s")
            else:
                print(f"  ❌ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ❌ {endpoint}: {str(e)}")


def run_integration_tests():
    """Run integration tests simulating real scenarios"""
    print("\n🔗 Running Integration Tests")
    print("=" * 40)

    base_url = "http://localhost:5000/api/v1"

    print("📋 Scenario: Rural Store Customer Journey")

    try:
        # 1. Create customer wallet
        print("  1. Creating customer wallet...")
        wallet_response = requests.post(
            f"{base_url}/wallets/create",
            json={
                "customer_name": "Thabo Molefe",
                "customer_phone": "+26772345678",
                "initial_balance": 0,
            },
        )

        if wallet_response.status_code == 200:
            wallet_id = wallet_response.json()["data"]["wallet_id"]
            print(f"     ✅ Wallet created: {wallet_id}")

            # 2. Accept payment from Orange Money
            print("  2. Accepting payment from Orange Money...")
            accept_response = requests.post(
                f"{base_url}/payments/accept",
                json={
                    "wallet_id": wallet_id,
                    "amount": 500.0,
                    "channel": "orange_money",
                    "description": "Top-up from Orange Money",
                },
            )

            if accept_response.status_code == 200:
                balance = accept_response.json()["data"]["wallet_balance"]
                print(f"     ✅ Payment accepted, Balance: P{balance}")

                # 3. Send payment to another phantom wallet
                print("  3. Sending phantom-to-phantom payment...")

                # Create second wallet
                wallet2_response = requests.post(
                    f"{base_url}/wallets/create",
                    json={
                        "customer_name": "Neo Kgomotso",
                        "customer_phone": "+26775432109",
                        "initial_balance": 0,
                    },
                )

                if wallet2_response.status_code == 200:
                    wallet2_id = wallet2_response.json()["data"]["wallet_id"]

                    # Send payment
                    send_response = requests.post(
                        f"{base_url}/payments/send",
                        json={
                            "from_wallet": wallet_id,
                            "to_wallet": wallet2_id,
                            "amount": 150.0,
                            "channel": "phantom_wallet",
                            "description": "Payment to friend",
                        },
                    )

                    if send_response.status_code == 200:
                        fee = send_response.json()["data"]["fee"]
                        print(f"     ✅ Payment sent, Fee: P{fee} (FREE!)")

                        # 4. Check transaction history
                        print("  4. Checking transaction history...")
                        history_response = requests.get(
                            f"{base_url}/wallets/{wallet_id}/transactions"
                        )

                        if history_response.status_code == 200:
                            txn_count = history_response.json()["count"]
                            print(
                                f"     ✅ Transaction history: {txn_count} transactions"
                            )

                            print("\n🎉 Integration test completed successfully!")
                            print(
                                "💰 Customer saved P92 vs traditional Orange Money withdrawal"
                            )
                        else:
                            print("     ❌ Failed to retrieve transaction history")
                    else:
                        print("     ❌ Failed to send payment")
                else:
                    print("     ❌ Failed to create second wallet")
            else:
                print("     ❌ Failed to accept payment")
        else:
            print("     ❌ Failed to create wallet")

    except Exception as e:
        print(f"  ❌ Integration test failed: {str(e)}")


def main():
    """Main test runner"""
    print("🏦 FNB Phantom Banking - Test Suite")
    print("=" * 50)
    print("🇧🇼 Testing Banking-as-a-Service for Botswana's Unbanked")
    print("=" * 50)

    # Check if API server is running
    try:
        response = requests.get("http://localhost:5000/api/v1/health", timeout=3)
        if response.status_code != 200:
            print("❌ API server not responding properly")
            print("💡 Make sure to run: python api_server.py")
            return False
    except:
        print("❌ API server not accessible")
        print("💡 Make sure to run: python api_server.py")
        return False

    print("✅ API server is running\n")

    # Run unit tests
    print("🧪 Running Unit Tests")
    print("=" * 30)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPhantomBankingAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurationManager))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    result = runner.run(suite)

    # Print summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors

    print(f"\n📊 Test Results Summary:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed} ✅")
    print(f"  Failed: {failures} ❌")
    print(f"  Errors: {errors} ⚠️")

    success_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
    print(f"  Success Rate: {success_rate:.1f}%")

    # Run performance tests
    run_performance_tests()

    # Run integration tests
    run_integration_tests()

    # Final summary
    print("\n" + "=" * 50)
    if failures == 0 and errors == 0:
        print("🎉 All tests passed! Phantom Banking is ready for demo.")
        print("💳 Ready to serve Botswana's 636,000 unbanked citizens!")
    else:
        print("⚠️  Some tests failed. Please review the issues above.")

    print("=" * 50)

    return failures == 0 and errors == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
