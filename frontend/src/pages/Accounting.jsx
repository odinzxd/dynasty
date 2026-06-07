import React, { useEffect, useState } from "react";
import { api, formatNOK, formatDate } from "@/lib/api";
import { toast } from "sonner";

export default function Accounting() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ entry_date: new Date().toISOString().slice(0,10), amount: 0, direction: "out", category: "", description: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/ledger");
      setEntries(r.data);
    } catch (err) {
      toast.error("Kunne ikke hente regnskapsposter");
    } finally {
      setLoading(false);
    }
  };

  const submit = async (e) => {
    e && e.preventDefault();
    setSaving(true);
    try {
      const r = await api.post("/ledger", form);
      toast.success("Post lagret");
      setForm({ entry_date: new Date().toISOString().slice(0,10), amount: 0, direction: "out", category: "", description: "" });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Kunne ikke lagre post");
    } finally {
      setSaving(false);
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
        <p className="text-d8-textMute mt-2">Registrer uttak og innbetalinger mot bedriftskontoen.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
        <div className="lg:col-span-1 d8-card">
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
            <button type="submit" disabled={saving} className="w-full bg-d8-red hover:bg-d8-redHover text-white py-3">{saving ? "Lagrer..." : "Lagre post"}</button>
          </form>
        </div>

        <div className="lg:col-span-2">
          <div className="d8-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg">Transaksjoner</h2>
              <div className="text-right">
                <div className="text-sm text-d8-textMute">Innbetalt</div>
                <div className="font-mono">{formatNOK(totalIn)}</div>
                <div className="text-sm text-d8-textMute">Uttak</div>
                <div className="font-mono">{formatNOK(totalOut)}</div>
                <div className="text-sm text-d8-textMute mt-2">Saldo</div>
                <div className="font-display text-lg text-d8-red">{formatNOK(balance)}</div>
              </div>
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
