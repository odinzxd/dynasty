import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatNOK, formatDate, STATUS_LABELS, STATUS_COLORS } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { ArrowUpRight, BarChart3, FileText, Wallet } from "lucide-react";

const HERO_URL = "https://images.unsplash.com/photo-1767794527055-86f3602f38a5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njd8MHwxfHNlYXJjaHwyfHxvc2xvJTIwc2t5bGluZSUyMG5pZ2h0fGVufDB8fHx8MTc4MDYwNzU4NHww&ixlib=rb-4.1.0&q=85";

function Stat({ label, value, sub, icon: Icon, testId }) {
  return (
    <div className="d8-card relative overflow-hidden group" data-testid={testId}>
      <div className="flex items-start justify-between">
        <div className="label-eyebrow">{label}</div>
        <Icon size={18} className="text-d8-red opacity-80" strokeWidth={1.5} />
      </div>
      <div className="mt-6 font-display text-4xl tracking-tight">{value}</div>
      {sub && <div className="text-d8-textMute text-sm mt-2">{sub}</div>}
      <div className="absolute -bottom-px left-0 h-px w-0 bg-d8-red group-hover:w-full transition-all duration-500" />
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/stats/dashboard").then(r => setData(r.data)).catch(() => setData({ day_revenue: 0, day_count: 0, recent_sales: [] }));
  }, []);

  return (
    <div className="p-6 sm:p-10">
      {/* Hero */}
      <div className="relative overflow-hidden border border-d8-line mb-10">
        <img src={HERO_URL} alt="" className="absolute inset-0 w-full h-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-r from-d8-bg via-d8-bg/80 to-transparent" />
        <div className="relative z-10 p-8 sm:p-12 flex flex-col md:flex-row md:items-end md:justify-between gap-6 animate-fade-in-up">
          <div>
            <div className="label-eyebrow text-d8-red mb-3">Dashboard</div>
            <h1 className="font-display text-4xl sm:text-5xl font-light leading-tight">
              Hei, <span className="italic">{user?.name?.split(" ")[0]}</span>.
            </h1>
            <p className="text-d8-textMute mt-3 max-w-lg">Her er en oversikt over dine resultater i dag.</p>
          </div>
          <Link
            to="/sales/new"
            data-testid="hero-new-sale"
            className="inline-flex items-center gap-2 bg-d8-red hover:bg-d8-redHover text-white px-6 py-3 transition-colors group"
          >
            <span>Registrer nytt salg</span>
            <ArrowUpRight size={18} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <Stat label="Salg i dag" value={data?.day_count ?? "—"} sub="aktive registreringer" icon={FileText} testId="stat-day-count" />
        <Stat label="Omsetning i dag" value={formatNOK(data?.day_revenue || 0)} sub="ekskl. kansellerte" icon={Wallet} testId="stat-day-revenue" />
        <Stat label="Snittpris" value={formatNOK(data?.day_count ? (data.day_revenue / data.day_count) : 0)} sub="per salg i dag" icon={BarChart3} testId="stat-avg" />
      </div>

      {/* Recent sales */}
      <div>
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="label-eyebrow mb-2">Siste salg</div>
            <h2 className="font-display text-2xl">Mine nyeste registreringer</h2>
          </div>
          <Link to="/sales" className="text-sm text-d8-textMute hover:text-d8-red transition-colors" data-testid="link-all-sales">Se alle →</Link>
        </div>

        <div className="d8-table">
          <table className="w-full text-sm">
            <thead className="bg-neutral-100 border-b border-neutral-200">
              <tr className="text-left">
                <th className="px-4 py-3 font-medium">Dato</th>
                <th className="px-4 py-3 font-medium">Kunde</th>
                <th className="px-4 py-3 font-medium">Sone / Pakke</th>
                <th className="px-4 py-3 font-medium text-right">Totalpris</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {data?.recent_sales?.length ? data.recent_sales.map((s) => (
                <tr key={s.sale_id} className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors" data-testid={`recent-sale-${s.sale_id}`}>
                  <td className="px-4 py-3">{formatDate(s.sale_date)}</td>
                  <td className="px-4 py-3 font-medium">{s.customer_name}</td>
                  <td className="px-4 py-3 text-neutral-600">{s.zone} · {s.package}</td>
                  <td className="px-4 py-3 text-right font-mono">{formatNOK(s.total_price)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2.5 py-1 text-[11px] uppercase tracking-wider border ${STATUS_COLORS[s.status]}`}>
                      {STATUS_LABELS[s.status]}
                    </span>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-neutral-500">Ingen salg registrert ennå. <Link to="/sales/new" className="text-d8-red hover:underline">Registrer ditt første salg →</Link></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
