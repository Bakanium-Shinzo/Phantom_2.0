# Phantom Banking - Mock Mobile Money System

Mock implementation of mobile money providers (Orange Money, Mascom MyZaka, BTC Smega) for development, testing, and demonstration of Phantom Banking integrations.

## 📱 Overview

The Mock Mobile Money System simulates the APIs of major mobile money providers in Botswana, enabling development and testing of Phantom Banking integration without requiring actual mobile money API access. It provides realistic API endpoints, transaction processing, and account management for Orange Money, Mascom MyZaka, and BTC Smega.

## 🚀 Features

### Mobile Money Providers
- **Orange Money**: Complete API simulation for Orange's mobile money service
- **Mascom MyZaka**: MyZaka mobile money platform simulation
- **BTC Smega**: BTC (Botswana Telecommunications Corporation) Smega simulation
- **Unified Interface**: Common API interface across all providers

### Mock Operations
- **Account Management**: Create and manage mock mobile money accounts
- **Balance Inquiries**: Check account balances and transaction limits
- **Money Transfers**: Send/receive money between mobile money accounts
- **Wallet Top-ups**: Transfer from mobile money to Phantom wallets
- **Cash-out Simulation**: Convert wallet balance to mobile money

### Testing Features
- **Provider-specific Behavior**: Realistic simulation of each provider's quirks
- **Network Simulation**: Simulate network delays and connectivity issues
- **Error Scenarios**: Test error handling with configurable failure modes
- **Transaction Limits**: Provider-specific daily and transaction limits
- **PIN Validation**: Mock PIN verification for secure transactions

## 📁 Structure

```
phantom_apps/mock_systems/mobile_money/
├── models.py              # Mock mobile money account and transaction models
├── serializers.py         # API serializers for mobile money data
├── views.py              # Mock mobile money API endpoints
├── urls.py               # URL routing for mock mobile money endpoints
├── admin.py              # Django admin for managing mock data
├── apps.py               # App configuration
├── services.py           # Mobile money business logic
├── providers/            # Provider-specific implementations
│   ├── orange.py         # Orange Money specific logic
│   ├── mascom.py         # MyZaka specific logic
│   └── btc.py            # BTC Smega specific logic
├── utils.py              # Helper functions and utilities
├── validators.py         # Mobile money validation logic
└── fixtures/             # Sample data for testing
    ├── mock_orange_accounts.json
    ├── mock_mascom_accounts.json
    └── mock_btc_accounts.json
```

## 🗄️ Models

### MockMobileMoneyAccount
Mock mobile money account for all providers:
- `account_id` (UUID): Unique account identifier
- `phone_number`: Mobile number (unique per provider)
- `provider`: Mobile money provider (orange, mascom, btc)
- `account_name`: Account holder name
- `balance`: Current account balance
- `currency`: Account currency (BWP)
- `pin_hash`: Hashed PIN for security simulation
- `is_active`: Account status
- `daily_limit`: Daily transaction limit
- `kyc_level`: KYC verification level (basic, enhanced, premium)
- `created_at`, `updated_at`: Timestamps

### MockMobileMoneyTransaction
Mobile money transaction records:
- `transaction_id` (UUID): Unique transaction identifier
- `account`: Associated mobile money account
- `transaction_type`: Type (send, receive, topup, cashout)
- `amount`: Transaction amount
- `fee`: Transaction fee
- `recipient_phone`: Recipient phone number (for transfers)
- `reference`: Transaction reference
- `status`: Transaction status
- `provider_reference`: Provider's transaction reference
- `description`: Transaction description
- `created_at`, `completed_at`: Timestamps

## 🔗 API Endpoints

### Account Management
- `GET /api/v1/mock-mobile-money/accounts/` - List mock accounts
- `POST /api/v1/mock-mobile-money/accounts/` - Create mock account
- `GET /api/v1/mock-mobile-money/accounts/{phone}/` - Get account details
- `GET /api/v1/mock-mobile-money/accounts/{phone}/balance/` - Check balance
- `POST /api/v1/mock-mobile-money/accounts/{phone}/verify-pin/` - Verify PIN

### Transaction Processing
- `POST /api/v1/mock-mobile-money/send/` - Send money to another mobile number
- `POST /api/v1/mock-mobile-money/topup-wallet/` - Top-up Phantom wallet
- `POST /api/v1/mock-mobile-money/cashout/` - Cash out from Phantom wallet
- `GET /api/v1/mock-mobile-money/transactions/` - List transactions
- `GET /api/v1/mock-mobile-money/transactions/{reference}/` - Get transaction details

