import { createContext, useContext, useEffect, useState } from "react";
import { authApi } from "../api/endpoints";

const AuthContext = createContext(null);

function decodeToken(token) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

function userFromToken(token) {
  const decoded = decodeToken(token);
  if (!decoded) return null;
  return {
    id: decoded.user_id,
    role: decoded.role, // "admin" | "showroom_user"
    showroomId: decoded.showroom_id,
    showroomName: decoded.showroom_name,
    fullName: decoded.full_name,
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) setUser(userFromToken(token));
    setLoading(false);
  }, []);

  // Single login path for both Admin and Showroom accounts — both are
  // `User` rows authenticated the same way, differing only by `role`.
  async function login(username, password) {
    const { data } = await authApi.login(username, password);
    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    const nextUser = userFromToken(data.access);
    setUser(nextUser);
    return nextUser;
  }

  function logout() {
    localStorage.clear();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, isAdmin: user?.role === "admin" }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
