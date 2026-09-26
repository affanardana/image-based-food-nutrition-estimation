# Setup, step by step

Follow this in order. Each part ends with a **checkpoint** — a command and
the output you should see. If the output doesn't match, stop and fix it
there; later steps assume the earlier ones work.

Total time: 60–90 minutes, most of it waiting for downloads and builds.

```
Vercel (frontend)
      │  HTTPS
      ▼
VPS  ── Caddy (TLS) ──▶ API container
      ▲
      │  SSH reverse tunnel (opened by CVIS, encrypted)
      │
CVIS ──▶ vision container (SAM3 + YOLO depth, CPU)  ──▶ Supabase
```

---

## Before you start

You need five things. Write them down before touching a terminal.

**1. The VPS's IPv4.** On the VPS:

```bash
curl -4 ifconfig.me
```

**2. The API hostname.** Two options:

- **Free:** `<the-ip>.sslip.io` — for IP `103.150.60.10` that's
  `103.150.60.10.sslip.io`. sslip.io resolves any name of that shape to
  the IP inside it, so there is nothing to configure.
- **A domain you own** (~$10/year): add a DNS `A` record pointing at the
  VPS IP, and use that name. Tidier on a CV.

**3. Your repo's clone URL.**

**4. Database and Supabase values.** From the Modal secret `ifne-api`:
`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. Copy them —
do not retype the database URL, one wrong character breaks it.

**5. Your Vercel URL**, exactly as the browser sends it.

---

# Part 1 — The VPS (API host)

You are `root` on Ubuntu 26.04, 1 vCPU, 3.8 GB RAM. That's plenty: the API
carries no torch.

### 1.1 Update and install Docker

```bash
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
```

**Checkpoint:**

```bash
docker --version
```

→ `Docker version 2x.x.x` or newer. Anything 20.10+ supports what we need.

### 1.2 Create the account the tunnel will use

The tunnel authenticates with an SSH key. Giving it its own account means
that key can't be used to log in as root.

```bash
adduser --disabled-password --gecos "" ifne
mkdir -p /home/ifne/.ssh && chmod 700 /home/ifne/.ssh
touch /home/ifne/.ssh/authorized_keys && chmod 600 /home/ifne/.ssh/authorized_keys
chown -R ifne:ifne /home/ifne/.ssh
```

**Checkpoint:**

```bash
ls -la /home/ifne/.ssh/
```

→ `authorized_keys` owned by `ifne`, mode `-rw-------`.

### 1.3 Clone the repo

```bash
cd ~
git clone <your-repo-url> ifne
cd ifne/backend/deploy/vps
```

**Checkpoint:**

```bash
ls
```

→ `Caddyfile  Dockerfile  docker-compose.yml  .env.example`

### 1.4 Configure

```bash
cp .env.example .env
nano .env
```

Fill in:

| Variable | Value |
|---|---|
| `API_HOSTNAME` | from Before-you-start #2 |
| `VISION_REMOTE_URL` | leave as `http://host.docker.internal:9099` |
| `DATABASE_URL` | pasted from the Modal secret |
| `SUPABASE_URL` | pasted |
| `SUPABASE_SERVICE_KEY` | pasted |
| `CORS_ORIGINS` | your Vercel URL |

Save with `Ctrl+O`, `Enter`, then exit with `Ctrl+X`.

### 1.5 Start the API

```bash
docker compose up -d --build
docker compose logs -f caddy
```

The first build takes a few minutes. Caddy will try to obtain a
certificate and **will fail** — the vision service doesn't exist yet, but
more importantly the certificate needs DNS to already point here. Watch
for `certificate obtained successfully`; press `Ctrl+C` to stop following
the logs.

**Checkpoint:**

```bash
curl https://<API_HOSTNAME>/api/v1/health
```

→ `{"status":"success","data":{"service":"healthy"}}`

**If the certificate fails:** confirm `API_HOSTNAME` resolves to this
machine (`dig +short <API_HOSTNAME>`), and that ports 80 and 443 are open
inbound. Caddy needs both.

---

# Part 2 — CVIS (vision service)

Log in to `server-cvis` as `theophilus`. You have `sudo`.

### 2.1 Clone the repo

```bash
cd ~
git clone <your-repo-url> ifne
cd ifne/backend/deploy/cvis
```

### 2.2 Download the checkpoints (~6 GB)

`facebook/sam3` is a gated repository. Request access on Hugging Face and
create a **fine-grained, read-only token scoped to `facebook/sam3`**, with
an expiry. Then:

```bash
read -s -p "HF token: " HF_TOKEN && export HF_TOKEN   # keeps it out of shell history
bash fetch-models.sh
```

Use `bash`, not `./` — the executable bit doesn't survive git on Windows.

On a shared host, treat anything typed at the prompt as visible to the
other sudoers: `export HF_TOKEN=...` on the command line lands in
`~/.bash_history`, which persists on disk. `read -s` avoids that. Either
way, **revoke the token once the download finishes** — nothing at runtime
reads it, and the script deletes the cached copy it leaves behind.

**Checkpoint:**

```bash
ls -lh models/
```

→ `sam3.pt` and `yolo26x-depth.pt`, both non-zero.

### 2.3 Start the service

```bash
docker compose up -d --build
docker compose logs -f
```

The build takes a while (it installs torch and the CLIP fork).

**Checkpoint:**

```bash
curl http://127.0.0.1:9099/health
```

