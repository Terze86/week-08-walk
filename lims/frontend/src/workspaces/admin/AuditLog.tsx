import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import type { AuditEvent } from "../../api/types";

export default function AuditLog() {
  const [entityId, setEntityId] = useState("");
  const events = useQuery({
    queryKey: ["audit", entityId],
    queryFn: () =>
      api<AuditEvent[]>(`/admin/audit${entityId ? `?entity_id=${encodeURIComponent(entityId)}` : ""}`),
  });
  const chain = useQuery({
    queryKey: ["audit-verify"],
    queryFn: () => api<{ intact: boolean; broken_event_ids: number[] }>("/admin/audit/verify"),
  });

  return (
    <section>
      <h2>Audit trail</h2>
      <p>
        Hash chain:{" "}
        {chain.data ? (
          chain.data.intact ? (
            <span className="pill active">intact</span>
          ) : (
            <span className="pill disabled">
              broken at {chain.data.broken_event_ids.join(", ")}
            </span>
          )
        ) : (
          "checking…"
        )}
      </p>
      <input
        placeholder="Filter by record id"
        value={entityId}
        onChange={(e) => setEntityId(e.target.value.trim())}
      />
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>When</th>
            <th>Action</th>
            <th>Record</th>
            <th>Reason</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          {events.data?.map((e) => (
            <tr key={e.id}>
              <td>{e.id}</td>
              <td>{new Date(e.occurred_at).toLocaleString()}</td>
              <td>{e.action}</td>
              <td>
                {e.entity_type}:{e.entity_id.slice(0, 8)}
              </td>
              <td>{e.reason ?? ""}</td>
              <td>
                <code>{JSON.stringify(e.after ?? {})}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
