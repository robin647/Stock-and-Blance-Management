import { useEffect, useState } from "react";
import { productApi, factoryStockApi, showroomApi, showroomStockApi, stockAdjustmentApi } from "../../api/endpoints";

const listData = (response) => response.data.results || response.data;

export default function StockAdjustments() {
  const [products, setProducts] = useState([]);
  const [showrooms, setShowrooms] = useState([]);
  const [stocks, setStocks] = useState({});
  const [history, setHistory] = useState([]);
  const [form, setForm] = useState({ product: "", location: "factory", showroom: "", new_quantity: "", reason: "" });
  const [message, setMessage] = useState("");

  async function load() {
    const [productRes, factoryRes, showroomRes, showroomStockRes, historyRes] = await Promise.all([
      productApi.list({ page_size: 200 }), factoryStockApi.list({ page_size: 200 }), showroomApi.list({ page_size: 200 }), showroomStockApi.list({ page_size: 200 }), stockAdjustmentApi.list({ page_size: 200 }),
    ]);
    const productRows = listData(productRes);
    const showroomRows = listData(showroomRes);
    const stockRows = {};
    listData(factoryRes).forEach((row) => { stockRows[`factory-${row.product}`] = row.quantity; });
    listData(showroomStockRes).forEach((row) => { stockRows[`showroom-${row.showroom}-${row.product}`] = row.quantity; });
    setProducts(productRows);
    setShowrooms(showroomRows);
    setStocks(stockRows);
    setHistory(listData(historyRes));
    setForm((current) => ({ ...current, product: current.product || String(productRows[0]?.id || ""), showroom: current.showroom || String(showroomRows[0]?.id || "") }));
  }

  useEffect(() => { load().catch(() => setMessage("Could not load stock data.")); }, []);

  const stockKey = form.location === "factory" ? `factory-${form.product}` : `showroom-${form.showroom}-${form.product}`;
  const currentQuantity = stocks[stockKey] ?? 0;

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    try {
      await stockAdjustmentApi.create({
        ...form,
        product: Number(form.product),
        showroom: form.location === "showroom" ? Number(form.showroom) : null,
        new_quantity: Number(form.new_quantity),
      });
      setMessage("Stock updated and adjustment recorded.");
      setForm((current) => ({ ...current, new_quantity: "", reason: "" }));
      await load();
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not adjust stock. Check the selected location and values.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Product Stock Adjustment</h1>
        <p className="text-sm text-gray-500 mt-1">Choose one inventory location. Other showrooms remain unchanged.</p>
      </div>
      <form onSubmit={submit} className="grid gap-4 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-3">
        <label className="text-sm text-gray-600">Product
          <select required value={form.product} onChange={(event) => setForm({ ...form, product: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900">
            {products.map((product) => <option key={product.id} value={product.id}>{product.name}{product.code ? ` · ${product.code}` : ""}{product.size ? ` · ${product.size}` : ""}</option>)}
          </select>
        </label>
        <label className="text-sm text-gray-600">Inventory location
          <select value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900">
            <option value="factory">Factory stock</option><option value="showroom">Showroom stock</option>
          </select>
        </label>
        {form.location === "showroom" && <label className="text-sm text-gray-600">Showroom
          <select required value={form.showroom} onChange={(event) => setForm({ ...form, showroom: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900">
            {showrooms.map((showroom) => <option key={showroom.id} value={showroom.id}>{showroom.name}</option>)}
          </select>
        </label>}
        <div className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-600">Current quantity <strong className="ml-2 text-gray-900">{currentQuantity} pcs</strong></div>
        <label className="text-sm text-gray-600">New quantity
          <input required type="number" min="0" step="1" value={form.new_quantity} onChange={(event) => setForm({ ...form, new_quantity: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900" />
        </label>
        <label className="text-sm text-gray-600 sm:col-span-2 lg:col-span-3">Reason
          <input required value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} placeholder="e.g. Physical inventory count" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900" />
        </label>
        <div className="flex items-center gap-4 sm:col-span-2 lg:col-span-3">
          <button className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600">Save adjustment</button>
          {form.new_quantity !== "" && <span className="text-sm text-gray-600">Updated: <strong className="text-gray-900">{form.new_quantity} pcs</strong> ({Number(form.new_quantity) - currentQuantity >= 0 ? "+" : ""}{Number(form.new_quantity) - currentQuantity})</span>}
          {message && <span role="status" className="text-sm text-gray-600">{message}</span>}
        </div>
      </form>
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold">Adjustment history</h2>
        <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Date</th><th>Product</th><th>Location</th><th>Previous</th><th>Updated</th><th>Change</th><th>Reason</th><th>User</th></tr></thead>
          <tbody>{history.map((row) => <tr key={row.id} className="border-t border-gray-100"><td className="px-4 py-3">{new Date(row.created_at).toLocaleString()}</td><td>{row.product_name}</td><td>{row.location === "factory" ? "Factory" : row.showroom_name}</td><td>{row.previous_quantity}</td><td>{row.new_quantity}</td><td>{row.difference > 0 ? `+${row.difference}` : row.difference}</td><td>{row.reason}</td><td>{row.created_by_name}</td></tr>)}</tbody>
        </table></div>
      </section>
    </div>
  );
}