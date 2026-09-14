import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { reportApi } from "../../api/endpoints";

function StatCard({ label, value }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-2xl font-semibold text-gray-900 mt-1">৳ {Number(value).toLocaleString()}</div>
    </div>
  );
}

export default function AdminDashboard() {
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
      <h1 className="text-lg font-semibold mb-4">Admin Dashboard — {data.date}</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Showrooms" value={data.total_showrooms} />
        <StatCard label="Today's Total Sales" value={data.total_sale} />
        <StatCard label="Cash Sales" value={data.cash_sale} />
        <StatCard label="Card Sales" value={data.card_sale} />
        <StatCard label="Expenses" value={data.expense} />
        <StatCard label="Deposit" value={data.deposit} />
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-4">
        <div className="text-sm font-medium text-gray-700 mb-4">Showroom-wise Sales</div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data.showroom_wise}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey="showroom__name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="total_sale" fill="#3b5fe0" radius={[6, 6, 0, 0]} name="Total Sale" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
