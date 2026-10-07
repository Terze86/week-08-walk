import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";

import { api, ApiError, getDevUser, setDevUser } from "./api/client";
import type { Me, Role } from "./api/types";
import DevSignIn from "./components/DevSignIn";
import CasePage from "./pages/CasePage";
import Cases from "./pages/Cases";
import Custody from "./pages/Custody";
import MyWork from "./pages/MyWork";
import ReceiptPage from "./pages/ReceiptPage";
import AuditLog from "./workspaces/admin/AuditLog";
import Reference from "./workspaces/admin/Reference";
import Users from "./workspaces/admin/Users";
import Placeholder from "./workspaces/Placeholder";

const CASEWORK: Role[] = ["case_scientist", "screening_lab_officer", "dna_lab_officer", "reviewer"];

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
  const casework = user.roles.some((r) => CASEWORK.includes(r));
  const home = user.workspaces[0] ? workspacePath(user.workspaces[0].key) : "/";
  return (
    <div className="shell">
      <header className="topbar noprint">
        <strong>DNA LIMS</strong>
        <nav>
          {user.workspaces.map((w) => (
            <NavLink key={w.key} to={workspacePath(w.key)}>
              {w.title}
            </NavLink>
          ))}
          {casework && (
            <>
              <NavLink to="/cases">Cases</NavLink>
              <NavLink to="/custody">Custody</NavLink>
            </>
          )}
        </nav>
        <span className="who">
          {user.display_name}
          <button onClick={() => switchUser(null)}>Sign out</button>
        </span>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Navigate to={home} replace />} />
          <Route path="/work/:key" element={<Workspace me={user} />} />
          {user.roles.includes("lims_admin") && <Route path="/admin/*" element={<AdminWorkspace />} />}
          {casework && (
            <>
              <Route path="/cases" element={<Cases />} />
              <Route path="/cases/:caseId" element={<CasePage />} />
              <Route path="/receipts/:receiptId" element={<ReceiptPage />} />
              <Route path="/custody" element={<Custody />} />
            </>
          )}
          <Route path="*" element={<p>You do not have access to this page.</p>} />
        </Routes>
      </main>
    </div>
  );
}

const workspacePath = (key: string) => (key === "admin" ? "/admin" : `/work/${key}`);

function Workspace({ me }: { me: Me }) {
  const { key } = useParams();
  const workspace = me.workspaces.find((w) => w.key === key);
  if (!workspace) return <p>You do not have access to this workspace.</p>;
  if (key === "codis") return <Placeholder title={workspace.title} />;
  return <MyWork title={workspace.title} />;
}

function AdminWorkspace() {
  return (
    <>
      <nav className="subnav">
        <NavLink to="/admin/users">Staff accounts</NavLink>
        <NavLink to="/admin/reference">Clients &amp; locations</NavLink>
        <NavLink to="/admin/audit">Audit trail</NavLink>
      </nav>
      <Routes>
        <Route index element={<Navigate to="users" replace />} />
        <Route path="users" element={<Users />} />
        <Route path="reference" element={<Reference />} />
        <Route path="audit" element={<AuditLog />} />
      </Routes>
    </>
  );
}
