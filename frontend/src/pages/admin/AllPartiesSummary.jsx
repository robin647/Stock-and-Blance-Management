import { useEffect, useState } from "react";
import { wholesalePartyApi, wholesaleReportApi } from "../../api/endpoints";

const money = (amount) => `৳ ${Number(amount || 0).toLocaleString()}`;

export default function AllPartiesSummary() {
  const [parties, setParties] = useState([]);
  const [data, setData] = useState({ results: [], grand_totals: {} });
  const [filters, setFilters] = useState({ party: "", start_date: "", end_date: "", invoice_number: "", payment_status: "", search: "", ordering: "party_name", page: 1 });
  const [error, setError] = useState("");

  useEffect(() => { wholesalePartyApi.list({ page_size: 200 }).then((response) => setParties(response.data.results || response.data)).catch(() => setError("Could not load parties.")); }, []);
  useEffect(() => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ""));
    wholesaleReportApi.summary(params).then((response) => setData(response.data)).catch(() => setError("Could not load party summary."));
  }, [filters]);

  const totals = data.grand_totals || {};
  const update = (key, value) => setFilters((current) => ({ ...current, [key]: value, page: key === "page" ? value : 1 }));

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-lg font-semibold">All Parties Summary</h1><p className="mt-1 text-sm text-gray-500">Combined wholesale account position for the selected filters</p></div><button onClick={() => { const params = Object.fromEntries(Object.entries(filters).filter(([key, value]) => value !== "" && key !== "page")); wholesaleReportApi.exportSummary(params).catch(() => setError("Could not export all-parties summary.")); }} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm">Export Excel</button></header>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">{[["Total sales", totals.total_sales], ["Payments", totals.total_payments], ["Returns", totals.total_returns], ["Outstanding due", totals.total_due], ["Party credit", totals.total_credit], ["Products purchased", totals.total_products]].map(([label, value]) => <div key={label} className="border-l-2 border-brand-500 bg-white px-4 py-3"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-lg font-semibold">{label === "Products purchased" ? Number(value || 0).toLocaleString() : money(value)}</div></div>)}</div>
      <section className="space-y-3 rounded-xl border border-gray-200 bg-white p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <input placeholder="Search party" value={filters.search} onChange={(event) => update("search", event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <select value={filters.party} onChange={(event) => update("party", event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm"><option value="">All parties</option>{parties.map((party) => <option key={party.id} value={party.id}>{party.name}</option>)}</select>
          <input type="date" aria-label="Start date" value={filters.start_date} onChange={(event) => update("start_date", event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input type="date" aria-label="End date" value={filters.end_date} onChange={(event) => update("end_date", event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input placeholder="Invoice number" value={filters.invoice_number} onChange={(event) => update("invoice_number", event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <select value={filters.payment_status} onChange={(event) => update("payment_status", event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm"><option value="">All payment statuses</option><option value="paid">Paid</option><option value="partial">Partial</option><option value="due">Due</option></select>
          <select value={filters.ordering} onChange={(event) => update("ordering", event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm"><option value="party_name">Sort: party A-Z</option><option value="-party_name">Sort: party Z-A</option><option value="-total_sales">Sort: highest sales</option><option value="-total_due">Sort: highest due</option><option value="total_due">Sort: lowest due</option></select>
          <button onClick={() => setFilters({ party: "", start_date: "", end_date: "", invoice_number: "", payment_status: "", search: "", ordering: "party_name", page: 1 })} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">Clear filters</button>
        </div>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      </section>
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="overflow-x-auto"><table className="w-full min-w-[860px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Party name</th><th>Total sales</th><th>Total payments</th><th>Total returns</th><th>Total due</th><th>Party credit</th><th>Qty purchased</th><th>Last purchase</th></tr></thead><tbody>{data.results?.map((row) => <tr key={row.party_id} className="border-t border-gray-100"><td className="px-4 py-3 font-medium">{row.party_name}</td><td>{money(row.total_sales)}</td><td>{money(row.total_payments)}</td><td>{money(row.total_returns)}</td><td className="font-semibold">{money(row.total_due)}</td><td>{money(row.total_credit)}</td><td>{row.total_products}</td><td>{row.last_purchase_date || "—"}</td></tr>)}</tbody></table></div>
        {!data.results?.length && <p className="px-4 py-8 text-center text-sm text-gray-500">No parties match these filters.</p>}
        <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3 text-sm text-gray-600"><span>{data.count || 0} parties</span><div className="flex gap-2"><button disabled={!data.previous} onClick={() => update("page", filters.page - 1)} className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Previous</button><button disabled={!data.next} onClick={() => update("page", filters.page + 1)} className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Next</button></div></div>
      </section>
    </div>
  );
}