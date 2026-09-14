import { useEffect, useState } from "react";
import { categoryApi, factoryStockApi, productApi, showroomApi, showroomStockApi } from "../../api/endpoints";

export default function Products() {
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [newCategory, setNewCategory] = useState("");
  const [factoryStock, setFactoryStock] = useState({});
  const [showroomStock, setShowroomStock] = useState({});
  const [showrooms, setShowrooms] = useState([]);
  const [form, setForm] = useState({ name: "", category: "", size: "", selling_price: "", initial_stock: "" });
  const [error, setError] = useState("");

  function loadAll() {
    categoryApi.list().then((res) => setCategories(res.data.results || res.data));
    productApi.list().then((res) => setProducts(res.data.results || res.data));
    factoryStockApi.list().then((res) => {
      const stocks = {};
      (res.data.results || res.data).forEach((stock) => { stocks[stock.product] = stock.quantity; });
      setFactoryStock(stocks);
    });
    showroomApi.list().then((res) => setShowrooms(res.data.results || res.data));
    showroomStockApi.list().then((res) => {
      const stocks = {};
      (res.data.results || res.data).forEach((stock) => {
        stocks[`${stock.product}-${stock.showroom}`] = stock.quantity;
      });
      setShowroomStock(stocks);
    });
  }

  useEffect(loadAll, []);

  async function handleAddCategory(e) {
    e.preventDefault();
    if (!newCategory.trim()) return;
    await categoryApi.create({ name: newCategory });
    setNewCategory("");
    loadAll();
  }

  async function handleAddProduct(e) {
    e.preventDefault();
    setError("");
    try {
      await productApi.create(form);
      setForm({ name: "", category: "", size: "", selling_price: "", initial_stock: "" });
      loadAll();
    } catch (err) {
      setError("Could not create product. Check the fields and try again.");
    }
  }

  async function toggleActive(p) {
    await productApi.update(p.id, { is_active: !p.is_active });
    loadAll();
  }

  return (
    <div className="space-y-8">
      <h1 className="text-lg font-semibold">Products</h1>

      <div className="bg-white rounded-2xl border border-gray-100 p-4 overflow-x-auto">
        <table className="w-full text-sm whitespace-nowrap">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="py-2">Name</th>
              <th>Category</th>
              <th>Size</th>
              <th>Price</th>
              <th>Factory stock</th>
              {showrooms.map((showroom) => <th key={showroom.id}>{showroom.name}</th>)}
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id} className="border-b border-gray-50">
                <td className="py-2 font-medium">{p.name}</td>
                <td className="text-gray-500">{p.category_name}</td>
                <td className="text-gray-500">{p.size || "—"}</td>
                <td>৳ {Number(p.selling_price).toLocaleString()}</td>
                <td className="font-medium">{factoryStock[p.id] || 0} pcs</td>
                {showrooms.map((showroom) => (
                  <td key={showroom.id}>{showroomStock[`${p.id}-${showroom.id}`] || 0} pcs</td>
                ))}
                <td>
                  <span className={`text-xs px-2 py-1 rounded-full ${p.is_active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {p.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <button onClick={() => toggleActive(p)} className="text-brand-600 text-xs hover:underline">
                    {p.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <form onSubmit={handleAddCategory} className="bg-white rounded-2xl border border-gray-100 p-4">
          <div className="text-sm font-medium text-gray-700 mb-3">Add category</div>
          <div className="flex gap-2">
            <input
              placeholder="e.g. Panjabi, Shirt, Shoe"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
            <button className="bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg">
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {categories.map((c) => (
              <span key={c.id} className="text-xs bg-gray-100 px-2 py-1 rounded-full text-gray-600">{c.name}</span>
            ))}
          </div>
        </form>

        <form onSubmit={handleAddProduct} className="bg-white rounded-2xl border border-gray-100 p-4">
          <div className="text-sm font-medium text-gray-700 mb-3">Add product</div>
          {error && <div className="text-xs text-red-600 mb-2">{error}</div>}
          <input
            placeholder="Product name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            required
          />
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            required
          >
            <option value="">Select category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <input
            placeholder="Size (optional)"
            value={form.size}
            onChange={(e) => setForm({ ...form, size: e.target.value })}
            className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="number"
            step="0.01"
            placeholder="Selling price"
            value={form.selling_price}
            onChange={(e) => setForm({ ...form, selling_price: e.target.value })}
            className="w-full mb-3 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            required
          />
          <input
            type="number"
            min="0"
            step="1"
            placeholder="Initial factory stock (pcs)"
            value={form.initial_stock}
            onChange={(e) => setForm({ ...form, initial_stock: e.target.value })}
            className="w-full mb-3 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            required
          />
          <button className="bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg">
            Add product
          </button>
        </form>
      </div>
    </div>
  );
}
