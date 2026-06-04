import React from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Navigate } from "react-router-dom";

const BG_URL = "https://images.unsplash.com/photo-1757439402296-000be181e38b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTZ8MHwxfHNlYXJjaHwzfHxsdXh1cnklMjByZWFsJTIwZXN0YXRlJTIwbmlnaHR8ZW58MHx8fHwxNzgwNjA3NTg0fDA&ixlib=rb-4.1.0&q=85";

export default function Login() {
  const { user, loading } = useAuth();

  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;

  const handleGoogleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="relative min-h-screen flex">
      {/* Left visual */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden">
        <img src={BG_URL} alt="Dynasty 8" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-r from-black via-black/70 to-black/30" />
        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-d8-red flex items-center justify-center font-display text-white text-xl">8</div>
            <div className="font-display text-2xl">Dynasty 8 AS</div>
          </div>
          <div className="max-w-xl">
            <div className="label-eyebrow mb-4 text-d8-red">Eiendomsmegling · Oslo &amp; Romerike</div>
            <h1 className="font-display text-5xl xl:text-6xl leading-tight font-light">
              Selger drømmer.<br/>
              <span className="italic text-d8-textMute">Måler resultater.</span>
            </h1>
            <p className="mt-6 text-d8-textMute max-w-md leading-relaxed">
              Et internt salgssystem for Dynasty 8 sitt team. Registrer salg, beregn priser og følg med på ytelsen din — i sanntid.
            </p>
          </div>
          <div className="text-[11px] uppercase tracking-[0.3em] text-d8-textMute">© Dynasty 8 AS</div>
        </div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center bg-d8-bg p-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-12">
            <div className="w-10 h-10 bg-d8-red flex items-center justify-center font-display text-white text-xl">8</div>
            <div className="font-display text-2xl">Dynasty 8 AS</div>
          </div>

          <div className="label-eyebrow text-d8-red mb-4">Innlogging</div>
          <h2 className="font-display text-4xl font-light leading-tight">Velkommen tilbake.</h2>
          <p className="text-d8-textMute mt-3 mb-10">
            Logg inn med din Dynasty 8-konto for å fortsette.
          </p>

          <button
            onClick={handleGoogleLogin}
            data-testid="google-login-btn"
            className="w-full flex items-center justify-center gap-3 bg-white text-neutral-900 py-4 hover:bg-d8-textMute hover:text-black transition-colors font-medium group"
          >
            <svg width="20" height="20" viewBox="0 0 48 48">
              <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.5-5.9 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.7 5.9 29.6 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z"/>
              <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 13 24 13c3 0 5.8 1.1 7.9 3l5.7-5.7C34.7 5.9 29.6 4 24 4 16.3 4 9.6 8.4 6.3 14.7z"/>
              <path fill="#4CAF50" d="M24 44c5.5 0 10.4-2.1 14.1-5.5l-6.5-5.5c-2 1.4-4.6 2.2-7.6 2.2-5.4 0-10-3.6-11.7-8.5l-6.6 5.1C9.4 39.4 16.1 44 24 44z"/>
              <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.2 4.2-4.1 5.6l6.5 5.5C41.9 36.4 44 30.6 44 24c0-1.2-.1-2.3-.4-3.5z"/>
            </svg>
            <span>Fortsett med Google</span>
          </button>

          <div className="mt-10 pt-8 border-t border-d8-line text-xs text-d8-textMute leading-relaxed">
            Tilgangen er rollebasert. Sensitive personopplysninger (navn, telefon) lagres sikkert og vises kun til autoriserte ansatte.
          </div>
        </div>
      </div>
    </div>
  );
}
