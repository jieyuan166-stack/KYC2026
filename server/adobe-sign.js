/**
 * Adobe Sign (Acrobat Sign) REST API wrapper.
 *
 * Implements the minimum subset needed by the Triton Compliance Portal:
 *   1. getAccessToken()             — refresh OAuth access token
 *   2. uploadTransientDocument()    — upload PDF buffer to Adobe Sign
 *   3. createAgreement()            — create a signing agreement and dispatch it
 *
 * Docs:
 *   https://secure.na1.echosign.com/public/docs/restapi/v6
 */

"use strict";

const FormData = require("form-data");

let cachedToken = null;        // { accessToken, expiresAt, apiAccessPoint }

/* -------------------------------------------------------- */
/*  OAuth                                                   */
/* -------------------------------------------------------- */
async function getAccessToken() {
  const now = Date.now();
  if (cachedToken && cachedToken.expiresAt - 60_000 > now) {
    return cachedToken;
  }

  const clientId     = process.env.ADOBE_CLIENT_ID;
  const clientSecret = process.env.ADOBE_CLIENT_SECRET;
  const refreshToken = process.env.ADOBE_REFRESH_TOKEN;
  const baseHost     = process.env.ADOBE_API_BASE || "https://api.na4.adobesign.com";

  if (!clientId || !clientSecret || !refreshToken) {
    throw new Error("Missing ADOBE_CLIENT_ID / ADOBE_CLIENT_SECRET / ADOBE_REFRESH_TOKEN in .env");
  }

  const url = `${baseHost}/oauth/v2/refresh`;
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    client_id: clientId,
    client_secret: clientSecret,
    refresh_token: refreshToken,
  });

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Adobe Sign token refresh failed (${res.status}): ${txt}`);
  }

  const json = await res.json();
  cachedToken = {
    accessToken: json.access_token,
    expiresAt: now + (json.expires_in || 3600) * 1000,
    apiAccessPoint: baseHost,           // baseUris is fetched lazily on first call below
  };
  // Resolve the true api access point for this user, so subsequent calls hit the correct region.
  try {
    const baseRes = await fetch(`${baseHost}/api/rest/v6/baseUris`, {
      headers: { Authorization: `Bearer ${cachedToken.accessToken}` },
    });
    if (baseRes.ok) {
      const baseJson = await baseRes.json();
      if (baseJson.apiAccessPoint) {
        cachedToken.apiAccessPoint = baseJson.apiAccessPoint.replace(/\/$/, "");
      }
    }
  } catch (_) { /* non-fatal — use configured baseHost */ }

  return cachedToken;
}

/* -------------------------------------------------------- */
/*  Transient document upload                               */
/* -------------------------------------------------------- */
async function uploadTransientDocument(pdfBuffer, fileName = "document.pdf") {
  const { accessToken, apiAccessPoint } = await getAccessToken();

  const form = new FormData();
  form.append("File-Name", fileName);
  form.append("Mime-Type", "application/pdf");
  form.append("File", pdfBuffer, { filename: fileName, contentType: "application/pdf" });

  const url = `${apiAccessPoint}/api/rest/v6/transientDocuments`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...form.getHeaders(),
    },
    body: form,
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Adobe Sign transient document upload failed (${res.status}): ${txt}`);
  }

  const json = await res.json();
  return json.transientDocumentId;
}

/* -------------------------------------------------------- */
/*  Create + dispatch agreement                             */
/* -------------------------------------------------------- */
/**
 * @param {object} args
 * @param {string} args.transientDocumentId
 * @param {string} args.name                  Agreement name shown in Adobe Sign dashboard / emails
 * @param {Array<{ email: string, name?: string }>} args.signers   In signing order
 * @param {string} [args.message]             Optional message to recipients
 * @returns {Promise<{ agreementId: string }>}
 */
async function createAgreement({ transientDocumentId, name, signers, message }) {
  const { accessToken, apiAccessPoint } = await getAccessToken();

  if (!Array.isArray(signers) || signers.length === 0) {
    throw new Error("createAgreement requires at least one signer");
  }

  const participantSetsInfo = signers.map((s, i) => ({
    order: i + 1,
    role: "SIGNER",
    memberInfos: [{ email: s.email, ...(s.name ? { name: s.name } : {}) }],
  }));

  const payload = {
    fileInfos: [{ transientDocumentId }],
    name: name || "Triton Compliance Agreement",
    participantSetsInfo,
    signatureType: "ESIGN",
    state: "IN_PROCESS",
    ...(message ? { message } : {}),
  };

  const url = `${apiAccessPoint}/api/rest/v6/agreements`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Adobe Sign create agreement failed (${res.status}): ${txt}`);
  }

  const json = await res.json();
  return { agreementId: json.id };
}

/* -------------------------------------------------------- */
/*  Convenience: full send pipeline                         */
/* -------------------------------------------------------- */
async function sendForSignature({ pdfBuffer, fileName, agreementName, signers, message }) {
  const transientDocumentId = await uploadTransientDocument(pdfBuffer, fileName);
  const { agreementId } = await createAgreement({ transientDocumentId, name: agreementName, signers, message });
  return { agreementId, transientDocumentId };
}

module.exports = {
  getAccessToken,
  uploadTransientDocument,
  createAgreement,
  sendForSignature,
};
