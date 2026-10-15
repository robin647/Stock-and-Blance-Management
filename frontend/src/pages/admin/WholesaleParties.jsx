import { useEffect, useState } from "react";
import { wholesalePartyApi } from "../../api/endpoints";

const blankForm = { name: "", phone: "", address: "", business_name: "", notes: "", is_active: true };
const rowsOf = (response) => response.data.results || response.data;
const money = (amount) => `৳ ${Number(amount || 0).toLocaleString()}`;

export default function WholesaleParties() {
  const [parties, setParties] = useState([]);
  const [history, setHistory] = useState(null);
  const [form, setForm] = useState(blankForm);
  const [editing, setEditing] = useState(null);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const response = await wholesalePartyApi.list({ search });
    setParties(rowsOf(response));
  }

  useEffect(() => { load().catch(() => setMessage("Could not load parties.")); }, [search]);

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    try {
      if (editing) await wholesalePartyApi.update(editing, form);
      else await wholesalePartyApi.create(form);
      setForm(blankForm);
      setEditing(null);
      await load();
      setMessage(editing ? "Party updated." : "Party added.");
    } catch (error) {
      setMessage(error.response?.data?.name?.[0] || "Could not save party information.");
    }
  }

  async function openHistory(party) {
    const response = await wholesalePartyApi.history(party.id);
    setHistory(response.data);
  }

  function startEdit(party) {
    setEditing(party.id);
    setForm({ name: party.name, phone: party.phone, address: party.address, business_name: party.business_name, notes: party.notes, is_active: party.is_active });
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-lg font-semibold">Wholesale Parties</h1><p className="mt-1 text-sm text-gray-500">Buyer profiles and account history</p></div>
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search party name" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm sm:w-72" />
      </header>
      <div className="grid gap-6 xl:grid-cols-[minmax(280px,0.8fr)_1.7fr]">
        <form onSubmit={submit} className="h-fit space-y-3 rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="text-sm font-semibold">{editing ? "Edit party" : "Add party"}</h2>
          <input required placeholder="Party name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input placeholder="Phone number" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input placeholder="Business name (optional)" value={form.business_name} onChange={(event) => setForm({ ...form, business_name: event.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <textarea placeholder="Address" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} rows="2" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <textarea placeholder="Notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} rows="2" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          {editing && <label className="flex items-center gap-2 text-sm text-gray-600"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /> Active</label>}
          <div className="flex gap-2"><button className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white">{editing ? "Save changes" : "Add party"}</button>{editing && <button type="button" onClick={() => { setEditing(null); setForm(blankForm); }} className="rounded-lg border border-gray-300 px-4 py-2 text-sm">Cancel</button>}</div>
          {message && <p role="status" className="text-sm text-gray-600">{message}</p>}
        </form>
        <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Party</th><th>Business / Phone</th><th>Total sales</th><th>Payments</th><th>Returns</th><th>Due</th><th>Credit</th><th>State</th><th></th></tr></thead>
            <tbody>{parties.map((party) => <tr key={party.id} className="border-t border-gray-100"><td className="px-4 py-3 font-medium">{party.name}</td><td>{party.business_name || party.phone || "—"}</td><td>{money(party.total_sales)}</td><td>{money(party.total_payments)}</td><td>{money(party.total_returns)}</td><td className="font-semibold">{money(party.total_due)}</td><td>{money(party.total_credit)}</td><td>{party.is_active ? "Active" : "Inactive"}</td><td className="space-x-3 whitespace-nowrap pr-4"><button onClick={() => openHistory(party)} className="text-brand-600 hover:underline">History</button><button onClick={() => startEdit(party)} className="text-gray-600 hover:underline">Edit</button></td></tr>)}</tbody>
          </table></div>
          {!parties.length && <p className="p-6 text-sm text-gray-500">No wholesale parties found.</p>}
        </section>
      </div>
      {history && <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3"><div><h2 className="text-sm font-semibold">{history.party.name} account history</h2><p className="text-xs text-gray-500">{history.party.phone} · {history.party.address}</p></div><button onClick={() => setHistory(null)} aria-label="Close history" className="px-2 py-1 text-lg text-gray-500">×</button></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Date / Invoice</th><th>Items</th><th>Gross sale</th><th>Payments</th><th>Returns</th><th>Due</th><th>Payment and return records</th></tr></thead><tbody>{history.invoices.map((invoice) => <tr key={invoice.id} className="border-t border-gray-100 align-top"><td className="px-4 py-3">{invoice.sale_date}<br /><span className="font-medium">{invoice.invoice_number}</span></td><td>{invoice.items.map((item) => <div key={item.id}>{item.product_name} × {item.quantity}</div>)}</td><td>{money(invoice.gross_amount)}</td><td>{money(invoice.total_payments)}</td><td>{money(invoice.return_amount)}</td><td className="font-semibold">{money(invoice.due_amount)}</td><td>{invoice.payments.map((payment) => <div key={`payment-${payment.id}`}>{payment.payment_date}: Bank {money(payment.bank_amount)}, bKash {money(payment.bkash_amount)}, Cash {money(payment.cash_amount)}</div>)}{invoice.return_history.map((entry) => <div key={`return-${entry.id}`}>{entry.return_date}: {entry.product_name} return × {entry.quantity}, {money(entry.amount)}{entry.notes ? ` · ${entry.notes}` : ""}</div>)}</td></tr>)}</tbody></table></div>
      </section>}
    </div>
  );
}