### Provider-Specific Endpoints
- `POST /api/v1/mock-mobile-money/orange/ussd/` - Orange USSD simulation
- `POST /api/v1/mock-mobile-money/mascom/api/` - MyZaka API simulation
- `POST /api/v1/mock-mobile-money/btc/sms/` - BTC SMS gateway simulation

### Wallet Integration
- `POST /api/v1/mock-mobile-money/wallet/topup/` - Top-up wallet from mobile money
- `POST /api/v1/mock-mobile-money/wallet/cashout/` - Cash out wallet to mobile money
- `GET /api/v1/mock-mobile-money/wallet/fees/` - Get transaction fees
- `POST /api/v1/mock-mobile-money/wallet/verify/` - Verify wallet transaction

### Development Tools
- `POST /api/v1/mock-mobile-money/reset/{provider}/` - Reset provider data
- `POST /api/v1/mock-mobile-money/seed/{provider}/` - Seed with sample data
- `GET /api/v1/mock-mobile-money/status/` - Mock system status
- `POST /api/v1/mock-mobile-money/simulate-error/` - Simulate errors

## 🛠️ Installation & Setup

### 1. Database Migration
```bash
python manage.py makemigrations mobile_money
python manage.py migrate
```

### 2. Load Sample Data
```bash
# Load sample accounts for all providers
python manage.py loaddata phantom_apps/mock_systems/mobile_money/fixtures/mock_orange_accounts.json
python manage.py loaddata phantom_apps/mock_systems/mobile_money/fixtures/mock_mascom_accounts.json
python manage.py loaddata phantom_apps/mock_systems/mobile_money/fixtures/mock_btc_accounts.json
```

### 3. Configuration
Add mobile money settings to Django settings:

```python
# Mock Mobile Money Configuration
MOCK_MOBILE_MONEY_SETTINGS = {
    'PROVIDERS': {
        'orange': {
            'name': 'Orange Money',
            'ussd_code': '*144#',
            'api_url': 'http://localhost:8000/api/v1/mock-mobile-money/orange/',
            'daily_limit': 50000.00,
            'transaction_fee': 2.00,
            'simulation_delay': 1000,  # ms
        },
        'mascom': {
            'name': 'Mascom MyZaka',
            'ussd_code': '*126#',
            'api_url': 'http://localhost:8000/api/v1/mock-mobile-money/mascom/',
            'daily_limit': 40000.00,
            'transaction_fee': 2.50,
            'simulation_delay': 1500,  # ms
        },
        'btc': {
            'name': 'BTC Smega',
            'ussd_code': '*777#',
            'api_url': 'http://localhost:8000/api/v1/mock-mobile-money/btc/',
            'daily_limit': 30000.00,
            'transaction_fee': 3.00,
            'simulation_delay': 2000,  # ms
        }
    },
    'ENABLE_ERROR_SIMULATION': True,
    'ERROR_RATE': 0.03,  # 3% random error rate
    'REQUIRE_PIN_VERIFICATION': True,
}
```

## 💼 Usage Examples

### Create Mock Mobile Money Account
```python
import requests

# Create Orange Money account
response = requests.post('http://localhost:8000/api/v1/mock-mobile-money/accounts/', 
json={
    'phone_number': '+26771234567',
    'provider': 'orange',
    'account_name': 'John Doe',
    'initial_balance': 1000.00,
    'pin': '1234',
    'kyc_level': 'enhanced'
})

account_id = response.json()['account_id']
```

### Top-up Phantom Wallet from Mobile Money
```python
# Top-up wallet using Orange Money
response = requests.post('http://localhost:8000/api/v1/mock-mobile-money/topup-wallet/', 
json={
    'source_phone': '+26771234567',
    'provider': 'orange',
    'wallet_id': 'phantom-wallet-uuid',
    'amount': 250.00,
    'pin': '1234',
    'reference': 'TOPUP-001'
})

transaction_reference = response.json()['reference']
fee = response.json()['fee']
status = response.json()['status']
```

### Send Money Between Mobile Numbers
```python
# Send money from Orange Money to MyZaka
response = requests.post('http://localhost:8000/api/v1/mock-mobile-money/send/', 
json={
    'sender_phone': '+26771234567',
    'sender_provider': 'orange',
    'recipient_phone': '+26772345678',
    'recipient_provider': 'mascom',
    'amount': 100.00,
    'sender_pin': '1234',
    'reference': 'SEND-001',
    'description': 'Payment for goods'
})

transaction_id = response.json()['transaction_id']
```

### Check Mobile Money Balance
```python
# Check Orange Money balance
response = requests.get(
    'http://localhost:8000/api/v1/mock-mobile-money/accounts/+26771234567/balance/',
    params={'provider': 'orange'}
)

balance = response.json()['balance']
daily_limit = response.json()['daily_limit']
available_limit = response.json()['available_limit']
```

