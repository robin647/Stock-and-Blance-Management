import { useEffect, useRef, useState } from "react";
import { easyWholesaleApi, productApi, showroomApi, wholesalePartyApi } from "../../api/endpoints";
import PartyCombobox from "../../components/PartyCombobox.jsx";

const today = new Date().toISOString().slice(0, 10);
const tabOptions = ["sales", "payments", "returns"];
const money = (amount) => `৳ ${Number(amount || 0).toLocaleString()}`;
const rowsOf = (response) => response.data.results || response.data;

function errorMessage(error, endpoint = "API request") {
  const body = error.response?.data;
  const statusCode = error.response?.status;
  if (!body) return `${endpoint}: request failed${statusCode ? ` (HTTP ${statusCode})` : ""}. Check the API URL and network connection.`;
  if (body.errors) return `${endpoint}: ${Object.values(body.errors).flat().join(" ")}`;
  const detail = typeof body === "string" ? body : body.detail || Object.values(body).flat().join(" ");
  if (statusCode === 404) {
    return `${endpoint}: endpoint not found (HTTP 404). Deploy the backend version containing the Easy Wholesale API routes.`;
  }
  if (statusCode === 401 || statusCode === 403) {
    return `${endpoint}: access denied (HTTP ${statusCode}). Sign in again with an Admin account.`;
  }
  if (statusCode >= 500) {
    return `${endpoint}: server error (HTTP ${statusCode}). Check backend logs and confirm database migrations have been applied. ${detail || ""}`;
  }
  return `${endpoint}: ${detail || "Request failed."}${statusCode ? ` (HTTP ${statusCode})` : ""}`;
}

