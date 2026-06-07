import React, { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import BrandLogo from "@/components/BrandLogo";
import { LogIn } from "lucide-react";

const BG_URL = "https://images.unsplash.com/photo-1757439402296-000be181e38b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTZ8MHwxfHNlYXJjaHwzfHxsdXh1cnklMjByZWFsJTIwZXN0YXRlJTIwbmlnaHR8ZW58MHx8fHwxNzgwNjA3NTg0fDA&ixlib=rb-4.1.0&q=85";
const inputCls = "w-full bg-d8-surface2 border border-d8-line px-4 py-3 text-white focus:outline-none focus:border-d8-red transition-colors";

export default function Login() {
  const { user, loading, setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [submitting, setSubmitting] = useState(false);

  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const r = await api.post("/auth/login", form);
      setUser(r.data);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Innlogging feilet");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen flex">
      <div className="hidden lg:flex flex-1 relative overflow-hidden">
        <img src={BG_URL} alt="Dynasty 8" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(249,_207,_78,_0.24),_transparent_18%),linear-gradient(180deg,_rgba(14,_57,_27,_0.92),_rgba(4,_8,_6,_0.82))]" />
        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div className="flex items-center gap-3">
            <BrandLogo className="w-12 h-12" />
            <div className="font-display text-2xl text-white">Dynasty 8 AS</div>
          </div>
          <div className="max-w-xl">
            <div className="label-eyebrow mb-4 text-[#F9CF4E]">Eiendomsmegling · Oslo &amp; Romerike</div>
            <h1 className="font-display text-5xl xl:text-6xl leading-tight font-light">
              Selger drømmer.<br/>
              <span className="italic text-[#CAD6B3]">Måler resultater.</span>
            </h1>
            <p className="mt-6 text-d8-textMute max-w-md leading-relaxed">
              Et internt salgssystem for Dynasty 8 sitt team. Registrer salg, beregn priser og følg med på ytelsen din i sanntid.
            </p>
          </div>
          <div className="text-[11px] uppercase tracking-[0.3em] text-d8-textMute">© Dynasty 8 AS</div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center bg-d8-bg p-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-12">
            <BrandLogo className="w-10 h-10" />
            <div className="font-display text-2xl text-white">Dynasty 8 AS</div>
          </div>

          <div className="label-eyebrow text-d8-red mb-4">Innlogging</div>
          <h2 className="font-display text-4xl font-light leading-tight">Velkommen tilbake.</h2>
          <p className="text-d8-textMute mt-3 mb-10">
            Logg inn med brukernavn og passord.
          </p>

          <form onSubmit={submit} className="space-y-5">
            <label className="block">
              <div className="label-eyebrow mb-2">Brukernavn eller e-post</div>
              <input
                className={inputCls}
                value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })}
                autoComplete="username"
                data-testid="login-email-input"
              />
            </label>
            <label className="block">
              <div className="label-eyebrow mb-2">Passord</div>
              <input
                type="password"
                className={inputCls}
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                autoComplete="current-password"
                data-testid="login-password-input"
              />
            </label>
            <button
              type="submit"
              disabled={submitting}
              data-testid="login-submit-button"
              className="w-full flex items-center justify-center gap-3 bg-d8-red hover:bg-d8-redHover text-white py-4 transition-colors font-medium disabled:opacity-60"
            >
              <LogIn size={18} />
              <span>{submitting ? "Logger inn..." : "Logg inn"}</span>
            </button>
          </form>

          <div className="mt-10 pt-8 border-t border-d8-line text-xs text-d8-textMute leading-relaxed">
            Administratorer oppretter brukere og setter passord i ansatt-panelet.
          </div>
        </div>
      </div>
    </div>
  );
}