### Cash Out from Phantom Wallet
```python
# Cash out from Phantom wallet to MyZaka
response = requests.post('http://localhost:8000/api/v1/mock-mobile-money/cashout/', 
json={
    'wallet_id': 'phantom-wallet-uuid',
    'destination_phone': '+26772345678',
    'provider': 'mascom',
    'amount': 150.00,
    'wallet_pin': '5678',
    'reference': 'CASHOUT-001'
})

transaction_id = response.json()['transaction_id']
```

## 📱 Provider-Specific Features

### Orange Money Simulation
- **USSD Interface**: Mock USSD menu navigation
- **Real-time Processing**: Instant transaction confirmation
- **Advanced KYC**: Support for enhanced and premium KYC levels
- **Cross-border**: Simulation of regional transfers

```python
# Orange-specific USSD simulation
response = requests.post('http://localhost:8000/api/v1/mock-mobile-money/orange/ussd/', 
json={
    'phone_number': '+26771234567',
    'ussd_input': '*144*1*250*26772345678#',  # Send 250 BWP
    'session_id': 'ussd_session_123'
})
```

### Mascom MyZaka Simulation
- **API Interface**: RESTful API simulation
- **Batch Processing**: Support for multiple transactions
- **Merchant Payments**: Business payment processing
- **QR Code Integration**: QR-based payment simulation

```python
# MyZaka API simulation
response = requests.post('http://localhost:8000/api/v1/mock-mobile-money/mascom/api/', 
json={
    'action': 'transfer',
    'source_msisdn': '+26771234567',
    'destination_msisdn': '+26772345678',
    'amount': 100.00,
    'pin': '1234'
})
```

### BTC Smega Simulation
- **SMS Gateway**: SMS-based transaction simulation
- **USSD Interface**: Traditional USSD menu system
- **Agent Network**: Cash-in/cash-out agent simulation
- **Loyalty Points**: Simulated rewards program

```python
# BTC SMS gateway simulation
response = requests.post('http://localhost:8000/api/v1/mock-mobile-money/btc/sms/', 
json={
    'from_number': '+26771234567',
    'sms_text': 'SEND 250 26772345678 1234',
    'message_id': 'sms_msg_123'
})
```

## 🏪 Transaction Fees & Limits

### Orange Money
- **Send Money**: BWP 2.00 + 0.5% of amount
- **Wallet Top-up**: BWP 1.50
- **Cash Out**: BWP 3.00
- **Daily Limit**: BWP 50,000
- **Single Transaction**: BWP 15,000

### Mascom MyZaka
- **Send Money**: BWP 2.50 + 0.6% of amount
- **Wallet Top-up**: BWP 2.00
- **Cash Out**: BWP 3.50
- **Daily Limit**: BWP 40,000
- **Single Transaction**: BWP 12,000

### BTC Smega
- **Send Money**: BWP 3.00 + 0.7% of amount
- **Wallet Top-up**: BWP 2.50
- **Cash Out**: BWP 4.00
- **Daily Limit**: BWP 30,000
- **Single Transaction**: BWP 10,000

## 🔧 Configuration Options

### Provider Settings
```python
MOBILE_MONEY_PROVIDERS = {
    'orange': {
        'display_name': 'Orange Money',
        'color': '#FF6600',
        'logo_url': '/static/logos/orange.png',
        'ussd_code': '*144#',
        'customer_service': '+26711234567',
        'features': ['ussd', 'api', 'qr_codes', 'cross_border'],
        'kyc_levels': ['basic', 'enhanced', 'premium'],
        'supported_currencies': ['BWP', 'ZAR', 'USD'],
    },
    # ... other providers
}
```

### Transaction Configuration
```python
TRANSACTION_CONFIG = {
    'fee_calculation': 'fixed_plus_percentage',
    'max_transaction_amount': 50000.00,
    'min_transaction_amount': 5.00,
    'require_pin_verification': True,
    'enable_cross_provider_transfers': True,
    'transaction_timeout_seconds': 300,
    'retry_failed_transactions': True,
    'max_retry_attempts': 3,
}
```

### Error Simulation
```python
ERROR_SIMULATION = {
    'network_timeout_rate': 0.02,
    'insufficient_balance_rate': 0.01,
    'invalid_pin_rate': 0.005,
    'system_maintenance_rate': 0.001,
    'provider_downtime': {
        'orange': 0.001,
        'mascom': 0.002,
        'btc': 0.003,
    }
}
```

## 📊 Mock Data Management

### Sample Accounts
Pre-created accounts for testing:

