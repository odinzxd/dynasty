import React from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LayoutDashboard, FilePlus2, ListChecks, Shield, LogOut, ScrollText } from "lucide-react";

function NavItem({ to, icon: Icon, label, testId }) {
  return (
    <NavLink
      to={to}
      data-testid={testId}
      className={({ isActive }) =>
        `group flex items-center gap-3 px-4 py-3 border-l-2 transition-all duration-200 ${
          isActive
            ? "border-d8-red bg-d8-red/10 text-white"
            : "border-transparent text-d8-textMute hover:text-white hover:bg-white/5"
        }`
      }
    >
      <Icon size={18} strokeWidth={1.5} />
      <span className="text-sm tracking-wide">{label}</span>
    </NavLink>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-d8-bg text-white">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 border-r border-d8-line bg-d8-surface/60 backdrop-blur-sm flex flex-col">
        <div className="p-6 border-b border-d8-line">
          <Link to="/dashboard" className="block" data-testid="brand-link">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-d8-red flex items-center justify-center font-display text-white text-lg">8</div>
              <div>
                <div className="font-display text-lg leading-none">Dynasty</div>
                <div className="label-eyebrow mt-1">Salgssystem</div>
              </div>
            </div>
          </Link>
        </div>

        <nav className="flex-1 py-4 flex flex-col gap-1">
          <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" testId="nav-dashboard" />
          <NavItem to="/sales/new" icon={FilePlus2} label="Nytt salg" testId="nav-new-sale" />
          <NavItem to="/sales" icon={ListChecks} label="Mine salg" testId="nav-my-sales" />
          {user?.role === "admin" && (
            <>
              <div className="mt-6 px-4 label-eyebrow">Admin</div>
              <NavItem to="/admin" icon={Shield} label="Adminpanel" testId="nav-admin" />
              <NavItem to="/admin/activity" icon={ScrollText} label="Aktivitetslogg" testId="nav-activity" />
            </>
          )}
        </nav>

        <div className="p-4 border-t border-d8-line">
          <div className="flex items-center gap-3 mb-3">
            {user?.picture ? (
              <img src={user.picture} alt="" className="w-9 h-9 object-cover" />
            ) : (
              <div className="w-9 h-9 bg-d8-line flex items-center justify-center text-sm">{user?.name?.[0]?.toUpperCase() || "?"}</div>
            )}
            <div className="min-w-0">
              <div className="text-sm truncate" data-testid="user-name">{user?.name}</div>
              <div className="text-[11px] text-d8-textMute uppercase tracking-wider">
                {user?.role === "admin" ? "Administrator" : "Ansatt"}
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            data-testid="logout-btn"
            className="w-full flex items-center justify-center gap-2 border border-d8-line hover:border-d8-red hover:text-d8-red text-sm py-2 transition-colors"
          >
            <LogOut size={14} /> Logg ut
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
