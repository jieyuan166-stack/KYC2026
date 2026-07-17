/**
 * Triton Compliance Form Portal — Adobe Sign backend
 * ---------------------------------------------------
 *
 *   POST /api/adobe-sign/send
 *     body: {
 *       pdfBase64:      string,      // PDF bytes encoded as base64 (no data:... prefix)
 *       fileName:       string,      // e.g. "Triton_Seg_Fund_John_Doe_2026-05-20.pdf"
 *       agreementName:  string,      // e.g. "Triton Compliance - John Doe - Segregated Fund"
 *       signers:        [{ email, name? }],  // signing order: advisor first, then client(s)
 *       message:        string?      // optional message included in the Adobe Sign email
 *     }
 *     200 response: { ok: true, agreementId, transientDocumentId }
 *
 *   GET /api/health     -> { ok: true }
 */

"use strict";

require("dotenv").config();

const express = require("express");
const cors    = require("cors");
const fs      = require("fs");
const path    = require("path");
const crypto  = require("crypto");

const adobeSign = require("./adobe-sign");

const app = express();
app.disable("x-powered-by");
app.set("trust proxy", 1);
app.use((req, res, next) => {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("X-Frame-Options", "DENY");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  if (req.path.startsWith("/api/")) res.setHeader("Cache-Control", "no-store");
  next();
});
app.use(express.json({ limit: "30mb" }));    // PDFs can be large; allow generous body size

const allowedOrigins = (process.env.ALLOWED_ORIGINS || "*")
  .split(",")
  .map(s => s.trim())
  .filter(Boolean);

app.use(cors({
  origin: (origin, cb) => {
    // Health checks and local development may not send Origin.
    if (!origin) return cb(null, true);
    if (allowedOrigins.includes("*") || allowedOrigins.includes(origin)) return cb(null, true);
    cb(new Error(`Origin ${origin} not allowed by CORS`));
  },
}));

const sendAttempts = new Map();
const SEND_WINDOW_MS = 15 * 60 * 1000;
const SEND_LIMIT = 10;
const DEFAULT_KYC_PASSWORD_HASH = "b4d892dcdd1c8a38a97f6cfcac5bf20075d10947cd9cde9d41e18d2bb2f216d9";
const DATA_DIR = process.env.KYC_DATA_DIR || path.join(__dirname, "data");
const DRAFTS_PATH = path.join(DATA_DIR, "drafts.json");
const AUTH_PATH = path.join(DATA_DIR, "auth.json");
const MAX_DRAFTS_PAYLOAD_BYTES = 28_000_000;
const authSessions = new Map();

const ensureDataDir = () => fs.mkdirSync(DATA_DIR, { recursive: true });

const sha256 = (value) => crypto.createHash("sha256").update(String(value || ""), "utf8").digest("hex");

const readJsonFile = (filePath, fallback) => {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(raw);
  } catch (err) {
    if (err.code !== "ENOENT") console.error(`[storage] Failed to read ${filePath}:`, err.message);
    return fallback;
  }
};

