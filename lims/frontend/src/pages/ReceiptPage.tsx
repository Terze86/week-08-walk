import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, getDevUser, post } from "../api/client";
import { fmt } from "../api/hooks";
import type { ExceptionKind, Exhibit, Receipt } from "../api/types";
import ErrorText from "../components/ErrorText";
import ReasonAction from "../components/ReasonAction";
import SignaturePad from "../components/SignaturePad";

const EXCEPTIONS: Record<ExceptionKind, string> = {
  submitter_refused: "Submitter refused to sign",
  signature_failed: "Signature could not be captured",
  handover_other: "Other handover problem",
};

export default function ReceiptPage() {
  const { receiptId } = useParams();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const receipt = useQuery({
    queryKey: ["receipt", receiptId],
    queryFn: () => api<Receipt>(`/receipts/${receiptId}`),
  });
  const [submitter, setSubmitter] = useState("");
  const [signature, setSignature] = useState<string | null>(null);
  const [exceptionKind, setExceptionKind] = useState<ExceptionKind>("submitter_refused");
  useEffect(() => {
    if (receipt.data?.actual_submitter_name) setSubmitter(receipt.data.actual_submitter_name);
  }, [receipt.data?.actual_submitter_name]);

  const act = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) =>
      post<Receipt>(`/receipts/${receiptId}/${path}`, body),
    onSuccess: (r) => {
      qc.setQueryData(["receipt", receiptId], r);
      qc.invalidateQueries({ queryKey: ["exhibits", r.subcase_id] });
      qc.invalidateQueries({ queryKey: ["receipts", r.subcase_id] });
    },
  });

  if (receipt.error) return <ErrorText error={receipt.error} />;
  const r = receipt.data;
  if (!r) return <p>Loading…</p>;

  return (
    <section className="receipt">
      <h2>
        Exhibit receipt {r.receipt_number} <span className={`pill ${r.state}`}>{r.state}</span>
      </h2>
      <p className="muted noprint">
        Prepared by {r.prepared_by?.display_name} · {fmt(r.created_at)}
      </p>
      <h3>Exhibits received</h3>
      <ExhibitTable exhibits={r.accepted_exhibits} />
      {r.rejected_exhibits.length > 0 && (
        <>
          <h3>Exhibits not accepted</h3>
          <ExhibitTable exhibits={r.rejected_exhibits} rejected />
        </>
      )}

      {r.state === "completed" && (
        <dl className="facts">
          <dt>Handed over by</dt>
          <dd>{r.actual_submitter_name}</dd>
          <dt>Signature</dt>
          <dd>
            <SignatureImage receiptId={r.id} />
          </dd>
          <dt>Received by</dt>
          <dd>{r.receiving_staff?.display_name}</dd>
          <dt>Completed</dt>
          <dd>{fmt(r.completed_at)}</dd>
        </dl>
      )}

      {r.state === "draft" && (
        <div className="panel noprint">
          <h3>Handover</h3>
          <label>
            Name of the person handing over the exhibits
            <input value={submitter} onChange={(e) => setSubmitter(e.target.value)} />
          </label>
          <p className="muted">Ask the submitter to sign below.</p>
          <SignaturePad onChange={setSignature} />
          <div className="actions">
            <button
              disabled={!signature || !submitter.trim() || act.isPending}
              onClick={() =>
                act.mutate({
                  path: "complete",
                  body: { actual_submitter_name: submitter, signature_png_base64: signature },
                })
              }
            >
              Complete receipt (I am receiving these exhibits)
            </button>
          </div>
          <h4>Could not complete?</h4>
          <div className="inline">
            <select
              value={exceptionKind}
              onChange={(e) => setExceptionKind(e.target.value as ExceptionKind)}
            >
              {Object.entries(EXCEPTIONS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <ReasonAction
              label="Record exception"
              prompt="What happened?"
              onConfirm={(note) => act.mutate({ path: "exception", body: { kind: exceptionKind, note } })}
            />
            <ReasonAction
              label="Cancel receipt"
              prompt="Reason for cancelling"
              onConfirm={(note) => act.mutate({ path: "cancel", body: { note } })}
            />
          </div>
        </div>
      )}

      {r.state === "exception" && (
        <div className="panel noprint">
          <p>
            <strong>{r.exception_kind && EXCEPTIONS[r.exception_kind]}:</strong> {r.exception_note}
          </p>
          <div className="inline">
            <ReasonAction
              label="Try again"
              prompt="Follow-up taken"
              onConfirm={(note) => act.mutate({ path: "retry", body: { note } })}
            />
            <ReasonAction
              label="Cancel receipt"
              prompt="Reason for cancelling"
              onConfirm={(note) => act.mutate({ path: "cancel", body: { note } })}
            />
          </div>
        </div>
      )}
      <ErrorText error={act.error} />
      <p className="noprint">
        <button onClick={() => window.print()}>Print</button>{" "}
        <button onClick={() => navigate(-1)}>Back</button>
      </p>
    </section>
  );
}

function ExhibitTable({ exhibits, rejected }: { exhibits: Exhibit[]; rejected?: boolean }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Exhibit</th>
          <th>Submitter's no.</th>
          <th>Description</th>
          <th>Marking</th>
          <th>Seal</th>
          <th>{rejected ? "Reason not accepted" : "Check notes"}</th>
        </tr>
      </thead>
      <tbody>
        {exhibits.map((e) => (
          <tr key={e.id}>
            <td>{e.barcode}</td>
            <td>{e.submitter_item_ref}</td>
            <td>{e.description}</td>
            <td>{e.marking}</td>
            <td>{e.seal}</td>
            <td>{rejected ? e.rejection_reason : e.check_notes}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SignatureImage({ receiptId }: { receiptId: string }) {
  // Fetched with the auth header, then shown from a local object URL.
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let url: string | null = null;
    fetch(`/api/receipts/${receiptId}/signature`, { headers: { "X-Dev-User": getDevUser() ?? "" } })
      .then((res) => (res.ok ? res.blob() : null))
      .then((blob) => {
        if (blob) {
          url = URL.createObjectURL(blob);
          setSrc(url);
        }
      });
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [receiptId]);
  return src ? <img className="sig" src={src} alt="Submitter signature" /> : null;
}
