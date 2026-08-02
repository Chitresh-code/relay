const KEY = "relay_session_id";

export function getSessionId(): string {
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(KEY, id);
  }
  return id;
}

export function newSessionId(): string {
  const id = crypto.randomUUID();
  localStorage.setItem(KEY, id);
  return id;
}
