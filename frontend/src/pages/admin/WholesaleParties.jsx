import { useEffect, useRef, useState } from "react";
import { productApi, wholesaleInvoiceApi, wholesalePartyApi, wholesalePaymentApi } from "../../api/endpoints";
import PartyCombobox from "../../components/PartyCombobox.jsx";

const blankForm = { name: "", contact_person: "", phone: "", address: "", business_name: "", notes: "", is_active: true };
const today = new Date().toISOString().slice(0, 10);
const money = (amount) => `৳ ${Number(amount || 0).toLocaleString()}`;

export default function WholesaleParties() {
  const [parties, setParties] = useState([]);
  const [partyLoading, setPartyLoading] = useState(true);
  const [partyPage, setPartyPage] = useState({ count: 0, next: null, previous: null });
  const [partySearchInput, setPartySearchInput] = useState("");
  const [partySearch, setPartySearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("true");
  const [partyPageNumber, setPartyPageNumber] = useState(1);
  const [selectedParty, setSelectedParty] = useState(null);
  const [statement, setStatement] = useState(null);
  const [statementLoading, setStatementLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [invoiceOptions, setInvoiceOptions] = useState([]);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState(blankForm);
  const [editingId, setEditingId] = useState(null);
  const [formError, setFormError] = useState("");
  const [message, setMessage] = useState("");
  const [draftFilters, setDraftFilters] = useState({ start_date: "", end_date: "", transaction_type: "", invoice_number: "", product: "" });
  const [appliedFilters, setAppliedFilters] = useState(draftFilters);
  const [statementPage, setStatementPage] = useState(1);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const paymentKeyRef = useRef({ payload: "", key: "" });
  const [payment, setPayment] = useState({ invoice: "", payment_date: today, bank_amount: "0", bkash_amount: "0", cash_amount: "0", reference: "", notes: "" });

  useEffect(() => {
    const timer = window.setTimeout(() => setPartySearch(partySearchInput.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [partySearchInput]);

  useEffect(() => {
    let cancelled = false;
    setPartyLoading(true);
    wholesalePartyApi.list({ search: partySearch, ...(activeFilter ? { is_active: activeFilter } : {}), page: partyPageNumber, page_size: 12 })
      .then(({ data }) => {
        if (!cancelled) {
          setParties(data.results || data);
          setPartyPage({ count: data.count ?? (data.results || data).length, next: data.next, previous: data.previous });
        }
      })
      .catch(() => { if (!cancelled) setMessage("Could not load parties."); })
      .finally(() => { if (!cancelled) setPartyLoading(false); });
    return () => { cancelled = true; };
  }, [partySearch, activeFilter, partyPageNumber]);

  useEffect(() => {
    productApi.list({ is_active: true, page_size: 200 }).then(({ data }) => setProducts(data.results || data)).catch(() => {});
  }, []);

  async function loadStatement(page = 1) {
    if (!selectedParty) return;
    setStatementLoading(true);
    try {
      const params = { ...appliedFilters, page, page_size: 20 };
      Object.keys(params).forEach((key) => { if (!params[key]) delete params[key]; });
      const { data } = await wholesalePartyApi.history(selectedParty.id, params);
      setStatement(data);
      setStatementPage(page);
    } catch {
      setMessage("Could not load the selected party statement.");
    } finally {
      setStatementLoading(false);
    }
  }

  useEffect(() => { loadStatement(1); }, [selectedParty, appliedFilters]);

  async function openParty(party) {
    setSelectedParty(party);
    setStatementPage(1);
    setPaymentOpen(false);
  }

  function startEdit(party) {
    setEditingId(party.id);
    setForm({ name: party.name, contact_person: party.contact_person || "", phone: party.phone, address: party.address, business_name: party.business_name, notes: party.notes, is_active: party.is_active });
    setFormError("");
    setFormOpen(true);
  }

  async function saveParty(event) {
    event.preventDefault();
    setFormError("");
    try {
      const response = editingId ? await wholesalePartyApi.update(editingId, form) : await wholesalePartyApi.create(form);
      const savedParty = response.data;
      setForm(blankForm);
      setEditingId(null);
      setFormOpen(false);
      setMessage(editingId ? "Party details updated." : "Party added.");
      setPartyPageNumber(1);
      if (!editingId) {
        setSelectedParty(savedParty);
        setPartySearchInput("");
        setPartySearch("");
      } else if (selectedParty?.id === savedParty.id) {
        setSelectedParty(savedParty);
      }
    } catch (error) {
      const errors = error.response?.data;
      setFormError(errors?.name?.[0] || errors?.detail || "Could not save party information.");
    }
  }

  async function beginPayment() {
    setPaymentOpen(true);
    paymentKeyRef.current = { payload: "", key: "" };
    setPayment({ invoice: "", payment_date: today, bank_amount: "0", bkash_amount: "0", cash_amount: "0", reference: "", notes: "" });
    try {
      const { data } = await wholesaleInvoiceApi.list({ party: selectedParty.id, page_size: 200, ordering: "sale_date" });
      setInvoiceOptions((data.results || data).filter((invoice) => Number(invoice.due_amount) > 0));
    } catch {
      setMessage("Could not load invoices for payment allocation.");
    }
  }

  async function savePayment(event) {
    event.preventDefault();
    if (paymentBusy) return;
    setPaymentBusy(true);
    setMessage("");
    try {
      const payload = { ...payment, invoice: Number(payment.invoice), bank_amount: Number(payment.bank_amount), bkash_amount: Number(payment.bkash_amount), cash_amount: Number(payment.cash_amount) };
      const fingerprint = JSON.stringify(payload);
      if (paymentKeyRef.current.payload !== fingerprint) {
        paymentKeyRef.current = { payload: fingerprint, key: window.crypto.randomUUID() };
      }
      await wholesalePaymentApi.create(payload, paymentKeyRef.current.key);
      paymentKeyRef.current = { payload: "", key: "" };
      setPaymentOpen(false);
      setMessage("Payment recorded on its payment date and allocated to the selected invoice.");
      await loadStatement(1);
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not record payment. Check the invoice due and amounts.");
    } finally {
      setPaymentBusy(false);
    }
  }

  const summary = statement?.summary;
  const totalPages = Math.max(1, Math.ceil((statement?.count || 0) / 20));

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-lg font-semibold">Wholesale Party Management</h1><p className="mt-1 text-sm text-gray-500">Party records and date-wise account statements</p></div>
        <button onClick={() => { setEditingId(null); setForm(blankForm); setFormError(""); setFormOpen(true); }} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white">Add New Party</button>
      </header>

      {message && <div role="status" className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700"><span>{message}</span><button onClick={() => setMessage("")} aria-label="Dismiss message" className="px-2 text-lg text-gray-500">×</button></div>}

      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3"><div><h2 className="text-sm font-semibold">All Parties</h2><p className="mt-0.5 text-xs text-gray-500">{partyPage.count} records</p></div><div className="flex flex-wrap gap-2"><input value={partySearchInput} onChange={(event) => { setPartyPageNumber(1); setPartySearchInput(event.target.value); }} placeholder="Search name or phone" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" /><select value={activeFilter} onChange={(event) => { setPartyPageNumber(1); setActiveFilter(event.target.value); }} aria-label="Party status" className="rounded-lg border border-gray-300 px-3 py-2 text-sm"><option value="true">Active</option><option value="false">Inactive</option><option value="">All statuses</option></select></div></div>
        {partyLoading ? <p className="px-4 py-8 text-center text-sm text-gray-500">Loading parties...</p> : !parties.length ? <p className="px-4 py-8 text-center text-sm text-gray-500">No parties match the current search.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Party Name</th><th>Phone</th><th>Net Sales</th><th>Payments</th><th>Returns</th><th>Due</th><th>Actions</th></tr></thead><tbody>{parties.map((party) => <tr key={party.id} className={`border-t border-gray-100 ${selectedParty?.id === party.id ? "bg-gray-50" : ""}`}><td className="px-4 py-3 font-medium">{party.name}<span className="ml-2 text-xs font-normal text-gray-500">{party.is_active ? "Active" : "Inactive"}</span></td><td>{party.phone || "—"}</td><td>{money(party.total_sales)}</td><td>{money(party.total_payments)}</td><td>{money(party.total_returns)}</td><td className="font-semibold">{money(party.total_due)}</td><td className="space-x-3 whitespace-nowrap pr-4"><button onClick={() => openParty(party)} className="text-brand-600 hover:underline">View Details</button><button onClick={() => startEdit(party)} className="text-gray-600 hover:underline">Edit</button></td></tr>)}</tbody></table></div>}
        <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3 text-sm text-gray-600"><span>Page {partyPageNumber} of {Math.max(1, Math.ceil(partyPage.count / 12))}</span><div className="flex gap-2"><button disabled={!partyPage.previous} onClick={() => setPartyPageNumber((page) => Math.max(1, page - 1))} className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Previous</button><button disabled={!partyPage.next} onClick={() => setPartyPageNumber((page) => page + 1)} className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Next</button></div></div>
      </section>

      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-4"><div><h2 className="text-sm font-semibold">Selected Party — Detailed Account Statement</h2><p className="mt-1 text-xs text-gray-500">Sales, payments, and returns are listed on their actual transaction dates.</p></div>{selectedParty && <div className="flex gap-2"><button onClick={() => wholesalePartyApi.exportStatement(selectedParty.id, appliedFilters).catch(() => setMessage("Could not export the selected party statement."))} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">Export Excel</button><button onClick={beginPayment} className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium">Add Payment</button></div>}</div>
        <div className="space-y-4 p-4">
          <div className="max-w-xl"><PartyCombobox value={selectedParty?.id || ""} onChange={(id, party) => { setSelectedParty(party || null); setStatementPage(1); }} label="Search or select a party" /></div>
          {!selectedParty ? <p className="rounded-lg bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">Select a party to view its account statement.</p> : <>
            <div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-medium">{selectedParty.name}</h3><p className="text-xs text-gray-500">{selectedParty.contact_person ? `${selectedParty.contact_person} · ` : ""}{selectedParty.phone || "No phone"}</p></div><div className="text-sm text-gray-600">Opening balance: <strong>{money(statement?.opening_balance)}</strong> · Closing due: <strong>{money(summary?.outstanding_due)}</strong>{Number(summary?.credit_balance) > 0 && <> · Credit: <strong>{money(summary.credit_balance)}</strong></>}</div></div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-5">{[["Product Quantity Sold", summary?.total_quantity_sold, false], ["Gross Sales", summary?.gross_sales, true], ["Return Quantity", summary?.return_quantity, false], ["Return Amount", summary?.return_amount, true], ["Net Sales", summary?.net_sales, true], ["Bank Payments", summary?.bank_payments, true], ["bKash Payments", summary?.bkash_payments, true], ["Cash Payments", summary?.cash_payments, true], ["Total Payments", summary?.total_payments, true], ["Outstanding Due", summary?.outstanding_due, true]].map(([label, value, currency]) => <div key={label} className="border-l-2 border-brand-500 bg-gray-50 px-3 py-2"><div className="text-[11px] text-gray-500">{label}</div><div className="mt-1 text-sm font-semibold">{currency ? money(value) : Number(value || 0).toLocaleString()}</div></div>)}</div>
            <form onSubmit={(event) => { event.preventDefault(); setStatementPage(1); setAppliedFilters({ ...draftFilters }); }} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
              <label className="text-xs text-gray-500">Start Date<input type="date" value={draftFilters.start_date} onChange={(event) => setDraftFilters({ ...draftFilters, start_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-2 text-sm text-gray-900" /></label>
              <label className="text-xs text-gray-500">End Date<input type="date" value={draftFilters.end_date} onChange={(event) => setDraftFilters({ ...draftFilters, end_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-2 text-sm text-gray-900" /></label>
              <label className="text-xs text-gray-500">Transaction Type<select value={draftFilters.transaction_type} onChange={(event) => setDraftFilters({ ...draftFilters, transaction_type: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-2 text-sm text-gray-900"><option value="">All</option><option value="sale">Sale</option><option value="payment">Payment</option><option value="return">Return</option></select></label>
              <label className="text-xs text-gray-500">Cash Memo / Bill<input value={draftFilters.invoice_number} onChange={(event) => setDraftFilters({ ...draftFilters, invoice_number: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-2 text-sm text-gray-900" /></label>
              <label className="text-xs text-gray-500">Product<select value={draftFilters.product} onChange={(event) => setDraftFilters({ ...draftFilters, product: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-2 text-sm text-gray-900"><option value="">All products</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}{product.size ? ` · ${product.size}` : ""}</option>)}</select></label>
              <div className="flex items-end gap-2"><button className="flex-1 rounded-lg bg-brand-500 px-3 py-2 text-sm font-medium text-white">Apply Filter</button><button type="button" onClick={() => { const empty = { start_date: "", end_date: "", transaction_type: "", invoice_number: "", product: "" }; setDraftFilters(empty); setAppliedFilters(empty); setStatementPage(1); }} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">Reset</button></div>
            </form>
            <p className="text-xs text-gray-500">Running balance uses debit-positive convention: sales increase the balance; payments and accepted returns reduce it. Negative balances are customer credit.</p>
            {statementLoading ? <p className="py-8 text-center text-sm text-gray-500">Loading account statement...</p> : !statement?.results?.length ? <p className="py-8 text-center text-sm text-gray-500">No transactions match this date range and filters.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[1320px] text-left text-xs"><thead className="bg-gray-50 text-[11px] uppercase text-gray-500"><tr><th className="px-3 py-3">Transaction Date</th><th>Type</th><th>Cash Memo / Bill</th><th>Product Qty</th><th>Gross Sale</th><th>Bank</th><th>bKash</th><th>Cash</th><th>Total Payment</th><th>Return Qty</th><th>Return Amount</th><th>Net Transaction</th><th>Running Balance</th><th>Payment Reference</th><th>Notes</th></tr></thead><tbody>{statement.results.map((row) => <tr key={`${row.type}-${row.id}`} className="border-t border-gray-100"><td className="whitespace-nowrap px-3 py-3">{row.date}</td><td className="capitalize">{row.type}</td><td>{row.invoice_number}</td><td>{row.quantity || "—"}</td><td>{Number(row.gross_sale) ? money(row.gross_sale) : "—"}</td><td>{Number(row.bank_payment) ? money(row.bank_payment) : "—"}</td><td>{Number(row.bkash_payment) ? money(row.bkash_payment) : "—"}</td><td>{Number(row.cash_payment) ? money(row.cash_payment) : "—"}</td><td>{Number(row.total_payment) ? money(row.total_payment) : "—"}</td><td>{row.return_quantity || "—"}</td><td>{Number(row.return_amount) ? money(row.return_amount) : "—"}</td><td>{money(row.net_amount)}</td><td className="font-semibold">{money(row.running_balance)}</td><td>{row.reference || "—"}</td><td>{row.notes || "—"}</td></tr>)}</tbody></table></div>}
            <div className="flex items-center justify-between text-sm text-gray-600"><span>{statement?.count || 0} transactions · Opening {money(statement?.opening_balance)} · Closing {money(statement?.closing_balance)}</span><div className="flex gap-2"><button disabled={statementPage <= 1 || statementLoading} onClick={() => loadStatement(statementPage - 1)} className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Previous</button><button disabled={statementPage >= totalPages || statementLoading} onClick={() => loadStatement(statementPage + 1)} className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Next</button></div></div>
          </>}
        </div>
      </section>

      {paymentOpen && selectedParty && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation"><form onSubmit={savePayment} className="max-h-[90vh] w-full max-w-lg space-y-3 overflow-y-auto rounded-xl bg-white p-5 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="payment-title"><div className="flex items-start justify-between"><div><h2 id="payment-title" className="text-base font-semibold">Add Payment</h2><p className="mt-1 text-sm text-gray-500">{selectedParty.name}. Allocate to one invoice with an outstanding balance.</p></div><button type="button" aria-label="Close payment form" onClick={() => setPaymentOpen(false)} className="px-2 text-lg text-gray-500">×</button></div>
        <label className="block text-xs text-gray-500">Invoice<select required value={payment.invoice} onChange={(event) => setPayment({ ...payment, invoice: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Select invoice</option>{invoiceOptions.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {invoice.sale_date} · due {money(invoice.due_amount)}</option>)}</select></label>
        <label className="block text-xs text-gray-500">Payment Date<input required type="date" value={payment.payment_date} onChange={(event) => setPayment({ ...payment, payment_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <div className="grid grid-cols-3 gap-2">{[["bank_amount", "Bank Payment"], ["bkash_amount", "bKash Payment"], ["cash_amount", "Cash Payment"]].map(([key, label]) => <label key={key} className="text-xs text-gray-500">{label}<input required type="number" min="0" step="0.01" value={payment[key]} onChange={(event) => setPayment({ ...payment, [key]: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-2 text-sm text-gray-900" /></label>)}</div>
        <label className="block text-xs text-gray-500">Payment Reference / Transaction ID<input value={payment.reference} onChange={(event) => setPayment({ ...payment, reference: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label><label className="block text-xs text-gray-500">Notes<textarea value={payment.notes} onChange={(event) => setPayment({ ...payment, notes: event.target.value })} rows="2" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <div className="flex justify-end gap-2"><button type="button" onClick={() => setPaymentOpen(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm">Cancel</button><button disabled={paymentBusy} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{paymentBusy ? "Saving..." : "Save Payment"}</button></div>
      </form></div>}

      {formOpen && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation"><form onSubmit={saveParty} className="max-h-[90vh] w-full max-w-lg space-y-3 overflow-y-auto rounded-xl bg-white p-5 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="party-form-title"><div className="flex items-start justify-between"><div><h2 id="party-form-title" className="text-base font-semibold">{editingId ? "Edit Party" : "Add New Party"}</h2><p className="mt-1 text-sm text-gray-500">A saved party is immediately available in the search and sales selectors.</p></div><button type="button" aria-label="Close party form" onClick={() => setFormOpen(false)} className="px-2 text-lg text-gray-500">×</button></div>
        <label className="block text-xs text-gray-500">Party / Business Name<input required autoFocus value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <label className="block text-xs text-gray-500">Contact Person (optional)<input value={form.contact_person} onChange={(event) => setForm({ ...form, contact_person: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <label className="block text-xs text-gray-500">Phone Number<input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <label className="block text-xs text-gray-500">Business Address<textarea value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} rows="2" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <label className="block text-xs text-gray-500">Notes<textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} rows="2" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
        <label className="flex items-center gap-2 text-sm text-gray-700"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /> Active</label>
        {formError && <p role="alert" className="text-sm text-red-600">{formError}</p>}
        <div className="flex justify-end gap-2"><button type="button" onClick={() => setFormOpen(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm">Cancel</button><button className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white">{editingId ? "Save Changes" : "Save Party"}</button></div>
      </form></div>}
    </div>
  );
}