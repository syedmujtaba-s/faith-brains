// Anonymous learner identity: a client-minted UUID sent as X-Session-Id.
// No account, no personal data — just continuity for saves and path progress.

const KEY = "faithbrains.session.v1";

function makeId(): string {
  // crypto.randomUUID exists only in secure contexts (https/localhost);
  // the beta serves over plain http, so fall back to getRandomValues.
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && crypto.getRandomValues) crypto.getRandomValues(bytes);
  else for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function sessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = window.localStorage.getItem(KEY);
    if (!id) {
      id = makeId();
      window.localStorage.setItem(KEY, id);
    }
    return id;
  } catch {
    return ""; // storage blocked — features degrade gracefully, nothing crashes
  }
}

export function sessionHeaders(): Record<string, string> {
  const id = sessionId();
  return id ? { "X-Session-Id": id } : {};
}
