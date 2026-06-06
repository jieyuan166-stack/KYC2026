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
    "triton-logo-cn.png",
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
  console.log(`  POST /api/adobe-sign/send`);
  console.log(`  GET  /api/health`);
  if (fs.existsSync(portalPath)) {
    console.log(`  GET  /                       (serves triton-compliance-portal.html)`);
  }
});
