# AWS Lightsail demo deploy (cheap, a few days)

This guide deploys the full stack from this repo (frontend + backend + workers + Postgres + Redis) to **one** AWS Lightsail instance, which is the cheapest and easiest option for a short course demo.

## 0) What you will get

- A public website at `http://<your-lightsail-ip>/`
- API calls work through the same URL (the browser calls `/api/...`)
- Only **port 80** is exposed to the internet (safer + simpler)

## 1) Create the Lightsail instance

In AWS Console → **Lightsail**:

- **Create instance**
  - **Platform**: Linux/Unix
  - **Blueprint**: Ubuntu (latest)
  - **Plan**:
    - Choose the smallest first (cheapest). If your app crashes with “out of memory”, upgrade to the next size.
    - If you’re unsure, start with **2 GB RAM**.
- **Networking (Firewall)**
  - Allow:
    - **TCP 22** (SSH)
    - **TCP 80** (HTTP)
  - Do **NOT** open database ports (5432) or Redis (6379).

After it’s created, copy the **Public IPv4 address**.

## 2) SSH into the instance

Use the Lightsail “Connect using SSH” button (easiest), or your terminal.

## 3) Install Docker + Docker Compose

Run on the server:

```bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

## 4) Get the code onto the server

If your repo is on GitHub:

```bash
git clone <YOUR_REPO_URL>
cd cs529-ai-project1
```

If it’s not on GitHub, copy the folder to the server (zip/scp) and `cd` into it.

## 5) Create the `.env` file (server secrets)

In the repo root on the server:

```bash
cp .env.example .env
nano .env
```

Minimum required:
- `OPENAI_API_KEY=...` (required for the AI features)

Recommended:
- Set `INTERNAL_COMPILE_TOKEN` to any random string (example: `INTERNAL_COMPILE_TOKEN=demo-12345`).

Do **not** commit `.env` to git.

## 6) Start the production containers

Run:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose ps
```

## 7) Verify it works

On the server:

```bash
curl -i http://localhost/healthz
```

From your laptop browser:
- Open `http://<LIGHTSAIL_PUBLIC_IP>/`

If the UI loads but API calls fail, confirm:
- your browser can reach `http://<LIGHTSAIL_PUBLIC_IP>/api/...`
- backend is healthy in `docker compose ps`

## 8) If something goes wrong (common fixes)

### View logs

```bash
docker compose logs -f --tail=200 reverse-proxy
docker compose logs -f --tail=200 backend
docker compose logs -f --tail=200 frontend
```

### Restart everything

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Out of memory

If builds crash or containers keep restarting, upgrade Lightsail to a bigger plan (usually the next one up).

## 9) Cleanup (stop paying)

After your demo, to stop charges:

1. In Lightsail, **delete the instance**
2. Also delete:
   - any **Snapshots** you created
   - any extra **Disks** attached to the instance (if you created them)

That’s it — no instance means no ongoing compute cost.

