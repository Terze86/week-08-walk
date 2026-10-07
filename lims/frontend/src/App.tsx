import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { api, ApiError, getDevUser, setDevUser } from "./api/client";
import type { Me } from "./api/types";
import DevSignIn from "./components/DevSignIn";
import AuditLog from "./workspaces/admin/AuditLog";
import Users from "./workspaces/admin/Users";
import Placeholder from "./workspaces/Placeholder";

export default function App() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [username, setUsername] = useState(getDevUser);
  const me = useQuery({
    queryKey: ["me", username],
    queryFn: () => api<Me>("/me"),
    enabled: username !== null,
  });

  const switchUser = (next: string | null) => {
    setDevUser(next);
    queryClient.clear();
    setUsername(next);
    navigate("/", { replace: true });
  };

  if (!username || (me.error instanceof ApiError && me.error.status < 500)) {
    return <DevSignIn error={me.error?.message} onSignIn={switchUser} />;
  }
  if (me.isPending) return <p className="page">Loading…</p>;
  if (me.error) return <p className="page error">{me.error.message}</p>;

  const user = me.data;
  const home = user.workspaces[0] ? `/${user.workspaces[0].key}` : "/";
  return (
    <div className="shell">
      <header className="topbar">
        <strong>DNA LIMS</strong>
        <nav>
          {user.workspaces.map((w) => (
            <NavLink key={w.key} to={`/${w.key}`}>
              {w.title}
            </NavLink>
          ))}
        </nav>
        <span className="who">
          {user.display_name}
          <button onClick={() => switchUser(null)}>Sign out</button>
        </span>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Navigate to={home} replace />} />
          {user.workspaces.map((w) =>
            w.key === "admin" ? (
              <Route key={w.key} path="/admin/*" element={<AdminWorkspace />} />
            ) : (
              <Route key={w.key} path={`/${w.key}`} element={<Placeholder title={w.title} />} />
            ),
          )}
          <Route path="*" element={<p>You do not have access to this workspace.</p>} />
        </Routes>
      </main>
    </div>
  );
}

function AdminWorkspace() {
  return (
    <>
      <nav className="subnav">
        <NavLink to="/admin/users">Staff accounts</NavLink>
        <NavLink to="/admin/audit">Audit trail</NavLink>
      </nav>
      <Routes>
        <Route index element={<Navigate to="users" replace />} />
        <Route path="users" element={<Users />} />
        <Route path="audit" element={<AuditLog />} />
      </Routes>
    </>
  );
}
