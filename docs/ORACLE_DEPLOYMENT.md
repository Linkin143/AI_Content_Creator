# Deploying AEVRIX on Oracle Cloud Always Free (free forever)

This guide puts the whole engine — FastAPI (OAuth), Telegram bot, scheduler, and
dashboard — on a single **Oracle Cloud Always Free** VM that stays on 24/7 at
**$0/month**. All deployment files live in `deploy/oracle/`.

> Why Oracle? It's the only genuinely free-forever VM big enough to run a
> long-lived bot + scheduler with a persistent disk. A payment card is required
> for identity verification, but the Always Free resources are never charged.

---

## What gets deployed

| Process | systemd unit | Port | Purpose |
|---|---|---|---|
| FastAPI | `aevrix-api` | 8000 (localhost) | REST API + OAuth callbacks + `/health` |
| Telegram bot | `aevrix-bot` | — | Approvals (long polling, 24/7) |
| Scheduler | `aevrix-scheduler` | — | Research 08:00 IST + due publications |
| Dashboard | `aevrix-dashboard` | 8501 (localhost) | Streamlit UI |
| Backup | `aevrix-backup.timer` | — | Daily WAL-safe SQLite copy |
| Caddy | `caddy` | 80/443 | Automatic HTTPS reverse proxy |

Only Caddy is exposed publicly; the app ports bind to `127.0.0.1`.

---

## Step 1 — Create the VM

1. Sign up at cloud.oracle.com (add a card for verification; pick the **Always
   Free** eligible home region).
2. **Compute → Instances → Create Instance**:
   - **Image:** Canonical Ubuntu 24.04.
   - **Shape:** `VM.Standard.A1.Flex` (Ampere ARM) — assign e.g. **2 OCPU /
     12 GB RAM** (well within Always Free). If ARM capacity is unavailable in
     your region, fall back to `VM.Standard.E2.1.Micro` (AMD, Always Free).
   - **SSH keys:** upload your public key (or let Oracle generate one and save
     the private key).
   - **Boot volume:** default ~47 GB is plenty (persistent — your DB lives here).
3. Note the instance's **public IP**.

## Step 2 — Open ports in Oracle's cloud firewall

Oracle has its own network firewall **separate from the OS firewall** — you must
open both. In the console: **Networking → VCN → your subnet → Security List →
Add Ingress Rules**:

- Source `0.0.0.0/0`, TCP, destination port **80**
- Source `0.0.0.0/0`, TCP, destination port **443**

(SSH port 22 is already allowed by default.)

## Step 3 — Point a domain at the VM

X and LinkedIn OAuth callbacks must be **HTTPS on a stable hostname**. Options:

- A domain you own → add an **A record** → VM public IP.
- Free: create a **DuckDNS** subdomain (e.g. `aevrix.duckdns.org`) pointing at
  the IP. Works perfectly with Caddy's auto-HTTPS.

## Step 4 — Push your code to a git remote

Git-based deploy is the recommended path. Push this repo to a remote the VM can
reach (GitHub/GitLab, private is fine).

- **Public repo:** nothing extra; the VM clones over HTTPS.
- **Private repo:** on the VM, authenticate first — either a GitHub **deploy key**
  (read-only SSH key added to the repo), or an HTTPS **Personal Access Token** in
  the clone URL. A read-only deploy key is the safer choice.

> `.gitattributes` forces all `.sh`/`.service`/`.timer`/`Caddyfile` files to **LF**,
> so git-cloned deploys don't hit the Windows CRLF (`\r`) problem. (Only the local
> rsync fallback needs `dos2unix`.)

## Step 5 — Run the provisioner (clones for you)

SSH in (`ssh ubuntu@<public-ip>`). You need the setup script on the box once —
the quickest way is a shallow clone to a temp dir, then let it clone the real
tree into `/opt/aevrix`:

```bash
git clone <your-repo-url> /tmp/aevrix-src
cd /tmp/aevrix-src
chmod +x deploy/oracle/oracle_setup.sh
# Pass your repo URL (and optionally a branch) → it clones into /opt/aevrix:
./deploy/oracle/oracle_setup.sh <your-repo-url> [branch]
```

This installs Python 3.12 + Caddy, creates the `aevrix` service user, **git-clones
the app to `/opt/aevrix`** (owned by the `aevrix` user), builds the venv with
`[providers]`, installs all systemd units + the backup timer, and opens the OS
firewall (ufw) for 80/443.

> Local (non-git) fallback: run `./deploy/oracle/oracle_setup.sh` with **no URL**
> from inside a checkout to rsync the current tree instead. `update.sh` git-pulls
> only work when you deployed with a URL.

## Step 6 — Fill in secrets

```bash
sudo nano /opt/aevrix/.env
```

Copy your **working local values** — especially:

- `APP_ENCRYPTION_KEY` and `APP_SESSION_SECRET` — **reuse the exact same values**
  as local, or previously stored OAuth tokens (LinkedIn!) can't be decrypted.
- `OPENAI_COMPATIBLE_*` (Azure Foundry GPT-5.x).
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ALLOWED_USER_IDS`.
- `LINKEDIN_*` and (once ready) `X_*`, with **HTTPS** redirect URIs on your domain.

Then set your real domain in Caddy:

```bash
sudo nano /etc/caddy/Caddyfile      # replace aevrix.example.com
sudo systemctl reload caddy         # Caddy fetches a Let's Encrypt cert
sudo systemctl restart aevrix-api aevrix-bot aevrix-scheduler aevrix-dashboard
```

## Step 7 — Update OAuth app redirect URIs

In the **X** and **LinkedIn** developer portals, change the authorized redirect
URIs from `http://localhost:8000/...` to:

- `https://<your-domain>/auth/x/callback`
- `https://<your-domain>/auth/linkedin/callback`

These must match `.env` exactly. Then reconnect from a browser:

- `https://<your-domain>/auth/linkedin/connect`
- `https://<your-domain>/auth/x/connect` (once the X app is Project-attached)

---

## Verify

```bash
systemctl status aevrix-api aevrix-bot aevrix-scheduler --no-pager
curl -s http://127.0.0.1:8000/health          # local health
curl -s https://<your-domain>/health          # through Caddy/HTTPS
journalctl -u aevrix-bot -f                    # live bot logs
```

Send `/pending` or `/connect_status` to your bot to confirm it's live.

---

## Migrating your existing data (optional)

To carry over your 1,038 articles + 9 drafts + LinkedIn token, copy the local
DB up **before** starting services (or stop them first):

```bash
# From your Windows dev machine (adjust paths):
scp data\aevrix.db ubuntu@<public-ip>:/tmp/aevrix.db
# On the VM:
sudo systemctl stop aevrix-api aevrix-bot aevrix-scheduler aevrix-dashboard
sudo mv /tmp/aevrix.db /opt/aevrix/data/aevrix.db
sudo chown aevrix:aevrix /opt/aevrix/data/aevrix.db
sudo systemctl start aevrix-api aevrix-bot aevrix-scheduler aevrix-dashboard
```

This only works if `APP_ENCRYPTION_KEY` on the VM matches the one that encrypted
those tokens.

---

## Day-2 operations

- **Logs:** `journalctl -u aevrix-<service> -n 100 --no-pager`
- **Restart one:** `sudo systemctl restart aevrix-bot`
- **Deploy new code (git):** on the VM run `sudo /opt/aevrix/deploy/oracle/update.sh <ref>`
  where `<ref>` is a **tag** (`v1.2.0`, recommended), a branch, or a commit SHA
  (omit to update the current branch). It fetches, checks out that exact ref,
  reinstalls deps + unit files, restarts services, and health-checks. Your `.env`
  and `data/` are untracked, so a deploy never touches secrets or the DB.