**Orange Money**:
- +26771000001 (Balance: BWP 5,000, PIN: 1234)
- +26771000002 (Balance: BWP 10,000, PIN: 5678)

**Mascom MyZaka**:
- +26772000001 (Balance: BWP 3,000, PIN: 2345)
- +26772000002 (Balance: BWP 8,000, PIN: 6789)

**BTC Smega**:
- +26773000001 (Balance: BWP 2,000, PIN: 3456)
- +26773000002 (Balance: BWP 6,000, PIN: 7890)

### Transaction Scenarios
- **Successful Transfer**: Normal processing flow
- **Insufficient Balance**: Account balance too low
- **Invalid PIN**: Incorrect PIN provided
- **Daily Limit Exceeded**: Transaction exceeds daily limit
- **Network Timeout**: Simulated connectivity issues
- **Provider Maintenance**: Service temporarily unavailable

## 🧪 Testing Integration

### Cross-Provider Transfers
```python
def test_cross_provider_transfer():
    """Test transfer from Orange Money to MyZaka"""
    
    # Setup accounts
    orange_account = create_orange_account(balance=1000.00)
    mascom_account = create_mascom_account(balance=500.00)
    
    # Process transfer
    transfer_response = send_mobile_money(
        sender_phone=orange_account.phone_number,
        sender_provider='orange',
        recipient_phone=mascom_account.phone_number,
        recipient_provider='mascom',
        amount=200.00,
        sender_pin='1234'
    )
    
    assert transfer_response.status == 'completed'
    assert orange_account.balance == 798.00  # 1000 - 200 - 2 (fee)
    assert mascom_account.balance == 700.00  # 500 + 200
```

### Wallet Integration Tests
```python
def test_wallet_topup_from_mobile_money():
    """Test Phantom wallet top-up from mobile money"""
    
    # Create mobile money account and Phantom wallet
    mobile_account = create_orange_account(balance=500.00)
    wallet = create_phantom_wallet(balance=100.00)
    
    # Process top-up
    topup_response = topup_wallet_from_mobile_money(
        wallet_id=wallet.wallet_id,
        source_phone=mobile_account.phone_number,
        provider='orange',
        amount=200.00,
        pin='1234'
    )
    
    assert topup_response.status == 'completed'
    assert wallet.balance == 300.00  # 100 + 200
    assert mobile_account.balance == 298.50  # 500 - 200 - 1.50 (fee)
```

## 🔄 Integration with Real Providers

### Environment-based Configuration
```python
# Development - use mock providers
if DEBUG:
    MOBILE_MONEY_BASE_URLS = {
        'orange': 'http://localhost:8000/api/v1/mock-mobile-money/orange/',
        'mascom': 'http://localhost:8000/api/v1/mock-mobile-money/mascom/',
        'btc': 'http://localhost:8000/api/v1/mock-mobile-money/btc/',
    }
else:
    # Production - use real provider APIs
    MOBILE_MONEY_BASE_URLS = {
        'orange': 'https://api.orange.co.bw/v1/',
        'mascom': 'https://api.mascom.co.bw/v1/',
        'btc': 'https://api.btc.co.bw/v1/',
    }
```

### Unified Provider Interface
```python
class MobileMoneyProvider:
    def __init__(self, provider_name):
        self.provider = provider_name
        self.base_url = settings.MOBILE_MONEY_BASE_URLS[provider_name]
        self.is_mock = 'mock-mobile-money' in self.base_url
    
    def send_money(self, sender, recipient, amount, pin):
        # Same interface for mock and real providers
        return self._make_request('POST', '/send/', {
            'sender_phone': sender,
            'recipient_phone': recipient,
            'amount': amount,
            'pin': pin
        })
```

## 🛡️ Security Simulation

### PIN Validation
- Secure PIN hashing (even in mock environment)
- PIN attempt limiting
- Account lockout simulation
- PIN reset simulation

### Transaction Security
- Amount validation
- Duplicate transaction prevention
- Session management
- Fraud detection simulation

## 🐛 Troubleshooting

### Common Issues

1. **Mock Provider Not Responding**
   - Check provider configuration
   - Verify URL routing
   - Check for port conflicts

2. **PIN Verification Failing**
   - Verify PIN format requirements
   - Check account lockout status
   - Review PIN hash configuration

3. **Cross-Provider Transfers Failing**
   - Check provider compatibility settings
   - Verify account existence on both sides
   - Review transfer limits and fees

## 🚀 Future Enhancements

- Real provider sandbox integration
- Advanced fraud simulation
- Offline transaction handling
- Agent network simulation
- Merchant payment simulation
- International transfer simulation
- Loyalty program integration