"""
FNB Phantom Banking - Demo Utilities & Monitoring
Helper tools for hackathon presentation and system monitoring
"""

import requests
import json
import time
import sqlite3
import random
import threading
from datetime import datetime, timedelta
from config import current_config
import subprocess
import psutil
import sys


class DemoMonitor:
    """Monitor demo system performance and status"""

    def __init__(self, api_base_url="http://localhost:5000/api/v1"):
        self.api_base_url = api_base_url
        self.monitoring = False
        self.stats = {
            "api_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "avg_response_time": 0,
            "start_time": None,
        }

    def check_api_health(self):
        """Check if API is healthy"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            response_time = time.time() - start_time

            self.stats["api_calls"] += 1

            if response.status_code == 200:
                self.stats["successful_calls"] += 1
                return True, response_time
            else:
                self.stats["failed_calls"] += 1
                return False, response_time

        except Exception as e:
            self.stats["api_calls"] += 1
            self.stats["failed_calls"] += 1
            return False, 0

    def get_system_stats(self):
        """Get system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage(".").percent,
            "network_io": psutil.net_io_counters()._asdict()
            if hasattr(psutil.net_io_counters(), "_asdict")
            else {},
        }

    def monitor_loop(self, interval=30):
        """Main monitoring loop"""
        print("🔍 Starting demo monitoring...")
        self.stats["start_time"] = datetime.now()

        while self.monitoring:
            # Check API health
            api_healthy, response_time = self.check_api_health()

            # Update average response time
            if response_time > 0:
                current_avg = self.stats["avg_response_time"]
                call_count = self.stats["successful_calls"]
                self.stats["avg_response_time"] = (
                    ((current_avg * (call_count - 1)) + response_time) / call_count
                    if call_count > 0
                    else response_time
                )

            # Get system stats
            system_stats = self.get_system_stats()

            # Print status
            uptime = datetime.now() - self.stats["start_time"]
            print(
                f"\r🔍 Monitor | Uptime: {str(uptime).split('.')[0]} | "
                f"API: {'✅' if api_healthy else '❌'} | "
                f"CPU: {system_stats['cpu_percent']:.1f}% | "
                f"RAM: {system_stats['memory_percent']:.1f}% | "
                f"Calls: {self.stats['api_calls']} | "
                f"Avg Response: {self.stats['avg_response_time']:.3f}s",
                end="",
            )

            time.sleep(interval)

    def start_monitoring(self):
        """Start monitoring in background thread"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        return monitor_thread

    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False

    def get_stats_summary(self):
        """Get monitoring statistics summary"""
        uptime = (
            datetime.now() - self.stats["start_time"]
            if self.stats["start_time"]
            else timedelta(0)
        )
        success_rate = (
            (self.stats["successful_calls"] / self.stats["api_calls"] * 100)
            if self.stats["api_calls"] > 0
            else 0
        )

        return {
            "uptime": str(uptime).split(".")[0],
            "total_api_calls": self.stats["api_calls"],
            "successful_calls": self.stats["successful_calls"],
            "failed_calls": self.stats["failed_calls"],
            "success_rate": f"{success_rate:.1f}%",
            "avg_response_time": f"{self.stats['avg_response_time']:.3f}s",
        }


class DemoDataGenerator:
    """Generate realistic demo data for presentations"""

    def __init__(self, api_base_url="http://localhost:5000/api/v1"):
        self.api_base_url = api_base_url

        # Botswana-specific names and phone numbers
        self.first_names = [
            "Thabo",
            "Neo",
            "Kabo",
            "Mpho",
            "Lesego",
            "Keabetswe",
            "Boitumelo",
            "Tshepiso",
            "Gorata",
            "Lorato",
            "Kagiso",
            "Onalenna",
            "Tlotlo",
            "Refilwe",
            "Mompati",
            "Dineo",
        ]

        self.last_names = [
            "Molefe",
            "Kgomotso",
            "Seretse",
            "Tebogo",
            "Bogatsu",
            "Motse",
            "Segwabe",
            "Ramaboa",
            "Maseko",
            "Seeletso",
            "Mosimanegape",
            "Kgalagadi",
            "Mmutlane",
            "Gabonamong",
            "Mothibi",
        ]

        self.business_types = [
            "General Store",
            "Tuck Shop",
            "Hair Salon",
            "Mechanic Shop",
            "Restaurant",
            "Clothing Store",
            "Electronics Shop",
            "Pharmacy",
            "Bakery",
            "Internet Cafe",
        ]

        self.locations = [
            "Gaborone",
            "Francistown",
            "Molepolole",
            "Selebi-Phikwe",
            "Serowe",
            "Kanye",
            "Mahalapye",
            "Palapye",
            "Lobatse",
            "Kasane",
            "Ghanzi",
            "Maun",
        ]

    def generate_customer_name(self):
        """Generate realistic Botswana customer name"""
        first = random.choice(self.first_names)
        last = random.choice(self.last_names)
        return f"{first} {last}"

    def generate_phone_number(self):
        """Generate realistic Botswana phone number"""
        # Botswana mobile numbers start with +267 7X
        prefixes = ["71", "72", "73", "74", "75", "76", "77"]
        prefix = random.choice(prefixes)
        number = "".join([str(random.randint(0, 9)) for _ in range(6)])
        return f"+267{prefix}{number}"

    def generate_transaction_description(self):
        """Generate realistic transaction descriptions"""
        descriptions = [
            "Grocery shopping",
            "Airtime purchase",
            "Electricity bill",
            "Water bill",
            "School fees",
            "Transport fare",
            "Medicine purchase",
            "Clothing purchase",
            "Phone repair",
            "Food delivery",
            "Mobile data",
            "Hair styling",
            "Car maintenance",
            "Building materials",
            "Farming supplies",
        ]
        return random.choice(descriptions)

    def create_demo_customers(self, count=10):
        """Create demo customer wallets"""
        print(f"👥 Creating {count} demo customers...")

        created_wallets = []

        for i in range(count):
            customer_data = {
                "customer_name": self.generate_customer_name(),
                "customer_phone": self.generate_phone_number(),
                "initial_balance": round(random.uniform(0, 1000), 2),
                "metadata": {
                    "demo_generated": True,
                    "location": random.choice(self.locations),
                    "customer_type": "demo",
                },
            }

            try:
                response = requests.post(
                    f"{self.api_base_url}/wallets/create", json=customer_data
                )
                if response.status_code == 200:
                    wallet_data = response.json()["data"]
                    created_wallets.append(wallet_data)
                    print(
                        f"  ✅ {customer_data['customer_name']} - {wallet_data['wallet_id']}"
                    )
                else:
                    print(
                        f"  ❌ Failed to create wallet for {customer_data['customer_name']}"
                    )
            except Exception as e:
                print(f"  ❌ Error creating wallet: {str(e)}")

        print(f"✅ Created {len(created_wallets)} demo customers")
        return created_wallets

    def simulate_transactions(self, wallet_list, transaction_count=20):
        """Simulate realistic transactions between wallets"""
        print(f"💸 Simulating {transaction_count} transactions...")

        channels = ["phantom_wallet", "orange_money", "myzaka", "ussd", "qr_code"]
        channel_weights = [40, 30, 20, 5, 5]  # Phantom wallet preferred

        successful_transactions = 0

        for i in range(transaction_count):
            if len(wallet_list) < 2:
                break

            # Select random sender and receiver
            sender = random.choice(wallet_list)
            receiver = random.choice(
                [w for w in wallet_list if w["wallet_id"] != sender["wallet_id"]]
            )

            # Generate transaction
            amount = round(random.uniform(10, 500), 2)
            channel = random.choices(channels, weights=channel_weights)[0]
            description = self.generate_transaction_description()

            transaction_data = {
                "from_wallet": sender["wallet_id"],
                "to_wallet": receiver["wallet_id"],
                "amount": amount,
                "channel": channel,
                "description": description,
            }

            try:
                response = requests.post(
                    f"{self.api_base_url}/payments/send", json=transaction_data
                )
                if response.status_code == 200:
                    txn_data = response.json()["data"]
                    fee = txn_data["fee"]
                    successful_transactions += 1
                    print(f"  ✅ P{amount} via {channel} (Fee: P{fee})")
                else:
                    print(
                        f"  ❌ Transaction failed: {response.json().get('error', 'Unknown error')}"
                    )
            except Exception as e:
                print(f"  ❌ Transaction error: {str(e)}")

            # Small delay to avoid overwhelming the API
            time.sleep(0.1)

        print(f"✅ Completed {successful_transactions}/{transaction_count} transactions")
        return successful_transactions


class HackathonPresentationHelper:
    """Helper tools for hackathon presentation"""

    def __init__(self):
        self.api_base_url = "http://localhost:5000/api/v1"
        self.frontend_url = "http://localhost:8501"

    def show_market_impact(self):
        """Display market impact statistics"""
        market_data = current_config.MARKET_DATA

        print("\n🇧🇼 BOTSWANA MARKET IMPACT")
        print("=" * 50)
        print(f"📊 Total Population: {market_data['total_population']:,}")
        print(
            f"👥 Unbanked Adults: {market_data['unbanked_population']:,} ({market_data['unbanked_percentage']}%)"
        )
        print(
            f"📱 Mobile Money Users: {market_data['mobile_money_users']:,} ({market_data['mobile_money_adoption']}%)"
        )
        print(f"💰 Annual MM Volume: P{market_data['annual_mobile_money_volume']:,}")
        print(f"🟠 Orange Money Share: {market_data['orange_money_market_share']}%")
        print(f"🟣 MyZaka Share: {market_data['myzaka_market_share']}%")
        print(f"👶 Median Age: {market_data['median_age']} years")

    def show_cost_savings(self):
        """Display cost savings comparison"""
        print("\n💰 COST SAVINGS ANALYSIS")
        print("=" * 50)

        fee_structure = current_config.FEE_STRUCTURE
        traditional_fees = {
            "orange_money_withdrawal": 92.00,
            "myzaka_withdrawal": 99.00,
            "bank_transfer": 15.00,
        }

        print("Service                  | Traditional | Phantom | Savings")
        print("-" * 55)
        print(
            f"Orange Money Withdrawal  | P 92.00     | P {fee_structure['orange_money']:.2f}    | P {92.00 - fee_structure['orange_money']:.2f}"
        )
        print(
            f"MyZaka Withdrawal        | P 99.00     | P {fee_structure['myzaka']:.2f}    | P {99.00 - fee_structure['myzaka']:.2f}"
        )
        print(f"Phantom-to-Phantom       | N/A         | FREE     | 100%")
        print(
            f"USSD Payments            | P 1.50      | P {fee_structure['ussd']:.2f}    | P {1.50 - fee_structure['ussd']:.2f}"
        )
        print(f"QR Code Payments         | Varies      | FREE     | 100%")

        # Calculate annual savings
        annual_transactions = 12  # Average per customer
        orange_annual_savings = annual_transactions * (
            92.00 - fee_structure["orange_money"]
        )
        myzaka_annual_savings = annual_transactions * (99.00 - fee_structure["myzaka"])

        print(f"\n💡 Annual Savings per Customer:")
        print(f"   Orange Money Users: P {orange_annual_savings:.2f}")
        print(f"   MyZaka Users: P {myzaka_annual_savings:.2f}")

    def demo_api_live(self):
        """Live API demonstration"""
        print("\n🔧 LIVE API DEMONSTRATION")
        print("=" * 50)

        # Test health check
        print("1. Health Check...")
        try:
            response = requests.get(f"{self.api_base_url}/health")
            if response.status_code == 200:
                print("   ✅ API is healthy and responsive")
            else:
                print("   ❌ API health check failed")
                return
        except:
            print("   ❌ Cannot connect to API")
            return

        # Create demo wallet
        print("\n2. Creating Demo Wallet...")
        wallet_data = {
            "customer_name": "Live Demo Customer",
            "customer_phone": "+26771111111",
            "initial_balance": 500.0,
            "metadata": {"demo_type": "live_presentation"},
        }

        try:
            response = requests.post(
                f"{self.api_base_url}/wallets/create", json=wallet_data
            )
            if response.status_code == 200:
                wallet = response.json()["data"]
                print(f"   ✅ Wallet created: {wallet['wallet_id']}")
                print(f"   📱 USSD Code: {wallet['ussd_code']}")

                # Accept payment
                print("\n3. Accepting Payment from Orange Money...")
                payment_data = {
                    "wallet_id": wallet["wallet_id"],
                    "amount": 250.0,
                    "channel": "orange_money",
                    "description": "Live demo top-up",
                }

                response = requests.post(
                    f"{self.api_base_url}/payments/accept", json=payment_data
                )
                if response.status_code == 200:
                    result = response.json()["data"]
                    print(
                        f"   ✅ Payment accepted, New balance: P{result['wallet_balance']}"
                    )

                    # Show transaction history
                    print("\n4. Checking Transaction History...")
                    response = requests.get(
                        f"{self.api_base_url}/wallets/{wallet['wallet_id']}/transactions"
                    )
                    if response.status_code == 200:
                        transactions = response.json()["data"]
                        print(f"   ✅ Found {len(transactions)} transactions")

                        print("\n🎉 Live API demonstration completed successfully!")
                        print(
                            "💡 This customer saved P89.50 vs traditional Orange Money!"
                        )
                    else:
                        print("   ❌ Failed to retrieve transaction history")
                else:
                    print("   ❌ Failed to accept payment")
            else:
                print("   ❌ Failed to create wallet")
        except Exception as e:
            print(f"   ❌ Demo failed: {str(e)}")

    def show_integration_benefits(self):
        """Show integration benefits for businesses"""
        print("\n🏪 BUSINESS INTEGRATION BENEFITS")
        print("=" * 50)
        print("✅ Serve ALL customers (not just banked ones)")
        print("✅ 15-minute API integration")
        print("✅ Multi-channel payment acceptance")
        print("✅ Lower transaction costs (67% savings)")
        print("✅ Customer wallet management")
        print("✅ Seamless upgrade to full FNB accounts")
        print("✅ Real-time transaction processing")
        print("✅ Bank-grade security and compliance")

        print("\n📈 MARKET OPPORTUNITY")
        print("=" * 50)
        print("• 636,000 unbanked adults in Botswana")
        print("• 1.8M mobile money users ready for better solution")
        print("• P26.5B annual mobile money volume")
        print("• 69.5% mobile money adoption rate")
        print("• Median age 23.4 years (digital natives)")


def main():
    """Main demo utilities interface"""
    print("🏦 FNB Phantom Banking - Demo Utilities")
    print("=" * 60)
    print("🇧🇼 Hackathon Presentation Tools")
    print("=" * 60)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "monitor":
            # Start monitoring
            monitor = DemoMonitor()
            try:
                monitor_thread = monitor.start_monitoring()
                print("\n🔍 Monitoring started. Press Ctrl+C to stop.")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                monitor.stop_monitoring()
                print("\n\n📊 Final Statistics:")
                stats = monitor.get_stats_summary()
                for key, value in stats.items():
                    print(f"   {key}: {value}")
                print("👋 Monitoring stopped")

        elif command == "generate":
            # Generate demo data
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            generator = DemoDataGenerator()
            wallets = generator.create_demo_customers(count)
            if wallets:
                generator.simulate_transactions(wallets, count * 2)

        elif command == "present":
            # Presentation helper
            helper = HackathonPresentationHelper()
            helper.show_market_impact()
            helper.show_cost_savings()
            helper.show_integration_benefits()

            # Ask for live demo
            response = input("\n🎤 Run live API demo? (y/N): ")
            if response.lower() == "y":
                helper.demo_api_live()

        elif command == "stats":
            # Show current stats
            try:
                response = requests.get("http://localhost:5000/api/v1/stats/dashboard")
                if response.status_code == 200:
                    data = response.json()["data"]
                    print("📊 Current System Statistics:")
                    print(
                        f"   Active Wallets: {data.get('wallet_stats', {}).get('active', 0)}"
                    )
                    print(
                        f"   Monthly Transactions: {data.get('monthly_transactions', 0)}"
                    )
                    print(f"   Monthly Volume: P{data.get('monthly_volume', 0):,.2f}")
                    print(f"   Total Balance: P{data.get('total_balance', 0):,.2f}")
                else:
                    print("❌ Failed to get statistics")
            except:
                print("❌ Cannot connect to API")

        else:
            print(f"❌ Unknown command: {command}")
            show_help()

    else:
        show_help()


def show_help():
    """Show help information"""
    print(
        """
🔧 Available Commands:

  python demo_utils.py monitor          # Monitor system performance
  python demo_utils.py generate [N]     # Generate N demo customers (default: 10)
  python demo_utils.py present          # Hackathon presentation helper
  python demo_utils.py stats            # Show current system statistics

🎯 Hackathon Tips:
  • Use 'present' for comprehensive market data and live demo
  • Use 'generate' to populate with realistic demo data
  • Use 'monitor' to show system performance during presentation
  • Use 'stats' to get real-time system metrics

🚀 Demo URLs:
  • Frontend: http://localhost:8501
  • API: http://localhost:5000
    """
    )


if __name__ == "__main__":
    main()
