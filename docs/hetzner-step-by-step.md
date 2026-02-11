# Hetzner Step-by-Step Deployment

Use this flow when you start from zero server.

## 1) Create Hetzner VM

1. Create a new Hetzner Cloud server:
   - Image: Ubuntu 24.04
   - Type: CX22 or higher
   - Region: nearest to your users
2. Add your SSH key in server creation wizard.
3. Note server public IP.

## 2) Point domain to server

1. Create DNS A record:
   - Host: `api` (or your chosen subdomain)
   - Value: `<your-hetzner-server-ip>`
2. Wait until DNS propagates.

## 3) Prepare server runtime

SSH into server:

```bash
ssh root@<SERVER_IP>
```

Install Docker + Compose plugin:

```bash
apt update
apt install -y ca-certificates curl gnupg git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
```

## 4) Clone repo and prepare deploy files

```bash
cd /opt
git clone https://github.com/zippro/homeai.git
cd homeai
cp deploy/backend-api.env.production.example deploy/backend-api.env
cp deploy/Caddyfile.hetzner.template deploy/Caddyfile
```

Edit `deploy/backend-api.env` and fill real values:
- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `ADMIN_API_TOKEN`
- provider keys
- webhook secrets

Edit `deploy/Caddyfile` and set your real API domain.

## 5) Start backend stack

If this server is dedicated to HomeAI:

```bash
cd /opt/homeai/deploy
docker compose -f docker-compose.hetzner.yml up -d --build
docker compose -f docker-compose.hetzner.yml ps
```

If this server already hosts another website/proxy:

```bash
cd /opt/homeai/deploy
docker compose -f docker-compose.hetzner.backend-only.yml up -d --build
docker compose -f docker-compose.hetzner.backend-only.yml ps
```

## 6) Verify health and route preview

From server:

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS "http://127.0.0.1:8000/v1/config/provider-route-preview?operation=restyle&tier=preview&target_part=full_room"
```

From local machine (replace domain):

```bash
curl -fsS https://api.yourdomain.com/healthz
curl -fsS "https://api.yourdomain.com/v1/config/provider-route-preview?operation=restyle&tier=preview&target_part=full_room"
```

## 7) Connect web and admin

1. Web app settings -> `API Base URL` = `https://api.yourdomain.com`
2. Admin dashboard settings -> `API Base URL` = `https://api.yourdomain.com`

## 8) Basic operations

Update deployment:

```bash
cd /opt/homeai
git pull origin main
cd deploy
docker compose -f docker-compose.hetzner.yml up -d --build
```

View logs:

```bash
cd /opt/homeai/deploy
docker compose -f docker-compose.hetzner.yml logs -f backend-api
```
