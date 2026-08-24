# Triton Compliance Portal — Adobe Sign Backend

Small Node + Express service that the Triton Compliance Form Portal calls to:

- authenticate portal users
- persist client drafts on the NAS
- push generated PDFs into **Adobe Sign (Acrobat Sign)** and create a signing agreement

The frontend (`triton-compliance-portal.html`) stays a single static file. This backend exists because Adobe Sign's OAuth credentials and client draft records must never live only in the browser.

---

## 1. Prerequisites

- Node.js **18 or newer** (uses the built-in `fetch` API)
- An Adobe Sign / Acrobat Sign account with API access
- An OAuth application registered in Adobe Sign

---

## 2. Set up the Adobe Sign OAuth application

1. Log in to Adobe Sign → **Account → Adobe Sign API → API Applications** (or via Adobe Developer Console)
2. **Create** a new application. Set:
   - Display Name: `Triton Compliance Portal`
   - Domain: any value (e.g. `triton.local`)
3. Open the application → **Configure OAuth for Application**
   - Redirect URI: `https://triton.local/callback` (any reachable URL; for local testing use `http://localhost:3000/callback`)
   - Enabled scopes:
     - `user_login:self`
     - `agreement_send:account`
     - `agreement_write:account`
     - `agreement_read:account`
   - **Save**
4. From the application page, copy:
   - **Client ID**
   - **Client Secret**

### Generate a refresh token

Adobe's REST docs walk through this. Quick recipe:

a. Open this URL in a browser (replace placeholders):
```
https://secure.na4.adobesign.com/public/oauth/v2
  ?response_type=code
  &client_id=<YOUR_CLIENT_ID>
  &redirect_uri=<YOUR_REDIRECT_URI>
  &scope=user_login:self+agreement_send:account+agreement_write:account+agreement_read:account
```
(If your account lives in a different region, replace `na4` with `na1`, `na2`, `eu1`, `jp1`, etc.)

b. Approve the prompt. You'll be redirected to `<YOUR_REDIRECT_URI>?code=<CODE>`. Copy the `code` value.

c. Exchange the code for a refresh token:
```bash
curl -X POST "https://api.na4.adobesign.com/oauth/v2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=<CLIENT_ID>" \
  -d "client_secret=<CLIENT_SECRET>" \
  -d "redirect_uri=<REDIRECT_URI>" \
  -d "code=<CODE_FROM_STEP_B>"
```
Response contains `refresh_token`. Save it.

---

## 3. Configure the backend

```bash
cd server
cp .env.example .env
```

Edit `.env` and fill in:
```
ADOBE_CLIENT_ID=<from step 2>
ADOBE_CLIENT_SECRET=<from step 2>
ADOBE_REFRESH_TOKEN=<from step 2c>
ADOBE_API_BASE=https://api.na4.adobesign.com    # adjust region if needed
PORT=3000
ALLOWED_ORIGINS=*                                 # tighten for production
```

---

## 4. Install & run

```bash
cd server
npm install
npm start
```

You should see:
```
[triton-compliance] Adobe Sign backend listening on http://localhost:3000
  POST /api/auth/login
  GET  /api/drafts
  POST /api/adobe-sign/send
  GET  /api/health
  GET  /                       (serves triton-compliance-portal.html)
```

Verify credentials are loaded:
```bash
curl http://localhost:3000/api/health
```
Expected: `{ "ok": true, "hasClientId": true, "hasClientSecret": true, "hasRefreshToken": true, ... }`

---

## 5. Use the portal

Open **http://192.168.50.158:3000/** while connected to the same private network as the NAS.
The NAS issues a local session automatically, so the hosted portal does not show a password screen.
Requests arriving through the public Cloudflare tunnel cannot create sessions or access drafts,
password changes, or Adobe Sign. The public health endpoint remains available for uptime checks.

When you reach the **Review & Generate PDF** step:

1. Click **Generate PDF** to download a local copy (no network needed).
2. Click **Send via Adobe Sign**, fill in advisor + client email(s), click **Send**.
3. The backend uploads the PDF, creates a sequential signing agreement, and returns the Adobe Sign **agreement ID**.
4. Adobe Sign emails the first signer (advisor) immediately. When the advisor finishes, the next signer (client) is notified, and so on.

---

## 6. REST API reference

### `POST /api/auth/login`

Authenticates the portal password and returns a temporary session token.
When `remember` is enabled, the signed trusted-device token remains valid for
180 days and survives routine NAS/container restarts. Changing the portal
password invalidates all previously issued signed tokens.

### `GET /api/drafts` / `PUT /api/drafts`

Loads and saves the active draft list. Drafts are stored on the NAS in `server/data/drafts.json`.
The `server/data/*.json` files are intentionally ignored by Git so client records are
included in NAS backups but are not committed to GitHub in plaintext.

### `POST /api/adobe-sign/send`

Request:
```json
{
  "pdfBase64":     "JVBERi0xLj... (base64-encoded PDF)",
  "fileName":      "Triton_Seg_Fund_John_Doe_2026-05-20.pdf",
  "agreementName": "Triton Compliance — John Doe — Segregated Fund",
  "signers": [
    { "email": "advisor@example.com", "name": "Jie Yuan" },
    { "email": "client@example.com",  "name": "John Doe" }
  ],
  "message": "Please review and sign — Triton Wealth Management."
}
```

Success (200):
```json
{ "ok": true, "agreementId": "CBJCHBC...", "transientDocumentId": "3AAA..." }
```

Failure (400/500):
```json
{ "ok": false, "error": "Invalid signer email: foo" }
```

### `GET /api/health`
Returns status + which env vars are set (boolean only, not the secrets themselves).

---

## 7. Production notes

- Run behind HTTPS (e.g. nginx / Caddy reverse proxy) before exposing publicly.
- Replace `ALLOWED_ORIGINS=*` with your portal's actual origin.
- Keep `server/data/` on persistent NAS storage and include it in NAS backups.
- Do not commit `server/data/*.json`; those files can contain client records and the portal password hash.
- On the NAS, use `sh docker/nas-git.sh status` or `sh docker/nas-git.sh log --oneline -5`
  when the host does not have a native `git` command. GitHub pushes still require GitHub credentials
  configured on the NAS; do not hard-code tokens in this repository.
- The current implementation supports a **single Adobe Sign account** (single `.env`). For multi-advisor setups, add per-advisor credential storage.
- Refresh tokens last 60 days unless rotated. Re-run the refresh-token recipe in step 2 when needed.
