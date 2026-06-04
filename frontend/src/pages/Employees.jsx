import React, { useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import { toast } from "sonner";
import { Pencil, Trash2, UserX, ShieldCheck, ShieldOff, X, Power } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const inputCls = "w-full bg-d8-surface2 border border-d8-line px-3 py-2 text-white focus:outline-none focus:border-d8-red transition-colors";

export default function Employees() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [edit, setEdit] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/users");
      setUsers(r.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const toggleActive = async (u) => {
    const next = !(u.is_active !== false);
    if (!window.confirm(next ? `Aktivere ${u.name}?` : `Deaktivere ${u.name}? Alle aktive sesjoner blir avsluttet.`)) return;
    try {
      await api.patch(`/users/${u.user_id}`, { is_active: next });
      toast.success(next ? "Bruker aktivert" : "Bruker deaktivert");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Feilet"); }
  };

  const toggleRole = async (u) => {
    const next = u.role === "admin" ? "ansatt" : "admin";
    if (!window.confirm(`Endre rolle til ${next === "admin" ? "Administrator" : "Ansatt"} for ${u.name}?`)) return;
    try {
      await api.patch(`/users/${u.user_id}`, { role: next });
      toast.success("Rolle oppdatert");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Feilet"); }
  };

  const kick = async (u) => {
    if (!window.confirm(`Kaste ut ${u.name}? Brukeren blir logget ut umiddelbart.`)) return;
    try {
      const r = await api.post(`/users/${u.user_id}/revoke-sessions`);
      toast.success(`${u.name} ble logget ut (${r.data.revoked} sesjoner avsluttet)`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Feilet"); }
  };

  const removeUser = async (u) => {
    if (!window.confirm(`Slette brukeren ${u.name} permanent? Salgshistorikken beholdes, men brukeren mister all tilgang.`)) return;
    try {
      await api.delete(`/users/${u.user_id}`);
      toast.success("Bruker slettet");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Feilet"); }
  };

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-8">
        <div className="label-eyebrow text-d8-red mb-2">Adminstyring</div>
        <h1 className="font-display text-4xl font-light">Ansatte</h1>
        <p className="text-d8-textMute mt-2">Administrer roller, deaktiver kontoer eller kast ansatte ut av systemet.</p>
      </div>

      <div className="d8-table">
        <table className="w-full text-sm">
          <thead className="bg-neutral-100 border-b border-neutral-200 text-left">
            <tr>
              <th className="px-4 py-3 font-medium">Navn</th>
              <th className="px-4 py-3 font-medium">E-post</th>
              <th className="px-4 py-3 font-medium">Ansattnr.</th>
              <th className="px-4 py-3 font-medium">Rolle</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Opprettet</th>
              <th className="px-4 py-3 font-medium text-right">Handlinger</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-neutral-500">Laster…</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-neutral-500">Ingen ansatte ennå.</td></tr>
            ) : users.map(u => {
              const active = u.is_active !== false;
              const self = u.user_id === me?.user_id;
              return (
                <tr key={u.user_id} className="border-b border-neutral-100 hover:bg-neutral-50" data-testid={`user-row-${u.user_id}`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {u.picture
                        ? <img src={u.picture} alt="" className="w-8 h-8 object-cover" />
                        : <div className="w-8 h-8 bg-neutral-200 flex items-center justify-center text-xs">{u.name?.[0]?.toUpperCase()}</div>}
                      <span className="font-medium">{u.name}{self && <span className="text-d8-red text-[10px] ml-2 uppercase tracking-wider">deg</span>}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-neutral-600">{u.email}</td>
                  <td className="px-4 py-3 text-neutral-600 font-mono">{u.employee_number || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2.5 py-1 text-[11px] uppercase tracking-wider border ${u.role === "admin" ? "border-d8-red text-d8-red bg-d8-red/10" : "border-neutral-300 text-neutral-700"}`}>
                      {u.role === "admin" ? "Administrator" : "Ansatt"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2.5 py-1 text-[11px] uppercase tracking-wider border ${active ? "border-emerald-400 text-emerald-600 bg-emerald-50" : "border-neutral-400 text-neutral-500 bg-neutral-100"}`}>
                      {active ? "Aktiv" : "Deaktivert"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-neutral-500 text-xs">{formatDate(u.created_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <IconBtn title="Rediger" onClick={() => setEdit(u)} testId={`edit-user-${u.user_id}`}><Pencil size={14} /></IconBtn>
                      <IconBtn title={u.role === "admin" ? "Gjør til ansatt" : "Gjør til administrator"} disabled={self} onClick={() => toggleRole(u)} testId={`role-${u.user_id}`}>
                        {u.role === "admin" ? <ShieldOff size={14} /> : <ShieldCheck size={14} />}
                      </IconBtn>
                      <IconBtn title={active ? "Deaktiver" : "Aktiver"} disabled={self} onClick={() => toggleActive(u)} testId={`active-${u.user_id}`}>
                        <Power size={14} className={active ? "" : "text-emerald-500"} />
                      </IconBtn>
                      <IconBtn title="Kast ut (logg ut alle sesjoner)" disabled={self} onClick={() => kick(u)} testId={`kick-${u.user_id}`}>
                        <UserX size={14} />
                      </IconBtn>
                      <IconBtn title="Slett bruker" disabled={self} danger onClick={() => removeUser(u)} testId={`delete-user-${u.user_id}`}>
                        <Trash2 size={14} />
                      </IconBtn>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {edit && <EditUserModal user={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); }} />}
    </div>
  );
}

function IconBtn({ children, onClick, title, danger, disabled, testId }) {
  return (
    <button
      onClick={onClick}
      title={title}
      disabled={disabled}
      data-testid={testId}
      className={`p-2 transition-colors ${disabled ? "text-neutral-300 cursor-not-allowed" : danger ? "text-neutral-600 hover:text-d8-red" : "text-neutral-600 hover:text-d8-red"}`}
    >
      {children}
    </button>
  );
}

function EditUserModal({ user, onClose, onSaved }) {
  const [form, setForm] = useState({ name: user.name || "", employee_number: user.employee_number || "", role: user.role || "ansatt" });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch(`/users/${user.user_id}`, {
        name: form.name,
        employee_number: form.employee_number || null,
        role: form.role,
      });
      toast.success("Bruker oppdatert");
      onSaved();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Kunne ikke lagre");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={submit} className="bg-d8-surface border border-d8-line max-w-lg w-full p-8" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="label-eyebrow text-d8-red mb-2">Rediger ansatt</div>
            <h2 className="font-display text-2xl">{user.email}</h2>
          </div>
          <button type="button" onClick={onClose} className="text-d8-textMute hover:text-white"><X /></button>
        </div>

        <div className="space-y-5">
          <label className="block">
            <div className="label-eyebrow mb-2">Navn</div>
            <input className={inputCls} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="edit-user-name" />
          </label>
          <label className="block">
            <div className="label-eyebrow mb-2">Ansattnummer</div>
            <input className={inputCls} value={form.employee_number} onChange={e => setForm({ ...form, employee_number: e.target.value })} placeholder="f.eks. E101" data-testid="edit-user-empnum" />
          </label>
          <label className="block">
            <div className="label-eyebrow mb-2">Rolle</div>
            <select className={inputCls} value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} data-testid="edit-user-role">
              <option value="ansatt">Ansatt</option>
              <option value="admin">Administrator</option>
            </select>
          </label>
        </div>

        <div className="flex justify-end gap-3 mt-8">
          <button type="button" onClick={onClose} className="border border-d8-line px-5 py-2 text-sm hover:border-white/40">Avbryt</button>
          <button type="submit" disabled={saving} data-testid="save-user" className="bg-d8-red hover:bg-d8-redHover text-white px-5 py-2 text-sm">
            {saving ? "Lagrer…" : "Lagre"}
          </button>
        </div>
      </form>
    </div>
  );
}
