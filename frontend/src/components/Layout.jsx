import React from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LayoutDashboard, FilePlus2, ListChecks, Shield, LogOut, ScrollText, Users } from "lucide-react";

function NavItem({ to, icon: Icon, label, testId, mobile = false }) {
  return (
    <NavLink
      to={to}
      data-testid={mobile ? `${testId}-mobile` : testId}
      className={({ isActive }) =>
        mobile
          ? `group flex min-w-[4.75rem] flex-col items-center justify-center gap-1 px-2 py-2 border-t-2 transition-all duration-200 ${
              isActive
                ? "border-d8-red bg-d8-red/10 text-white"
                : "border-transparent text-d8-textMute hover:text-white hover:bg-white/5"
            }`
          : `group flex items-center gap-3 px-4 py-3 border-l-2 transition-all duration-200 ${
          isActive
            ? "border-d8-red bg-d8-red/10 text-white"
            : "border-transparent text-d8-textMute hover:text-white hover:bg-white/5"
        }`
      }
    >
      <Icon size={mobile ? 19 : 18} strokeWidth={1.5} />
      <span className={mobile ? "text-[11px] leading-tight" : "text-sm tracking-wide"}>{label}</span>
    </NavLink>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navItems = [
    { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard", testId: "nav-dashboard" },
    { to: "/sales/new", icon: FilePlus2, label: "Nytt salg", testId: "nav-new-sale" },
    { to: "/sales", icon: ListChecks, label: "Mine salg", testId: "nav-my-sales" },
  ];
  const adminItems = user?.role === "admin"
    ? [
        { to: "/admin", icon: Shield, label: "Admin", testId: "nav-admin" },
        { to: "/admin/employees", icon: Users, label: "Ansatte", testId: "nav-employees" },
        { to: "/admin/activity", icon: ScrollText, label: "Logg", testId: "nav-activity" },
      ]
    : [];

  return (
    <div className="min-h-screen bg-d8-bg text-white md:flex">
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-d8-line bg-d8-bg/95 px-4 py-3 backdrop-blur md:hidden">
        <Link to="/dashboard" className="flex items-center gap-3" data-testid="brand-link-mobile">
          <div className="w-8 h-8 bg-d8-red flex items-center justify-center font-display text-white text-base">8</div>
          <div>
            <div className="font-display text-base leading-none">Dynasty</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-d8-textMute mt-0.5">Salgssystem</div>
          </div>
        </Link>
        <button
          onClick={logout}
          data-testid="logout-btn-mobile"
          className="flex h-10 w-10 items-center justify-center border border-d8-line text-d8-textMute hover:border-d8-red hover:text-d8-red"
          title="Logg ut"
        >
          <LogOut size={17} />
        </button>
      </header>

      {/* Sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 border-r border-d8-line bg-d8-surface/60 backdrop-blur-sm flex-col">
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
          {navItems.map(item => <NavItem key={item.to} {...item} />)}
          {user?.role === "admin" && (
            <>
              <div className="mt-6 px-4 label-eyebrow">Admin</div>
              {adminItems.map(item => <NavItem key={item.to} {...item} />)}
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

      <main className="d8-mobile-safe flex-1 min-w-0">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-40 flex overflow-x-auto border-t border-d8-line bg-d8-bg/95 backdrop-blur md:hidden" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        {[...navItems, ...adminItems].map(item => <NavItem key={item.to} {...item} mobile />)}
      </nav>
    </div>
  );
}
