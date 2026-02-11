# Hetzner Existing Server (No Conflict Plan)

Yes, you can host HomeAI backend on the same server as another website.

Use a separate API subdomain (example: `api.yourdomain.com`) and run backend on localhost-only port `18000`, then route traffic from your existing reverse proxy.

## 1) Confirm current ports

SSH to server:

```bash
ssh root@<SERVER_IP>
```

Check who already uses 80/443:

```bash
ss -ltnp | grep -E ':80|:443' || true
```

If another site already uses these ports, do **not** start another public reverse proxy container for HomeAI.

## 2) DNS for API subdomain

Add DNS A record:
- Host: `api`
- Value: `<SERVER_IP>`

## 3) Deploy backend only (localhost bind)

```bash
cd /opt
git clone https://github.com/zippro/homeai.git || true
cd /opt/homeai
git pull origin main
cp deploy/backend-api.env.production.example deploy/backend-api.env
```

Edit env:

```bash
nano deploy/backend-api.env
```

Minimum required:
- `APP_ENV=production`
- `ALLOW_OPEN_ADMIN_MODE=false`
- `DATABASE_URL=...`
- `ALLOWED_ORIGINS=https://home-ai-five.vercel.app,https://home-ai-five.vercel.app`
- `ADMIN_API_TOKEN=...`
- provider keys + webhook secrets

Start backend:

```bash
cd /opt/homeai/deploy
docker compose -f docker-compose.hetzner.backend-only.yml up -d --build
docker compose -f docker-compose.hetzner.backend-only.yml ps
```

Backend now listens at `127.0.0.1:18000` only (no public port conflict).

## 4) Add reverse proxy route in your existing proxy

Use **one** of these, based on your current setup.

### If existing proxy is Nginx

Create `/etc/nginx/sites-available/homeai-api.conf`:

```nginx
server {
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:18000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
ln -sf /etc/nginx/sites-available/homeai-api.conf /etc/nginx/sites-enabled/homeai-api.conf
nginx -t && systemctl reload nginx
```

### If existing proxy is Caddy

Add to your current Caddyfile:

```caddy
api.yourdomain.com {
  reverse_proxy 127.0.0.1:18000
}
```

Reload:

```bash
caddy reload --config /etc/caddy/Caddyfile
```

## 5) Verify endpoints

From server:

```bash
curl -fsS http://127.0.0.1:18000/healthz
curl -fsS "http://127.0.0.1:18000/v1/config/provider-route-preview?operation=restyle&tier=preview&target_part=full_room"
```

From your laptop:

```bash
curl -fsS https://api.yourdomain.com/healthz
curl -fsS "https://api.yourdomain.com/v1/config/provider-route-preview?operation=restyle&tier=preview&target_part=full_room"
```

## 6) Connect web/admin

Set API Base URL in both:
- Web app settings: `https://api.yourdomain.com`
- Admin dashboard settings: `https://api.yourdomain.com`

This keeps your old website intact and avoids port/domain collisions.
