import React, { useEffect, useState, useMemo } from "react";
import { api, API, formatNOK, formatDate, STATUS_LABELS, STATUS_COLORS } from "@/lib/api";
import { toast } from "sonner";
import { Download, FileSpreadsheet, Pencil, Trash2, X } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line, PieChart, Pie, Cell, Legend
} from "recharts";

const inputCls = "w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white focus:outline-none focus:border-d8-red transition-colors";
const RED_PALETTE = ["#D32F2F", "#EF4444", "#F87171", "#FCA5A5", "#7F1D1D", "#991B1B"];

function StatTile({ label, value, sub }) {
  return (
    <div className="d8-card">
      <div className="label-eyebrow">{label}</div>
      <div className="font-display text-3xl mt-3">{value}</div>
      {sub && <div className="text-d8-textMute text-xs mt-1">{sub}</div>}
    </div>
  );
}

export default function AdminPanel() {
  const [stats, setStats] = useState(null);
  const [sales, setSales] = useState([]);
  const [users, setUsers] = useState([]);
  const [matrix, setMatrix] = useState(null);
  const [editSale, setEditSale] = useState(null);

  const [filters, setFilters] = useState({ zone: "", package: "", status: "", employee_id: "", date_from: "", date_to: "" });

  const loadAll = async () => {
    const [s, sa, u, m] = await Promise.all([
      api.get("/stats/admin"),
      api.get("/sales", { params: { ...cleanFilters(filters) } }),
      api.get("/users"),
      api.get("/price-matrix"),
    ]);
    setStats(s.data); setSales(sa.data); setUsers(u.data); setMatrix(m.data);
  };

  useEffect(() => { loadAll(); /* eslint-disable-next-line */ }, []);
  useEffect(() => {
    api.get("/sales", { params: { ...cleanFilters(filters) } }).then(r => setSales(r.data));
  }, [filters]);

  const onDelete = async (id) => {
    if (!window.confirm("Er du sikker på at du vil slette dette salget?")) return;
    try {
      await api.delete(`/sales/${id}`);
      toast.success("Salg slettet");
      loadAll();
    } catch { toast.error("Sletting feilet"); }
  };

  const exportFile = (type) => {
    window.open(`${API}/export/${type}`, "_blank");
  };

  return (
    <div className="p-6 sm:p-10">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
        <div>
          <div className="label-eyebrow text-d8-red mb-2">Adminpanel</div>
          <h1 className="font-display text-4xl font-light">Ledelsens kontrollrom</h1>
        </div>
        <div className="flex gap-3">
          <button onClick={() => exportFile("csv")} data-testid="export-csv" className="inline-flex items-center gap-2 border border-d8-line hover:border-d8-red px-4 py-2 text-sm transition-colors">
            <Download size={14} /> CSV
          </button>
          <button onClick={() => exportFile("xlsx")} data-testid="export-xlsx" className="inline-flex items-center gap-2 border border-d8-line hover:border-d8-red px-4 py-2 text-sm transition-colors">
            <FileSpreadsheet size={14} /> Excel
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <StatTile label="Total omsetning" value={formatNOK(stats?.total_revenue || 0)} sub="ekskl. kansellerte" />
        <StatTile label="Totalt antall salg" value={stats?.total_count ?? 0} />
        <StatTile label="Antall ansatte" value={users.length} />
        <StatTile label="Aktive soner" value={stats?.per_zone?.length ?? 0} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
        <div className="d8-card lg:col-span-2">
          <div className="label-eyebrow mb-4">Omsetning per dag</div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats?.per_day || []}>
                <CartesianGrid stroke="#262626" strokeDasharray="3 3" />
                <XAxis dataKey="day" stroke="#A3A3A3" fontSize={12} />
                <YAxis stroke="#A3A3A3" fontSize={12} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ background: "#141414", border: "1px solid #262626", color: "#fff" }} formatter={(v) => formatNOK(v)} />
                <Line type="monotone" dataKey="revenue" stroke="#D32F2F" strokeWidth={2} dot={{ fill: "#D32F2F" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="d8-card">
          <div className="label-eyebrow mb-4">Salg per sone</div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={stats?.per_zone || []} dataKey="count" nameKey="zone" outerRadius={90} innerRadius={50}>
                  {(stats?.per_zone || []).map((_, i) => <Cell key={i} fill={RED_PALETTE[i % RED_PALETTE.length]} />)}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 12, color: "#A3A3A3" }} />
                <Tooltip contentStyle={{ background: "#141414", border: "1px solid #262626", color: "#fff" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="d8-card mb-10">
        <div className="label-eyebrow mb-4">Omsetning per ansatt</div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats?.per_employee || []}>
              <CartesianGrid stroke="#262626" strokeDasharray="3 3" />
              <XAxis dataKey="employee_name" stroke="#A3A3A3" fontSize={12} />
              <YAxis stroke="#A3A3A3" fontSize={12} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
              <Tooltip contentStyle={{ background: "#141414", border: "1px solid #262626", color: "#fff" }} formatter={(v) => formatNOK(v)} />
              <Bar dataKey="revenue" fill="#D32F2F" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Filters */}
      <div className="d8-card mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <select className={inputCls} value={filters.zone} onChange={e => setFilters(f => ({ ...f, zone: e.target.value }))} data-testid="filter-zone">
            <option value="">Alle soner</option>
            {(matrix?.zones || []).map(z => <option key={z} value={z}>{z}</option>)}
          </select>
          <select className={inputCls} value={filters.package} onChange={e => setFilters(f => ({ ...f, package: e.target.value }))} data-testid="filter-package">
            <option value="">Alle pakker</option>
            {(matrix?.packages || []).map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <select className={inputCls} value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))} data-testid="filter-status">
            <option value="">Alle statuser</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select className={inputCls} value={filters.employee_id} onChange={e => setFilters(f => ({ ...f, employee_id: e.target.value }))} data-testid="filter-employee">
            <option value="">Alle ansatte</option>
            {users.map(u => <option key={u.user_id} value={u.user_id}>{u.name}</option>)}
          </select>
          <input type="date" className={inputCls} value={filters.date_from} onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))} data-testid="filter-from" />
          <input type="date" className={inputCls} value={filters.date_to} onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))} data-testid="filter-to" />
        </div>
      </div>

      {/* Sales table */}
      <div className="d8-table">
        <table className="w-full text-sm">
          <thead className="bg-neutral-100 border-b border-neutral-200 text-left">
            <tr>
              <th className="px-4 py-3 font-medium">Dato</th>
              <th className="px-4 py-3 font-medium">Kunde</th>
              <th className="px-4 py-3 font-medium">Adresse</th>
              <th className="px-4 py-3 font-medium">Sone / Pakke</th>
              <th className="px-4 py-3 font-medium">Ansatt</th>
              <th className="px-4 py-3 font-medium text-right">Totalpris</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Handling</th>
            </tr>
          </thead>
          <tbody>
            {sales.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-10 text-center text-neutral-500">Ingen salg matcher filteret.</td></tr>
            ) : sales.map(s => (
              <tr key={s.sale_id} className="border-b border-neutral-100 hover:bg-neutral-50" data-testid={`admin-sale-${s.sale_id}`}>
                <td className="px-4 py-3">{formatDate(s.sale_date)}</td>
                <td className="px-4 py-3 font-medium">{s.customer_name}</td>
                <td className="px-4 py-3 text-neutral-600">{s.address}</td>
                <td className="px-4 py-3 text-neutral-600">{s.zone} · {s.package}</td>
                <td className="px-4 py-3 text-neutral-600">{s.employee_name}</td>
                <td className="px-4 py-3 text-right font-mono">{formatNOK(s.total_price)}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2.5 py-1 text-[11px] uppercase tracking-wider border ${STATUS_COLORS[s.status]}`}>
                    {STATUS_LABELS[s.status]}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => setEditSale(s)} data-testid={`edit-${s.sale_id}`} className="text-neutral-600 hover:text-d8-red p-1.5 transition-colors"><Pencil size={14} /></button>
                  <button onClick={() => onDelete(s.sale_id)} data-testid={`delete-${s.sale_id}`} className="text-neutral-600 hover:text-d8-red p-1.5 transition-colors"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editSale && <EditModal sale={editSale} matrix={matrix} onClose={() => setEditSale(null)} onSaved={() => { setEditSale(null); loadAll(); }} />}
    </div>
  );
}

function cleanFilters(f) {
  const out = {};
  for (const [k, v] of Object.entries(f)) if (v) out[k] = v;
  return out;
}

function EditModal({ sale, matrix, onClose, onSaved }) {
  const [form, setForm] = useState({ ...sale });
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setForm(s => ({ ...s, [k]: v }));

  const submit = async () => {
    setSaving(true);
    try {
      await api.patch(`/sales/${sale.sale_id}`, {
        customer_name: form.customer_name, phone: form.phone, address: form.address,
        zone: form.zone, package: form.package, addons: form.addons || [],
        tenant_count: Number(form.tenant_count) || 0, discount_type: form.discount_type || null,
        sale_date: form.sale_date, comment: form.comment, status: form.status,
      });
      toast.success("Salg oppdatert");
      onSaved();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Oppdatering feilet");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-d8-surface border border-d8-line max-w-2xl w-full p-8 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="label-eyebrow text-d8-red mb-2">Rediger</div>
            <h2 className="font-display text-2xl">Salg #{sale.sale_id.slice(-6)}</h2>
          </div>
          <button onClick={onClose} className="text-d8-textMute hover:text-white" data-testid="modal-close"><X /></button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Lbl label="Kunde"><input className={inputCls} value={form.customer_name || ""} onChange={e => set("customer_name", e.target.value)} /></Lbl>
          <Lbl label="Telefon"><input className={inputCls} value={form.phone || ""} onChange={e => set("phone", e.target.value)} /></Lbl>
          <Lbl label="Adresse" full><input className={inputCls} value={form.address || ""} onChange={e => set("address", e.target.value)} /></Lbl>
          <Lbl label="Sone">
            <select className={inputCls} value={form.zone || ""} onChange={e => set("zone", e.target.value)}>
              {(matrix?.zones || []).map(z => <option key={z} value={z}>{z}</option>)}
            </select>
          </Lbl>
          <Lbl label="Pakke">
            <select className={inputCls} value={form.package || ""} onChange={e => set("package", e.target.value)}>
              {(matrix?.packages || []).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </Lbl>
          <Lbl label="Status">
            <select className={inputCls} value={form.status || "aktiv"} onChange={e => set("status", e.target.value)} data-testid="edit-status">
              {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Lbl>
          <Lbl label="Dato"><input type="date" className={inputCls} value={form.sale_date || ""} onChange={e => set("sale_date", e.target.value)} /></Lbl>
          <Lbl label="Kommentar" full><input className={inputCls} value={form.comment || ""} onChange={e => set("comment", e.target.value)} /></Lbl>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="border border-d8-line px-5 py-2 text-sm hover:border-white/40">Avbryt</button>
          <button onClick={submit} disabled={saving} data-testid="save-edit" className="bg-d8-red hover:bg-d8-redHover text-white px-5 py-2 text-sm">
            {saving ? "Lagrer…" : "Lagre endringer"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Lbl({ label, children, full }) {
  return (
    <label className={`block ${full ? "sm:col-span-2" : ""}`}>
      <div className="label-eyebrow mb-2">{label}</div>
      {children}
    </label>
  );
}
