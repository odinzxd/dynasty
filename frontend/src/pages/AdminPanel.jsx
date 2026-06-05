import React, { useEffect, useState, useMemo } from "react";
import { api, API, formatNOK, formatDate, STATUS_LABELS, STATUS_COLORS } from "@/lib/api";
import { toast } from "sonner";
import { Database, Download, FileSpreadsheet, Pencil, Plus, Trash2, X } from "lucide-react";
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

function DatabaseStatus({ status }) {
  const ok = status?.ok === true;
  const checked = status !== null;
  const tone = !checked
    ? "border-neutral-300 text-neutral-500 bg-neutral-100"
    : ok
      ? "border-emerald-500/40 text-emerald-300 bg-emerald-500/10"
      : "border-d8-red/50 text-d8-red bg-d8-red/10";
  return (
    <div className={`col-span-2 sm:col-auto inline-flex items-center justify-center gap-2 border px-3 py-2 text-sm ${tone}`}>
      <span className={`h-2.5 w-2.5 rounded-full ${!checked ? "bg-neutral-400" : ok ? "bg-emerald-400" : "bg-d8-red"}`} />
      <Database size={15} />
      <span>{checked ? (ok ? "Database oppe" : "Database feil") : "Sjekker database"}</span>
    </div>
  );
}

export default function AdminPanel() {
  const [stats, setStats] = useState(null);
  const [sales, setSales] = useState([]);
  const [users, setUsers] = useState([]);
  const [matrix, setMatrix] = useState(null);
  const [products, setProducts] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [databaseStatus, setDatabaseStatus] = useState(null);
  const [editSale, setEditSale] = useState(null);
  const [editProduct, setEditProduct] = useState(null);
  const [editCoupon, setEditCoupon] = useState(null);

  const [filters, setFilters] = useState({ zone: "", package: "", status: "", employee_id: "", date_from: "", date_to: "" });

  const loadAll = async () => {
    const [s, sa, u, m, p, c, db] = await Promise.all([
      api.get("/stats/admin"),
      api.get("/sales", { params: { ...cleanFilters(filters) } }),
      api.get("/users"),
      api.get("/price-matrix"),
      api.get("/products"),
      api.get("/coupons"),
      api.get("/system/database").catch(e => ({ data: { ok: false, error: e?.response?.data?.detail || "Kunne ikke sjekke database" } })),
    ]);
    setStats(s.data); setSales(sa.data); setUsers(u.data); setMatrix(m.data);
    setProducts(p.data);
    setCoupons(c.data);
    setDatabaseStatus(db.data);
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
    <div className="p-4 sm:p-10">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
        <div>
          <div className="label-eyebrow text-d8-red mb-2">Adminpanel</div>
          <h1 className="font-display text-3xl sm:text-4xl font-light">Ledelsens kontrollrom</h1>
        </div>
        <div className="grid grid-cols-2 sm:flex sm:flex-wrap items-center gap-3">
          <DatabaseStatus status={databaseStatus} />
          <button onClick={() => exportFile("csv")} data-testid="export-csv" className="inline-flex items-center justify-center gap-2 border border-d8-line hover:border-d8-red px-4 py-2 text-sm transition-colors">
            <Download size={14} /> CSV
          </button>
          <button onClick={() => exportFile("xlsx")} data-testid="export-xlsx" className="inline-flex items-center justify-center gap-2 border border-d8-line hover:border-d8-red px-4 py-2 text-sm transition-colors">
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

      <ProductManager products={products} onEdit={setEditProduct} onDeleted={loadAll} />
      <CouponManager coupons={coupons} onEdit={setEditCoupon} onDeleted={loadAll} />

      {/* Filters */}
      <div className="d8-card mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <select className={inputCls} value={filters.zone} onChange={e => setFilters(f => ({ ...f, zone: e.target.value }))} data-testid="filter-zone">
            <option value="">Alle soner</option>
            {(matrix?.zones || []).map(z => <option key={z} value={z}>{z}</option>)}
          </select>
          <select className={inputCls} value={filters.package} onChange={e => setFilters(f => ({ ...f, package: e.target.value }))} data-testid="filter-package">
            <option value="">Alle boligtyper</option>
            {(matrix?.products || []).map(p => <option key={p.product_id} value={`${p.category} - ${p.name}`}>{p.category} - {p.name}</option>)}
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
      {editProduct && <ProductModal product={editProduct === "new" ? null : editProduct} onClose={() => setEditProduct(null)} onSaved={() => { setEditProduct(null); loadAll(); }} />}
      {editCoupon && <CouponModal coupon={editCoupon === "new" ? null : editCoupon} onClose={() => setEditCoupon(null)} onSaved={() => { setEditCoupon(null); loadAll(); }} />}
    </div>
  );
}

