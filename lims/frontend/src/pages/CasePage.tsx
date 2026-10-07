import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, post } from "../api/client";
import { fmt, useMe, useStaff } from "../api/hooks";
import type { CaseDetail, Exhibit, Receipt, ReceiptSummary, Subcase } from "../api/types";
import ErrorText from "../components/ErrorText";
import ReasonAction from "../components/ReasonAction";

export default function CasePage() {
  const { caseId } = useParams();
  const detail = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api<CaseDetail>(`/cases/${caseId}`),
  });
  if (detail.error) return <ErrorText error={detail.error} />;
  if (!detail.data) return <p>Loading…</p>;
  const c = detail.data.case;
  return (
    <section>
      <h2>
        Case {c.case_number} <span className="muted">({c.client_reference})</span>
      </h2>
      <dl className="facts">
        <dt>Submitter</dt>
        <dd>
          {c.submitter_name} {c.submitter_contact && `· ${c.submitter_contact}`}
        </dd>
        <dt>Investigating officer</dt>
        <dd>
          {c.investigating_officer_name}{" "}
          {c.investigating_officer_contact && `· ${c.investigating_officer_contact}`}
        </dd>
        <dt>Received as</dt>
        <dd>
          {c.source} {c.submission_reference && `(${c.submission_reference})`}
        </dd>
        <dt>Case information</dt>
        <dd>{c.case_information || "—"}</dd>
      </dl>
      {detail.data.subcases.map((s) => (
        <SubcasePanel key={s.id} subcase={s} />
      ))}
    </section>
  );
}

function SubcasePanel({ subcase }: { subcase: Subcase }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const me = useMe();
  const roles = me.data?.roles ?? [];
  const reception = roles.includes("case_scientist") || roles.includes("screening_lab_officer");
  const exhibits = useQuery({
    queryKey: ["exhibits", subcase.id],
    queryFn: () => api<Exhibit[]>(`/subcases/${subcase.id}/exhibits`),
  });
  const receipts = useQuery({
    queryKey: ["receipts", subcase.id],
    queryFn: () => api<ReceiptSummary[]>(`/subcases/${subcase.id}/receipts`),
  });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["exhibits", subcase.id] });
    qc.invalidateQueries({ queryKey: ["receipts", subcase.id] });
    qc.invalidateQueries({ queryKey: ["case"] });
  };
  const prepare = useMutation({
    mutationFn: () =>
      post<Receipt>(`/subcases/${subcase.id}/receipts`, { exhibit_ids: [...selected] }),
    onSuccess: (r) => navigate(`/receipts/${r.id}`),
  });

  return (
    <div className="panel">
      <h3>
        Laboratory subcase {subcase.subcase_number} <span className="pill">{subcase.state}</span>
      </h3>
      <AssignScientist subcase={subcase} onDone={refresh} />
      <table>
        <thead>
          <tr>
            <th />
            <th>Exhibit</th>
            <th>Description</th>
            <th>Marking / seal</th>
            <th>Status</th>
            <th>Examiner</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {exhibits.data?.map((e) => (
            <tr key={e.id}>
              <td>
                {e.state === "accepted" && !e.receipt_id && (
                  <input
                    type="checkbox"
                    aria-label={`Select ${e.barcode} for receipt`}
                    checked={selected.has(e.id)}
                    onChange={() => {
                      const next = new Set(selected);
                      if (next.has(e.id)) next.delete(e.id);
                      else next.add(e.id);
                      setSelected(next);
                    }}
                  />
                )}
              </td>
              <td>
                <Link to={`/custody?item=${e.barcode}`}>{e.barcode}</Link>
                {e.submitter_item_ref && <div className="muted">{e.submitter_item_ref}</div>}
              </td>
              <td>{e.description}</td>
              <td>
                {e.marking || "—"} / {e.seal || "—"}
              </td>
              <td>
                <span className={`pill ${e.state}`}>{e.state}</span>
                {e.rejection_reason && <div className="muted">{e.rejection_reason}</div>}
                {e.check_notes && <div className="muted">{e.check_notes}</div>}
              </td>
              <td>{e.examiner?.display_name ?? "—"}</td>
              <td>
                <ExhibitActions exhibit={e} reception={reception} onDone={refresh} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {reception && subcase.state === "open" && <AddExhibit subcaseId={subcase.id} onDone={refresh} />}
      {reception && (
        <div className="actions">
          <button disabled={selected.size === 0 || prepare.isPending} onClick={() => prepare.mutate()}>
            Prepare receipt for {selected.size} selected exhibit{selected.size === 1 ? "" : "s"}
          </button>
          <ErrorText error={prepare.error} />
        </div>
      )}
      <h4>Receipts</h4>
      <ul>
        {receipts.data?.map((r) => (
          <li key={r.id}>
            <Link to={`/receipts/${r.id}`}>{r.receipt_number}</Link>{" "}
            <span className={`pill ${r.state}`}>{r.state}</span> {fmt(r.completed_at ?? r.created_at)}
          </li>
        ))}
        {receipts.data?.length === 0 && <li className="muted">None yet</li>}
      </ul>
    </div>
  );
}

function AssignScientist({ subcase, onDone }: { subcase: Subcase; onDone: () => void }) {
  const me = useMe();
  const staff = useStaff();
  const [userId, setUserId] = useState("");
  const [reason, setReason] = useState("");
  const assign = useMutation({
    mutationFn: () =>
      post(`/subcases/${subcase.id}/assignment`, { user_id: userId, reason: reason || null }),
    onSuccess: () => {
      setUserId("");
      setReason("");
      onDone();
    },
  });
  const canAssign = me.data?.roles.some((r) => r === "case_scientist" || r === "reviewer");
  return (
    <p className="inline">
      Case Scientist: <strong>{subcase.case_scientist?.display_name ?? "unassigned"}</strong>
      {canAssign && subcase.state === "open" && (
        <>
          <select value={userId} onChange={(e) => setUserId(e.target.value)}>
            <option value="">Assign…</option>
            {staff.data
              ?.filter((s) => s.roles.includes("case_scientist"))
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.display_name}
                </option>
              ))}
          </select>
          {subcase.case_scientist && (
            <input
              placeholder="Reason for reassignment"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          )}
          <button disabled={!userId || assign.isPending} onClick={() => assign.mutate()}>
            Assign
          </button>
        </>
      )}
      <ErrorText error={assign.error} />
    </p>
  );
}

