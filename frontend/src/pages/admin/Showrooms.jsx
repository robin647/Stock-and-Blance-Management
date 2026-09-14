import { Fragment, useEffect, useState } from "react";
import { showroomApi } from "../../api/endpoints";

const emptyForm = { name: "", address: "", phone: "", username: "", password: "" };

export default function Showrooms() {
  const [showrooms, setShowrooms] = useState([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState("");
  const [creating, setCreating] = useState(false);

  // Which showroom row is currently showing its inline "reset login" form.
  const [credentialsRowId, setCredentialsRowId] = useState(null);
  const [credentialsForm, setCredentialsForm] = useState({ username: "", password: "" });
  const [credentialsError, setCredentialsError] = useState("");
  const [credentialsSuccess, setCredentialsSuccess] = useState("");

  function loadShowrooms() {
    showroomApi.list().then((res) => setShowrooms(res.data.results || res.data));
  }

  useEffect(loadShowrooms, []);

  function firstError(data) {
    if (!data) return "Something went wrong.";
    const errors = data.errors || data;
    const firstKey = Object.keys(errors).find((key) => key !== "detail");
    if (!firstKey) return data.detail || "Something went wrong.";
    const val = errors[firstKey];
    return Array.isArray(val) ? val[0] : String(val);
  }

  const visibleShowrooms = showrooms.filter((showroom) => {
    const needle = search.trim().toLowerCase();
    return !needle || [showroom.name, showroom.login_username, showroom.address, showroom.phone]
      .filter(Boolean).some((value) => value.toLowerCase().includes(needle));
  });

  async function handleCreate(e) {
    e.preventDefault();
    setFormError("");
    setCreating(true);
    try {
      await showroomApi.create(form);
      setForm(emptyForm);
      loadShowrooms();
    } catch (err) {
      setFormError(firstError(err.response?.data));
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(sr) {
    await showroomApi.update(sr.id, { is_active: !sr.is_active });
    loadShowrooms();
  }

  function openCredentialsForm(sr) {
    setCredentialsRowId(sr.id);
    setCredentialsForm({ username: sr.login_username || "", password: "" });
    setCredentialsError("");
    setCredentialsSuccess("");
  }

  function closeCredentialsForm() {
    setCredentialsRowId(null);
    setCredentialsForm({ username: "", password: "" });
  }

  async function handleSaveCredentials(e, sr) {
    e.preventDefault();
    setCredentialsError("");
    setCredentialsSuccess("");
    try {
      await showroomApi.update(sr.id, credentialsForm);
      setCredentialsSuccess("Login updated.");
      loadShowrooms();
      setTimeout(() => closeCredentialsForm(), 900);
    } catch (err) {
      setCredentialsError(firstError(err.response?.data));
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Showrooms</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage all {showrooms.length} showrooms and their login credentials.
          </p>
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search showrooms"
          className="w-full sm:w-60 border border-gray-300 rounded-lg px-3 py-2 text-sm"
        />
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100 bg-gray-50/60">
              <th className="py-3 px-4 font-medium">Name</th>
              <th className="px-4 font-medium">Login username</th>
              <th className="px-4 font-medium">Address</th>
              <th className="px-4 font-medium">Status</th>
              <th className="px-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleShowrooms.map((sr) => (
              <Fragment key={sr.id}>
                <tr className="border-b border-gray-50">
                  <td className="py-3 px-4 font-medium text-gray-900">{sr.name}</td>
                  <td className="px-4 text-gray-600">
                    {sr.has_login ? (
                      sr.login_username
                    ) : (
                      <span className="text-amber-600 text-xs font-medium">No login set up</span>
                    )}
                  </td>
                  <td className="px-4 text-gray-500">{sr.address || "—"}</td>
                  <td className="px-4">
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        sr.is_active
                          ? "bg-green-50 text-green-700"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {sr.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 text-right space-x-3 whitespace-nowrap">
                    <button
                      onClick={() =>
                        credentialsRowId === sr.id ? closeCredentialsForm() : openCredentialsForm(sr)
                      }
                      className="text-brand-600 text-xs font-medium hover:underline"
                    >
                      {sr.has_login ? "Reset login" : "Set up login"}
                    </button>
                    <button
                      onClick={() => toggleActive(sr)}
                      className="text-gray-500 text-xs font-medium hover:underline"
                    >
                      {sr.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
                {credentialsRowId === sr.id && (
                  <tr className="border-b border-gray-50 bg-gray-50/60">
                    <td colSpan={5} className="px-4 py-4">
                      <form
                        onSubmit={(e) => handleSaveCredentials(e, sr)}
                        className="flex flex-wrap items-end gap-3 max-w-2xl"
                      >
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Username
                          </label>
                          <input
                            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-44"
                            value={credentialsForm.username}
                            onChange={(e) =>
                              setCredentialsForm({ ...credentialsForm, username: e.target.value })
                            }
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            New password
                          </label>
                          <input
                            type="password"
                            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-44"
                            placeholder="••••••••"
                            value={credentialsForm.password}
                            onChange={(e) =>
                              setCredentialsForm({ ...credentialsForm, password: e.target.value })
                            }
                            required
                          />
                        </div>
                        <button className="bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium px-4 py-2 rounded-lg">
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={closeCredentialsForm}
                          className="text-xs text-gray-500 hover:text-gray-700 px-2 py-2"
                        >
                          Cancel
                        </button>
                        {credentialsError && (
                          <div className="w-full text-xs text-red-600">{credentialsError}</div>
                        )}
                        {credentialsSuccess && (
                          <div className="w-full text-xs text-green-700">{credentialsSuccess}</div>
                        )}
                      </form>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {visibleShowrooms.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400 text-sm">
                  No showrooms yet — add one below.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <form onSubmit={handleCreate} className="bg-white rounded-2xl border border-gray-100 p-5 max-w-xl">
        <div className="text-sm font-semibold text-gray-900 mb-1">Add new showroom</div>
        <p className="text-xs text-gray-500 mb-4">
          Set a username and password here — the showroom staff will use these to sign in on the
          Showroom Login portal.
        </p>

        {formError && (
          <div className="mb-3 text-xs text-red-700 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {formError}
          </div>
        )}

        <div className="space-y-3">
          <input
            placeholder="Showroom name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            required
          />
          <input
            placeholder="Address (optional)"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <input
            placeholder="Phone (optional)"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />

          <div className="pt-2 border-t border-gray-100 space-y-3">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Login credentials
            </div>
            <input
              placeholder="Username for login"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              required
            />
            <input
              type="password"
              placeholder="Password for login"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              required
            />
          </div>
        </div>

        <button
          disabled={creating}
          className="mt-4 w-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium py-2.5 rounded-lg disabled:opacity-60"
        >
          {creating ? "Creating..." : "Add showroom"}
        </button>
      </form>
    </div>
  );
}
