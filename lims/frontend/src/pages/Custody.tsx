import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, post } from "../api/client";
import { fmt, placeLabel, useLocations, useMe, useStaff } from "../api/hooks";
import type { Handover, Item, Movement } from "../api/types";
import ErrorText from "../components/ErrorText";
import ScanList from "../components/ScanList";

export default function Custody() {
  return (
    <section>
      <h2>Custody</h2>
      <Incoming />
      <div className="columns">
        <MoveItems />
        <OfferHandover />
      </div>
      <ItemLookup />
    </section>
  );
}

function ItemLookup() {
  const [params, setParams] = useSearchParams();
  const barcode = params.get("item") ?? "";
  const [draft, setDraft] = useState(barcode);
  const item = useQuery({
    queryKey: ["item", barcode],
    queryFn: () => api<Item>(`/custody/items/${encodeURIComponent(barcode)}`),
    enabled: barcode !== "",
  });
  return (
    <div className="panel">
      <h3>Item history</h3>
      <form
        className="inline"
        onSubmit={(e) => {
          e.preventDefault();
          setParams(draft.trim() ? { item: draft.trim() } : {});
        }}
      >
        <input placeholder="Scan an item" value={draft} onChange={(e) => setDraft(e.target.value)} />
        <button>Show</button>
      </form>
      <ErrorText error={item.error} />
      {item.data && (
        <>
          <p>
            <strong>{item.data.barcode}</strong> {item.data.label} · now with{" "}
            <strong>{item.data.current ? placeLabel(item.data.current) : "nobody (not received)"}</strong>
          </p>
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>What</th>
                <th>From</th>
                <th>To</th>
                <th>Recorded by</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {item.data.history.map((entry) => (
                <tr key={entry.movement.id} className={entry.original ? "corrected" : ""}>
                  <td>{fmt(entry.movement.moved_at)}</td>
                  <td>
                    {entry.original ? "correction of " + entry.original.kind : entry.movement.kind}
                    {entry.original && (
                      <div className="muted">
                        originally recorded: {placeLabel(entry.original)} at{" "}
                        {fmt(entry.original.moved_at)}
                      </div>
                    )}
                    {entry.movement.note && <div className="muted">{entry.movement.note}</div>}
                  </td>
                  <td>
                    {placeLabel({
                      to_person: entry.movement.from_person,
                      to_location: entry.movement.from_location,
                    })}
                  </td>
                  <td>{placeLabel(entry.movement)}</td>
                  <td>{entry.movement.recorded_by?.display_name}</td>
                  <td>
                    <RequestCorrection movement={entry.original ?? entry.movement} barcode={barcode} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function RequestCorrection({ movement, barcode }: { movement: Movement; barcode: string }) {
  const qc = useQueryClient();
  const locations = useLocations();
  const staff = useStaff();
  const me = useMe();
  const authorizer = me.data?.roles.some((r) => r === "case_scientist" || r === "reviewer");
  const [open, setOpen] = useState(false);
  const [locationId, setLocationId] = useState("");
  const [personId, setPersonId] = useState("");
  const [reason, setReason] = useState("");
  const request = useMutation({
    mutationFn: (authorizeNow: boolean) =>
      post(`/custody/movements/${movement.id}/corrections`, {
        reason,
        to_location_id: locationId || null,
        to_person_id: personId || null,
        authorize_now: authorizeNow,
      }),
    onSuccess: () => {
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["item", barcode] });
    },
  });
  if (!open) return <button onClick={() => setOpen(true)}>Correct…</button>;
  return (
    <div className="checkform">
      <select value={personId} onChange={(e) => setPersonId(e.target.value)}>
        <option value="">No person</option>
        {staff.data?.map((s) => (
          <option key={s.id} value={s.id}>
            {s.display_name}
          </option>
        ))}
      </select>
      <select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
        <option value="">No location</option>
        {locations.data?.filter((l) => l.active).map((l) => (
          <option key={l.id} value={l.id}>
            {l.code} {l.name}
          </option>
        ))}
      </select>
      <input placeholder="Reason (required)" value={reason} onChange={(e) => setReason(e.target.value)} />
      <div className="actions">
        <button disabled={reason.trim().length < 3} onClick={() => request.mutate(false)}>
          Request correction
        </button>
        {authorizer && (
          <button disabled={reason.trim().length < 3} onClick={() => request.mutate(true)}>
            Correct and authorise
          </button>
        )}
        <button onClick={() => setOpen(false)}>Cancel</button>
      </div>
      <ErrorText error={request.error} />
    </div>
  );
}

function MoveItems() {
  const qc = useQueryClient();
  const locations = useLocations();
  const [items, setItems] = useState<string[]>([]);
  const [checked, setChecked] = useState<string[]>([]);
  const [locationId, setLocationId] = useState("");
  const [keep, setKeep] = useState(false);
  const move = useMutation({
    mutationFn: () =>
      post<Item[]>("/custody/move", {
        barcodes: items,
        verified_barcodes: checked,
        to_location_id: locationId || null,
        keep_with_me: keep,
      }),
    onSuccess: () => {
      setItems([]);
      setChecked([]);
      qc.invalidateQueries({ queryKey: ["item"] });
    },
  });
  const unchecked = items.filter((c) => !checked.includes(c));
  return (
    <div className="panel">
      <h3>Store, retrieve or move</h3>
      <ScanList label="1. Select items" value={items} onChange={setItems} />
      <label>
        2. Destination
        <select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
          <option value="">(no location)</option>
          {locations.data?.filter((l) => l.active).map((l) => (
            <option key={l.id} value={l.id}>
              {l.code} {l.name}
            </option>
          ))}
        </select>
      </label>
      <label className="check">
        <input type="checkbox" checked={keep} onChange={() => setKeep(!keep)} />
        Keep the items with me
      </label>
      <ScanList label="3. Check each item before completing" value={checked} onChange={setChecked} />
      {items.length > 0 && unchecked.length > 0 && (
        <p className="muted">Still to check: {unchecked.join(", ")}</p>
      )}
      <button
        disabled={items.length === 0 || unchecked.length > 0 || (!locationId && !keep) || move.isPending}
        onClick={() => move.mutate()}
      >
        Complete movement
      </button>
      {move.isSuccess && <p className="ok">Movement recorded.</p>}
      <ErrorText error={move.error} />
    </div>
  );
}

function OfferHandover() {
  const staff = useStaff();
  const me = useMe();
  const [items, setItems] = useState<string[]>([]);
  const [checked, setChecked] = useState<string[]>([]);
  const [to, setTo] = useState("");
  const [note, setNote] = useState("");
  const offer = useMutation({
    mutationFn: () =>
      post("/custody/handovers", {
        barcodes: items,
        verified_barcodes: checked,
        to_person_id: to,
        note: note || null,
      }),
    onSuccess: () => {
      setItems([]);
      setChecked([]);
      setNote("");
    },
  });
  const unchecked = items.filter((c) => !checked.includes(c));
  return (
    <div className="panel">
      <h3>Hand over to a colleague</h3>
      <ScanList label="1. Items you hold" value={items} onChange={setItems} />
      <label>
        2. Receiving person
        <select value={to} onChange={(e) => setTo(e.target.value)}>
          <option value="">Select…</option>
          {staff.data
            ?.filter((s) => s.id !== me.data?.id)
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.display_name}
              </option>
            ))}
        </select>
      </label>
      <input placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
      <ScanList label="3. Check each item" value={checked} onChange={setChecked} />
      <button
        disabled={items.length === 0 || unchecked.length > 0 || !to || offer.isPending}
        onClick={() => offer.mutate()}
      >
        Offer handover
      </button>
      {offer.isSuccess && <p className="ok">Waiting for the receiver to accept.</p>}
      <ErrorText error={offer.error} />
    </div>
  );
}

function Incoming() {
  const handovers = useQuery({
    queryKey: ["incoming"],
    queryFn: () => api<Handover[]>("/custody/handovers/incoming"),
  });
  if (!handovers.data?.length) return null;
  return (
    <div className="panel attention">
      <h3>Handovers waiting for you</h3>
      {handovers.data.map((h) => (
        <AcceptHandover key={h.id} handover={h} />
      ))}
    </div>
  );
}

export function AcceptHandover({ handover }: { handover: Handover }) {
  const qc = useQueryClient();
  const [checked, setChecked] = useState<string[]>([]);
  const accept = useMutation({
    mutationFn: () =>
      post(`/custody/handovers/${handover.id}/accept`, {
        barcodes: checked,
        verified_barcodes: checked,
      }),
    onSuccess: () => {
      setChecked([]);
      qc.invalidateQueries({ queryKey: ["incoming"] });
      qc.invalidateQueries({ queryKey: ["my-work"] });
    },
  });
  const expected = handover.items.map((i) => i.barcode);
  return (
    <div>
      <p>
        From <strong>{handover.from_person?.display_name}</strong> · {fmt(handover.created_at)}{" "}
        {handover.note && `· ${handover.note}`}
      </p>
      <ul>
        {handover.items.map((i) => (
          <li key={i.id}>
            {checked.includes(i.barcode) ? "✓ " : ""}
            {i.barcode} {i.label}
          </li>
        ))}
      </ul>
      <ScanList label="Scan the items you are accepting" value={checked} onChange={setChecked} />
      <button
        disabled={checked.length === 0 || checked.some((c) => !expected.includes(c)) || accept.isPending}
        onClick={() => accept.mutate()}
      >
        Accept {checked.length} item{checked.length === 1 ? "" : "s"}
      </button>
      <ErrorText error={accept.error} />
    </div>
  );
}