→ `{"status":"success","service":"healthy"}` from *this* machine.

Note: it binds to `127.0.0.1` only. Nothing on the network can reach it —
the tunnel in Part 3 is the only way in, which is what keeps this
unauthenticated endpoint private on a shared host.

---

# Part 3 — The tunnel

The campus firewall blocks inbound to CVIS, so the VPS cannot call it
directly. Instead, CVIS opens an **outbound** SSH connection and asks the
VPS to forward a port back down it. Outbound SSH is permitted, and SSH is
not TLS, so the campus inspection doesn't interfere.

### 3.1 Generate a key on CVIS

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_tunnel -N "" -C "ifne-tunnel"
cat ~/.ssh/id_ed25519_tunnel.pub
```

Copy the whole line it prints (starts with `ssh-ed25519`).

### 3.2 Authorise it on the VPS

Back on the **VPS**:

```bash
echo "<paste the public key line>" >> /home/ifne/.ssh/authorized_keys
tail -1 /home/ifne/.ssh/authorized_keys
```

### 3.3 Test the tunnel by hand first

On **CVIS** — always do this before installing the service, so you see the
error directly instead of through a restart loop:

```bash
ssh -NT -i ~/.ssh/id_ed25519_tunnel -o StrictHostKeyChecking=accept-new \
    -R 9099:localhost:9099 ifne@<vps-ip>
```

It will sit there with no output — that means it worked. Leave it running
and, in a **second terminal on the VPS**, run:

```bash
curl http://127.0.0.1:9099/health
```

→ the vision service's health response, arriving through the tunnel.

Then `Ctrl+C` the ssh command on CVIS.

### 3.4 Make it permanent

On **CVIS**:

```bash
cd ~/ifne/backend/deploy/cvis
cp .env.example .env
nano .env                     # VPS_SSH_TARGET=ifne@<vps-ip>
```

Open the unit and adjust two lines if your paths differ:
`User=theophilus` and `EnvironmentFile=/home/theophilus/ifne/backend/deploy/cvis/.env`.

```bash
sudo cp ifne-tunnel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ifne-tunnel
```

**Checkpoint:**

```bash
systemctl status ifne-tunnel
```

→ `active (running)`. Then from the **VPS**:

```bash
curl http://127.0.0.1:9099/health
```

→ healthy. `Restart=always` means a dropped tunnel comes back by itself.

---

# Part 4 — Verify the whole chain

On the VPS, each command tests one link:

```bash
curl http://127.0.0.1:9099/health
```
→ tunnel is up

```bash
docker compose exec api curl -s http://host.docker.internal:9099/health
```
→ the API container can reach it (this is the one that catches a wrong
`VISION_REMOTE_URL`)

```bash
curl https://<API_HOSTNAME>/api/v1/health
```
→ TLS and the API

```bash
curl "https://<API_HOSTNAME>/api/v1/foods/search?q=rice&limit=1"
```
→ the database

Finally, run a **real analysis** in the browser before moving the
frontend: point your local frontend at `https://<API_HOSTNAME>`, upload a
photo, label it, and check the result and history. This is the only test
that exercises the whole pipeline.

---

# Part 5 — Switch over

1. **Vercel** → `VITE_API_BASE_URL=https://<API_HOSTNAME>` → **redeploy**.
   Vite inlines this at build time; saving the variable does nothing.
2. **cron-job.org** → point the job at
   `https://<API_HOSTNAME>/api/v1/foods/search?q=rice&limit=1`.
3. **Leave Modal running.** Rollback is one Vercel variable and a
   redeploy, so keep it until the new stack has served real traffic.
4. Then decommission Modal — see `DECOMMISSION.md`.

---

## When something fails

| Symptom | Cause |
|---|---|
| Caddy can't get a certificate | `API_HOSTNAME` doesn't resolve to this IP, or inbound 80/443 is blocked |
| `curl 127.0.0.1:9099` fails on the VPS | Tunnel down: `systemctl status ifne-tunnel` on CVIS, then `sudo journalctl -u ifne-tunnel -n 30` |
| Tunnel restarts repeatedly | Key not authorised, or wrong `VPS_SSH_TARGET`. Re-run the manual test in 3.3 |
| API can't reach the vision service | `VISION_REMOTE_URL` must be `http://host.docker.internal:9099`. Inside the container, `127.0.0.1` is the container itself |
| API returns 502 | `docker compose logs api` on the VPS |
| Analysis hangs, then errors | Tunnel up but vision container down: `docker compose logs vision` on CVIS |
| Analysis is slow | Expected on CPU, and while other jobs on the shared host are busy. The first request after a restart loads the models |
| Browser blocks the request | `API_HOSTNAME` is serving plain HTTP — mixed-content errors mean TLS is broken |

## Notes

- `MAX_UPLOAD_SIZE_MB=2` bounds peak memory: the API holds the image, the
  masks and the depth map at once.
- Both `.env` files are gitignored — one holds the database password and
  the Supabase service key, the other the tunnel target.
- Why a tunnel rather than a network route: the campus firewall blocks
  inbound, and it intercepts TLS to VPN-like services — `tailscaled` fails
  with `x509: certificate signed by unknown authority`, seeing a Fortinet
  appliance's certificate. **Do not** try to fix that by trusting the
  campus CA; that defeats a control the institution put there on purpose.
  SSH is not TLS and the connection is outbound, so it is unaffected.
