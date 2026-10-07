import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, post, put } from "../../api/client";
import { ROLE_LABELS, type Role, type User } from "../../api/types";

const ALL_ROLES = Object.keys(ROLE_LABELS) as Role[];

export default function Users() {
  const users = useQuery({ queryKey: ["users"], queryFn: () => api<User[]>("/admin/users") });
  const [editing, setEditing] = useState<User | null>(null);

  return (
    <section>
      <h2>Staff accounts</h2>
      <NewUser />
      {users.error && <p className="error">{users.error.message}</p>}
      <table>
        <thead>
          <tr>
            <th>Username</th>
            <th>Name</th>
            <th>Roles</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {users.data?.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td>
              <td>{u.display_name}</td>
              <td>{u.roles.map((r) => ROLE_LABELS[r]).join(", ")}</td>
              <td>
                <span className={`pill ${u.status}`}>{u.status}</span>
              </td>
              <td>
                <button onClick={() => setEditing(u)}>Change…</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {editing && <EditUser user={editing} onClose={() => setEditing(null)} />}
    </section>
  );
}

function NewUser() {
  const qc = useQueryClient();
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const create = useMutation({
    mutationFn: () => post<User>("/admin/users", { username, display_name: displayName }),
    onSuccess: () => {
      setUsername("");
      setDisplayName("");
      qc.invalidateQueries({ queryKey: ["users"] });
    },
  });
  return (
    <form
      className="inline"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate();
      }}
    >
      <input placeholder="username" value={username} onChange={(e) => setUsername(e.target.value)} />
      <input
        placeholder="Display name"
        value={displayName}
        onChange={(e) => setDisplayName(e.target.value)}
      />
      <button disabled={!username || !displayName || create.isPending}>Add account</button>
      {create.error && <span className="error">{create.error.message}</span>}
    </form>
  );
}

function EditUser({ user, onClose }: { user: User; onClose: () => void }) {
  const qc = useQueryClient();
  const [roles, setRoles] = useState<Set<Role>>(new Set(user.roles));
  const [reason, setReason] = useState("");
  const done = () => {
    qc.invalidateQueries({ queryKey: ["users"] });
    onClose();
  };
  const saveRoles = useMutation({
    mutationFn: () => put(`/admin/users/${user.id}/roles`, { roles: [...roles], reason }),
    onSuccess: done,
  });
  const toggleStatus = useMutation({
    mutationFn: () =>
      put(`/admin/users/${user.id}/status`, {
        status: user.status === "active" ? "disabled" : "active",
        reason,
      }),
    onSuccess: done,
  });
  const error = saveRoles.error ?? toggleStatus.error;

  return (
    <div className="dialog">
      <h3>{user.display_name}</h3>
      <fieldset>
        <legend>Roles</legend>
        {ALL_ROLES.map((r) => (
          <label key={r}>
            <input
              type="checkbox"
              checked={roles.has(r)}
              onChange={() => {
                const next = new Set(roles);
                if (next.has(r)) next.delete(r);
                else next.add(r);
                setRoles(next);
              }}
            />
            {ROLE_LABELS[r]}
          </label>
        ))}
      </fieldset>
      <label>
        Reason for change (required)
        <input value={reason} onChange={(e) => setReason(e.target.value)} />
      </label>
      <div className="actions">
        <button disabled={reason.trim().length < 3} onClick={() => saveRoles.mutate()}>
          Save roles
        </button>
        <button disabled={reason.trim().length < 3} onClick={() => toggleStatus.mutate()}>
          {user.status === "active" ? "Disable account" : "Enable account"}
        </button>
        <button onClick={onClose}>Cancel</button>
      </div>
      {error && <p className="error">{error.message}</p>}
    </div>
  );
}
