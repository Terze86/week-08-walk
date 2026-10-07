import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api, post } from "../api/client";
import { fmt, placeLabel } from "../api/hooks";
import type { MyWork as Work } from "../api/types";
import ErrorText from "../components/ErrorText";
import ReasonAction from "../components/ReasonAction";
import { AcceptHandover } from "./Custody";

export default function MyWork({ title }: { title: string }) {
  const work = useQuery({ queryKey: ["my-work"], queryFn: () => api<Work>("/my-work") });
  if (work.error) return <ErrorText error={work.error} />;
  const w = work.data;
  if (!w) return <p>Loading…</p>;
  const empty =
    !w.subcases.length &&
    !w.examinations.length &&
    !w.incoming_handovers.length &&
    !w.receipt_exceptions.length &&
    !w.corrections_to_decide.length;
  return (
    <section>
      <h2>{title}: my work</h2>
      {empty && <p className="muted">Nothing is waiting for you.</p>}
      {w.incoming_handovers.length > 0 && (
        <div className="panel attention">
          <h3>Handovers waiting for you</h3>
          {w.incoming_handovers.map((h) => (
            <AcceptHandover key={h.id} handover={h} />
          ))}
        </div>
      )}
      {w.subcases.length > 0 && (
        <div className="panel">
          <h3>My subcases</h3>
          <ul>
            {w.subcases.map((s) => (
              <li key={s.id}>
                <Link to={`/cases/${s.case_id}`}>{s.subcase_number}</Link> · opened {fmt(s.created_at)}
              </li>
            ))}
          </ul>
        </div>
      )}
      {w.examinations.length > 0 && (
        <div className="panel">
          <h3>My exhibit examinations</h3>
          <ul>
            {w.examinations.map((e) => (
              <li key={e.id}>
                <Link to={`/custody?item=${e.barcode}`}>{e.barcode}</Link> {e.description}
              </li>
            ))}
          </ul>
        </div>
      )}
      {w.receipt_exceptions.length > 0 && (
        <div className="panel attention">
          <h3>Receipt exceptions to follow up</h3>
          <ul>
            {w.receipt_exceptions.map((r) => (
              <li key={r.id}>
                <Link to={`/receipts/${r.id}`}>{r.receipt_number}</Link> · {r.exception_note}
              </li>
            ))}
          </ul>
        </div>
      )}
      {w.corrections_to_decide.length > 0 && <Corrections work={w} />}
    </section>
  );
}

function Corrections({ work }: { work: Work }) {
  const qc = useQueryClient();
  const decide = useMutation({
    mutationFn: ({ id, authorize, note }: { id: string; authorize: boolean; note: string }) =>
      post(`/custody/corrections/${id}/decision`, { authorize, note }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-work"] }),
  });
  return (
    <div className="panel attention">
      <h3>Custody corrections to authorise</h3>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Recorded</th>
            <th>Corrected to</th>
            <th>Reason</th>
            <th>Requested by</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {work.corrections_to_decide.map((c) => (
            <tr key={c.id}>
              <td>{c.barcode}</td>
              <td>
                {placeLabel(c.original)} · {fmt(c.original.moved_at)}
              </td>
              <td>
                {placeLabel(c)} · {fmt(c.moved_at)}
              </td>
              <td>{c.reason}</td>
              <td>{c.requested_by?.display_name}</td>
              <td>
                <ReasonAction
                  label="Authorise"
                  prompt="Basis for authorising"
                  onConfirm={(note) => decide.mutate({ id: c.id, authorize: true, note })}
                />
                <ReasonAction
                  label="Decline"
                  prompt="Reason for declining"
                  onConfirm={(note) => decide.mutate({ id: c.id, authorize: false, note })}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ErrorText error={decide.error} />
    </div>
  );
}