- **Backups:** daily at 02:30 VM time → `/opt/aevrix/data/backups/` (last 14
  kept). Run on demand: `sudo systemctl start aevrix-backup.service`
- **Env changes don't hot-reload** (settings are cached) — always
  `systemctl restart` the affected service after editing `.env`.

---

## Push-to-deploy (GitHub Actions → VM)

Automate releases: pushing a **version tag** (`vX.Y.Z`) makes GitHub Actions SSH
into the VM and run `update.sh` for that exact tag. The workflow is
`.github/workflows/deploy.yml`. The VM pulls the code itself over git — the runner
only triggers it — so your `.env`/`data/` are never touched.

> **Why tags, not every push?** AEVRIX is one live, always-on instance. Tag-based
> deploys keep `main` a free iteration branch and make shipping a deliberate act
> (a bad commit on `main` won't restart your live bot/scheduler). You still get a
> **Run workflow** button to deploy any branch/commit on demand.

### 1. Create a dedicated deploy user on the VM

Keep this account SEPARATE from the `aevrix` service user (so it can't edit the
script it's allowed to sudo):

```bash
sudo useradd --create-home --shell /bin/bash deploy
```

### 2. Add an SSH key for the deploy user

Generate a dedicated keypair (do this on your machine, no passphrase so CI can
use it non-interactively):

```bash
ssh-keygen -t ed25519 -f aevrix_deploy -C "github-actions-deploy" -N ""
```

Put the **public** half on the VM:

```bash
sudo -u deploy mkdir -p /home/deploy/.ssh && sudo -u deploy chmod 700 /home/deploy/.ssh
# paste the contents of aevrix_deploy.pub:
sudo -u deploy tee -a /home/deploy/.ssh/authorized_keys < aevrix_deploy.pub
sudo -u deploy chmod 600 /home/deploy/.ssh/authorized_keys
```

### 3. Allow passwordless sudo for update.sh only

```bash
sudo cp /opt/aevrix/deploy/oracle/sudoers-deploy /etc/sudoers.d/aevrix-deploy
sudo chmod 440 /etc/sudoers.d/aevrix-deploy
sudo visudo -c                 # must report "parsed OK"
```

(The snippet assumes the user is `deploy`; edit the file if yours differs.)

### 4. Add GitHub repository secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `DEPLOY_SSH_HOST` | VM public IP (or hostname) |
| `DEPLOY_SSH_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | full contents of the **private** key `aevrix_deploy` |
| `DEPLOY_SSH_PORT` | `22` (optional) |

### 5. Test it

- **Release (automatic):** tag a commit and push the tag:
  ```bash
  git tag v0.1.0
  git push origin v0.1.0
  ```
  The `deploy` workflow runs and deploys exactly `v0.1.0` on the VM.
- **On-demand (manual):** Actions tab → **deploy** → **Run workflow**; optionally
  type a ref (tag, branch, or commit SHA) to deploy. Leave it blank to update the
  VM's current branch.
- **Rollback:** deploy an older tag — Run workflow with `v0.1.0`, or on the VM
  `sudo /opt/aevrix/deploy/oracle/update.sh v0.1.0`.

> Security notes: the deploy key is SSH-only and the deploy user can run exactly
> one root command. Also restrict SSH ingress — in Oracle's Security List, prefer
> limiting port 22 to known IPs, or use GitHub's published Actions IP ranges.
> Never commit the private key; it lives only in the GitHub secret.

## Troubleshooting

- **`database is locked`** → ensure only ONE `aevrix-scheduler` runs against the DB.
- **HTTPS cert fails** → confirm DNS A record resolves to the VM, and that both
  Oracle Security List AND ufw allow 80/443. Caddy needs port 80 reachable.
- **Bot silent** → `journalctl -u aevrix-bot -f`; verify token + allowed IDs.
- **ARM capacity error on VM create** → retry later or use the AMD micro shape.

See also `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, and `docs/TROUBLESHOOTING.md`.
