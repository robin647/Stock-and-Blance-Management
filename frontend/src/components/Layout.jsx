import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";

const linkClass = ({ isActive }) =>
  `block px-4 py-2 rounded-lg text-sm font-medium ${
    isActive ? "bg-brand-500 text-white shadow-sm" : "text-gray-600 hover:bg-gray-100 dark:text-slate-200 dark:hover:bg-slate-800"
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
    <div className="min-h-screen flex bg-gray-50 dark:bg-slate-950">
      {menuOpen && <button aria-label="Close menu" onClick={() => setMenuOpen(false)} className="fixed inset-0 z-30 bg-slate-950/45 md:hidden" />}
      <aside className={`fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 flex flex-col transition-transform duration-200 md:static md:translate-x-0 dark:bg-slate-900 ${menuOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="p-4 border-b border-gray-200">
          <div className="font-semibold text-brand-700 text-lg">Mahir Sherwani</div>
          <div className="text-xs text-gray-500 mt-1">
            {isAdmin ? "Admin Panel" : user?.showroomName}
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {isAdmin ? (
            <>
              <NavLink onClick={() => setMenuOpen(false)} to="/" end className={linkClass}>Dashboard</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/showrooms" className={linkClass}>Showrooms</NavLink>
              <NavLink onClick={() => setMenuOpen(false)} to="/products" className={linkClass}>Products</NavLink>
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
        <div className="p-3 border-t border-gray-200">
          <div className="text-sm text-gray-700 mb-2">{user?.fullName}</div>
          <button onClick={toggleTheme} className="w-full text-sm text-left px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100 dark:text-slate-200 dark:hover:bg-slate-800">
            {theme === "dark" ? "Light theme" : "Dark theme"}
          </button>
          <button
            onClick={handleLogout}
            className="w-full text-sm text-left px-4 py-2 rounded-lg text-red-600 hover:bg-red-50"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 overflow-y-auto">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-gray-200 bg-white/95 px-4 py-3 backdrop-blur md:hidden dark:bg-slate-900/95">
          <button onClick={() => setMenuOpen(true)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 dark:text-slate-100">Menu</button>
          <span className="font-semibold text-brand-700">Mahir Sherwani</span>
          <button onClick={toggleTheme} className="rounded-lg px-2 py-1.5 text-sm text-gray-700 dark:text-slate-100">{theme === "dark" ? "Light" : "Dark"}</button>
        </header>
        <div className="p-4 sm:p-6">{children}</div>
      </main>
    </div>
  );
}
