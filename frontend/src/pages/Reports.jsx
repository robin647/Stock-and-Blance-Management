import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { reportApi, showroomApi } from "../api/endpoints";

const todayStr = () => new Date().toISOString().slice(0, 10);

export default function Reports() {
  const { user, isAdmin } = useAuth();
  const [tab, setTab] = useState("daily");
  const [showrooms, setShowrooms] = useState([]);
  const [showroomId, setShowroomId] = useState(isAdmin ? "" : user.showroomId);
  const [date, setDate] = useState(todayStr());
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [dailyData, setDailyData] = useState(null);
  const [monthlyData, setMonthlyData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isAdmin) showroomApi.list().then((res) => setShowrooms(res.data.results || res.data));
  }, [isAdmin]);

  async function loadDaily() {
    setError("");
    if (!showroomId) {
      setError("Please select a showroom.");
      return;
    }
    try {
      const { data } = await reportApi.daily({ date, showroom: showroomId });
      setDailyData(data);
    } catch {
      setError("Could not load daily statement.");
    }
  }

  async function loadMonthly() {
    setError("");
    try {
      const params = { year, month };
      if (showroomId) params.showroom = showroomId;
      const { data } = await reportApi.monthly(params);
      setMonthlyData(data);
    } catch {
      setError("Could not load monthly report.");
    }
  }

  useEffect(() => {
    if (tab === "daily") loadDaily();
    else loadMonthly();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Reports</h1>

      <div className="flex gap-2">
        <button
          onClick={() => setTab("daily")}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === "daily" ? "bg-brand-500 text-white" : "bg-white border border-gray-200 text-gray-600"}`}
        >
          Daily
        </button>
        <button
          onClick={() => setTab("monthly")}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === "monthly" ? "bg-brand-500 text-white" : "bg-white border border-gray-200 text-gray-600"}`}
        >
          Monthly
        </button>
      </div>

      {error && <div className="text-sm text-red-600">{error}</div>}

      {tab === "daily" && (
        <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-4">
          <div className="flex flex-wrap gap-3 items-end">
            {isAdmin && (
              <div>
                <label className="block text-xs text-gray-500 mb-1">Showroom</label>
                <select value={showroomId} onChange={(e) => setShowroomId(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">Select</option>
                  {showrooms.map((sr) => <option key={sr.id} value={sr.id}>{sr.name}</option>)}
                </select>
              </div>
            )}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date</label>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <button onClick={loadDaily} className="bg-brand-500 hover:bg-brand-600 text-white text-sm px-4 py-2 rounded-lg">Load</button>
            <button
              onClick={() => reportApi.exportDaily({ date, showroom: showroomId }, `daily-${showroomId}-${date}.xlsx`)}
              className="border border-gray-300 text-sm px-4 py-2 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Download Excel
            </button>
          </div>

          {dailyData && (
            <>
              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Stock</div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b border-gray-100">
                      <th className="py-1">Product</th><th>Opening</th><th>Received</th><th>Sold</th><th>Return</th><th>Closing</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dailyData.stock.map((s, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="py-1">{s.product}</td><td>{s.opening}</td><td>{s.received}</td><td>{s.sold}</td><td>{s.return}</td><td>{s.closing}</td>
                      </tr>
                    ))}
                    {dailyData.stock.length === 0 && (
                      <tr><td colSpan={6} className="text-gray-400 py-3">No stock entries for this date.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Balance</div>
                {dailyData.balance ? (
                  <table className="w-full text-sm max-w-sm">
                    <tbody>
                      {[
                        ["Opening Balance", dailyData.balance.opening_balance],
                        ["Cash Sale", dailyData.balance.cash_sale],
                        ["Card Sale", dailyData.balance.card_sale],
                        ["Total Sale", dailyData.balance.total_sale],
                        ["Expense", dailyData.balance.expense],
                        ["Salary", dailyData.balance.salary],
                        ["Deposit", dailyData.balance.deposit],
                        ["Closing Balance", dailyData.balance.closing_balance],
                      ].map(([label, val]) => (
                        <tr key={label} className="border-b border-gray-50">
                          <td className="py-1 text-gray-500">{label}</td>
                          <td className="text-right font-medium">৳ {Number(val).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="text-gray-400 text-sm">No balance entry for this date.</div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {tab === "monthly" && (
        <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-4">
          <div className="flex flex-wrap gap-3 items-end">
            {isAdmin && (
              <div>
                <label className="block text-xs text-gray-500 mb-1">Showroom (optional)</label>
                <select value={showroomId} onChange={(e) => setShowroomId(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">All showrooms</option>
                  {showrooms.map((sr) => <option key={sr.id} value={sr.id}>{sr.name}</option>)}
                </select>
              </div>
            )}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Year</label>
              <input type="number" value={year} onChange={(e) => setYear(e.target.value)} className="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Month</label>
              <input type="number" min="1" max="12" value={month} onChange={(e) => setMonth(e.target.value)} className="w-20 border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <button onClick={loadMonthly} className="bg-brand-500 hover:bg-brand-600 text-white text-sm px-4 py-2 rounded-lg">Load</button>
            <button
              onClick={() => reportApi.exportMonthly({ year, month, ...(showroomId ? { showroom: showroomId } : {}) }, `monthly-${year}-${month}.xlsx`)}
              className="border border-gray-300 text-sm px-4 py-2 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Download Excel
            </button>
          </div>

          {monthlyData && (
            <>
              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Balance summary</div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b border-gray-100">
                      <th className="py-1">Showroom</th><th>Total Sale</th><th>Cash</th><th>Card</th><th>Expense</th><th>Salary</th><th>Deposit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyData.balance_summary.map((r, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="py-1">{r.showroom__name}</td>
                        <td>৳ {Number(r.total_sale).toLocaleString()}</td>
                        <td>৳ {Number(r.cash_sale).toLocaleString()}</td>
                        <td>৳ {Number(r.card_sale).toLocaleString()}</td>
                        <td>৳ {Number(r.expense).toLocaleString()}</td>
                        <td>৳ {Number(r.salary).toLocaleString()}</td>
                        <td>৳ {Number(r.deposit).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Stock summary</div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b border-gray-100">
                      <th className="py-1">Product</th><th>Received</th><th>Sold</th><th>Return</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyData.stock_summary.map((r, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="py-1">{r.product__name}</td><td>{r.received}</td><td>{r.sold}</td><td>{r.returned}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
