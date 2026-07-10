// Anonymous learner identity: a client-minted UUID sent as X-Session-Id.
// No account, no personal data — just continuity for saves and path progress.

const KEY = "faithbrains.session.v1";

export function sessionId(): string {
  if (typeof window === "undefined") return "";
  let id = window.localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(KEY, id);
  }
  return id;
}

export function sessionHeaders(): Record<string, string> {
  const id = sessionId();
  return id ? { "X-Session-Id": id } : {};
}