export default function EasyWholesaleManagement() {
  const [tab, setTab] = useState("sales");
  const [products, setProducts] = useState([]);
  const [showrooms, setShowrooms] = useState([]);
  const [sales, setSales] = useState([]);
  const [payments, setPayments] = useState([]);
  const [returns, setReturns] = useState([]);
  const [historyPages, setHistoryPages] = useState({
    sales: { page: 1, count: 0, next: null, previous: null },
    payments: { page: 1, count: 0, next: null, previous: null },
    returns: { page: 1, count: 0, next: null, previous: null },
  });
  const [selectedPartyIds, setSelectedPartyIds] = useState({ sales: "", payments: "", returns: "" });
  const [sale, setSale] = useState({ party: "", sale_date: today, bill_number: "", product: "", product_name: "", quantity: "1", total_amount: "", stock_location: "", showroom: "", notes: "" });
  const [payment, setPayment] = useState({ party: "", payment_date: today, bank_amount: "0", bkash_amount: "0", cash_amount: "0", reference: "", notes: "" });
  const [returnForm, setReturnForm] = useState({ party: "", return_date: today, original_bill_number: "", easy_sale: "", product: "", product_name: "", quantity: "1", amount: "", stock_location: "", showroom: "", notes: "" });
  const [status, setStatus] = useState({ loading: true, saving: false, message: "", error: "" });
  const submissionRef = useRef({ fingerprint: "", key: "" });

  async function loadLists(pages = { sales: 1, payments: 1, returns: 1 }) {
    const requests = [
      { section: "sales", label: "Easy Sales API (/wholesale/easy/sales/)", request: easyWholesaleApi.sales.list({ page: pages.sales, page_size: 20 }) },
      { section: "payments", label: "Easy Payments API (/wholesale/easy/payments/)", request: easyWholesaleApi.payments.list({ page: pages.payments, page_size: 20 }) },
      { section: "returns", label: "Easy Returns API (/wholesale/easy/returns/)", request: easyWholesaleApi.returns.list({ page: pages.returns, page_size: 20 }) },
    ];
    const results = await Promise.allSettled(requests.map(({ request }) => request));
    const failures = [];
    results.forEach((result, index) => {
      const { section, label } = requests[index];
      if (result.status === "rejected") {
        failures.push(errorMessage(result.reason, label));
        return;
      }
      const { data } = result.value;
      setHistoryPages((current) => ({
        ...current,
        [section]: { page: pages[section], count: data.count, next: data.next, previous: data.previous },
      }));
      if (section === "sales") setSales(rowsOf(result.value));
      if (section === "payments") setPayments(rowsOf(result.value));
      if (section === "returns") setReturns(rowsOf(result.value));
    });
    if (failures.length) throw new Error(failures.join("\n"));
  }

  async function loadHistory(section, page) {
    try {
      const { data } = await easyWholesaleApi[section].list({ page, page_size: 20 });
      if (section === "sales") setSales(rowsOf({ data }));
      if (section === "payments") setPayments(rowsOf({ data }));
      if (section === "returns") setReturns(rowsOf({ data }));
      setHistoryPages((current) => ({ ...current, [section]: { page, count: data.count, next: data.next, previous: data.previous } }));
    } catch (error) {
      setStatus((current) => ({ ...current, error: errorMessage(error) }));
    }
  }

  useEffect(() => {
    const requests = [
      { label: "Products API (/products/)", request: productApi.list({ is_active: true, page_size: 200 }) },
      { label: "Showrooms API (/showrooms/)", request: showroomApi.list({ page_size: 200 }) },
      { label: "Wholesale transaction histories", request: loadLists() },
    ];
    Promise.allSettled(requests.map(({ request }) => request)).then((results) => {
      const failures = [];
      results.forEach((result, index) => {
        if (result.status === "rejected") {
          failures.push(result.reason.message?.includes(" API (")
            ? result.reason.message
            : errorMessage(result.reason, requests[index].label));
          return;
        }
        if (index === 0) setProducts(rowsOf(result.value));
        if (index === 1) setShowrooms(rowsOf(result.value));
      });
      setStatus((current) => ({ ...current, loading: false, error: failures.join("\n") }));
    });
  }, []);

  function updateParty(key, id) {
    setSelectedPartyIds((current) => ({ ...current, [key]: id }));
    if (key === "sales") setSale((current) => ({ ...current, party: id }));
    if (key === "payments") setPayment((current) => ({ ...current, party: id }));
    if (key === "returns") setReturnForm((current) => ({ ...current, party: id, easy_sale: "" }));
  }

  function updateReturnQuantity(quantity) {
    const linkedSale = sales.find((row) => String(row.id) === returnForm.easy_sale);
    const amount = linkedSale && Number(linkedSale.quantity) > 0
      ? (Number(linkedSale.total_amount) / Number(linkedSale.quantity) * Number(quantity || 0)).toFixed(2)
      : returnForm.amount;
    setReturnForm((current) => ({ ...current, quantity, amount }));
  }

  function requestKey(payload) {
    const fingerprint = JSON.stringify(payload);
    if (submissionRef.current.fingerprint !== fingerprint) {
      submissionRef.current = { fingerprint, key: window.crypto.randomUUID() };
    }
    return submissionRef.current.key;
  }

  async function submitSale(event) {
    event.preventDefault();
    if (status.saving) return;
    setStatus({ loading: false, saving: true, message: "", error: "" });
    try {
      const payload = {
        ...sale,
        party: Number(sale.party),
        product: sale.product ? Number(sale.product) : null,
        quantity: Number(sale.quantity),
        total_amount: sale.total_amount,
        stock_location: sale.product && sale.stock_location ? sale.stock_location : null,
        showroom: sale.product && sale.stock_location === "showroom" ? Number(sale.showroom) : null,
      };
      await easyWholesaleApi.sales.create(payload, requestKey(payload));
      submissionRef.current = { fingerprint: "", key: "" };
      setSale((current) => ({ ...current, bill_number: "", product: "", product_name: "", quantity: "1", total_amount: "", notes: "" }));
      setStatus({ loading: false, saving: false, message: "Sale saved successfully.", error: "" });
      try { await loadLists(); } catch { setStatus({ loading: false, saving: false, message: "Sale saved successfully.", error: "The history refresh failed. Reload the page to view the saved sale." }); }
    } catch (error) {
      setStatus({ loading: false, saving: false, message: "", error: errorMessage(error) });
    }
  }

  async function submitPayment(event) {
    event.preventDefault();
    if (status.saving) return;
    setStatus({ loading: false, saving: true, message: "", error: "" });
    try {
      const payload = { ...payment, party: Number(payment.party) };
      const key = requestKey(payload);
      await easyWholesaleApi.payments.create(payload, key);
      submissionRef.current = { fingerprint: "", key: "" };
      setPayment((current) => ({ ...current, bank_amount: "0", bkash_amount: "0", cash_amount: "0", reference: "", notes: "" }));
      setStatus({ loading: false, saving: false, message: "Payment saved successfully.", error: "" });
      try { await loadLists(); } catch { setStatus({ loading: false, saving: false, message: "Payment saved successfully.", error: "The history refresh failed. Reload the page to view the saved payment." }); }
    } catch (error) {
      setStatus({ loading: false, saving: false, message: "", error: errorMessage(error) });
    }
  }

  async function submitReturn(event) {
    event.preventDefault();
    if (status.saving) return;
    setStatus({ loading: false, saving: true, message: "", error: "" });
    try {
      const payload = {
        ...returnForm,
        party: Number(returnForm.party),
        easy_sale: returnForm.easy_sale ? Number(returnForm.easy_sale) : null,
        product: returnForm.product ? Number(returnForm.product) : null,
        quantity: Number(returnForm.quantity),
        amount: returnForm.amount,
        stock_location: returnForm.easy_sale ? null : returnForm.stock_location || null,
        showroom: !returnForm.easy_sale && returnForm.stock_location === "showroom" ? Number(returnForm.showroom) : null,
      };
      await easyWholesaleApi.returns.create(payload, requestKey(payload));
      submissionRef.current = { fingerprint: "", key: "" };
      setReturnForm((current) => ({ ...current, original_bill_number: "", easy_sale: "", product: "", product_name: "", quantity: "1", amount: "", stock_location: "", showroom: "", notes: "" }));
      setStatus({ loading: false, saving: false, message: "Return saved successfully.", error: "" });
      try { await loadLists(); } catch { setStatus({ loading: false, saving: false, message: "Return saved successfully.", error: "The history refresh failed. Reload the page to view the saved return." }); }
    } catch (error) {
      setStatus({ loading: false, saving: false, message: "", error: errorMessage(error) });
    }
  }

  const paymentTotal = Number(payment.bank_amount || 0) + Number(payment.bkash_amount || 0) + Number(payment.cash_amount || 0);
  const partyEasySales = sales.filter((row) => String(row.party) === returnForm.party);

  return (
    <div className="space-y-5">
      <header><h1 className="text-lg font-semibold">Easy Wholesale Sales Management</h1><p className="mt-1 text-sm text-gray-500">Quick party sales, separate dated payments, and returns. Existing Wholesale Sales remains a separate workflow.</p></header>
      <nav className="flex gap-2 border-b border-gray-200" aria-label="Easy wholesale transaction types">{tabOptions.map((option) => <button key={option} onClick={() => { setTab(option); setStatus((current) => ({ ...current, message: "", error: "" })); }} className={`border-b-2 px-4 py-2 text-sm capitalize ${tab === option ? "border-brand-500 font-semibold text-brand-700" : "border-transparent text-gray-600"}`}>{option}</button>)}</nav>
      {status.message && <div role="status" className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">{status.message}</div>}
      {status.error && <div role="alert" className="whitespace-pre-line rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{status.error}</div>}
      {status.loading ? <p className="py-10 text-center text-sm text-gray-500">Loading easy wholesale records...</p> : <>
        {tab === "sales" && <>
          <form onSubmit={submitSale} className="grid gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
            <PartyCombobox value={selectedPartyIds.sales} onChange={(id) => updateParty("sales", id)} label="Party Name" />
            <label className="text-xs text-gray-500">Sale Date<input required type="date" value={sale.sale_date} onChange={(event) => setSale({ ...sale, sale_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500">Bill No / Cash Memo No<input value={sale.bill_number} onChange={(event) => setSale({ ...sale, bill_number: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500">Catalog Product (optional)<select value={sale.product} onChange={(event) => { const product = products.find((row) => String(row.id) === event.target.value); setSale({ ...sale, product: event.target.value, product_name: product?.name || sale.product_name, stock_location: "", showroom: "" }); }} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">No catalog product</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}{product.size ? ` · ${product.size}` : ""}</option>)}</select></label>
            <label className="text-xs text-gray-500">Product Name (optional)<input value={sale.product_name} onChange={(event) => setSale({ ...sale, product_name: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            {sale.product && <label className="text-xs text-gray-500">Stock movement (optional)<select value={sale.stock_location} onChange={(event) => setSale({ ...sale, stock_location: event.target.value, showroom: "" })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Do not change stock</option><option value="factory">Deduct factory stock</option><option value="showroom">Deduct showroom stock</option></select></label>}
            {sale.product && sale.stock_location === "showroom" && <label className="text-xs text-gray-500">Showroom<select required value={sale.showroom} onChange={(event) => setSale({ ...sale, showroom: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Select showroom</option>{showrooms.map((showroom) => <option key={showroom.id} value={showroom.id}>{showroom.name}</option>)}</select></label>}
            <label className="text-xs text-gray-500">Product Quantity<input required min="1" type="number" value={sale.quantity} onChange={(event) => setSale({ ...sale, quantity: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500">Total Sales Amount<input required min="0" step="0.01" type="number" value={sale.total_amount} onChange={(event) => setSale({ ...sale, total_amount: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500 sm:col-span-2 lg:col-span-4">Notes<input value={sale.notes} onChange={(event) => setSale({ ...sale, notes: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <button disabled={status.saving || !sale.party} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{status.saving ? "Saving..." : "Save Easy Sale"}</button>
          </form>
          <TransactionHistory title="Sales History" empty="No easy sales saved yet." rows={sales} pageInfo={historyPages.sales} onPageChange={(page) => loadHistory("sales", page)} columns={[["Sale Date", (row) => row.sale_date], ["Party", (row) => row.party_name], ["Bill No", (row) => row.bill_number || "—"], ["Product", (row) => row.product_label || "—"], ["Quantity", (row) => `${row.quantity} pcs`], ["Sales Amount", (row) => money(row.total_amount)], ["Inventory", (row) => row.stock_location === "factory" ? "Factory" : row.stock_location === "showroom" ? "Showroom" : "No movement"]]} />
        </>}
        {tab === "payments" && <>
          <form onSubmit={submitPayment} className="grid gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
            <PartyCombobox value={selectedPartyIds.payments} onChange={(id) => updateParty("payments", id)} label="Party Name" />
            <label className="text-xs text-gray-500">Payment Date<input required type="date" value={payment.payment_date} onChange={(event) => setPayment({ ...payment, payment_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            {[ ["bank_amount", "Bank Payment"], ["bkash_amount", "bKash Payment"], ["cash_amount", "Cash Payment"] ].map(([key, label]) => <label key={key} className="text-xs text-gray-500">{label}<input min="0" step="0.01" type="number" value={payment[key]} onChange={(event) => setPayment({ ...payment, [key]: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>)}
            <label className="text-xs text-gray-500">Total Payment<input readOnly value={money(paymentTotal)} className="mt-1 w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm font-semibold text-gray-900" /></label>
            <label className="text-xs text-gray-500">Payment Reference<input value={payment.reference} onChange={(event) => setPayment({ ...payment, reference: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500 sm:col-span-2">Notes<input value={payment.notes} onChange={(event) => setPayment({ ...payment, notes: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <button disabled={status.saving || !payment.party || paymentTotal <= 0} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{status.saving ? "Saving..." : "Save Payment"}</button>
          </form>
          <TransactionHistory title="Payment History" empty="No easy payments saved yet." rows={payments} pageInfo={historyPages.payments} onPageChange={(page) => loadHistory("payments", page)} columns={[["Payment Date", (row) => row.payment_date], ["Party", (row) => row.party_name], ["Bank", (row) => money(row.bank_amount)], ["bKash", (row) => money(row.bkash_amount)], ["Cash", (row) => money(row.cash_amount)], ["Total Payment", (row) => money(row.total_amount)], ["Reference", (row) => row.reference || "—"]]} />
        </>}
        {tab === "returns" && <>
          <form onSubmit={submitReturn} className="grid gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
            <PartyCombobox value={selectedPartyIds.returns} onChange={(id) => updateParty("returns", id)} label="Party Name" />
            <label className="text-xs text-gray-500">Return Date<input required type="date" value={returnForm.return_date} onChange={(event) => setReturnForm({ ...returnForm, return_date: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500">Original Easy Sale (optional)<select value={returnForm.easy_sale} onChange={(event) => { const selected = partyEasySales.find((row) => String(row.id) === event.target.value); const unitAmount = selected && Number(selected.quantity) ? Number(selected.total_amount) / Number(selected.quantity) : 0; setReturnForm({ ...returnForm, easy_sale: event.target.value, original_bill_number: selected?.bill_number || "", product: selected?.product ? String(selected.product) : "", product_name: selected?.product_label || "", stock_location: "", showroom: "", amount: selected ? unitAmount.toFixed(2) : "" }); }} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Financial-only return</option>{partyEasySales.map((row) => <option key={row.id} value={row.id}>{row.bill_number || `Sale ${row.id}`} · {row.sale_date} · {row.product_label || "No product"} · {row.quantity} pcs · {money(row.total_amount)}</option>)}</select></label>
            <label className="text-xs text-gray-500">Original Bill No<input value={returnForm.original_bill_number} onChange={(event) => setReturnForm({ ...returnForm, original_bill_number: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500">Product Name (optional)<input value={returnForm.product_name} onChange={(event) => setReturnForm({ ...returnForm, product_name: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            {!returnForm.easy_sale && <label className="text-xs text-gray-500">Physical Product (optional)<select value={returnForm.product} onChange={(event) => { const product = products.find((row) => String(row.id) === event.target.value); setReturnForm({ ...returnForm, product: event.target.value, product_name: product?.name || returnForm.product_name, stock_location: "", showroom: "" }); }} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">No stock adjustment</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}{product.size ? ` · ${product.size}` : ""}</option>)}</select></label>}
            {!returnForm.easy_sale && returnForm.product && <label className="text-xs text-gray-500">Restore Physical Stock To<select value={returnForm.stock_location} onChange={(event) => setReturnForm({ ...returnForm, stock_location: event.target.value, showroom: "" })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Do not change stock</option><option value="factory">Factory</option><option value="showroom">Showroom</option></select></label>}
            <label className="text-xs text-gray-500">Return Product Quantity<input required min="1" type="number" value={returnForm.quantity} onChange={(event) => updateReturnQuantity(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            {returnForm.stock_location === "showroom" && !returnForm.easy_sale && <label className="text-xs text-gray-500">Showroom<select required value={returnForm.showroom} onChange={(event) => setReturnForm({ ...returnForm, showroom: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"><option value="">Select showroom</option>{showrooms.map((showroom) => <option key={showroom.id} value={showroom.id}>{showroom.name}</option>)}</select></label>}
            <label className="text-xs text-gray-500">Return Amount<input required min="0" step="0.01" type="number" value={returnForm.amount} onChange={(event) => setReturnForm({ ...returnForm, amount: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <label className="text-xs text-gray-500 sm:col-span-2">Return Reason / Notes<input value={returnForm.notes} onChange={(event) => setReturnForm({ ...returnForm, notes: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" /></label>
            <button disabled={status.saving || !returnForm.party} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{status.saving ? "Saving..." : "Save Return"}</button>
          </form>
          <TransactionHistory title="Return History" empty="No easy returns saved yet." rows={returns} pageInfo={historyPages.returns} onPageChange={(page) => loadHistory("returns", page)} columns={[["Return Date", (row) => row.return_date], ["Party", (row) => row.party_name], ["Bill No", (row) => row.original_bill_number || "—"], ["Product", (row) => row.product_label || "—"], ["Quantity", (row) => `${row.quantity} pcs`], ["Return Amount", (row) => money(row.amount)], ["Notes", (row) => row.notes || "—"]]} />
        </>}
      </>}
    </div>
  );
}

function TransactionHistory({ title, empty, rows, columns, pageInfo, onPageChange }) {
  return <section className="overflow-hidden rounded-xl border border-gray-200 bg-white"><h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold">{title}</h2>{!rows.length ? <p className="px-4 py-7 text-center text-sm text-gray-500">{empty}</p> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr>{columns.map(([label]) => <th key={label} className="px-4 py-3">{label}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.id} className="border-t border-gray-100">{columns.map(([label, render], index) => <td key={label} className={index === 0 ? "whitespace-nowrap px-4 py-3" : "py-3"}>{render(row)}</td>)}</tr>)}</tbody></table></div>}<div className="flex items-center justify-between border-t border-gray-100 px-4 py-3 text-sm text-gray-600"><span>{pageInfo.count} records · Page {pageInfo.page} of {Math.max(1, Math.ceil(pageInfo.count / 20))}</span><div className="flex gap-2"><button disabled={!pageInfo.previous} onClick={() => onPageChange(pageInfo.page - 1)} className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Previous</button><button disabled={!pageInfo.next} onClick={() => onPageChange(pageInfo.page + 1)} className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Next</button></div></div></section>;
}