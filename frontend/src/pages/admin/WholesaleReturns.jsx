import { useEffect, useRef, useState } from "react";
import { wholesaleInvoiceApi, wholesaleReturnApi } from "../../api/endpoints";

const listOf = (response) => response.data.results || response.data;
const today = new Date().toISOString().slice(0, 10);
const apiError = (error) => {
  const data = error.response?.data;
  if (!data) return "Request failed. Check your connection and try again.";
  if (data.errors) return Object.values(data.errors).flat().join(" ");
  return data.detail || Object.values(data).flat().join(" ") || "Could not save the return.";
};

export default function WholesaleReturns() {
  const [invoices, setInvoices] = useState([]);
  const [returns, setReturns] = useState([]);
  const [invoiceFilter, setInvoiceFilter] = useState("");
  const [form, setForm] = useState({ invoice_item: "", quantity: 1, amount: "", return_date: today, notes: "" });
  const [message, setMessage] = useState("");
  const requestKeyRef = useRef({ payload: "", key: "" });

  async function load() {
    const [invoiceRes, returnRes] = await Promise.all([wholesaleInvoiceApi.list({ page_size: 200 }), wholesaleReturnApi.list({ invoice_number: invoiceFilter, page_size: 200 })]);
    setInvoices(listOf(invoiceRes));
    setReturns(listOf(returnRes));
  }
  useEffect(() => { load().catch(() => setMessage("Could not load return records.")); }, [invoiceFilter]);

  const eligibleItems = invoices.flatMap((invoice) => invoice.items.map((item) => ({ ...item, invoice_number: invoice.invoice_number, party_name: invoice.party_name, eligible_quantity: item.quantity - item.returned_quantity })).filter((item) => item.eligible_quantity > 0));
  const selectedItem = eligibleItems.find((item) => String(item.id) === form.invoice_item);

  function setQuantity(quantity) {
    const parsedQuantity = Number(quantity);
    setForm((current) => ({
      ...current,
      quantity,
      amount: selectedItem && parsedQuantity > 0 ? (parsedQuantity * Number(selectedItem.unit_price)).toFixed(2) : "",
    }));
  }

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    try {
      const payload = { ...form, invoice_item: Number(form.invoice_item), quantity: Number(form.quantity), amount: Number(form.amount) };
      const fingerprint = JSON.stringify(payload);
      if (requestKeyRef.current.payload !== fingerprint) requestKeyRef.current = { payload: fingerprint, key: window.crypto.randomUUID() };
      await wholesaleReturnApi.create(payload, requestKeyRef.current.key);
      requestKeyRef.current = { payload: "", key: "" };
      setForm((current) => ({ ...current, quantity: 1, amount: "", notes: "" }));
      setMessage("Return recorded and inventory restored at the original stock location.");
      try { await load(); } catch { setMessage("Return saved, but history could not refresh. Reload the page to view it."); }
    } catch (error) {
      setMessage(apiError(error));
    }
  }

  return (
    <div className="space-y-6">
      <header><h1 className="text-lg font-semibold">Wholesale Returns</h1><p className="mt-1 text-sm text-gray-500">Returned quantities go back to the inventory location used by the invoice.</p></header>
      {message && <div role="status" className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm">{message}</div>}
      <form onSubmit={submit} className="grid gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className="text-xs text-gray-500 sm:col-span-2">Original cash memo / product<select required value={form.invoice_item} onChange={(event) => { const item = eligibleItems.find((row) => String(row.id) === event.target.value); setForm({ ...form, invoice_item: event.target.value, quantity: 1, amount: item ? Number(item.unit_price).toFixed(2) : "" }); }} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Select product sold</option>{eligibleItems.map((item) => <option key={item.id} value={item.id}>{item.invoice_number} · {item.party_name} · {item.product_name} · sold at ৳ {Number(item.unit_price).toLocaleString()} · eligible {item.eligible_quantity}</option>)}</select></label>
        <label className="text-xs text-gray-500">Return quantity<input required type="number" min="1" max={selectedItem?.eligible_quantity || undefined} value={form.quantity} onChange={(event) => setQuantity(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <label className="text-xs text-gray-500">Return amount (original sale price)<input required readOnly type="number" min="0" step="0.01" value={form.amount} className="mt-1 w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-900" /></label>
        <label className="text-xs text-gray-500">Return date<input required type="date" value={form.return_date} onChange={(event) => setForm({ ...form, return_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <label className="text-xs text-gray-500 sm:col-span-2 lg:col-span-4">Notes<input value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <button className="self-end rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white">Record return</button>
      </form>
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3"><h2 className="text-sm font-semibold">Return history</h2><input value={invoiceFilter} onChange={(event) => setInvoiceFilter(event.target.value)} placeholder="Filter invoice number" className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm" /></div><div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Date</th><th>Invoice</th><th>Product</th><th>Qty</th><th>Return amount</th><th>Notes</th></tr></thead><tbody>{returns.map((entry) => <tr key={entry.id} className="border-t border-gray-100"><td className="px-4 py-3">{entry.return_date}</td><td>{entry.invoice_number}</td><td>{entry.product_name}</td><td>{entry.quantity}</td><td>৳ {Number(entry.amount).toLocaleString()}</td><td>{entry.notes || "—"}</td></tr>)}</tbody></table></div></section>
    </div>
  );
}