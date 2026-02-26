import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppLayout({ title, children }: { title: string; children: React.ReactNode }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>ShiftSync</h1>
          <p>{title}</p>
        </div>
        <div className="header-actions">
          <span>
            {user?.name} ({user?.role})
          </span>
          <Link to={`/${user?.role}`}>Home</Link>
          <button
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            Logout
          </button>
        </div>
      </header>
      <main className="app-content">{children}</main>
    </div>
  );
}
