import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";

import Login from "./pages/Login.jsx";
import Reports from "./pages/Reports.jsx";
import AdminDashboard from "./pages/admin/AdminDashboard.jsx";
import Products from "./pages/admin/Products.jsx";
import Showrooms from "./pages/admin/Showrooms.jsx";
import BalanceEntry from "./pages/showroom/BalanceEntry.jsx";
import ShowroomDashboard from "./pages/showroom/ShowroomDashboard.jsx";
import StockEntry from "./pages/showroom/StockEntry.jsx";

function Home() {
  const { isAdmin } = useAuth();
  return isAdmin ? <AdminDashboard /> : <ShowroomDashboard />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout><Home /></Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/showrooms"
        element={
          <ProtectedRoute requireAdmin>
            <Layout><Showrooms /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/products"
        element={
          <ProtectedRoute requireAdmin>
            <Layout><Products /></Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/stock"
        element={
          <ProtectedRoute>
            <Layout><StockEntry /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/balance"
        element={
          <ProtectedRoute>
            <Layout><BalanceEntry /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <Layout><Reports /></Layout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