const writeJsonFile = (filePath, value) => {
  ensureDataDir();
  const tmp = `${filePath}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(value, null, 2));
  fs.renameSync(tmp, filePath);
};

const getActivePasswordHash = () => {
  if (process.env.KYC_PASSWORD_HASH) return process.env.KYC_PASSWORD_HASH;
  const auth = readJsonFile(AUTH_PATH, null);
  return auth?.passwordHash || DEFAULT_KYC_PASSWORD_HASH;
};

const createSession = (remember) => {
  const token = crypto.randomBytes(32).toString("hex");
  const ttlMs = remember ? 30 * 24 * 60 * 60 * 1000 : 12 * 60 * 60 * 1000;
  const expiresAt = Date.now() + ttlMs;
  authSessions.set(token, expiresAt);
  return { token, expiresAt };
};

const getBearerToken = (req) => {
  const header = String(req.get("authorization") || "");
  if (header.toLowerCase().startsWith("bearer ")) return header.slice(7).trim();
  return String(req.get("x-kyc-session-token") || "").trim();
};

const requirePortalSession = (req, res, next) => {
  const token = getBearerToken(req);
  const expiresAt = authSessions.get(token);
  if (!token || !expiresAt || expiresAt <= Date.now()) {
    if (token) authSessions.delete(token);
    return res.status(401).json({ ok: false, error: "Unauthorized" });
  }
  next();
};

const readDraftsPayload = () => {
  const parsed = readJsonFile(DRAFTS_PATH, null);
  if (Array.isArray(parsed)) return { drafts: parsed, updatedAt: 0 };
  if (parsed && Array.isArray(parsed.drafts)) return parsed;
  return { drafts: [], updatedAt: 0 };
};

const writeDraftsPayload = (drafts) => {
  writeJsonFile(DRAFTS_PATH, {
    drafts,
    updatedAt: Date.now(),
  });
};

const limitAdobeSend = (req, res, next) => {
  const origin = req.get("origin");
  if (process.env.NODE_ENV === "production" && !origin) {
    return res.status(403).json({ ok: false, error: "Browser origin is required" });
  }
  const now = Date.now();
  const key = req.ip || req.socket.remoteAddress || "unknown";
  const recent = (sendAttempts.get(key) || []).filter(ts => now - ts < SEND_WINDOW_MS);
  if (recent.length >= SEND_LIMIT) {
    return res.status(429).json({ ok: false, error: "Too many Adobe Sign requests. Please try again later." });
  }
  recent.push(now);
  sendAttempts.set(key, recent);
  next();
};

/* -------------------------------------------------------- */
app.get("/api/health", (req, res) => {
  res.json({
    ok: true,
    hasClientId:     !!process.env.ADOBE_CLIENT_ID,
    hasClientSecret: !!process.env.ADOBE_CLIENT_SECRET,
    hasRefreshToken: !!process.env.ADOBE_REFRESH_TOKEN,
    apiBase:         process.env.ADOBE_API_BASE || "https://api.na4.adobesign.com",
  });
});

/* -------------------------------------------------------- */
app.post("/api/auth/login", (req, res) => {
  const { password, remember } = req.body || {};
  if (typeof password !== "string" || password.length > 200) {
    return res.status(400).json({ ok: false, error: "Invalid password" });
  }
  if (sha256(password) !== getActivePasswordHash()) {
    return res.status(401).json({ ok: false, error: "Password is incorrect" });
  }
  res.json({ ok: true, ...createSession(!!remember) });
});

app.post("/api/auth/change-password", requirePortalSession, (req, res) => {
  const { currentPassword, newPassword } = req.body || {};
  if (typeof currentPassword !== "string" || typeof newPassword !== "string") {
    return res.status(400).json({ ok: false, error: "Missing password" });
  }
  if (newPassword.length < 8 || newPassword.length > 200) {
    return res.status(400).json({ ok: false, error: "New password must be between 8 and 200 characters" });
  }
  if (sha256(currentPassword) !== getActivePasswordHash()) {
    return res.status(401).json({ ok: false, error: "Current password is incorrect" });
  }
  writeJsonFile(AUTH_PATH, {
    passwordHash: sha256(newPassword),
    updatedAt: Date.now(),
  });
  authSessions.clear();
  res.json({ ok: true, ...createSession(true) });
});

app.get("/api/drafts", requirePortalSession, (req, res) => {
  res.json({ ok: true, ...readDraftsPayload() });
});

app.put("/api/drafts", requirePortalSession, (req, res) => {
  const drafts = req.body?.drafts;
  if (!Array.isArray(drafts)) {
    return res.status(400).json({ ok: false, error: "drafts must be an array" });
  }
  const bytes = Buffer.byteLength(JSON.stringify(drafts), "utf8");
  if (bytes > MAX_DRAFTS_PAYLOAD_BYTES) {
    return res.status(413).json({ ok: false, error: "Draft payload is too large" });
  }
  writeDraftsPayload(drafts);
  res.json({ ok: true, updatedAt: Date.now() });
});

/* -------------------------------------------------------- */
app.post("/api/adobe-sign/send", limitAdobeSend, async (req, res) => {
  try {
    const { pdfBase64, fileName, agreementName, signers, message } = req.body || {};

    if (!pdfBase64)               return res.status(400).json({ ok: false, error: "Missing pdfBase64" });
    if (!Array.isArray(signers))  return res.status(400).json({ ok: false, error: "signers must be an array" });
    if (signers.length === 0)     return res.status(400).json({ ok: false, error: "At least one signer is required" });
    if (signers.length > 5)       return res.status(400).json({ ok: false, error: "A maximum of five signers is allowed" });
    if (typeof pdfBase64 !== "string" || pdfBase64.length > 42_000_000) {
      return res.status(413).json({ ok: false, error: "PDF payload is too large" });
    }
    if (String(fileName || "").length > 180 || String(agreementName || "").length > 180 || String(message || "").length > 2000) {
      return res.status(400).json({ ok: false, error: "One or more text fields are too long" });
    }

    for (const s of signers) {
      if (!s || !s.email)         return res.status(400).json({ ok: false, error: "Every signer must have an email" });
      if (String(s.email).length > 254 || String(s.name || "").length > 120) {
        return res.status(400).json({ ok: false, error: "Signer details are too long" });
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s.email)) {
        return res.status(400).json({ ok: false, error: `Invalid signer email: ${s.email}` });
      }
    }

    const cleanBase64 = pdfBase64.replace(/^data:application\/pdf;base64,/, "");
    const pdfBuffer   = Buffer.from(cleanBase64, "base64");

    if (pdfBuffer.length < 100) {
      return res.status(400).json({ ok: false, error: "PDF buffer is too small / invalid" });
    }
    if (pdfBuffer.subarray(0, 5).toString("ascii") !== "%PDF-") {
      return res.status(400).json({ ok: false, error: "Uploaded content is not a valid PDF" });
    }

    const result = await adobeSign.sendForSignature({
      pdfBuffer,
      fileName:      fileName      || "Triton-Compliance.pdf",
      agreementName: agreementName || "Triton Compliance Agreement",
      signers,
      message,
    });

    console.log(`[adobe-sign] Sent agreement ${result.agreementId} to:`, signers.map(s => s.email).join(", "));
    res.json({ ok: true, ...result });
  } catch (err) {
    console.error("[adobe-sign] ERROR:", err.message);
    res.status(500).json({ ok: false, error: "Adobe Sign request failed. Check the server logs for details." });
  }
});

/* -------------------------------------------------------- */
/*  Static hosting of the portal (optional convenience)     */
/*  If triton-compliance-portal.html sits in the parent     */
/*  directory, expose it at /                              */
/* -------------------------------------------------------- */
const portalDir = path.resolve(__dirname, "..");
const portalPath = path.join(portalDir, "triton-compliance-portal.html");
if (fs.existsSync(portalPath)) {
  app.get("/", (req, res) => res.sendFile(portalPath));
  app.get("/triton-compliance-portal.html", (req, res) => res.sendFile(portalPath));
  const publicAssets = new Set([
    "triton-logo.png",
    "Triton Logo 2.png",
    "triton-logo-data.js",
  ]);
  app.get("/:asset", (req, res, next) => {
    if (!publicAssets.has(req.params.asset)) return next();
    res.sendFile(path.join(portalDir, req.params.asset));
  });
}

/* -------------------------------------------------------- */
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`[triton-compliance] Adobe Sign backend listening on http://localhost:${PORT}`);
  console.log(`  POST /api/auth/login`);
  console.log(`  GET  /api/drafts`);
  console.log(`  POST /api/adobe-sign/send`);
  console.log(`  GET  /api/health`);
  if (fs.existsSync(portalPath)) {
    console.log(`  GET  /                       (serves triton-compliance-portal.html)`);
  }
});
