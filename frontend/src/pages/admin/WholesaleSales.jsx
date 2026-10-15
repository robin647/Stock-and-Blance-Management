import { useEffect, useState } from "react";
import { productApi, showroomApi, wholesaleInvoiceApi, wholesalePartyApi, wholesalePaymentApi } from "../../api/endpoints";

const listOf = (response) => response.data.results || response.data;
const today = new Date().toISOString().slice(0, 10);
const line = () => ({ product: "", quantity: 1, unit_price: "" });
const money = (amount) => `৳ ${Number(amount || 0).toLocaleString()}`;

export default function WholesaleSales() {
  const [parties, setParties] = useState([]);
  const [products, setProducts] = useState([]);
  const [showrooms, setShowrooms] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [form, setForm] = useState({ party: "", invoice_number: "", sale_date: today, stock_location: "factory", showroom: "", notes: "", items: [line()], initial_bank_payment: "0", initial_bkash_payment: "0", initial_cash_payment: "0" });
  const [payment, setPayment] = useState({ invoice: "", payment_date: today, bank_amount: "0", bkash_amount: "0", cash_amount: "0", notes: "" });
  const [message, setMessage] = useState("");

  async function load() {
    const [partyRes, productRes, showroomRes, invoiceRes] = await Promise.all([
      wholesalePartyApi.list({ is_active: true, page_size: 200 }), productApi.list({ is_active: true, page_size: 200 }), showroomApi.list({ page_size: 200 }), wholesaleInvoiceApi.list({ page_size: 200 }),
    ]);
    const partyRows = listOf(partyRes);
    setParties(partyRows);
    setProducts(listOf(productRes));
    setShowrooms(listOf(showroomRes));
    setInvoices(listOf(invoiceRes));
    if (!form.party && partyRows[0]) setForm((current) => ({ ...current, party: String(partyRows[0].id) }));
  }
  useEffect(() => { load().catch(() => setMessage("Could not load wholesale data.")); }, []);

  function updateItem(index, key, value) {
    const items = [...form.items];
    items[index] = { ...items[index], [key]: value };
    if (key === "product") {
      const selected = products.find((product) => String(product.id) === value);
      items[index].unit_price = selected?.selling_price || "";
    }
    setForm({ ...form, items });
  }

  const total = form.items.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0);

  async function createInvoice(event) {
    event.preventDefault();
    setMessage("");
    try {
      await wholesaleInvoiceApi.create({ ...form, party: Number(form.party), showroom: form.stock_location === "showroom" ? Number(form.showroom) : null, items: form.items.map((item) => ({ ...item, product: Number(item.product), quantity: Number(item.quantity), unit_price: Number(item.unit_price) })) });
      setMessage("Invoice saved. Inventory and payment history updated.");
      setForm((current) => ({ ...current, invoice_number: "", notes: "", items: [line()], initial_bank_payment: "0", initial_bkash_payment: "0", initial_cash_payment: "0" }));
      await load();
    } catch (error) {
      setMessage(error.response?.data?.detail || JSON.stringify(error.response?.data || "Could not save invoice."));
    }
  }

  async function recordPayment(event) {
    event.preventDefault();
    setMessage("");
    try {
      await wholesalePaymentApi.create({ ...payment, invoice: Number(payment.invoice), bank_amount: Number(payment.bank_amount), bkash_amount: Number(payment.bkash_amount), cash_amount: Number(payment.cash_amount) });
      setPayment((current) => ({ ...current, bank_amount: "0", bkash_amount: "0", cash_amount: "0", notes: "" }));
      setMessage("Payment recorded against the selected invoice.");
      await load();
    } catch (error) {
      setMessage(error.response?.data?.detail || JSON.stringify(error.response?.data || "Could not record payment."));
    }
  }

  return (
    <div className="space-y-6">
      <div><h1 className="text-lg font-semibold">Wholesale Sales / New Invoice</h1><p className="mt-1 text-sm text-gray-500">Sales are saved once and deduct from the selected inventory location.</p></div>
      {message && <div role="status" className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700">{message}</div>}
      <div className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]">
        <form onSubmit={createInvoice} className="space-y-4 rounded-xl border border-gray-200 bg-white p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="text-xs text-gray-500 sm:col-span-2">Party<select required value={form.party} onChange={(event) => setForm({ ...form, party: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Select party</option>{parties.map((party) => <option key={party.id} value={party.id}>{party.name}</option>)}</select></label>
            <label className="text-xs text-gray-500">Invoice number<input required value={form.invoice_number} onChange={(event) => setForm({ ...form, invoice_number: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500">Sale date<input required type="date" value={form.sale_date} onChange={(event) => setForm({ ...form, sale_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500">Stock location<select value={form.stock_location} onChange={(event) => setForm({ ...form, stock_location: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="factory">Factory stock</option><option value="showroom">Showroom stock</option></select></label>
            {form.stock_location === "showroom" && <label className="text-xs text-gray-500">Showroom<select required value={form.showroom} onChange={(event) => setForm({ ...form, showroom: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Select showroom</option>{showrooms.map((showroom) => <option key={showroom.id} value={showroom.id}>{showroom.name}</option>)}</select></label>}
          </div>
          <section className="space-y-2">
            <div className="flex items-center justify-between"><h2 className="text-sm font-semibold">Products</h2><button type="button" onClick={() => setForm({ ...form, items: [...form.items, line()] })} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">Add product</button></div>
            {form.items.map((item, index) => <div key={index} className="grid gap-2 rounded-lg bg-gray-50 p-3 sm:grid-cols-[2fr_0.6fr_0.8fr_auto] sm:items-end">
              <label className="text-xs text-gray-500">Product<select required value={item.product} onChange={(event) => updateItem(index, "product", event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"><option value="">Select product</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}{product.code ? ` · ${product.code}` : ""}{product.size ? ` · ${product.size}` : ""}</option>)}</select></label>
              <label className="text-xs text-gray-500">Quantity<input required type="number" min="1" value={item.quantity} onChange={(event) => updateItem(index, "quantity", event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
              <label className="text-xs text-gray-500">Unit price<input required type="number" min="0" step="0.01" value={item.unit_price} onChange={(event) => updateItem(index, "unit_price", event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
              <button type="button" disabled={form.items.length === 1} onClick={() => setForm({ ...form, items: form.items.filter((_, rowIndex) => rowIndex !== index) })} aria-label="Remove product" className="rounded-lg px-3 py-2 text-sm text-red-600 disabled:opacity-30">Remove</button>
            </div>)}
            <div className="text-right text-sm">Invoice total <strong className="ml-2 text-base">{money(total)}</strong></div>
          </section>
          <section><h2 className="mb-2 text-sm font-semibold">Payment received now</h2><div className="grid gap-3 sm:grid-cols-3">{[["initial_bank_payment", "Bank"], ["initial_bkash_payment", "bKash"], ["initial_cash_payment", "Cash"]].map(([key, label]) => <label key={key} className="text-xs text-gray-500">{label}<input type="number" min="0" step="0.01" value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>)}</div></section>
          <textarea placeholder="Invoice notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} rows="2" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <button className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white">Save invoice</button>
        </form>
        <form onSubmit={recordPayment} className="h-fit space-y-3 rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="text-sm font-semibold">Record invoice payment</h2>
          <label className="block text-xs text-gray-500">Invoice<select required value={payment.invoice} onChange={(event) => setPayment({ ...payment, invoice: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Select invoice</option>{invoices.filter((invoice) => Number(invoice.due_amount) > 0).map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {invoice.party_name} · due {money(invoice.due_amount)}</option>)}</select></label>
          <label className="block text-xs text-gray-500">Payment date<input type="date" required value={payment.payment_date} onChange={(event) => setPayment({ ...payment, payment_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
          {[["bank_amount", "Bank"], ["bkash_amount", "bKash"], ["cash_amount", "Cash"]].map(([key, label]) => <label key={key} className="block text-xs text-gray-500">{label}<input type="number" min="0" step="0.01" required value={payment[key]} onChange={(event) => setPayment({ ...payment, [key]: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>)}
          <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium">Record payment</button>
        </form>
      </div>
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white"><h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold">Invoices</h2><div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Date</th><th>Invoice</th><th>Party</th><th>Quantity</th><th>Sale</th><th>Payment</th><th>Returns</th><th>Due</th><th>Location</th></tr></thead><tbody>{invoices.map((invoice) => <tr key={invoice.id} className="border-t border-gray-100"><td className="px-4 py-3">{invoice.sale_date}</td><td className="font-medium">{invoice.invoice_number}</td><td>{invoice.party_name}</td><td>{invoice.total_quantity}</td><td>{money(invoice.gross_amount)}</td><td>{money(invoice.total_payments)}</td><td>{money(invoice.return_amount)}</td><td className="font-semibold">{money(invoice.due_amount)}</td><td>{invoice.stock_location === "factory" ? "Factory" : "Showroom"}</td></tr>)}</tbody></table></div></section>
    </div>
  );
}