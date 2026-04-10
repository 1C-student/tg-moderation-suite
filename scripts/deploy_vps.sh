#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: ./scripts/deploy_vps.sh <domain> <email>"
  echo "Example: ./scripts/deploy_vps.sh bot.example.com admin@example.com"
  exit 1
fi

DOMAIN="$1"
EMAIL="$2"

if [[ ! -f "./bot_server/.env" ]]; then
  echo "Missing ./bot_server/.env"
  echo "Copy .env.example -> .env and fill TELEGRAM_TOKEN + MANAGER_API_KEY first."
  exit 1
fi

cp ./deploy/nginx/conf.d/bot.conf.template ./deploy/nginx/conf.d/bot.conf
sed -i "s/__DOMAIN__/${DOMAIN}/g" ./deploy/nginx/conf.d/bot.conf

docker compose up -d --build bot_server nginx

docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d "${DOMAIN}" \
  --email "${EMAIL}" \
  --agree-tos \
  --no-eff-email

cat > ./deploy/nginx/conf.d/bot.conf <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    location / {
        proxy_pass http://bot_server:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

docker compose restart nginx

echo "Deployment done."
echo "API URL: https://${DOMAIN}"
echo "Remember to set this URL in manager app."
