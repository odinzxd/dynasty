import React, { useEffect, useState } from "react";
import { api, formatNOK, formatDate } from "@/lib/api";

export default function Corporate() {
  const [deals, setDeals] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [d, a] = await Promise.all([api.get("/company-deals"), api.get("/announcements")]);
      setDeals(d.data || []);
      setAnnouncements(a.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="p-4 sm:p-10">
      <div className="mb-8">
        <div className="label-eyebrow text-d8-red mb-2">Fordeler og informasjon</div>
        <h1 className="font-display text-3xl sm:text-4xl font-light">Bedriftsavtaler & Kunngjøringer</h1>
        <p className="text-d8-textMute mt-2">Her finner du aktive bedriftsavtaler og interne kunngjøringer.</p>
      </div>

      {loading ? (
        <div className="text-neutral-500">Laster...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="d8-card">
            <div className="label-eyebrow mb-4">Bedriftsavtaler</div>
            {deals.length === 0 ? (
              <div className="text-neutral-500">Ingen avtaler tilgjengelig.</div>
            ) : (
              <ul className="space-y-4">
                {deals.map(d => (
                  <li key={d.deal_id} className="border p-3 rounded">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium">{d.title}</div>
                        <div className="text-sm text-neutral-500 mt-1">{d.description}</div>
                        {d.discount_percent ? <div className="text-sm text-neutral-400 mt-1">Rabatt: {d.discount_percent}%</div> : null}
                        {d.valid_from || d.valid_to ? <div className="text-sm text-neutral-400 mt-1">Gyldig: {d.valid_from || '-'} — {d.valid_to || '-'}</div> : null}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="d8-card">
            <div className="label-eyebrow mb-4">Kunngjøringer</div>
            {announcements.length === 0 ? (
              <div className="text-neutral-500">Ingen kunngjøringer.</div>
            ) : (
              <ul className="space-y-4">
                {announcements.map(a => (
                  <li key={a.announcement_id} className="border p-3 rounded">
                    <div className="font-medium">{a.title}</div>
                    <div className="text-sm text-neutral-500 mt-1">{a.content}</div>
                    <div className="text-xs text-neutral-400 mt-2">Publisert: {formatDate(a.created_at)}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
