import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import { SiteFooter } from "./SiteFooter.jsx";

const linkClass = ({ isActive }) =>
  `block px-3.5 py-2.5 rounded-xl text-[13px] font-medium transition-all ${
    isActive ? "bg-brand-500 text-white shadow-md shadow-brand-500/20" : "text-gray-600 hover:bg-brand-50 hover:text-brand-700 dark:text-slate-200 dark:hover:bg-slate-800"
  }`;

export default function Layout({ children }) {
  const { user, logout, isAdmin } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50 dark:bg-slate-950">
      {menuOpen && <button aria-label="Close menu" onClick={() => setMenuOpen(false)} className="fixed inset-0 z-30 bg-slate-950/45 md:hidden" />}
      <aside className={`fixed inset-y-0 left-0 z-40 w-[272px] bg-white border-r border-gray-200 flex flex-col transition-transform duration-200 md:static md:translate-x-0 dark:bg-slate-900 ${menuOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="px-5 py-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-sm font-bold tracking-wide text-white shadow-md shadow-brand-500/20">MS</div>
            <div>
              <div className="font-bold tracking-tight text-gray-900">Mahir Sherwani</div>
              <div className="mt-0.5 text-[11px] font-medium uppercase tracking-[.12em] text-brand-600">Stock &amp; Sales</div>
            </div>
          </div>
          <div className="text-xs text-gray-500 mt-3 pl-1">
            {isAdmin ? "Admin Panel" : user?.showroomName}
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {isAdmin ? (
            <>
              <NavLink onClick={() => setMenuOpen(false)} to="/" end className={linkClass}>Dashboard</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/showrooms" className={linkClass}>Showrooms</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/products" className={linkClass}>Products</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/stock-adjustments" className={linkClass}>Product Stock Adjustment</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/wholesale/parties" className={linkClass}>Wholesale Party Management</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/wholesale/sales" className={linkClass}>Wholesale Sales / New Invoice</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/wholesale/easy" className={linkClass}>Easy Wholesale Sales Management</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/wholesale/returns" className={linkClass}>Wholesale Returns</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/wholesale/summary" className={linkClass}>All Parties Summary</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/wholesale/reports" className={linkClass}>Wholesale Reports</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/reports" className={linkClass}>Reports</NavLink>
            </>
          ) : (
            <>
              <NavLink onClick={() => setMenuOpen(false)} to="/" end className={linkClass}>Dashboard</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/stock" className={linkClass}>Stock Entry</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/balance" className={linkClass}>Balance Entry</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/reports" className={linkClass}>Reports</NavLink>
            </>
          )}
        </nav>
        <div className="p-3 border-t border-gray-100 dark:border-slate-700">
          <div className="mb-3 flex items-center gap-3 rounded-xl bg-gray-50 p-3 dark:bg-slate-800">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">{user?.fullName?.charAt(0)?.toUpperCase() || "U"}</div>
            <div className="min-w-0"><div className="truncate text-sm font-semibold text-gray-800 dark:text-slate-100">{user?.fullName}</div><div className="text-xs text-gray-500">{isAdmin ? "Administrator" : "Showroom user"}</div></div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full text-left px-3.5 py-2.5 rounded-xl text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex h-screen min-h-0 min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-gray-200/80 bg-white/90 px-4 py-3 backdrop-blur-xl sm:px-6 lg:px-8 dark:bg-slate-900/90">
          <div className="flex items-center gap-3">
            <button onClick={() => setMenuOpen(true)} className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 md:hidden dark:text-slate-100">Menu</button>
            <div className="min-w-0 truncate text-sm font-semibold text-gray-800 dark:text-slate-100">
              {isAdmin ? "Administration" : user?.showroomName || "Showroom"}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-gray-500 sm:block">{user?.fullName}</span>
            <button
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-200 text-gray-700 transition-colors hover:bg-gray-50 dark:border-slate-700 dark:text-slate-100 dark:hover:bg-slate-800"
            >
              {theme === "dark" ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="h-5 w-5">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="h-5 w-5">
                  <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z" />
                </svg>
              )}
            </button>
          </div>
        </header>
        <div className="mx-auto w-full max-w-[1600px] min-h-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">{children}</div>
        <SiteFooter />
      </main>
    </div>
  );
}
