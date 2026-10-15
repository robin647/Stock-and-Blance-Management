import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { SiteFooter } from "../components/SiteFooter.jsx";

const MODES = {
  admin: {
    label: "Admin",
    heading: "Admin sign in",
    subtext: "Manage showrooms, products, and reports.",
    userPlaceholder: "Admin username",
  },
  showroom: {
    label: "Showroom",
    heading: "Showroom sign in",
    subtext: "Use the username and password your Admin set up for your showroom.",
    userPlaceholder: "Showroom username",
  },
};

export default function Login() {
  const [mode, setMode] = useState("admin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const copy = MODES[mode];

  function switchMode(next) {
    setMode(next);
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // Both Admin and Showroom sign in through the exact same call — the
      // account's role (returned in the token) decides what it can do next.
      const user = await login(username, password);
      if (mode === "admin" && user?.role !== "admin") {
        setError("These credentials belong to a Showroom account. Switch to the Showroom tab.");
        return;
      }
      if (mode === "showroom" && user?.role === "admin") {
        setError("These credentials belong to the Admin account. Switch to the Admin tab.");
        return;
      }
      navigate("/");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Login failed. Please check your username and password."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-gradient-to-br from-brand-50 via-white to-slate-100 px-4 py-10 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <div className="pointer-events-none absolute -left-24 -top-24 h-80 w-80 rounded-full bg-brand-200/40 blur-3xl dark:bg-brand-700/20" />
      <div className="pointer-events-none absolute -bottom-32 -right-24 h-96 w-96 rounded-full bg-indigo-200/40 blur-3xl dark:bg-indigo-700/20" />
      <div className="relative w-full max-w-md">
        <div className="text-center mb-7">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white font-bold text-lg mb-4 shadow-lg shadow-brand-500/25">
            MS
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">Mahir Sherwani</h1>
          <p className="text-sm text-gray-500 mt-1">Showroom stock &amp; sales management</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl shadow-slate-900/5 border border-gray-100 p-7 sm:p-8 dark:border-slate-700">
          {/* Login mode switch */}
          <div className="mb-7 grid grid-cols-2 gap-1.5 bg-gray-100 rounded-xl p-1.5 dark:bg-slate-800">
            {Object.entries(MODES).map(([key, m]) => (
              <button
                key={key}
                type="button"
                onClick={() => switchMode(key)}
                aria-pressed={mode === key}
                className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                  mode === key
                    ? "bg-white text-brand-700 shadow-sm dark:bg-slate-700 dark:text-white"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {m.label} Login
              </button>
            ))}
          </div>

          <div className="mb-5">
            <h2 className="text-base font-semibold text-gray-900">{copy.heading}</h2>
            <p className="text-xs text-gray-500 mt-0.5">{copy.subtext}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <input
                className="w-full border border-gray-200 bg-gray-50/70 rounded-xl px-3.5 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent dark:bg-slate-800"
                placeholder={copy.userPlaceholder}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                className="w-full border border-gray-200 bg-gray-50/70 rounded-xl px-3.5 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent dark:bg-slate-800"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold py-3 rounded-xl transition-colors disabled:opacity-60 shadow-md shadow-brand-500/20"
            >
              {loading ? "Signing in..." : `Sign in as ${copy.label}`}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          Showroom accounts are created by the Admin. Contact your Admin if you don&apos;t have login details.
        </p>
      </div>
      <div className="relative mt-8 w-full">
        <SiteFooter />
      </div>
    </div>
  );
}
