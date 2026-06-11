import React, { useEffect, useState } from "react";
import { api, formatNOK, formatDate } from "@/lib/api";
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";

export default function Stats() {
  const today = new Date().toISOString().slice(0, 10);
  const [start, setStart] = useState("2026-06-01");
  const [end, setEnd] = useState(today);
  const [loading, setLoading] = useState(true);
  const [rangeStats, setRangeStats] = useState(null);
  const [sales, setSales] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/stats/range", { params: { start, end } });
      setRangeStats(r.data);
      setSales(r.data.sales || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="p-4 sm:p-10">
      <div className="label-eyebrow text-d8-red mb-2">Statistikk</div>
      <h1 className="font-display text-3xl mb-2">Salg og inntekt</h1>

      <div className="d8-card mb-6">
        <div className="flex gap-3 items-center mb-4">
          <label className="text-sm">Fra <input type="date" className="ml-2 p-2 bg-d8-surface2 border border-d8-line" value={start} onChange={e => setStart(e.target.value)} /></label>
          <label className="text-sm">Til <input type="date" className="ml-2 p-2 bg-d8-surface2 border border-d8-line" value={end} onChange={e => setEnd(e.target.value)} /></label>
          <button onClick={load} className="ml-auto bg-d8-red text-white px-3 py-2">Oppdater</button>
        </div>

        {loading || !rangeStats ? (
          <div className="text-neutral-500">Laster...</div>
        ) : (
          <div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              <div className="d8-card">Total omsetning<br /><div className="font-display text-2xl mt-2">{formatNOK(rangeStats.total_revenue || 0)}</div></div>
              <div className="d8-card">Antall salg<br /><div className="font-display text-2xl mt-2">{rangeStats.total_count || 0}</div></div>
              <div className="d8-card">Periode<br /><div className="font-display text-2xl mt-2">{start} — {end}</div></div>
            </div>

            <div className="d8-card mb-6">
              <div className="label-eyebrow mb-2">Inntjening per dag</div>
              <div style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={rangeStats.per_day || []}>
                    <CartesianGrid stroke="#262626" strokeDasharray="3 3" />
                    <XAxis dataKey="day" stroke="#A3A3A3" />
                    <YAxis stroke="#A3A3A3" tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v) => formatNOK(v)} />
                    <Line type="monotone" dataKey="revenue" stroke="#D32F2F" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="d8-card">
              <div className="label-eyebrow mb-2">Alle salg i perioden</div>
              <div className="d8-table">
                <table className="w-full text-sm">
                  <thead className="bg-neutral-100 border-b border-neutral-200 text-left">
                    <tr>
                      <th className="px-4 py-3">Dato</th>
                      <th className="px-4 py-3">Kunde</th>
                      <th className="px-4 py-3">Ansatt</th>
                      <th className="px-4 py-3 text-right">Totalpris</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sales.length === 0 ? (
                      <tr><td colSpan={4} className="px-4 py-8 text-neutral-500">Ingen salg i perioden.</td></tr>
                    ) : sales.map(s => (
                      <tr key={s.sale_id} className="border-b border-neutral-100 hover:bg-neutral-50">
                        <td className="px-4 py-3">{formatDate(s.sale_date)}</td>
                        <td className="px-4 py-3">{s.customer_name}</td>
                        <td className="px-4 py-3">{s.employee_name}</td>
                        <td className="px-4 py-3 text-right font-mono">{formatNOK(s.total_price)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
