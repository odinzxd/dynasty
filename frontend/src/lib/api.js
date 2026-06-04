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
