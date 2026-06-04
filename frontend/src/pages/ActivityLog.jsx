import React, { useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";

const ACTION_LABELS = {
  login: "Innlogging",
  logout: "Utlogging",
  sale_created: "Nytt salg",
  sale_updated: "Salg endret",
  sale_deleted: "Salg slettet",
  export_csv: "CSV eksport",
  export_xlsx: "Excel eksport",
  user_updated: "Bruker endret",
  user_kicked: "Bruker kastet ut",
  user_deleted: "Bruker slettet",
};

export default function ActivityLog() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    api.get("/activity-log").then(r => setLogs(r.data));
  }, []);

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-8">
        <div className="label-eyebrow text-d8-red mb-2">Logg</div>
        <h1 className="font-display text-4xl font-light">Aktivitetslogg</h1>
        <p className="text-d8-textMute mt-2">Siste 200 hendelser i systemet.</p>
      </div>

      <div className="d8-card p-0 bg-d8-surface">
        <table className="w-full text-sm">
          <thead className="bg-d8-surface2 border-b border-d8-line text-left">
            <tr className="text-d8-textMute">
              <th className="px-4 py-3 font-medium">Tidspunkt</th>
              <th className="px-4 py-3 font-medium">Bruker</th>
              <th className="px-4 py-3 font-medium">Handling</th>
              <th className="px-4 py-3 font-medium">Detaljer</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.log_id} className="border-b border-d8-line hover:bg-white/5">
                <td className="px-4 py-3 text-d8-textMute font-mono text-xs">{formatDate(l.timestamp)} {new Date(l.timestamp).toLocaleTimeString("nb-NO")}</td>
                <td className="px-4 py-3">{l.user_email}</td>
                <td className="px-4 py-3">
                  <span className="inline-block px-2 py-1 text-[11px] uppercase tracking-wider border border-d8-red/40 text-d8-red bg-d8-red/10">
                    {ACTION_LABELS[l.action] || l.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-d8-textMute text-xs font-mono">{JSON.stringify(l.details || {})}</td>
              </tr>
            ))}
            {logs.length === 0 && <tr><td colSpan={4} className="px-4 py-10 text-center text-d8-textMute">Ingen aktivitet ennå.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
