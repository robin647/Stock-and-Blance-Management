import { useEffect, useState } from "react";
import { wholesaleReportApi } from "../../api/endpoints";

const today = new Date().toISOString().slice(0, 10);
const month = today.slice(0, 7);
const money = (amount) => `৳ ${Number(amount || 0).toLocaleString()}`;

export default function WholesaleReports() {
  const [period, setPeriod] = useState("daily");
  const [day, setDay] = useState(today);
  const [monthValue, setMonthValue] = useState(month);
  const [range, setRange] = useState({ start_date: today, end_date: today });
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  function paramsForPeriod() {
    if (period === "daily") return { start_date: day, end_date: day };
    if (period === "monthly") {
      const [year, monthNumber] = monthValue.split("-").map(Number);
      return { start_date: `${monthValue}-01`, end_date: new Date(year, monthNumber, 0).toISOString().slice(0, 10) };
    }
    return range;
  }

  const params = paramsForPeriod();
  useEffect(() => {
    wholesaleReportApi.reports(params).then((response) => setReport(response.data)).catch(() => setError("Could not load wholesale report."));
  }, [period, day, monthValue, range.start_date, range.end_date]);

  async function exportReport() {
    setError("");
    try { await wholesaleReportApi.export(params); } catch { setError("Could not export the report."); }
  }

  const totals = report?.grand_totals || {};
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-lg font-semibold">Wholesale Reports</h1><p className="mt-1 text-sm text-gray-500">Sales, payment channels, returns, inventory quantities, and dues</p></div><button onClick={exportReport} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium">Export .xlsx</button></header>
      <section className="flex flex-wrap items-center gap-2 border-b border-gray-200 pb-3">
        {["daily", "monthly", "range"].map((value) => <button key={value} onClick={() => setPeriod(value)} className={`rounded-lg px-3 py-2 text-sm capitalize ${period === value ? "bg-brand-500 text-white" : "border border-gray-300 bg-white text-gray-700"}`}>{value === "range" ? "Date range" : value}</button>)}
        {period === "daily" && <input type="date" value={day} onChange={(event) => setDay(event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />}
        {period === "monthly" && <input type="month" value={monthValue} onChange={(event) => setMonthValue(event.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />}
        {period === "range" && <><input aria-label="Start date" type="date" value={range.start_date} onChange={(event) => setRange({ ...range, start_date: event.target.value })} className="rounded-lg border border-gray-300 px-3 py-2 text-sm" /><input aria-label="End date" type="date" value={range.end_date} onChange={(event) => setRange({ ...range, end_date: event.target.value })} className="rounded-lg border border-gray-300 px-3 py-2 text-sm" /></>}
      </section>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">{[["Gross sales", totals.total_sales], ["Payments", totals.total_payments], ["Returns", totals.total_returns], ["Outstanding due", totals.total_due], ["Party credit", totals.total_credit], ["Quantity sold", totals.total_products]].map(([label, value]) => <div key={label} className="border-l-2 border-brand-500 bg-white px-4 py-3"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-lg font-semibold">{label === "Quantity sold" ? Number(value || 0).toLocaleString() : money(value)}</div></div>)}</div>
      <div className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]">
        <section className="overflow-hidden rounded-xl border border-gray-200 bg-white"><h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold">Invoice-wise and party-wise sales</h2><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Date</th><th>Invoice</th><th>Party</th><th>Products</th><th>Gross sale</th><th>Payments</th><th>Returns</th><th>Due</th></tr></thead><tbody>{report?.invoices?.map((invoice) => <tr key={invoice.id} className="border-t border-gray-100 align-top"><td className="px-4 py-3">{invoice.sale_date}</td><td>{invoice.invoice_number}</td><td>{invoice.party_name}</td><td>{invoice.items.map((item) => <div key={item.id}>{item.product_name} × {item.quantity}</div>)}</td><td>{money(invoice.gross_amount)}</td><td>{money(invoice.total_payments)}</td><td>{money(invoice.return_amount)} ({invoice.return_quantity} pcs)</td><td className="font-semibold">{money(invoice.due_amount)}</td></tr>)}</tbody></table></div></section>
        <div className="space-y-6">
          <section className="rounded-xl border border-gray-200 bg-white p-4"><h2 className="mb-3 text-sm font-semibold">Payments by channel</h2>{[["Bank", report?.payment_breakdown?.bank], ["bKash", report?.payment_breakdown?.bkash], ["Cash", report?.payment_breakdown?.cash]].map(([label, value]) => <div key={label} className="flex justify-between border-t border-gray-100 py-2 text-sm"><span className="text-gray-600">{label}</span><strong>{money(value)}</strong></div>)}</section>
          <section className="rounded-xl border border-gray-200 bg-white p-4"><h2 className="mb-3 text-sm font-semibold">Wholesale product quantities</h2>{report?.product_quantities?.map((item) => <div key={item.product} className="flex justify-between border-t border-gray-100 py-2 text-sm"><span>{item.product}</span><strong>{item.quantity} pcs</strong></div>)}{!report?.product_quantities?.length && <p className="text-sm text-gray-500">No sales in this period.</p>}</section>
        </div>
      </div>
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white"><h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold">Party-wise wholesale accounts</h2><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Party</th><th>Sales</th><th>Payments</th><th>Returns</th><th>Outstanding due</th><th>Party credit</th></tr></thead><tbody>{report?.party_totals?.map((row) => <tr key={row.party} className="border-t border-gray-100"><td className="px-4 py-3 font-medium">{row.party}</td><td>{money(row.sales)}</td><td>{money(row.payments)}</td><td>{money(row.returns)}</td><td className="font-semibold">{money(row.due)}</td><td>{money(row.credit)}</td></tr>)}</tbody></table></div></section>
    </div>
  );
}