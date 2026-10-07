import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { post, put } from "../../api/client";
import { useClients, useLaboratories, useLocations } from "../../api/hooks";
import type { LocationKind } from "../../api/types";
import ErrorText from "../../components/ErrorText";
import ReasonAction from "../../components/ReasonAction";

const KINDS: LocationKind[] = ["storage", "bench", "instrument", "transit", "disposal"];

export default function Reference() {
  const qc = useQueryClient();
  const clients = useClients();
  const locations = useLocations();
  const labs = useLaboratories();
  const [client, setClient] = useState({ code: "", name: "" });
  const [loc, setLoc] = useState({ code: "", name: "", kind: "storage" as LocationKind, laboratory_id: "" });

  const addClient = useMutation({
    mutationFn: () => post("/admin/clients", client),
    onSuccess: () => {
      setClient({ code: "", name: "" });
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
  });
  const addLocation = useMutation({
    mutationFn: () => post("/admin/locations", { ...loc, laboratory_id: loc.laboratory_id || labs.data?.[0]?.id }),
    onSuccess: () => {
      setLoc({ ...loc, code: "", name: "" });
      qc.invalidateQueries({ queryKey: ["locations"] });
    },
  });
  const toggle = useMutation({
    mutationFn: ({ id, active, reason }: { id: string; active: boolean; reason: string }) =>
      put(`/admin/locations/${id}/active`, { active, reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["locations"] }),
  });

  return (
    <section>
      <h2>Clients</h2>
      <form
        className="inline"
        onSubmit={(e) => {
          e.preventDefault();
          addClient.mutate();
        }}
      >
        <input placeholder="Code" value={client.code} onChange={(e) => setClient({ ...client, code: e.target.value })} />
        <input placeholder="Name" value={client.name} onChange={(e) => setClient({ ...client, name: e.target.value })} />
        <button disabled={!client.code || !client.name}>Add client</button>
      </form>
      <ErrorText error={addClient.error} />
      <ul>
        {clients.data?.map((c) => (
          <li key={c.id}>
            <strong>{c.code}</strong> {c.name}
          </li>
        ))}
      </ul>

      <h2>Locations</h2>
      <form
        className="inline"
        onSubmit={(e) => {
          e.preventDefault();
          addLocation.mutate();
        }}
      >
        <input placeholder="Code (barcode)" value={loc.code} onChange={(e) => setLoc({ ...loc, code: e.target.value })} />
        <input placeholder="Name" value={loc.name} onChange={(e) => setLoc({ ...loc, name: e.target.value })} />
        <select value={loc.kind} onChange={(e) => setLoc({ ...loc, kind: e.target.value as LocationKind })}>
          {KINDS.map((k) => (
            <option key={k}>{k}</option>
          ))}
        </select>
        <select value={loc.laboratory_id} onChange={(e) => setLoc({ ...loc, laboratory_id: e.target.value })}>
          {labs.data?.map((l) => (
            <option key={l.id} value={l.id}>
              {l.code}
            </option>
          ))}
        </select>
        <button disabled={!loc.code || !loc.name}>Add location</button>
      </form>
      <ErrorText error={addLocation.error ?? toggle.error} />
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Kind</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {locations.data?.map((l) => (
            <tr key={l.id}>
              <td>{l.code}</td>
              <td>{l.name}</td>
              <td>{l.kind}</td>
              <td>
                <span className={`pill ${l.active ? "active" : "disabled"}`}>{l.active ? "in use" : "retired"}</span>
              </td>
              <td>
                <ReasonAction
                  label={l.active ? "Retire" : "Bring back into use"}
                  prompt="Reason"
                  onConfirm={(reason) => toggle.mutate({ id: l.id, active: !l.active, reason })}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
