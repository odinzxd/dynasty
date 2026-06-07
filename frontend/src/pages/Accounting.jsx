import React, { useEffect, useState } from "react";
import { api, formatNOK, formatDate } from "@/lib/api";
import { toast } from "sonner";

export default function Accounting() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ entry_date: new Date().toISOString().slice(0,10), amount: 0, direction: "out", category: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [register, setRegister] = useState(null);
  const [registerForm, setRegisterForm] = useState({ balance: 0, note: "" });
  const [registerSaving, setRegisterSaving] = useState(false);
  const [mustUpdateRegister, setMustUpdateRegister] = useState(false);

  useEffect(() => { load(); }, []);

  const isUpdatedToday = (isoString) => {
    if (!isoString) return false;
    return isoString.slice(0, 10) === new Date().toISOString().slice(0, 10);
  };

  const load = async () => {
    setLoading(true);
    try {
      const [ledgerRes, registerRes] = await Promise.all([api.get("/ledger"), api.get("/cash-register")]);
      setEntries(ledgerRes.data);
      setRegister(registerRes.data);
      setRegisterForm({ balance: registerRes.data.balance, note: registerRes.data.note || "" });
      setMustUpdateRegister(!isUpdatedToday(registerRes.data.updated_at));
    } catch (err) {
      toast.error("Kunne ikke hente regnskapsposter");
    } finally {
      setLoading(false);
    }
  };

  const submit = async (e) => {
    e && e.preventDefault();
    if (mustUpdateRegister) {
      toast.error("Oppdater kassa før du registrerer flere transaksjoner.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/ledger", form);
      toast.success("Post lagret");
      setForm({ entry_date: new Date().toISOString().slice(0,10), amount: 0, direction: "out", category: "", description: "" });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Kunne ikke lagre post");
    } finally {
      setSaving(false);
    }
  };

  const updateRegister = async (e) => {
    e && e.preventDefault();
    setRegisterSaving(true);
    try {
      const r = await api.post("/cash-register", registerForm);
      setRegister(r.data);
      setMustUpdateRegister(!isUpdatedToday(r.data.updated_at));
      toast.success("Kassa oppdatert");
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Kunne ikke oppdatere kassa");
    } finally {
      setRegisterSaving(false);
    }
  };

  const totalIn = entries.reduce((s, e) => s + (e.direction === "in" ? Number(e.amount) : 0), 0);
  const totalOut = entries.reduce((s, e) => s + (e.direction === "out" ? Number(e.amount) : 0), 0);
  const balance = totalIn - totalOut;

  return (
    <div className="p-4 sm:p-10 max-w-7xl">
      <div className="mb-8">
        <div className="label-eyebrow text-d8-red mb-2">Regnskap</div>
        <h1 className="font-display text-3xl sm:text-4xl font-light">Bedriftskonto - inn og ut</h1>
        <p className="text-d8-textMute mt-2">Registrer uttak og innbetalinger mot bedriftskontoen. Kassa må oppdateres daglig.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 sm:gap-8">
        <div className="lg:col-span-1 d8-card">
          <h2 className="font-display text-lg mb-4">Kasseoppdatering</h2>
          <div className="space-y-3 mb-4">
            {mustUpdateRegister ? (
              <div className="rounded-lg border border-d8-red bg-d8-surface p-3 text-sm text-d8-red">Kassa er ikke oppdatert i dag. Oppdater saldo før du legger inn nye transaksjoner.</div>
            ) : (
              <div className="rounded-lg border border-d8-green bg-d8-surface p-3 text-sm text-d8-green">Kassa er oppdatert i dag.</div>
            )}
            <div className="text-d8-textMute text-sm">Sist oppdatert: {register?.updated_at ? formatDate(register.updated_at) : "Ingen registrering"}</div>
            <div className="text-sm">Saldo: <span className="font-mono">{formatNOK(register?.balance ?? 0)}</span></div>
            <div className="text-sm">Notat: {register?.note || "Ingen notat"}</div>
            <div className="text-sm">Oppdatert av: {register?.updated_by_name || "-"}</div>
          </div>
          <form onSubmit={updateRegister} className="space-y-4">
            <label className="block">
              <div className="label-eyebrow mb-2">Saldo</div>
              <input
                type="number"
                step="0.01"
                className="w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white"
                value={registerForm.balance}
                onChange={(e) => setRegisterForm({ ...registerForm, balance: Number(e.target.value) })}
              />
            </label>
            <label className="block">
              <div className="label-eyebrow mb-2">Notat</div>
              <input
                className="w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white"
                value={registerForm.note}
                onChange={(e) => setRegisterForm({ ...registerForm, note: e.target.value })}
              />
            </label>
            <button type="submit" disabled={registerSaving} className="w-full bg-d8-red hover:bg-d8-redHover text-white py-3">
              {registerSaving ? "Oppdaterer..." : "Oppdater kassa"}
            </button>
          </form>
        </div>

        <div className="lg:col-span-3">
          <div className="d8-card mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg">Status</h2>
              <div className="text-right">
                <div className="text-sm text-d8-textMute">Innbetalt</div>
                <div className="font-mono">{formatNOK(totalIn)}</div>
                <div className="text-sm text-d8-textMute">Uttak</div>
                <div className="font-mono">{formatNOK(totalOut)}</div>
                <div className="text-sm text-d8-textMute mt-2">Saldo</div>
                <div className="font-display text-lg text-d8-red">{formatNOK(balance)}</div>
              </div>
            </div>
          </div>

          <div className="d8-card">
            <h2 className="font-display text-lg mb-4">Ny post</h2>
            <form onSubmit={submit} className="space-y-4">
              <label className="block">
                <div className="label-eyebrow mb-2">Dato</div>
                <input type="date" className="w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white" value={form.entry_date} onChange={e => setForm({...form, entry_date: e.target.value})} />
              </label>
              <label className="block">
                <div className="label-eyebrow mb-2">Beløp</div>
                <input type="number" step="0.01" className="w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} />
              </label>
              <label className="block">
                <div className="label-eyebrow mb-2">Type</div>
                <select className="w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white" value={form.direction} onChange={e => setForm({...form, direction: e.target.value})}>
                  <option value="in">Innbetaling</option>
                  <option value="out">Uttak</option>
                </select>
              </label>
              <label className="block">
                <div className="label-eyebrow mb-2">Kategori</div>
                <input className="w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white" value={form.category} onChange={e => setForm({...form, category: e.target.value})} />
              </label>
              <label className="block">
                <div className="label-eyebrow mb-2">Beskrivelse</div>
                <input className="w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white" value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
              </label>
              <button type="submit" disabled={saving || mustUpdateRegister} className="w-full bg-d8-red hover:bg-d8-redHover text-white py-3">
                {saving ? "Lagrer..." : "Lagre post"}
              </button>
            </form>
          </div>

          <div className="d8-card mt-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg">Transaksjoner</h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-neutral-100 border-b border-neutral-200 text-left">
                <tr>
                  <th className="px-4 py-3">Dato</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Kategori</th>
                  <th className="px-4 py-3">Beskrivelse</th>
                  <th className="px-4 py-3 text-right">Beløp</th>
                  <th className="px-4 py-3">Ansatt</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-d8-textMute">Laster…</td></tr>
                ) : entries.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-d8-textMute">Ingen poster ennå.</td></tr>
                ) : entries.map(e => (
                  <tr key={e.entry_id} className="border-b border-neutral-100 hover:bg-neutral-50">
                    <td className="px-4 py-3">{formatDate(e.entry_date)}</td>
                    <td className="px-4 py-3">{e.direction === "in" ? "Innbetaling" : "Uttak"}</td>
                    <td className="px-4 py-3">{e.category || "-"}</td>
                    <td className="px-4 py-3">{e.description || "-"}</td>
                    <td className="px-4 py-3 text-right font-mono">{formatNOK(e.amount)}</td>
                    <td className="px-4 py-3">{e.employee_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
