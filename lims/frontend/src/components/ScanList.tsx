import { useState } from "react";

// Barcode entry for keyboard-wedge scanners: each scan ends with Enter and is
// added to the list. Codes can also be typed.
export default function ScanList({
  label,
  value,
  onChange,
  placeholder = "Scan or type a barcode, then Enter",
}: {
  label: string;
  value: string[];
  onChange: (codes: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const code = draft.trim();
    if (code && !value.includes(code)) onChange([...value, code]);
    setDraft("");
  };
  return (
    <div className="scan">
      <label>
        {label}
        <input
          value={draft}
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
        />
      </label>
      <div className="chips">
        {value.map((code) => (
          <span key={code} className="chip">
            {code}
            <button
              type="button"
              aria-label={`Remove ${code}`}
              onClick={() => onChange(value.filter((c) => c !== code))}
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
