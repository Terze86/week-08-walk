import { useState } from "react";

// Development-only sign-in. Production builds authenticate through the
// organisation's OIDC provider instead; the API rejects dev headers there.
const DEV_USERS = ["admin1", "cs1", "cs2", "slo1", "dlo1", "dlo2", "rev1", "codis1"];

export default function DevSignIn({
  error,
  onSignIn,
}: {
  error?: string;
  onSignIn: (username: string) => void;
}) {
  const [username, setUsername] = useState(DEV_USERS[0]);
  return (
    <form
      className="signin"
      onSubmit={(e) => {
        e.preventDefault();
        onSignIn(username);
      }}
    >
      <h1>DNA LIMS</h1>
      <p className="muted">Development sign-in</p>
      <label>
        Account
        <select value={username} onChange={(e) => setUsername(e.target.value)}>
          {DEV_USERS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </select>
      </label>
      <button type="submit">Sign in</button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
