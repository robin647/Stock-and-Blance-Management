import { useEffect, useState } from "react";
import { reportApi } from "../../api/endpoints";

function StatCard({ label, value, isCurrency = true }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-2xl font-semibold text-gray-900 mt-1">
        {isCurrency ? `৳ ${Number(value).toLocaleString()}` : value}
      </div>
    </div>
  );
}

export default function ShowroomDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    reportApi
      .dashboard({ date: new Date().toISOString().slice(0, 10) })
      .then((res) => setData(res.data))
      .catch(() => setError("Could not load dashboard data."));
  }, []);

  if (error) return <div className="text-red-600 text-sm">{error}</div>;
  if (!data) return <div className="text-gray-500 text-sm">Loading dashboard...</div>;

  return (
    <div>
      <h1 className="text-lg font-semibold mb-4">Today's Overview — {data.date}</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label="Total Sale" value={data.total_sale} />
        <StatCard label="Cash Sale" value={data.cash_sale} />
        <StatCard label="Card Sale" value={data.card_sale} />
        <StatCard label="Expense" value={data.expense} />
        <StatCard label="Salary" value={data.salary} />
        <StatCard label="Deposit" value={data.deposit} />
      </div>
    </div>
  );
}
