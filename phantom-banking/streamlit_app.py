"""
FNB Phantom Banking - Complete Interactive Application with Enhanced Features
Banking-as-a-Service for Botswana's 636,000 unbanked population
"""
###streamlit_app.py###
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json

# Configuration
API_BASE_URL = "http://localhost:5000/api/v1"

# Page configuration
st.set_page_config(
    page_title="FNB Phantom Banking",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()

def check_api_connection():
    """Check if API server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def get_auth_headers():
    """Get authentication headers for API requests"""
    if st.session_state.user_data and 'user_id' in st.session_state.user_data:
        headers = {
            'Authorization': f"Bearer {st.session_state.user_data['user_id']}",
            'User-Type': st.session_state.user_data.get('user_type', 'merchant'),
            'Content-Type': 'application/json'
        }
        # Add customer phone for customer requests
        if st.session_state.user_data.get('user_type') == 'customer' and 'customer_phone' in st.session_state.user_data:
            headers['Customer-Phone'] = st.session_state.user_data['customer_phone']
        return headers
    return {'Content-Type': 'application/json'}

def api_request(endpoint, method="GET", data=None):
    """Make API request with proper authentication"""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        headers = get_auth_headers()
        
        # Add customer phone to data for customer requests
        if (st.session_state.user_data and 
            st.session_state.user_data.get('user_type') == 'customer' and 
            data and 'customer_phone' not in data):
            data['customer_phone'] = st.session_state.user_data.get('customer_phone')
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            return {"success": False, "error": f"API Error: {response.status_code} - {response.text}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to API server"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def show_header():
    """Display main header"""
    st.markdown("""
    <div style="background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; text-align: center; margin: 0;">
            🏦 FNB Phantom Banking
        </h1>
        <p style="color: #e0e0e0; text-align: center; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            Banking-as-a-Service for Botswana's 636,000 Unbanked Citizens
        </p>
    </div>
    """, unsafe_allow_html=True)

def show_home():
    """Home page with platform overview"""
    show_header()
    
    # Hero section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## 🎯 **Revolutionizing Financial Inclusion in Botswana**")
        st.markdown("""
        **FNB Phantom Banking** provides instant digital wallets for the unbanked, 
        with **67% cost savings** vs traditional mobile money services.
        
        ### 🌟 **Key Benefits:**
        - 🆓 **FREE wallet-to-wallet transfers** (customers ↔ customers, customers → merchants)
        - 📱 **Works on any phone** (USSD *167#)
        - 💰 **P89+ savings** per transaction vs Orange Money
        - ⚡ **Instant setup** - no bank account required
        - 🔐 **4-digit PIN security** with SMS delivery
        - 🔄 **Multi-channel support** - Orange Money, MyZaka, USSD, QR
        - 📈 **Account upgrade path** to full FNB banking
        - 🏪 **Merchant payments** - customers can pay businesses directly
        """)
        
        # Action buttons
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("🏪 Merchant Login", use_container_width=True, key="home_merchant_login"):
                st.session_state.page = "merchant_login"
                st.rerun()
        with col_b:
            if st.button("📱 Customer Login", use_container_width=True, key="home_customer_login"):
                st.session_state.page = "customer_login"
                st.rerun()
        with col_c:
            if st.button("🚀 Register Business", use_container_width=True, key="home_register_business"):
                st.session_state.page = "merchant_register"
                st.rerun()
    
    with col2:
        st.markdown("### 📊 **Market Impact**")
        
        # Market statistics
        market_data = {
            'Metric': ['Unbanked Adults', 'Mobile Money Users', 'Annual Volume', 'Potential Savings'],
            'Value': ['636,000', '1.8M (69.5%)', 'P 26.5B', 'P 590M+'],
            'Impact': ['24% of population', 'High adoption', 'Growing market', '67% cost reduction']
        }
        
        df_market = pd.DataFrame(market_data)
        st.dataframe(df_market, hide_index=True, use_container_width=True)
        
        # Live demo indicator
        if check_api_connection():
            st.success("🟢 **Live Demo Active**")
            st.markdown("API server running on port 5000")
        else:
            st.error("🔴 **API Server Offline**")
            st.markdown("Please start: `python api_server.py`")

    # Features showcase
    st.markdown("---")
    st.markdown("## 🚀 **Platform Features**")
    
    feature_cols = st.columns(4)
    
    features = [
        {
            "title": "🏪 Merchant Dashboard",
            "desc": "Create wallets, top-up balances, monitor transactions, view analytics",
            "benefits": ["Real-time updates", "Cost savings tracking", "Customer management", "API documentation"]
        },
        {
            "title": "📱 Customer Wallets", 
            "desc": "Send money to customers, merchants, top-up, view history with PIN security",
            "benefits": ["FREE transfers", "Pay merchants directly", "Multi-channel", "USSD support", "SMS notifications"]
        },
        {
            "title": "💰 Cost Savings",
            "desc": "67% reduction vs traditional fees",
            "benefits": ["P92→P2.50 Orange Money", "P99→P3.00 MyZaka", "FREE internal transfers"]
        },
        {
            "title": "🔔 Real-time Services",
            "desc": "Instant notifications and account upgrades",
            "benefits": ["Cross-platform sync", "Live updates", "Smart badges", "FNB account upgrade"]
        }
    ]
    
    for i, feature in enumerate(features):
        with feature_cols[i]:
            st.markdown(f"**{feature['title']}**")
            st.markdown(feature['desc'])
            for benefit in feature['benefits']:
                st.markdown(f"• {benefit}")

def show_merchant_login():
    """Merchant login page"""
    show_header()
    
    st.markdown("## 🏪 **Merchant Login**")
    st.markdown("Access your business dashboard and manage customer wallets")
    
    with st.form("merchant_login"):
        email = st.text_input("Business Email", placeholder="admin@kgalagadi.store")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        submitted = st.form_submit_button("🔑 Login", use_container_width=True)
        
        if submitted:
            if not email or not password:
                st.error("❌ Please enter both email and password")
                return
            
            with st.spinner("🔄 Authenticating..."):
                result = api_request("auth/merchant/login", "POST", {
                    "email": email,
                    "password": password
                })
            
            if result.get('success'):
                st.session_state.user_data = result['data']
                st.session_state.page = "merchant_dashboard"
                st.success("✅ Login successful!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Login failed: {result.get('error', 'Invalid credentials')}")
    
    # Demo credentials
    st.markdown("---")
    st.markdown("### 🔐 **Demo Credentials**")
    col1, col2 = st.columns(2)
    with col1:
        st.code("Email: admin@kgalagadi.store")
    with col2:
        st.code("Password: admin123")
    
    # Navigation
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Back to Home", key="merchant_login_back"):
            st.session_state.page = "home"
            st.rerun()
    with col_b:
        if st.button("🚀 Register Business", key="merchant_login_register"):
            st.session_state.page = "merchant_register"
            st.rerun()

def show_merchant_dashboard():
    """Enhanced merchant dashboard with all new features"""
    show_header()
    
    if not st.session_state.user_data:
        st.error("❌ Please login first")
        st.session_state.page = "merchant_login"
        st.rerun()
        return
    
    user = st.session_state.user_data
    
    # Header with user info and logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## 🏪 **{user['business_name']} Dashboard**")
        st.markdown(f"*Merchant ID: {user['user_id']}*")
    with col2:
        if st.button("🚪 Logout", key="merchant_dashboard_logout"):
            st.session_state.user_data = None
            st.session_state.auth_token = None
            st.session_state.page = "home"
            st.rerun()
    
    # Show merchant balance if they've received phantom payments
    merchant_balance_data = api_request(f"merchants/{user['user_id']}/balance")
    if merchant_balance_data.get('success') and merchant_balance_data['data']['balance'] > 0:
        balance = merchant_balance_data['data']['balance']
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
                    padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 1rem;">
            <h4 style="margin: 0;">💰 Phantom Wallet Balance: P {balance:,.2f}</h4>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">
                Received from customer phantom transfers | Merchant ID: {user['user_id']}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "👥 Customer Management", "📖 API Documentation", "🔔 Notifications"])
    
    with tab1:
        show_merchant_overview(user)
    
    with tab2:
        show_customer_management(user)
    
    with tab3:
        show_api_documentation()
    
    with tab4:
        show_merchant_notifications(user)

def show_merchant_overview(user):
    """Merchant dashboard overview tab"""
    # Auto-refresh toggle
    auto_refresh = st.checkbox("🔄 Auto-refresh every 30 seconds", value=False)
    
    # Manual refresh button
    col_refresh1, col_refresh2 = st.columns([1, 4])
    with col_refresh1:
        if st.button("🔄 Refresh Now", use_container_width=True, key="manual_refresh"):
            st.rerun()
    
    # Get dashboard data for this specific merchant
    dashboard_data = api_request(f"stats/dashboard/{user['user_id']}")
    
    if not dashboard_data.get('success'):
        st.error(f"❌ Error loading dashboard: {dashboard_data.get('error')}")
        return
    
    data = dashboard_data['data']
    
    # Key metrics
    st.markdown("### 📊 **Your Business Metrics**")
    
    metric_cols = st.columns(5)
    
    with metric_cols[0]:
        active_wallets = data['wallet_stats'].get('active', {}).get('count', 0)
        st.metric("👥 Your Customers", active_wallets)
    
    with metric_cols[1]:
        monthly_txns = data['monthly_transactions']
        st.metric("💳 Monthly Transactions", monthly_txns)
    
    with metric_cols[2]:
        monthly_volume = data['monthly_volume']
        st.metric("💰 Monthly Volume", f"P {monthly_volume:,.2f}")
    
    with metric_cols[3]:
        total_saved = data['competitive_advantage']['total_fees_saved']
        st.metric("🎯 Fees Saved", f"P {total_saved:,.2f}")
    
    with metric_cols[4]:
        # Show phantom balance received from customers
        phantom_balance = data.get('phantom_balance', 0)
        st.metric("💰 Phantom Balance", f"P {phantom_balance:,.2f}")
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        # Channel performance
        st.markdown("### 📊 **Channel Performance**")
        
        if data['channel_breakdown']:
            channel_names = [c['channel'].replace('_', ' ').title() for c in data['channel_breakdown']]
            channel_amounts = [c['total_amount'] for c in data['channel_breakdown']]
            
            fig = px.pie(
                values=channel_amounts,
                names=channel_names,
                title="Your Transaction Volume by Channel"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No transaction data available yet")
    
    with col2:
        # Cost savings summary
        st.markdown("### 💰 **Your Cost Savings & Revenue**")
        
        competitive = data['competitive_advantage']
        st.metric("Total Fees Saved", f"P {competitive['total_fees_saved']:,.2f}")
        st.metric("Cost Reduction", f"{competitive['cost_reduction_percentage']}%")
        
        if phantom_balance > 0:
            st.success(f"💰 You've received P {phantom_balance:,.2f} from customer phantom payments!")
        
        st.markdown("""
        **Your Phantom Banking Advantage:**
        - Orange Money: P92 → P2.50 (97% savings)
        - MyZaka: P99 → P3.00 (97% savings)
        - Phantom Transfers: FREE (100% savings)
        - Direct customer payments: FREE income
        """)
    
    # Recent transactions
    st.markdown("### 📈 **Recent Transactions**")
    
    if data['recent_transactions']:
        txn_data = []
        for txn in data['recent_transactions'][:10]:
            txn_data.append({
                'Time': datetime.fromisoformat(txn['created_at']).strftime('%m-%d %H:%M'),
                'Customer': txn['customer_name'],
                'Amount': f"P {txn['amount']:.2f}",
                'Channel': txn['channel'].replace('_', ' ').title(),
                'Fee': f"P {txn['fee']:.2f}" if txn['fee'] > 0 else "FREE",
                'Type': 'Payment to You' if txn.get('to_merchant') else 'Customer Transaction'
            })
        
        df_txns = pd.DataFrame(txn_data)
        st.dataframe(df_txns, hide_index=True, use_container_width=True)
    else:
        st.info("No recent transactions")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

def show_customer_management(user):
    """Customer management tab"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Customer wallet creation
        st.markdown("### 👥 **Create Customer Wallet**")
        
        with st.form("create_wallet"):
            customer_name = st.text_input("Customer Name", placeholder="e.g., John Doe")
            customer_phone = st.text_input("Phone Number", placeholder="+267 71 234 567")
            customer_email = st.text_input("Email (Optional)", placeholder="john@example.com")
            initial_balance = st.number_input("Initial Balance (BWP)", min_value=0.0, value=0.0)
            
            if st.form_submit_button("🎉 Create Wallet", use_container_width=True):
                if not customer_name or not customer_phone:
                    st.error("❌ Name and phone number are required")
                else:
                    with st.spinner("Creating wallet and generating PIN..."):
                        wallet_data = {
                            "customer_name": customer_name,
                            "customer_phone": customer_phone,
                            "customer_email": customer_email,
                            "initial_balance": initial_balance,
                            "business_id": user['user_id']
                        }
                        
                        result = api_request("wallets/create", "POST", wallet_data)
                        
                        if result.get('success'):
                            st.success("🎉 Wallet created successfully!")
                            st.balloons()
                            
                            # Show wallet details including PIN
                            wallet = result['data']
                            st.info(f"""
                            **Wallet Created Successfully!**
                            
                            **Wallet ID:** {wallet['wallet_id']}
                            **Customer:** {wallet['customer_name']}
                            **Phone:** {wallet['customer_phone']}
                            **PIN:** {wallet['customer_pin']} *(sent via SMS)*
                            **USSD Code:** {wallet['ussd_code']}
                            **Balance:** P {wallet['balance']:.2f}
                            **SMS Sent:** ✅ Yes
                            """)
                            
                            st.success("📱 **PIN has been sent to customer via SMS**")
                            
                            # Auto-refresh to show new data
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {result.get('error')}")
    
    with col2:
        # Customer wallet top-up
        st.markdown("### 💰 **Top-up Customer Wallet**")
        
        # Get list of wallets for selection
        wallets_data = api_request(f"wallets/merchant/{user['user_id']}")
        
        if wallets_data.get('success') and wallets_data['data']:
            wallets = wallets_data['data']
            
            with st.form("topup_wallet"):
                # Select customer
                wallet_options = [f"{w['customer_name']} - P{w['balance']:.2f} ({w['customer_phone']})" for w in wallets]
                selected_idx = st.selectbox("Select Customer Wallet", range(len(wallet_options)), 
                                          format_func=lambda x: wallet_options[x])
                
                amount = st.number_input("Top-up Amount (BWP)", min_value=1.0, value=50.0)
                description = st.text_input("Description", value="Merchant top-up")
                
                if st.form_submit_button("💰 Top-up Wallet", use_container_width=True):
                    selected_wallet = wallets[selected_idx]
                    
                    with st.spinner("Processing top-up..."):
                        topup_data = {
                            "amount": amount,
                            "description": description
                        }
                        
                        result = api_request(f"wallets/{selected_wallet['wallet_id']}/topup", "POST", topup_data)
                        
                        if result.get('success'):
                            st.success("💰 Wallet topped up successfully!")
                            
                            topup = result['data']
                            st.info(f"""
                            **Top-up Successful!**
                            
                            **Customer:** {topup['customer_name']}
                            **Amount Added:** P {topup['amount_added']:.2f}
                            **Previous Balance:** P {topup['previous_balance']:.2f}
                            **New Balance:** P {topup['new_balance']:.2f}
                            **SMS Sent:** ✅ Customer notified
                            """)
                            
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {result.get('error')}")
        else:
            st.info("No customer wallets found. Create a wallet first!")
    
    # Customer Management Table
    st.markdown("### 👥 **Your Customer Wallets**")
    
    wallets_data = api_request(f"wallets/merchant/{user['user_id']}")
    
    if wallets_data.get('success') and wallets_data['data']:
        wallets = wallets_data['data']
        
        # Create DataFrame for display
        wallet_display = []
        for wallet in wallets:
            wallet_display.append({
                'Customer': wallet['customer_name'],
                'Phone': wallet['customer_phone'],
                'Balance': f"P {wallet['balance']:.2f}",
                'Status': wallet['status'].title(),
                'Transactions': wallet.get('transaction_count', 0),
                'Created': wallet['created_at'][:10] if wallet.get('created_at') else 'N/A',
                'Actions': wallet['wallet_id']  # For action buttons
            })
        
        df_wallets = pd.DataFrame(wallet_display)
        st.dataframe(df_wallets.drop('Actions', axis=1), hide_index=True, use_container_width=True)
        
        # Wallet management actions
        with st.expander("🛠️ **Wallet Management & Account Upgrades**"):
            selected_wallet = st.selectbox(
                "Select wallet to manage:",
                options=[f"{w['customer_name']} ({w['wallet_id']})" for w in wallets],
                format_func=lambda x: x.split(' (')[0],
                key="manage_wallet_select"
            )
            
            if selected_wallet:
                wallet_id = selected_wallet.split('(')[1].replace(')', '')
                selected_wallet_data = next(w for w in wallets if w['wallet_id'] == wallet_id)
                
                col_manage_1, col_manage_2, col_manage_3 = st.columns(3)
                
                with col_manage_1:
                    if st.button("⏸️ Deactivate Wallet", use_container_width=True, key=f"deactivate_{wallet_id}"):
                        result = api_request(f"wallets/{wallet_id}/deactivate", "PUT")
                        if result.get('success'):
                            st.success("✅ Wallet deactivated")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {result.get('error')}")
                
                with col_manage_2:
                    if st.button("▶️ Activate Wallet", use_container_width=True, key=f"activate_{wallet_id}"):
                        result = api_request(f"wallets/{wallet_id}/activate", "PUT")
                        if result.get('success'):
                            st.success("✅ Wallet activated")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {result.get('error')}")
                
                with col_manage_3:
                    if st.button("📈 Suggest Account Upgrade", use_container_width=True, key=f"upgrade_{wallet_id}"):
                        upgrade_data = {
                            "reason": f"Customer {selected_wallet_data['customer_name']} meets criteria for full FNB account",
                            "documents_provided": ["ID Copy", "Proof of Address"]
                        }
                        
                        result = api_request(f"wallets/{wallet_id}/suggest-upgrade", "POST", upgrade_data)
                        if result.get('success'):
                            st.success("📈 Account upgrade suggested!")
                            
                            upgrade = result['data']
                            st.info(f"""
                            **Upgrade Suggestion Sent!**
                            
                            **Benefits for Customer:**
                            • Higher transaction limits
                            • Debit card access  
                            • Internet banking
                            • Loan eligibility
                            • Investment products
                            
                            **Next Steps:**
                            • Customer visits FNB branch
                            • Brings required documents
                            • Completes KYC process
                            • Maintains phantom wallet during transition
                            """)
                            
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {result.get('error')}")
    else:
        st.info("No customer wallets found. Create your first customer wallet above!")

def show_api_documentation():
    """API documentation tab"""
    st.markdown("### 📖 **FNB Phantom Banking API Documentation**")
    
    # Get API documentation
    docs_data = api_request("docs")
    
    if docs_data.get('success'):
        docs = docs_data['data']
        
        st.markdown(f"**Version:** {docs['version']}")
        st.markdown(f"**Base URL:** `{docs['base_url']}`")
        
        # Authentication section
        st.markdown("#### 🔐 **Authentication**")
        st.code(f"""
Headers:
Authorization: Bearer {{merchant_id}}
User-Type: merchant
Content-Type: application/json
        """)
        
        # Endpoints by category
        categories = [
            ("Authentication", "authentication"),
            ("Wallet Management", "wallet_management"), 
            ("Transactions", "transactions"),
            ("Account Services", "account_services"),
            ("Analytics", "analytics")
        ]
        
        for category_name, category_key in categories:
            if category_key in docs['endpoints']:
                st.markdown(f"#### 📋 **{category_name}**")
                
                for endpoint_name, endpoint_data in docs['endpoints'][category_key].items():
                    with st.expander(f"{endpoint_data['method']} {endpoint_data['url']} - {endpoint_data['description']}"):
                        st.markdown(f"**Method:** `{endpoint_data['method']}`")
                        st.markdown(f"**URL:** `{endpoint_data['url']}`")
                        st.markdown(f"**Description:** {endpoint_data['description']}")
                        
                        if 'auth_required' in endpoint_data:
                            st.markdown(f"**Auth Required:** {endpoint_data['auth_required']}")
                        
                        if 'body' in endpoint_data:
                            st.markdown("**Request Body:**")
                            st.code(json.dumps(endpoint_data['body'], indent=2))
                        
                        if 'response' in endpoint_data:
                            st.markdown("**Response:**")
                            st.code(json.dumps(endpoint_data['response'], indent=2))
                        
                        if 'fees' in endpoint_data:
                            st.markdown("**Fee Structure:**")
                            for channel, fee in endpoint_data['fees'].items():
                                st.markdown(f"• **{channel.replace('_', ' ').title()}:** {fee}")
        
        # Error codes
        st.markdown("#### ⚠️ **Error Codes**")
        for code, description in docs['error_codes'].items():
            st.markdown(f"• **{code}:** {description}")
        
        # Rate limits
        st.markdown("#### ⏱️ **Rate Limits**")
        st.markdown(f"• **Requests per minute:** {docs['rate_limits']['requests_per_minute']}")
        st.markdown(f"• **Burst limit:** {docs['rate_limits']['burst_limit']}")
    
    else:
        st.error("❌ Could not load API documentation")

def show_merchant_notifications(user):
    """Merchant notifications tab"""
    st.markdown("### 🔔 **Your Notifications**")
    
    notifications = api_request("notifications")
    if notifications.get('success'):
        if notifications['data']:
            for notif in notifications['data']:
                notification_type = notif['type']
                icon = "🎉" if notification_type == "success" else "ℹ️" if notification_type == "info" else "⚠️"
                
                # Create notification card
                with st.container():
                    st.markdown(f"""
                    <div style="border-left: 4px solid {'#28a745' if notification_type == 'success' else '#17a2b8' if notification_type == 'info' else '#ffc107'}; 
                                padding: 1rem; margin: 0.5rem 0; background: #f8f9fa; border-radius: 0 8px 8px 0;">
                        {icon} {notif['message']}
                        <br><small style="color: #6c757d;">{notif['created_at']}</small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("📭 No new notifications")
    else:
        st.error("❌ Could not load notifications")

def show_customer_login():
    """Customer login page"""
    show_header()
    
    st.markdown("## 📱 **Customer Login**")
    st.markdown("Access your digital wallet with PIN security")
    
    with st.form("customer_login"):
        phone = st.text_input("Phone Number", placeholder="+267 71 123 456")
        pin = st.text_input("4-Digit PIN", type="password", placeholder="Enter your 4-digit PIN", max_chars=4)
        
        submitted = st.form_submit_button("🔑 Login to Wallet", use_container_width=True)
        
        if submitted:
            if not phone or not pin:
                st.error("❌ Please enter both phone number and PIN")
                return
            
            if len(pin) != 4 or not pin.isdigit():
                st.error("❌ PIN must be exactly 4 digits")
                return
            
            with st.spinner("🔄 Authenticating..."):
                result = api_request("auth/customer/login", "POST", {
                    "phone": phone,
                    "pin": pin
                })
            
            if result.get('success'):
                st.session_state.user_data = result['data']
                st.session_state.page = "customer_wallet"
                st.success("✅ Welcome to your digital wallet!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Login failed: {result.get('error', 'Invalid phone number or PIN')}")
    
    # Demo credentials
    st.markdown("---")
    st.markdown("### 🔐 **Demo Credentials**")
    
    demo_customers = [
        {"phone": "+267 71 123 456", "name": "Thabo Molefe"},
        {"phone": "+267 72 234 567", "name": "Neo Kgomotso"},
        {"phone": "+267 73 345 678", "name": "Kabo Seretse"}
    ]
    
    for customer in demo_customers:
        col1, col2 = st.columns(2)
        with col1:
            st.code(f"Phone: {customer['phone']}")
        with col2:
            st.code("PIN: 1234 (any 4 digits)")
    
    # Navigation
    if st.button("← Back to Home", key="customer_login_back"):
        st.session_state.page = "home"
        st.rerun()

def show_customer_wallet():
    """Enhanced customer wallet interface"""
    show_header()
    
    if not st.session_state.user_data:
        st.error("❌ Please login first")
        st.session_state.page = "customer_login"
        st.rerun()
        return
    
    user = st.session_state.user_data
    
    # Header with user info and logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## 📱 **{user['customer_name']}'s Digital Wallet**")
        st.markdown(f"*Phone: {user['customer_phone']}*")
    with col2:
        if st.button("🚪 Logout", key="customer_wallet_logout"):
            st.session_state.user_data = None
            st.session_state.page = "home"
            st.rerun()
    
    # Get current balance
    balance_data = api_request(f"wallets/{user['wallet_id']}/balance")
    
    if balance_data.get('success'):
        wallet = balance_data['data']
        current_balance = wallet.get('balance', 0)
        
        # Balance display
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;">
            <h2 style="margin: 0;">P {current_balance:,.2f}</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Available Balance</p>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">
                USSD: {wallet.get('ussd_code', 'N/A')} | Daily Limit: P {wallet.get('daily_limit', 5000):,.2f}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Customer wallet tabs
        tab1, tab2, tab3, tab4 = st.tabs(["💸 Send Money", "💰 Top-up", "📊 History", "🔔 Notifications"])
        
        with tab1:
            show_customer_send_money(user, wallet)
        
        with tab2:
            show_customer_topup(user, wallet)
        
        with tab3:
            show_customer_history(user)
        
        with tab4:
            show_customer_notifications(user)
    
    else:
        st.error(f"❌ Error loading wallet: {balance_data.get('error')}")
        st.info("💡 Try logging out and logging back in, or contact support if the issue persists.")

def show_customer_send_money(user, wallet):
    """Customer send money functionality"""
    st.markdown("### 💸 **Send Money**")
    
    with st.form("customer_send_money"):
        col1, col2 = st.columns(2)
        
        with col1:
            amount = st.number_input("Amount (BWP)", min_value=1.0, value=100.0)
            channel = st.selectbox("Send via", [
                "orange_money", "myzaka", "phantom_wallet", "ussd", "qr_code"
            ], format_func=lambda x: {
                "orange_money": "🍊 Orange Money",
                "myzaka": "💙 MyZaka", 
                "phantom_wallet": "👻 Phantom Wallet (FREE)",
                "ussd": "📞 USSD", 
                "qr_code": "📱 QR Code (FREE)"
            }[x])
        
        with col2:
            if channel == "phantom_wallet":
                recipient = st.text_input("Recipient ID", placeholder="pw_bw_2024_xxxxx or merchant_xxxxx")
                st.info("💡 Use wallet ID (pw_bw_) for customers or merchant ID (merchant_) for businesses")
                
                # Show available wallets and merchants for demo purposes
                with st.expander("🔍 View Available Recipients (Demo)"):
                    col_demo1, col_demo2 = st.columns(2)
                    
                    with col_demo1:
                        st.markdown("**👥 Customer Wallets:**")
                        
                        # Get list of other wallets
                        try:
                            available_wallets = api_request("wallets/available")
                            if available_wallets.get('success'):
                                for wallet in available_wallets['data'][:3]:  # Show first 3
                                    if wallet['wallet_id'] != user['wallet_id']:  # Don't show own wallet
                                        st.code(f"{wallet['wallet_id']}")
                                        st.caption(f"👤 {wallet['customer_name']}")
                            else:
                                # Fallback demo wallet IDs
                                st.code("pw_bw_2024_12345678")
                                st.caption("👤 Demo Customer 1")
                                st.code("pw_bw_2024_87654321")
                                st.caption("👤 Demo Customer 2")
                        except:
                            # Fallback if API fails
                            st.code("pw_bw_2024_12345678")
                            st.caption("👤 Demo Customer")
                    
                    with col_demo2:
                        st.markdown("**🏪 Merchants:**")
                        
                        # Get list of merchants
                        try:
                            available_merchants = api_request("merchants/available")
                            if available_merchants.get('success'):
                                for merchant in available_merchants['data'][:3]:  # Show first 3
                                    st.code(f"{merchant['merchant_id']}")
                                    st.caption(f"🏪 {merchant['business_name']}")
                            else:
                                # Fallback demo merchant IDs
                                st.code("merchant_0918cd8a")
                                st.caption("🏪 Kgalagadi General Store")
                                st.code("merchant_12345678")
                                st.caption("🏪 Demo Merchant")
                        except:
                            # Fallback if API fails
                            st.code("merchant_0918cd8a")
                            st.caption("🏪 Kgalagadi Store")
            else:
                recipient = st.text_input("Recipient Phone", placeholder="+267 71 234 567")
                st.info("💡 Use phone number for external transfers")
                
            description = st.text_input("Description (Optional)", placeholder="Payment for...")
        
        # Fee calculation
        fee_schedule = {
            "phantom_wallet": 0.0,
            "orange_money": 2.50,
            "myzaka": 3.00,
            "ussd": 1.50,
            "qr_code": 0.0
        }
        
        fee = fee_schedule.get(channel, 2.50)
        total = amount + fee
        
        # Savings calculation
        traditional_fees = {"orange_money": 92, "myzaka": 99}
        savings = traditional_fees.get(channel, 0) - fee
        
        if savings > 0:
            st.success(f"💰 You save P {savings:.2f} vs traditional {channel.replace('_', ' ')}!")
        
        if fee == 0:
            st.success("🎉 FREE transfer!")
        
        st.info(f"**Fee:** P {fee:.2f} | **Total:** P {total:.2f}")
        
        if total > wallet['balance']:
            st.error(f"❌ Insufficient balance. You need P {total:.2f} but have P {wallet['balance']:.2f}")
        
        if st.form_submit_button("💸 Send Payment", use_container_width=True, disabled=total > wallet['balance']):
            if not recipient:
                st.error("❌ Please enter recipient details")
                return
            
            # Validate recipient format
            if channel == "phantom_wallet" and not (recipient.startswith("pw_bw_") or recipient.startswith("merchant_")):
                st.error("❌ Invalid recipient ID format. Use wallet ID (pw_bw_xxxxx) or merchant ID (merchant_xxxxx)")
                return
            
            with st.spinner("Processing payment..."):
                payment_data = {
                    "amount": amount,
                    "channel": channel,
                    "recipient": recipient,
                    "description": description or f"Payment to {recipient}",
                    "customer_phone": user['customer_phone'],  # Ensure phone is included
                    "wallet_id": user['wallet_id']  # Ensure wallet_id is included
                }
                
                result = api_request("customer/send-payment", "POST", payment_data)
            
            if result.get('success'):
                st.success("✅ Payment sent successfully!")
                st.balloons()
                
                payment = result['data']
                
                # Enhanced success message based on recipient type
                recipient_msg = f"**Recipient:** {payment['recipient']}"
                if payment.get('recipient_info'):
                    if payment['recipient_info']['type'] == 'customer':
                        recipient_msg += f" ({payment['recipient_info']['name']})"
                    elif payment['recipient_info']['type'] == 'merchant':
                        recipient_msg += f" ({payment['recipient_info']['name']})"
                
                st.info(f"""
                **Payment Successful!**
                
                **Transaction ID:** {payment['transaction_id']}
                **Amount:** P {payment['amount']:.2f}
                **Fee:** P {payment['fee']:.2f}
                {recipient_msg}
                **New Balance:** P {payment['new_balance']:.2f}
                **Channel:** {payment['channel'].replace('_', ' ').title()}
                """)
                
                # Show special message for phantom transfers
                if payment['channel'] == 'phantom_wallet':
                    if payment.get('recipient_info'):
                        recipient_type = payment['recipient_info']['type']
                        if recipient_type == 'customer':
                            st.success("🎉 FREE customer-to-customer transfer completed!")
                        elif recipient_type == 'merchant':
                            st.success("🎉 FREE customer-to-merchant payment completed!")
                    else:
                        st.success("🎉 FREE phantom transfer completed!")
                
                if payment.get('fee_saved'):
                    st.success(f"💰 You saved P {payment['fee_saved']:.2f} vs traditional fees!")
                
                time.sleep(3)
                st.rerun()
            else:
                st.error(f"❌ Payment failed: {result.get('error')}")
                
                # Show helpful error messages
                if "authentication" in result.get('error', '').lower():
                    st.info("💡 **Tip:** Make sure you're logged in properly. Try logging out and back in.")
                elif "wallet" in result.get('error', '').lower() or "not found" in result.get('error', '').lower():
                    st.info("💡 **Tip:** Check the recipient ID format:")
                    st.info("   • Customer wallets: pw_bw_2024_xxxxx")
                    st.info("   • Merchants: merchant_xxxxx") 
                    st.info("   • Phone numbers: +267 71 234 567")
                elif "insufficient" in result.get('error', '').lower():
                    st.info("💡 **Tip:** You don't have enough balance for this transaction.")
                elif "recipient" in result.get('error', '').lower():
                    st.info("💡 **Tip:** Make sure the recipient ID exists and is active.")

def show_customer_topup(user, wallet):
    """Customer top-up functionality"""
    st.markdown("### 💰 **Top-up Your Wallet**")
    
    # Get current balance safely
    current_balance = wallet.get('balance', user.get('balance', 0))
    
    with st.form("customer_topup"):
        col1, col2 = st.columns(2)
        
        with col1:
            amount = st.number_input("Top-up Amount (BWP)", min_value=10.0, value=100.0)
            source = st.selectbox("Top-up from", [
                "orange_money", "myzaka", "bank_transfer"
            ], format_func=lambda x: {
                "orange_money": "🍊 Orange Money",
                "myzaka": "💙 MyZaka",
                "bank_transfer": "🏦 Bank Transfer"
            }[x])
        
        with col2:
            reference = st.text_input("Reference Number", placeholder="OM123456789 or transaction ref")
            st.info(f"Adding P {amount:.2f} to your current balance of P {current_balance:.2f}")
        
        # Add the submit button inside the form
        submit_topup = st.form_submit_button("💰 Top-up Wallet", use_container_width=True)
        
        if submit_topup:
            if not reference:
                st.error("❌ Please enter a reference number")
                return
            
            with st.spinner("Processing top-up..."):
                topup_data = {
                    "amount": amount,
                    "source": source,
                    "reference": reference
                }
                
                result = api_request("customer/topup", "POST", topup_data)
            
            if result.get('success'):
                st.success("💰 Wallet topped up successfully!")
                st.balloons()
                
                topup = result['data']
                st.info(f"""
                **Top-up Successful!**
                
                **Transaction ID:** {topup['transaction_id']}
                **Amount Added:** P {topup['amount']:.2f}
                **Source:** {topup['source'].replace('_', ' ').title()}
                **Previous Balance:** P {topup['old_balance']:.2f}
                **New Balance:** P {topup['new_balance']:.2f}
                **Reference:** {topup['reference']}
                """)
                
                time.sleep(3)
                st.rerun()
            else:
                st.error(f"❌ Top-up failed: {result.get('error')}")

def show_customer_history(user):
    """Customer transaction history"""
    st.markdown("### 📊 **Transaction History**")
    
    transactions = api_request(f"wallets/{user['wallet_id']}/transactions")
    
    if transactions.get('success'):
        if transactions['data']:
            txn_data = []
            for txn in transactions['data']:
                # Determine if sent or received
                txn_type = "📤 Sent" if txn['type'] == 'sent' else "📥 Received"
                
                txn_data.append({
                    'Date': datetime.fromisoformat(txn['created_at']).strftime('%m-%d %H:%M'),
                    'Type': txn_type,
                    'Amount': f"P {txn['amount']:.2f}",
                    'Fee': f"P {txn['fee']:.2f}" if txn['fee'] and txn['fee'] > 0 else "FREE",
                    'Channel': txn['channel'].replace('_', ' ').title(),
                    'Description': txn['description'] or 'No description',
                    'Status': txn['status'].title()
                })
            
            df_txns = pd.DataFrame(txn_data)
            st.dataframe(df_txns, hide_index=True, use_container_width=True)
            
            # Summary
            summary = transactions.get('summary', {})
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Transactions", summary.get('total_transactions', 0))
            with col2:
                st.metric("Total Fees Saved", f"P {summary.get('total_fees_saved', 0):.2f}")
            with col3:
                st.metric("Free Transfers", summary.get('phantom_transfers', 0))
        else:
            st.info("📭 No transactions found")
    else:
        st.error(f"❌ Error loading transactions: {transactions.get('error')}")

def show_customer_notifications(user):
    """Customer notifications"""
    st.markdown("### 🔔 **Your Notifications**")
    
    notifications = api_request("notifications")
    if notifications.get('success'):
        if notifications['data']:
            for notif in notifications['data']:
                notification_type = notif['type']
                icon = "🎉" if notification_type == "success" else "ℹ️" if notification_type == "info" else "⚠️"
                
                # Create notification card
                with st.container():
                    st.markdown(f"""
                    <div style="border-left: 4px solid {'#28a745' if notification_type == 'success' else '#17a2b8' if notification_type == 'info' else '#ffc107'}; 
                                padding: 1rem; margin: 0.5rem 0; background: #f8f9fa; border-radius: 0 8px 8px 0;">
                        {icon} {notif['message']}
                        <br><small style="color: #6c757d;">{notif['created_at']}</small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("📭 No new notifications")
    else:
        st.error("❌ Could not load notifications")

def show_merchant_register():
    """Enhanced merchant registration"""
    show_header()
    
    st.markdown("## 🏪 **Register Your Business**")
    st.markdown("Join FNB Phantom Banking and serve Botswana's unbanked population")
    
    # Initialize registration success state
    if 'registration_success' not in st.session_state:
        st.session_state.registration_success = None
    
    # Show success message if registration was successful
    if st.session_state.registration_success:
        st.success("🎉 Business registered successfully!")
        st.balloons()
        
        # Display success info outside of form
        st.markdown("### ✅ Registration Complete!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"""
            **Business:** {st.session_state.registration_success['business_name']}
            **Email:** {st.session_state.registration_success['email']}
            **Merchant ID:** {st.session_state.registration_success['merchant_id']}
            """)
        
        with col2:
            st.success(f"""
            **API Key:** `{st.session_state.registration_success['api_key']}`
            *(Save this for API integration)*
            """)
        
        st.markdown("### 🎯 What's Next?")
        st.markdown("""
        1. **Login** with your new credentials
        2. **Create customer wallets** for your clients with automatic PIN generation
        3. **Accept payments** with 67% cost savings
        4. **Top-up customer wallets** as needed
        5. **Suggest account upgrades** to full FNB accounts
        6. **Monitor** your business dashboard with real-time analytics
        """)
        
        # Navigation buttons outside of form
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("🔑 Login Now", use_container_width=True, key="register_success_login"):
                st.session_state.registration_success = None  # Clear success state
                st.session_state.page = "merchant_login"
                st.rerun()
        with col_nav2:
            if st.button("🏠 Back to Home", use_container_width=True, key="register_success_home"):
                st.session_state.registration_success = None  # Clear success state
                st.session_state.page = "home"
                st.rerun()
        
        return  # Exit early to prevent showing the form again
    
    # Registration form
    with st.form("merchant_registration"):
        col1, col2 = st.columns(2)
        
        with col1:
            business_name = st.text_input("Business Name *", placeholder="e.g., Gaborone General Store")
            email = st.text_input("Business Email *", placeholder="admin@yourbusiness.co.bw")
            phone = st.text_input("Phone Number *", placeholder="+267 75 123 456")
            
        with col2:
            location = st.text_input("Location", placeholder="Gaborone, Botswana")
            business_type = st.selectbox("Business Type", [
                "General Store", "Hair Salon", "Electronics Shop", 
                "Restaurant", "Pharmacy", "Clothing Store", "Other"
            ])
            fnb_account = st.text_input("FNB Account (Optional)", placeholder="62012345678")
        
        password = st.text_input("Password *", type="password", placeholder="Minimum 6 characters")
        confirm_password = st.text_input("Confirm Password *", type="password")
        
        submitted = st.form_submit_button("🚀 Register Business", use_container_width=True)
        
        if submitted:
            # Validation
            if not all([business_name, email, phone, password]):
                st.error("❌ Please fill in all required fields marked with *")
                return
                
            if password != confirm_password:
                st.error("❌ Passwords do not match")
                return
                
            if len(password) < 6:
                st.error("❌ Password must be at least 6 characters")
                return
            
            # Registration data
            registration_data = {
                'business_name': business_name,
                'email': email,
                'phone': phone,
                'location': location,
                'business_type': business_type,
                'fnb_account': fnb_account,
                'password': password
            }
            
            # Call registration API
            with st.spinner("🔄 Registering your business..."):
                result = api_request("auth/merchant/register", "POST", registration_data)
            
            if result.get('success'):
                # Store success data in session state
                st.session_state.registration_success = result['data']
                st.rerun()  # Rerun to show success message
            else:
                st.error(f"❌ Registration failed: {result.get('error', 'Unknown error')}")
    
    # Back to home button (outside form, only shown when not successful)
    if not st.session_state.registration_success:
        if st.button("← Back to Home", key="register_back_home"):
            st.session_state.page = "home"
            st.rerun()

def main():
    """Main application"""
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 🧭 **Navigation**")
        
        if st.button("🏠 Home", use_container_width=True, key="sidebar_home"):
            st.session_state.page = "home"
            st.rerun()
        
        st.markdown("### 🏪 **For Merchants**")
        if st.button("🚀 Register Business", use_container_width=True, key="sidebar_register"):
            st.session_state.page = "merchant_register"
            st.rerun()
        
        if st.button("🔑 Merchant Login", use_container_width=True, key="sidebar_merchant_login"):
            st.session_state.page = "merchant_login"
            st.rerun()
        
        st.markdown("### 📱 **For Customers**")
        if st.button("💳 Customer Login", use_container_width=True, key="sidebar_customer_login"):
            st.session_state.page = "customer_login"
            st.rerun()
        
        st.markdown("---")
        
        # API Status
        if check_api_connection():
            st.success("🟢 **API Connected**")
        else:
            st.error("🔴 **API Offline**")
            st.markdown("Start: `python api_server.py`")
        
        # User info
        if st.session_state.user_data:
            st.markdown("### 👤 **Logged In**")
            user = st.session_state.user_data
            if user.get('user_type') == 'merchant':
                st.markdown(f"**Business:** {user.get('business_name', 'Unknown')}")
                st.markdown(f"**Type:** Merchant")
            else:
                st.markdown(f"**Customer:** {user.get('customer_name', 'Unknown')}")
                st.markdown(f"**Type:** Customer")
                st.markdown(f"**Balance:** P {user.get('balance', 0):.2f}")
        
        # System info
        st.markdown("### ℹ️ **System Info**")
        st.markdown(f"**Page:** {st.session_state.page}")
        st.markdown(f"**Last Update:** {st.session_state.last_update.strftime('%H:%M:%S')}")
    
    # Route to appropriate page
    if st.session_state.page == "home":
        show_home()
    elif st.session_state.page == "merchant_register":
        show_merchant_register()
    elif st.session_state.page == "merchant_login":
        show_merchant_login()
    elif st.session_state.page == "customer_login":
        show_customer_login()
    elif st.session_state.page == "merchant_dashboard":
        show_merchant_dashboard()
    elif st.session_state.page == "customer_wallet":
        show_customer_wallet()
    else:
        show_home()

if __name__ == "__main__":
    main()