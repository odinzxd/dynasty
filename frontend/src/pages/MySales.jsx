import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatNOK, formatDate, STATUS_LABELS, STATUS_COLORS } from "@/lib/api";

export default function MySales() {
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/sales", { params: { mine: true } })
      .then(r => setSales(r.data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-4 sm:p-10">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8">
        <div>
          <div className="label-eyebrow text-d8-red mb-2">Mine salg</div>
          <h1 className="font-display text-3xl sm:text-4xl font-light">Alle dine registreringer</h1>
        </div>
        <Link to="/sales/new" data-testid="my-sales-new-btn" className="inline-flex w-full sm:w-auto justify-center bg-d8-red hover:bg-d8-redHover text-white px-5 py-3 transition-colors">Nytt salg</Link>
      </div>

      <div className="d8-table">
        <table className="w-full text-sm">
          <thead className="bg-neutral-100 border-b border-neutral-200 text-left">
            <tr>
              <th className="px-4 py-3 font-medium">Dato</th>
              <th className="px-4 py-3 font-medium">Kunde</th>
              <th className="px-4 py-3 font-medium">Adresse</th>
              <th className="px-4 py-3 font-medium">Sone / Pakke</th>
              <th className="px-4 py-3 font-medium">Rabatt</th>
              <th className="px-4 py-3 font-medium text-right">Totalpris</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-neutral-500">Laster…</td></tr>
            ) : sales.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-neutral-500">Ingen salg ennå.</td></tr>
            ) : sales.map(s => (
              <tr key={s.sale_id} className="border-b border-neutral-100 hover:bg-neutral-50" data-testid={`my-sale-${s.sale_id}`}>
                <td className="px-4 py-3">{formatDate(s.sale_date)}</td>
                <td className="px-4 py-3 font-medium">{s.customer_name}</td>
                <td className="px-4 py-3 text-neutral-600">{s.address}</td>
                <td className="px-4 py-3 text-neutral-600">{s.zone} · {s.package}</td>
                <td className="px-4 py-3">{s.discount_percent ? `${s.discount_percent}%` : "—"}</td>
                <td className="px-4 py-3 text-right font-mono">{formatNOK(s.total_price)}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2.5 py-1 text-[11px] uppercase tracking-wider border ${STATUS_COLORS[s.status]}`}>
                    {STATUS_LABELS[s.status]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
