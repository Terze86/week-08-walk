// Thin typed wrapper over fetch. In dev mode the signed-in user is sent as
// X-Dev-User; in production the OIDC access token is sent as a bearer token.

const DEV_USER_KEY = "lims.devUser";

export function getDevUser(): string | null {
  try {
    return localStorage.getItem(DEV_USER_KEY);
  } catch {
    return null;
  }
}

export function setDevUser(username: string | null): void {
  try {
    if (username) localStorage.setItem(DEV_USER_KEY, username);
    else localStorage.removeItem(DEV_USER_KEY);
  } catch {
    // Storage unavailable (private mode); the session simply won't persist.
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public rule?: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const user = getDevUser();
  if (user) headers.set("X-Dev-User", user);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) {
    let body: { code?: string; message?: string; detail?: unknown; rule?: string } = {};
    try {
      body = await res.json();
    } catch {
      // non-JSON error body
    }
    const message =
      body.message ?? (typeof body.detail === "string" ? body.detail : res.statusText);
    throw new ApiError(res.status, body.code ?? "error", message, body.rule);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const post = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "PUT", body: JSON.stringify(body) });
