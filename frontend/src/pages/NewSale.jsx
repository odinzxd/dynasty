import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatNOK } from "@/lib/api";
import { toast } from "sonner";
import { Calculator, CheckCircle2 } from "lucide-react";

const initial = {
  customer_name: "",
  phone: "",
  address: "",
  zone: "",
  package: "",
  addons: [],
  tenant_count: 0,
  discount_type: "",
  sale_date: new Date().toISOString().slice(0, 10),
  comment: "",
  status: "aktiv",
};

const Field = ({ label, children, required }) => (
  <label className="block">
    <div className="label-eyebrow mb-2">{label}{required && <span className="text-d8-red ml-1">*</span>}</div>
    {children}
  </label>
);

const inputCls = "w-full bg-d8-surface2 border border-d8-line px-3 py-2.5 text-white focus:outline-none focus:border-d8-red transition-colors";

export default function NewSale() {
  const navigate = useNavigate();
  const [matrix, setMatrix] = useState(null);
  const [form, setForm] = useState(initial);
  const [calc, setCalc] = useState({ base_price: 0, total_price: 0, discount_percent: 0 });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { api.get("/price-matrix").then(r => setMatrix(r.data)); }, []);

  // Auto-calc whenever pricing inputs change
  useEffect(() => {
    if (!form.zone || !form.package) { setCalc({ base_price: 0, total_price: 0, discount_percent: 0 }); return; }
    const t = setTimeout(async () => {
      try {
        const r = await api.post("/price-calculator", {
          zone: form.zone, package: form.package, addons: form.addons,
          tenant_count: Number(form.tenant_count) || 0, discount_type: form.discount_type || null,
        });
        setCalc(r.data);
      } catch { /* ignore */ }
    }, 150);
    return () => clearTimeout(t);
  }, [form.zone, form.package, form.addons, form.tenant_count, form.discount_type]);

  const toggleAddon = (key) => {
    setForm(f => ({ ...f, addons: f.addons.includes(key) ? f.addons.filter(x => x !== key) : [...f.addons, key] }));
  };

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.customer_name || !form.phone || !form.zone || !form.package) {
      toast.error("Fyll ut alle obligatoriske felter");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/sales", { ...form, tenant_count: Number(form.tenant_count) || 0 });
      toast.success("Salg registrert");
      navigate("/sales");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Kunne ikke registrere salg");
    } finally { setSubmitting(false); }
  };

  const zones = matrix?.zones || [];
  const packages = matrix?.packages || [];

  const hasLeietaker = useMemo(() => true, []);

  return (
    <div className="p-6 sm:p-10 max-w-7xl">
      <div className="mb-8 animate-fade-in-up">
        <div className="label-eyebrow text-d8-red mb-2">Registrering</div>
        <h1 className="font-display text-4xl font-light">Nytt salg</h1>
        <p className="text-d8-textMute mt-2">Fyll ut detaljene under. Totalprisen beregnes automatisk.</p>
      </div>

      <form onSubmit={submit} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form */}
        <div className="lg:col-span-2 space-y-8">
          {/* Customer */}
          <section className="d8-card">
            <h2 className="font-display text-xl mb-6">Kundeinformasjon</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Field label="Kundenavn" required>
                <input data-testid="input-customer" className={inputCls} value={form.customer_name} onChange={e => set("customer_name", e.target.value)} />
              </Field>
              <Field label="Telefonnummer" required>
                <input data-testid="input-phone" className={inputCls} value={form.phone} onChange={e => set("phone", e.target.value)} />
              </Field>
              <Field label="Adresse / Eiendom" required>
                <input data-testid="input-address" className={inputCls} value={form.address} onChange={e => set("address", e.target.value)} />
              </Field>
              <Field label="Dato" required>
                <input type="date" data-testid="input-date" className={inputCls} value={form.sale_date} onChange={e => set("sale_date", e.target.value)} />
              </Field>
            </div>
          </section>

          {/* Sone + pakke */}
          <section className="d8-card">
            <h2 className="font-display text-xl mb-6">Sone og pakke</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Field label="Sone" required>
                <select data-testid="select-zone" className={inputCls} value={form.zone} onChange={e => set("zone", e.target.value)}>
                  <option value="">Velg sone</option>
                  {zones.map(z => <option key={z} value={z}>{z}</option>)}
                </select>
              </Field>
              <Field label="Boligtype / Pakke" required>
                <select data-testid="select-package" className={inputCls} value={form.package} onChange={e => set("package", e.target.value)}>
                  <option value="">Velg pakke</option>
                  {packages.map(p => <option key={p} value={p}>{p} {form.zone && matrix?.matrix?.[form.zone]?.[p] ? `— ${formatNOK(matrix.matrix[form.zone][p])}` : ""}</option>)}
                </select>
              </Field>
            </div>

            <div className="mt-6">
              <div className="label-eyebrow mb-3">Tillegg</div>
              <div className="flex flex-wrap gap-3">
                {["garasje", "hage"].map(key => (
                  <button type="button" key={key} data-testid={`addon-${key}`}
                    onClick={() => toggleAddon(key)}
                    className={`px-4 py-2 border text-sm transition-all ${form.addons.includes(key) ? "border-d8-red bg-d8-red/15 text-white" : "border-d8-line text-d8-textMute hover:border-white/40"}`}>
                    {key === "garasje" ? "Garasje +10%" : "Hage +5%"}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Field label="Leietakere (antall)">
                <input type="number" min="0" data-testid="input-tenants" className={inputCls} value={form.tenant_count} onChange={e => set("tenant_count", e.target.value)} />
                <div className="text-xs text-d8-textMute mt-1">+500 kr per leietaker</div>
              </Field>
              <Field label="Rabatt">
                <select data-testid="select-discount" className={inputCls} value={form.discount_type} onChange={e => set("discount_type", e.target.value)}>
                  <option value="">Ingen rabatt</option>
                  {matrix?.discounts?.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
              </Field>
            </div>
          </section>

          {/* Meta */}
          <section className="d8-card">
            <h2 className="font-display text-xl mb-6">Status og kommentar</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Field label="Status">
                <select data-testid="select-status" className={inputCls} value={form.status} onChange={e => set("status", e.target.value)}>
                  <option value="aktiv">Aktiv</option>
                  <option value="under_behandling">Under behandling</option>
                  <option value="betalt">Betalt</option>
                  <option value="kansellert">Kansellert</option>
                </select>
              </Field>
              <Field label="Kommentar / notat">
                <input data-testid="input-comment" className={inputCls} value={form.comment} onChange={e => set("comment", e.target.value)} />
              </Field>
            </div>
          </section>
        </div>

        {/* Summary / calculator */}
        <aside className="lg:sticky lg:top-6 self-start">
          <div className="d8-card border-d8-red/30 bg-gradient-to-b from-d8-surface to-black">
            <div className="flex items-center gap-2 mb-6">
              <Calculator size={18} className="text-d8-red" />
              <div className="label-eyebrow">Priskalkulator</div>
            </div>

            <div className="space-y-3 text-sm">
              <Row k="Sone" v={form.zone || "—"} />
              <Row k="Pakke" v={form.package || "—"} />
              <Row k="Grunnpris" v={formatNOK(calc.base_price)} mono />
              {form.addons.includes("garasje") && <Row k="Garasje" v="+10%" subtle />}
              {form.addons.includes("hage") && <Row k="Hage" v="+5%" subtle />}
              {Number(form.tenant_count) > 0 && <Row k={`Leietakere (${form.tenant_count})`} v={`+${500 * Number(form.tenant_count)} kr`} subtle />}
              {calc.discount_percent > 0 && <Row k="Rabatt" v={`-${calc.discount_percent}%`} subtle />}
            </div>

            <div className="border-t border-d8-line mt-6 pt-6">
              <div className="label-eyebrow mb-2">Totalpris</div>
              <div className="font-display text-4xl text-d8-red" data-testid="total-price">{formatNOK(calc.total_price)}</div>
            </div>

            <button type="submit" disabled={submitting} data-testid="submit-sale"
              className="mt-8 w-full bg-d8-red hover:bg-d8-redHover disabled:opacity-60 text-white py-4 flex items-center justify-center gap-2 transition-colors">
              <CheckCircle2 size={18} />
              <span>{submitting ? "Lagrer…" : "Lagre salg"}</span>
            </button>
          </div>
        </aside>
      </form>
    </div>
  );
}

function Row({ k, v, mono, subtle }) {
  return (
    <div className="flex items-center justify-between">
      <span className={`${subtle ? "text-d8-textMute" : "text-white"}`}>{k}</span>
      <span className={`${mono ? "font-mono" : ""} ${subtle ? "text-d8-textMute text-xs" : "text-white"}`}>{v}</span>
    </div>
  );
}
