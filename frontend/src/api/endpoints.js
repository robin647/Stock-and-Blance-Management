import api from "./axios";

// A single login endpoint is used for both Admin and Showroom accounts —
// the account's role (embedded in the returned JWT) determines what it can
// do, not which endpoint was called.
export const authApi = {
  login: (username, password) => api.post("/auth/login/", { username, password }),
  me: () => api.get("/accounts/me/"),
};

export const showroomApi = {
  list: () => api.get("/showrooms/"),
  create: (data) => api.post("/showrooms/", data),
  update: (id, data) => api.patch(`/showrooms/${id}/`, data),
};

export const showroomUserApi = {
  list: () => api.get("/accounts/showroom-users/"),
  create: (data) => api.post("/accounts/showroom-users/", data),
  // `data` may include `password` to reset it, or just `is_active` to
  // activate/deactivate the login — both go through the same PATCH.
  update: (id, data) => api.patch(`/accounts/showroom-users/${id}/`, data),
};

export const categoryApi = {
  list: () => api.get("/products/categories/"),
  create: (data) => api.post("/products/categories/", data),
};

export const productApi = {
  list: (params) => api.get("/products/", { params }),
  create: (data) => api.post("/products/", data),
  update: (id, data) => api.patch(`/products/${id}/`, data),
};

export const stockApi = {
  list: (params) => api.get("/inventory/stocks/", { params }),
  create: (data) => api.post("/inventory/stocks/", data),
  update: (id, data) => api.patch(`/inventory/stocks/${id}/`, data),
};

export const factoryStockApi = {
  list: (params) => api.get("/inventory/factory-stocks/", { params }),
};

export const stockAdjustmentApi = {
  list: (params) => api.get("/wholesale/stock-adjustments/", { params }),
  create: (data) => api.post("/wholesale/stock-adjustments/", data),
};

export const wholesalePartyApi = {
  list: (params) => api.get("/wholesale/parties/", { params }),
  get: (id) => api.get(`/wholesale/parties/${id}/`),
  create: (data) => api.post("/wholesale/parties/", data),
  update: (id, data) => api.patch(`/wholesale/parties/${id}/`, data),
  history: (id, params) => api.get(`/wholesale/parties/${id}/history/`, { params }),
  exportStatement: (id, params) => downloadFile(`/wholesale/parties/${id}/statement/export/`, params, `party-${id}-account-statement.xlsx`),
};

export const wholesaleInvoiceApi = {
  list: (params) => api.get("/wholesale/invoices/", { params }),
  create: (data) => api.post("/wholesale/invoices/", data),
};

export const wholesalePaymentApi = {
  list: (params) => api.get("/wholesale/payments/", { params }),
  create: (data, idempotencyKey) => api.post("/wholesale/payments/", data, { headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {} }),
};

export const wholesaleReturnApi = {
  list: (params) => api.get("/wholesale/returns/", { params }),
  create: (data, idempotencyKey) => api.post("/wholesale/returns/", data, { headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {} }),
};

export const wholesaleReportApi = {
  summary: (params) => api.get("/wholesale/summary/", { params }),
  exportSummary: (params) => downloadFile("/wholesale/summary/export/", params, "wholesale-all-parties-summary.xlsx"),
  reports: (params) => api.get("/wholesale/reports/", { params }),
  export: (params) => downloadFile("/wholesale/reports/export/", params, "wholesale-report.xlsx"),
};

export const showroomStockApi = {
  list: (params) => api.get("/inventory/showroom-stocks/", { params }),
};

export const stockTransferApi = {
  list: (params) => api.get("/inventory/transfers/", { params }),
  create: (data) => api.post("/inventory/transfers/", data),
  update: (id, data) => api.patch(`/inventory/transfers/${id}/`, data),
  summary: (params) => api.get("/inventory/transfers/summary/", { params }),
  // Helper methods for specific transfer types
  receive: (data) => api.post("/inventory/transfers/", { ...data, transfer_type: "receive" }),
  sell: (data) => api.post("/inventory/transfers/", { ...data, transfer_type: "sale" }),
  return: (data) => api.post("/inventory/transfers/", { ...data, transfer_type: "return" }),
};

export const balanceApi = {
  list: (params) => api.get("/inventory/balances/", { params }),
  create: (data) => api.post("/inventory/balances/", data),
  update: (id, data) => api.patch(`/inventory/balances/${id}/`, data),
};

export const reportApi = {
  dashboard: (params) => api.get("/reports/dashboard/", { params }),
  daily: (params) => api.get("/reports/daily/", { params }),
  monthly: (params) => api.get("/reports/monthly/", { params }),
  exportDaily: (params, filename) => downloadFile("/reports/export/daily/", params, filename),
  exportMonthly: (params, filename) => downloadFile("/reports/export/monthly/", params, filename),
};

// Excel export endpoints require the JWT header, so a plain <a href> link
// won't work — we fetch as a blob (auth header attached automatically by
// the axios interceptor) and then trigger the browser download manually.
async function downloadFile(path, params, filename) {
  const response = await api.get(path, { params, responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename || "report.xlsx");
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
