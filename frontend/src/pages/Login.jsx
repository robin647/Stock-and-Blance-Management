import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 via-white to-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-500 text-white font-semibold text-lg mb-3">
            MS
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Mahir Sherwani</h1>
          <p className="text-sm text-gray-500 mt-1">Showroom Stock &amp; Sales Management</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          {/* Login mode switch */}
          <div className="mb-6 grid grid-cols-2 gap-1 bg-gray-100 rounded-xl p-1">
            {Object.entries(MODES).map(([key, m]) => (
              <button
                key={key}
                type="button"
                onClick={() => switchMode(key)}
                aria-pressed={mode === key}
                className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                  mode === key
                    ? "bg-white text-brand-700 shadow-sm"
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
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
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
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
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
              className="w-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium py-2.5 rounded-lg transition-colors disabled:opacity-60"
            >
              {loading ? "Signing in..." : `Sign in as ${copy.label}`}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          Showroom accounts are created by the Admin. Contact your Admin if you don&apos;t have login details.
        </p>
      </div>
    </div>
  );
}
