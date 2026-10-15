import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";

import Login from "./pages/Login.jsx";
import Reports from "./pages/Reports.jsx";
import AdminDashboard from "./pages/admin/AdminDashboard.jsx";
import Products from "./pages/admin/Products.jsx";
import Showrooms from "./pages/admin/Showrooms.jsx";
import StockAdjustments from "./pages/admin/StockAdjustments.jsx";
import WholesaleParties from "./pages/admin/WholesaleParties.jsx";
import WholesaleSales from "./pages/admin/WholesaleSales.jsx";
import EasyWholesaleManagement from "./pages/admin/EasyWholesaleManagement.jsx";
import WholesaleReturns from "./pages/admin/WholesaleReturns.jsx";
import AllPartiesSummary from "./pages/admin/AllPartiesSummary.jsx";
import WholesaleReports from "./pages/admin/WholesaleReports.jsx";
import BalanceEntry from "./pages/showroom/BalanceEntry.jsx";
import ShowroomDashboard from "./pages/showroom/ShowroomDashboard.jsx";
import StockEntry from "./pages/showroom/StockEntry.jsx";
import { WhatsAppButton } from "./components/SiteFooter.jsx";

function Home() {
  const { isAdmin } = useAuth();
  return isAdmin ? <AdminDashboard /> : <ShowroomDashboard />;
}

export default function App() {
  return (
    <>
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
      <Route path="/stock-adjustments" element={<ProtectedRoute requireAdmin><Layout><StockAdjustments /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/parties" element={<ProtectedRoute requireAdmin><Layout><WholesaleParties /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/sales" element={<ProtectedRoute requireAdmin><Layout><WholesaleSales /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/easy" element={<ProtectedRoute requireAdmin><Layout><EasyWholesaleManagement /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/returns" element={<ProtectedRoute requireAdmin><Layout><WholesaleReturns /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/summary" element={<ProtectedRoute requireAdmin><Layout><AllPartiesSummary /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/reports" element={<ProtectedRoute requireAdmin><Layout><WholesaleReports /></Layout></ProtectedRoute>} />

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
    <WhatsAppButton />
    </>
  );
}
