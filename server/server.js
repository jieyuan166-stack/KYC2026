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
app.use(express.json({ limit: "30mb" }));    // PDFs can be large; allow generous body size

const allowedOrigins = (process.env.ALLOWED_ORIGINS || "*")
  .split(",")
  .map(s => s.trim())
  .filter(Boolean);

app.use(cors({
  origin: (origin, cb) => {
    // Allow non-browser callers (curl) and file:// (Origin null)
    if (!origin) return cb(null, true);
    if (allowedOrigins.includes("*") || allowedOrigins.includes(origin)) return cb(null, true);
    cb(new Error(`Origin ${origin} not allowed by CORS`));
  },
}));

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
app.post("/api/adobe-sign/send", async (req, res) => {
  try {
    const { pdfBase64, fileName, agreementName, signers, message } = req.body || {};

    if (!pdfBase64)               return res.status(400).json({ ok: false, error: "Missing pdfBase64" });
    if (!Array.isArray(signers))  return res.status(400).json({ ok: false, error: "signers must be an array" });
    if (signers.length === 0)     return res.status(400).json({ ok: false, error: "At least one signer is required" });

    for (const s of signers) {
      if (!s || !s.email)         return res.status(400).json({ ok: false, error: "Every signer must have an email" });
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s.email)) {
        return res.status(400).json({ ok: false, error: `Invalid signer email: ${s.email}` });
      }
    }

    const cleanBase64 = pdfBase64.replace(/^data:application\/pdf;base64,/, "");
    const pdfBuffer   = Buffer.from(cleanBase64, "base64");

    if (pdfBuffer.length < 100) {
      return res.status(400).json({ ok: false, error: "PDF buffer is too small / invalid" });
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
    res.status(500).json({ ok: false, error: err.message });
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
  // Serve assets (logo, etc.) from the parent directory so relative paths
  // like ./triton-logo.png work both in browser and file:// contexts.
  app.use(express.static(portalDir, {
    index: false,                          // don't auto-serve directory index
    extensions: ["html"],
  }));
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