function AddExhibit({ subcaseId, onDone }: { subcaseId: string; onDone: () => void }) {
  const empty = { description: "", marking: "", seal: "", submitter_item_ref: "" };
  const [form, setForm] = useState(empty);
  const add = useMutation({
    mutationFn: () =>
      post(`/subcases/${subcaseId}/exhibits`, {
        description: form.description,
        marking: form.marking || null,
        seal: form.seal || null,
        submitter_item_ref: form.submitter_item_ref || null,
      }),
    onSuccess: () => {
      setForm(empty);
      onDone();
    },
  });
  return (
    <form
      className="inline"
      onSubmit={(e) => {
        e.preventDefault();
        add.mutate();
      }}
    >
      <input
        placeholder="Submitter's item no."
        value={form.submitter_item_ref}
        onChange={(e) => setForm({ ...form, submitter_item_ref: e.target.value })}
      />
      <input
        placeholder="Description"
        value={form.description}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
        required
      />
      <input
        placeholder="Marking"
        value={form.marking}
        onChange={(e) => setForm({ ...form, marking: e.target.value })}
      />
      <input
        placeholder="Seal"
        value={form.seal}
        onChange={(e) => setForm({ ...form, seal: e.target.value })}
      />
      <button disabled={add.isPending}>Add exhibit</button>
      <ErrorText error={add.error} />
    </form>
  );
}

function ExhibitActions({
  exhibit,
  reception,
  onDone,
}: {
  exhibit: Exhibit;
  reception: boolean;
  onDone: () => void;
}) {
  const me = useMe();
  const [checking, setChecking] = useState(false);
  const [checks, setChecks] = useState({
    description_matches: true,
    marking_matches: true,
    seal_intact: true,
  });
  const [notes, setNotes] = useState("");
  const act = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) =>
      post(`/exhibits/${exhibit.id}/${path}`, body),
    onSuccess: () => {
      setChecking(false);
      onDone();
    },
  });
  const allOk = checks.description_matches && checks.marking_matches && checks.seal_intact;
  const isSlo = me.data?.roles.includes("screening_lab_officer");

  if (exhibit.state === "submitted" && reception) {
    if (!checking) return <button onClick={() => setChecking(true)}>Check…</button>;
    return (
      <div className="checkform">
        {(
          [
            ["description_matches", "Description matches"],
            ["marking_matches", "Marking matches"],
            ["seal_intact", "Seal intact"],
          ] as const
        ).map(([k, label]) => (
          <label key={k}>
            <input
              type="checkbox"
              checked={checks[k]}
              onChange={() => setChecks({ ...checks, [k]: !checks[k] })}
            />
            {label}
          </label>
        ))}
        <input
          placeholder={allOk ? "Notes (optional)" : "Explain the discrepancy, or the rejection reason"}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <div className="actions">
          <button
            disabled={!allOk && notes.trim().length < 3}
            onClick={() => act.mutate({ path: "accept", body: { ...checks, notes: notes || null } })}
          >
            Accept
          </button>
          <button
            disabled={notes.trim().length < 3}
            onClick={() => act.mutate({ path: "reject", body: { ...checks, reason: notes } })}
          >
            Reject
          </button>
          <button onClick={() => setChecking(false)}>Cancel</button>
        </div>
        <ErrorText error={act.error} />
      </div>
    );
  }
  if ((exhibit.state === "accepted" || exhibit.state === "rejected") && reception && !exhibit.receipt_id) {
    return (
      <>
        <ReasonAction
          label="Reconsider"
          prompt="Reason for reconsidering"
          pending={act.isPending}
          onConfirm={(reason) => act.mutate({ path: "reconsider", body: { reason } })}
        />
        <ErrorText error={act.error} />
      </>
    );
  }
  if (exhibit.state === "received" && !exhibit.examiner && isSlo) {
    return (
      <>
        <button onClick={() => act.mutate({ path: "examination", body: {} })}>
          Claim examination
        </button>
        <ErrorText error={act.error} />
      </>
    );
  }
  return null;
}
