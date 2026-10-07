import { useState } from "react";

// A button that asks for a mandatory reason inline before running an action.
export default function ReasonAction({
  label,
  prompt,
  onConfirm,
  pending,
}: {
  label: string;
  prompt: string;
  onConfirm: (reason: string) => void;
  pending?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  if (!open) return <button onClick={() => setOpen(true)}>{label}</button>;
  return (
    <form
      className="inline"
      onSubmit={(e) => {
        e.preventDefault();
        onConfirm(reason.trim());
      }}
    >
      <input
        autoFocus
        placeholder={prompt}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <button disabled={reason.trim().length < 3 || pending}>{label}</button>
      <button type="button" onClick={() => setOpen(false)}>
        Cancel
      </button>
    </form>
  );
}
