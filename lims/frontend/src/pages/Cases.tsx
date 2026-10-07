import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, post } from "../api/client";
import { fmt, useClients, useMe } from "../api/hooks";
import type { CaseDetail, CaseSummary } from "../api/types";
import ErrorText from "../components/ErrorText";

export default function Cases() {
  const [q, setQ] = useState("");
  const cases = useQuery({
    queryKey: ["cases", q],
    queryFn: () => api<CaseSummary[]>(`/cases${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  });
  const me = useMe();
  const canRegister = me.data?.roles.some((r) => r === "case_scientist" || r === "screening_lab_officer");
  return (
    <section>
      <h2>Cases</h2>
      {canRegister && <RegisterCase />}
      <input placeholder="Search case number or reference" value={q} onChange={(e) => setQ(e.target.value)} />
      <ErrorText error={cases.error} />
      <table>
        <thead>
          <tr>
            <th>Case</th>
            <th>Client reference</th>
            <th>Status</th>
            <th>Registered</th>
          </tr>
        </thead>
        <tbody>
          {cases.data?.map((c) => (
            <tr key={c.id}>
              <td>
                <Link to={`/cases/${c.id}`}>{c.case_number}</Link>
              </td>
              <td>{c.client_reference}</td>
              <td>{c.state}</td>
              <td>{fmt(c.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

const EMPTY = {
  client_id: "",
  client_reference: "",
  source: "paper",
  submission_reference: "",
  submitter_name: "",
  submitter_contact: "",
  investigating_officer_name: "",
  investigating_officer_contact: "",
  case_information: "",
};

function RegisterCase() {
  const navigate = useNavigate();
  const me = useMe();
  const clients = useClients();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) =>
    setForm({ ...form, [k]: e.target.value });
  const register = useMutation({
    mutationFn: () =>
      post<CaseDetail>("/cases", {
        ...Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v.trim() || null])),
        laboratory_id: me.data?.laboratory_ids[0],
      }),
    onSuccess: (d) => navigate(`/cases/${d.case.id}`),
  });

  if (!open) return <button onClick={() => setOpen(true)}>Register a case</button>;
  return (
    <form
      className="panel grid"
      onSubmit={(e) => {
        e.preventDefault();
        register.mutate();
      }}
    >
      <h3>Register a case</h3>
      <label>
        Client
        <select value={form.client_id} onChange={set("client_id")} required>
          <option value="">Select…</option>
          {clients.data
            ?.filter((c) => c.active)
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
        </select>
      </label>
      <label>
        Client case reference
        <input value={form.client_reference} onChange={set("client_reference")} required />
      </label>
      <label>
        Received as
        <select value={form.source} onChange={set("source")}>
          <option value="paper">Paper submission</option>
          <option value="electronic">Electronic submission</option>
        </select>
      </label>
      {form.source === "electronic" && (
        <label>
          Electronic submission reference
          <input value={form.submission_reference} onChange={set("submission_reference")} required />
        </label>
      )}
      <label>
        Submitter
        <input value={form.submitter_name} onChange={set("submitter_name")} required />
      </label>
      <label>
        Submitter contact
        <input value={form.submitter_contact} onChange={set("submitter_contact")} />
      </label>
      <label>
        Investigating officer
        <input
          value={form.investigating_officer_name}
          onChange={set("investigating_officer_name")}
          required
        />
      </label>
      <label>
        Investigating officer contact
        <input
          value={form.investigating_officer_contact}
          onChange={set("investigating_officer_contact")}
        />
      </label>
      <label className="wide">
        Case information
        <textarea value={form.case_information} onChange={set("case_information")} rows={3} />
      </label>
      <div className="actions wide">
        <button disabled={register.isPending}>Register</button>
        <button type="button" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
      <ErrorText error={register.error} />
    </form>
  );
}