function cleanFilters(f) {
  const out = {};
  for (const [k, v] of Object.entries(f)) if (v) out[k] = v;
  return out;
}

function ProductManager({ products, onEdit, onDeleted }) {
  const remove = async (product) => {
    if (!window.confirm(`Slette eller deaktivere ${product.category} - ${product.name}?`)) return;
    try {
      const r = await api.delete(`/products/${product.product_id}`);
      toast.success(r.data.deactivated ? "Boligtype deaktivert" : "Boligtype slettet");
      onDeleted();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Kunne ikke fjerne boligtype");
    }
  };

  return (
    <div className="d8-card mb-10">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <div className="label-eyebrow mb-2">Boligtyper</div>
          <h2 className="font-display text-2xl">Shell, IPL og MLO</h2>
        </div>
        <button onClick={() => onEdit("new")} className="inline-flex w-full sm:w-auto items-center justify-center gap-2 bg-d8-red hover:bg-d8-redHover text-white px-4 py-2.5 text-sm transition-colors">
          <Plus size={15} /> Ny boligtype
        </button>
      </div>
      <div className="d8-table">
        <table className="w-full text-sm">
          <thead className="bg-neutral-100 border-b border-neutral-200 text-left">
            <tr>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Navn</th>
              <th className="px-4 py-3 font-medium text-right">Pris per dag</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Handling</th>
            </tr>
          </thead>
          <tbody>
            {products.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-neutral-500">Ingen boligtyper opprettet.</td></tr>
            ) : products.map(product => (
              <tr key={product.product_id} className="border-b border-neutral-100 hover:bg-neutral-50">
                <td className="px-4 py-3">{product.category}</td>
                <td className="px-4 py-3 font-medium">{product.name}</td>
                <td className="px-4 py-3 text-right font-mono">{formatNOK(product.price_per_day)}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2.5 py-1 text-[11px] uppercase tracking-wider border ${product.is_active ? "border-emerald-400 text-emerald-600 bg-emerald-50" : "border-neutral-400 text-neutral-500 bg-neutral-100"}`}>
                    {product.is_active ? "Aktiv" : "Inaktiv"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => onEdit(product)} className="text-neutral-600 hover:text-d8-red p-1.5 transition-colors"><Pencil size={14} /></button>
                  <button onClick={() => remove(product)} className="text-neutral-600 hover:text-d8-red p-1.5 transition-colors"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProductModal({ product, onClose, onSaved }) {
  const [form, setForm] = useState({
    category: product?.category || "Shell",
    name: product?.name || "",
    price_per_day: product?.price_per_day || "",
    is_active: product?.is_active ?? true,
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, price_per_day: Number(form.price_per_day) || 0 };
      if (product) {
        await api.patch(`/products/${product.product_id}`, payload);
        toast.success("Boligtype oppdatert");
      } else {
        await api.post("/products", payload);
        toast.success("Boligtype opprettet");
      }
      onSaved();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Kunne ikke lagre boligtype");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={submit} className="bg-d8-surface border border-d8-line max-w-lg w-full p-4 sm:p-8 max-h-[calc(100vh-2rem)] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="label-eyebrow text-d8-red mb-2">{product ? "Rediger boligtype" : "Ny boligtype"}</div>
            <h2 className="font-display text-2xl">Pris per dag</h2>
          </div>
          <button type="button" onClick={onClose} className="text-d8-textMute hover:text-white"><X /></button>
        </div>
        <div className="space-y-5">
          <Lbl label="Type">
            <select className={inputCls} value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
              <option value="Shell">Shell</option>
              <option value="IPL">IPL</option>
              <option value="MLO">MLO</option>
            </select>
          </Lbl>
          <Lbl label="Navn">
            <input className={inputCls} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="f.eks. Shell Villa Stor" />
          </Lbl>
          <Lbl label="Pris per dag">
            <input type="number" min="0" step="1" className={inputCls} value={form.price_per_day} onChange={e => setForm({ ...form, price_per_day: e.target.value })} />
          </Lbl>
          <label className="flex items-center gap-3 text-sm">
            <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
            Aktiv i salgskalkulatoren
          </label>
        </div>
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 mt-8">
          <button type="button" onClick={onClose} className="border border-d8-line px-5 py-2.5 text-sm hover:border-white/40">Avbryt</button>
          <button type="submit" disabled={saving} className="bg-d8-red hover:bg-d8-redHover text-white px-5 py-2.5 text-sm">
            {saving ? "Lagrer..." : "Lagre"}
          </button>
        </div>
      </form>
    </div>
  );
}

function CouponManager({ coupons, onEdit, onDeleted }) {
  const remove = async (coupon) => {
    if (!window.confirm(`Slette eller deaktivere kupongen ${coupon.code}?`)) return;
    try {
      const r = await api.delete(`/coupons/${coupon.coupon_id}`);
      toast.success(r.data.deactivated ? "Kupong deaktivert" : "Kupong slettet");
      onDeleted();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Kunne ikke fjerne kupong");
    }
  };

  return (
    <div className="d8-card mb-10">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <div className="label-eyebrow mb-2">Rabattkuponger</div>
          <h2 className="font-display text-2xl">Kuponger ansatte kan bruke</h2>
        </div>
        <button onClick={() => onEdit("new")} className="inline-flex w-full sm:w-auto items-center justify-center gap-2 bg-d8-red hover:bg-d8-redHover text-white px-4 py-2.5 text-sm transition-colors">
          <Plus size={15} /> Ny kupong
        </button>
      </div>
      <div className="d8-table">
        <table className="w-full text-sm">
          <thead className="bg-neutral-100 border-b border-neutral-200 text-left">
            <tr>
              <th className="px-4 py-3 font-medium">Kode</th>
              <th className="px-4 py-3 font-medium">Navn</th>
              <th className="px-4 py-3 font-medium text-right">Rabatt</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Handling</th>
            </tr>
          </thead>
          <tbody>
            {coupons.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-neutral-500">Ingen kuponger opprettet.</td></tr>
            ) : coupons.map(coupon => (
              <tr key={coupon.coupon_id} className="border-b border-neutral-100 hover:bg-neutral-50">
                <td className="px-4 py-3 font-mono">{coupon.code}</td>
                <td className="px-4 py-3 font-medium">{coupon.name}</td>
                <td className="px-4 py-3 text-right font-mono">
                  {coupon.discount_kind === "percent" ? `${coupon.discount_value}%` : formatNOK(coupon.discount_value)}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2.5 py-1 text-[11px] uppercase tracking-wider border ${coupon.is_active ? "border-emerald-400 text-emerald-600 bg-emerald-50" : "border-neutral-400 text-neutral-500 bg-neutral-100"}`}>
                    {coupon.is_active ? "Aktiv" : "Inaktiv"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => onEdit(coupon)} className="text-neutral-600 hover:text-d8-red p-1.5 transition-colors"><Pencil size={14} /></button>
                  <button onClick={() => remove(coupon)} className="text-neutral-600 hover:text-d8-red p-1.5 transition-colors"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CouponModal({ coupon, onClose, onSaved }) {
  const [form, setForm] = useState({
    code: coupon?.code || "",
    name: coupon?.name || "",
    discount_kind: coupon?.discount_kind || "percent",
    discount_value: coupon?.discount_value || "",
    is_active: coupon?.is_active ?? true,
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, discount_value: Number(form.discount_value) || 0 };
      if (coupon) {
        await api.patch(`/coupons/${coupon.coupon_id}`, payload);
        toast.success("Kupong oppdatert");
      } else {
        await api.post("/coupons", payload);
        toast.success("Kupong opprettet");
      }
      onSaved();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Kunne ikke lagre kupong");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={submit} className="bg-d8-surface border border-d8-line max-w-lg w-full p-4 sm:p-8 max-h-[calc(100vh-2rem)] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="label-eyebrow text-d8-red mb-2">{coupon ? "Rediger kupong" : "Ny kupong"}</div>
            <h2 className="font-display text-2xl">Rabattkode</h2>
          </div>
          <button type="button" onClick={onClose} className="text-d8-textMute hover:text-white"><X /></button>
        </div>
        <div className="space-y-5">
          <Lbl label="Kode">
            <input className={inputCls} value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} placeholder="f.eks. SOMMER10" />
          </Lbl>
          <Lbl label="Navn">
            <input className={inputCls} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="f.eks. Sommerkampanje" />
          </Lbl>
          <Lbl label="Rabattype">
            <select className={inputCls} value={form.discount_kind} onChange={e => setForm({ ...form, discount_kind: e.target.value })}>
              <option value="percent">Prosent</option>
              <option value="amount">Fast beløp</option>
            </select>
          </Lbl>
          <Lbl label={form.discount_kind === "percent" ? "Prosent" : "Beløp"}>
            <input type="number" min="0" step="1" className={inputCls} value={form.discount_value} onChange={e => setForm({ ...form, discount_value: e.target.value })} />
          </Lbl>
          <label className="flex items-center gap-3 text-sm">
            <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
            Aktiv i salgskalkulatoren
          </label>
        </div>
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 mt-8">
          <button type="button" onClick={onClose} className="border border-d8-line px-5 py-2.5 text-sm hover:border-white/40">Avbryt</button>
          <button type="submit" disabled={saving} className="bg-d8-red hover:bg-d8-redHover text-white px-5 py-2.5 text-sm">
            {saving ? "Lagrer..." : "Lagre"}
          </button>
        </div>
      </form>
    </div>
  );
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
        zone: form.zone, product_id: form.product_id || form.package, package: form.product_id || form.package, addons: form.addons || [],
        tenant_count: Number(form.tenant_count) || 0, discount_type: form.discount_type || null,
        coupon_code: form.coupon_code || null, surcharge_label: form.surcharge_label || null,
        surcharge_amount: Number(form.surcharge_amount) || 0,
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
      <div className="bg-d8-surface border border-d8-line max-w-2xl w-full p-4 sm:p-8 max-h-[calc(100vh-2rem)] overflow-y-auto" onClick={e => e.stopPropagation()}>
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
            <select className={inputCls} value={form.product_id || form.package || ""} onChange={e => { set("product_id", e.target.value); set("package", e.target.value); }}>
              {(matrix?.products || []).map(p => <option key={p.product_id} value={p.product_id}>{p.category} - {p.name}</option>)}
            </select>
          </Lbl>
          <Lbl label="Status">
            <select className={inputCls} value={form.status || "aktiv"} onChange={e => set("status", e.target.value)} data-testid="edit-status">
              {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Lbl>
          <Lbl label="Kupong">
            <select className={inputCls} value={form.coupon_code || ""} onChange={e => set("coupon_code", e.target.value)}>
              <option value="">Ingen kupong</option>
              {(matrix?.coupons || []).map(c => <option key={c.coupon_id} value={c.code}>{c.code} - {c.name}</option>)}
            </select>
          </Lbl>
          <Lbl label="Påslag">
            <input className={inputCls} value={form.surcharge_label || ""} onChange={e => set("surcharge_label", e.target.value)} />
          </Lbl>
          <Lbl label="Påslag beløp">
            <input type="number" min="0" className={inputCls} value={form.surcharge_amount || 0} onChange={e => set("surcharge_amount", e.target.value)} />
          </Lbl>
          <Lbl label="Dato"><input type="date" className={inputCls} value={form.sale_date || ""} onChange={e => set("sale_date", e.target.value)} /></Lbl>
          <Lbl label="Kommentar" full><input className={inputCls} value={form.comment || ""} onChange={e => set("comment", e.target.value)} /></Lbl>
        </div>

        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 mt-6">
          <button onClick={onClose} className="border border-d8-line px-5 py-2.5 text-sm hover:border-white/40">Avbryt</button>
          <button onClick={submit} disabled={saving} data-testid="save-edit" className="bg-d8-red hover:bg-d8-redHover text-white px-5 py-2.5 text-sm">
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
