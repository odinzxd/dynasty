import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export function formatNOK(value) {
  if (value === null || value === undefined || isNaN(value)) return "0 kr";
  return new Intl.NumberFormat("nb-NO", {
    style: "currency",
    currency: "NOK",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDate(iso) {
  if (!iso) return "";
  const d = typeof iso === "string" ? new Date(iso) : iso;
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("nb-NO", { year: "numeric", month: "short", day: "2-digit" });
}

export function downloadFile(contents, filename, type = "text/html") {
  const blob = new Blob([contents], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const OFFER_LOGO_SVG = `
<svg width="160" height="120" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Dynasty 8 logo">
  <circle cx="118" cy="26" r="22" fill="#F9CF4E" />
  <path d="M16 64L44 36L84 64V98H16V64Z" fill="#1E5933" />
  <path d="M42 98H72V68L56 52L42 68V98Z" fill="#0F3420" />
  <rect x="26" y="72" width="24" height="16" rx="4" fill="#F9CF4E" />
  <text x="18" y="116" fill="#0F1A12" font-family="Inter, sans-serif" font-weight="700" font-size="24">Dynasty</text>
  <text x="112" y="116" fill="#F9CF4E" font-family="Inter, sans-serif" font-weight="800" font-size="32">8</text>
</svg>
`;

export function createOfferDocument(sale) {
  const customer = sale.customer_name || "-";
  const address = sale.address || "-";
  const date = formatDate(sale.sale_date);
  const packageName = sale.package || "-";
  const discount = sale.discount_percent ? `${sale.discount_percent}%` : "Ingen";
  const coupon = sale.coupon_code || "Ingen";
  const surcharge = sale.surcharge_amount ? `${formatNOK(sale.surcharge_amount)}${sale.surcharge_label ? ` (${sale.surcharge_label})` : ""}` : "Ingen";
  const addons = Array.isArray(sale.addons) && sale.addons.length > 0 ? sale.addons.map(a => `• ${a}`).join("<br />") : "Ingen";
  const total = formatNOK(sale.total_price);
  const base = formatNOK(sale.base_price);
  const comment = sale.comment || "Ingen tilleggsinformasjon";
  const createdBy = sale.employee_name || "Ansatt";
  const saleId = sale.sale_id ? sale.sale_id.replace("sale_", "") : "tilbud";

  return `<!DOCTYPE html>
<html lang="nb">
<head>
  <meta charset="utf-8" />
  <title>Tilbud ${saleId}</title>
  <style>
    body { font-family: Inter, system-ui, sans-serif; margin: 0; padding: 32px; color: #111827; background: #f4f7ef; }
    .container { max-width: 760px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 24px; border: 1px solid #dbe7d2; box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08); }
    .brand-bar { display: flex; align-items: center; gap: 18px; margin-bottom: 26px; }
    .brand-title { font-size: 28px; letter-spacing: -0.03em; margin: 0; color: #164127; }
    .brand-subtitle { margin: 2px 0 0; font-size: 12px; color: #7a8d6d; text-transform: uppercase; letter-spacing: 0.18em; }
    h1 { margin: 0; font-size: 32px; color: #0f2816; }
    h2 { font-size: 16px; margin: 30px 0 10px; color: #3f5b3d; }
    p, th, td { color: #4b5563; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid #e9efe0; }
    th { background: #f7f8f3; font-weight: 700; color: #264220; }
    .summary { margin-top: 28px; font-size: 18px; font-weight: 700; color: #0f2816; }
    .footer { margin-top: 32px; font-size: 14px; color: #6b7280; }
    .accent { color: #b07f2a; }
  </style>
</head>
<body>
  <div class="container">
    <div class="brand-bar">
      ${OFFER_LOGO_SVG}
      <div>
        <p class="brand-title">Dynasty 8</p>
        <p class="brand-subtitle">Tilbudsdokument</p>
      </div>
    </div>
    <h1>Tilbud</h1>
    <p>Tilbud nummer: <strong class="accent">${saleId}</strong></p>
    <p>Dato: <strong>${date}</strong></p>

    <h2>Kunde</h2>
    <table>
      <tr><th>Kunde</th><td>${customer}</td></tr>
      <tr><th>Adresse</th><td>${address}</td></tr>
      <tr><th>Boligtype</th><td>${packageName}</td></tr>
      <tr><th>Sone</th><td>${sale.zone || "-"}</td></tr>
      <tr><th>Rabatt</th><td>${discount}</td></tr>
      <tr><th>Kupong</th><td>${coupon}</td></tr>
      <tr><th>Ekstra</th><td>${addons}</td></tr>
      <tr><th>Påslag</th><td>${surcharge}</td></tr>
    </table>

    <h2>Prissammendrag</h2>
    <table>
      <tr><th>Pris per dag</th><td>${base}</td></tr>
      <tr><th>Kommentar</th><td>${comment}</td></tr>
      <tr><th>Opprettet av</th><td>${createdBy}</td></tr>
    </table>

    <p class="summary">Pris per dag: <span class="accent">${base}</span></p>

    <div class="footer">
      <p>Dette dokumentet kan brukes som tilbud til kunden.</p>
    </div>
  </div>
</body>
</html>`;
}

export const STATUS_LABELS = {
  aktiv: "Aktiv",
  betalt: "Betalt",
  kansellert: "Kansellert",
  under_behandling: "Under behandling",
};

export const STATUS_COLORS = {
  aktiv: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  betalt: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  kansellert: "bg-red-500/15 text-red-300 border-red-500/30",
  under_behandling: "bg-amber-500/15 text-amber-300 border-amber-500/30",
};
