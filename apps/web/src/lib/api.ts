import axios from "axios";

export type Role = "admin" | "manager" | "staff";

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: Role;
  location_ids: string[];
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  withCredentials: true,
});

export async function login(email: string, password: string): Promise<AuthUser> {
  const response = await api.post("/auth/login", { email, password });
  return response.data.user;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function getMe(): Promise<AuthUser> {
  const response = await api.get("/auth/me");
  return response.data.user;
}

export default api;
