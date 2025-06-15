#!/bin/bash
# FNB BaaS Deployment Script

echo "Starting FNB BaaS Platform Deployment..."

# Create directories
mkdir -p /opt/fnb-baas/{logs,data,config,backups}

# Set permissions
chmod 755 /opt/fnb-baas
chmod 700 /opt/fnb-baas/data

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from complete_baas_platform import DatabaseManager; DatabaseManager().init_database()"

# Create systemd service
cat > /etc/systemd/system/fnb-baas.service << EOF
[Unit]
Description=FNB BaaS Platform
After=network.target

[Service]
Type=simple
User=fnb-baas
WorkingDirectory=/opt/fnb-baas
ExecStart=/usr/bin/python3 /opt/fnb-baas/complete_baas_platform.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl enable fnb-baas
systemctl start fnb-baas

# Setup log rotation
cat > /etc/logrotate.d/fnb-baas << EOF
/opt/fnb-baas/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 fnb-baas fnb-baas
}
EOF

# Setup backup cron job
echo "0 2 * * * /opt/fnb-baas/backup.sh" | crontab -u fnb-baas -

echo "FNB BaaS Platform deployed successfully!"
echo "Dashboard: http://localhost:8000/dashboard"
echo "USSD: *120*3333#"
echo "API Docs: http://localhost:8000/docs"
