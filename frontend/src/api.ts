import type { ToolName } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type StreamEvent =
  | { type: "token"; text: string }
  | { type: "component"; tool: ToolName; content: any }
  | { type: "done" }
  | { type: "error"; message: string };

// Hand-rolled SSE parsing over fetch + ReadableStream: EventSource can't send a POST body,
// and this is small enough not to need a client library (ARCHITECTURE.md §5).
export async function* streamChat(sessionId: string, message: string): AsyncGenerator<StreamEvent> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  } catch {
    yield { type: "error", message: "Couldn't reach the server. Is the backend running?" };
    return;
  }

  if (!res.ok || !res.body) {
    const message = res.status === 429 ? "You're sending messages too fast — try again in a minute." : `Request failed (${res.status})`;
    yield { type: "error", message };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      let event = "";
      let data = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!event || !data) continue;
      const payload = JSON.parse(data);
      if (event === "token") yield { type: "token", text: payload.text };
      else if (event === "component") yield { type: "component", tool: payload.tool, content: payload.content };
      else if (event === "done") yield { type: "done" };
      else if (event === "error") yield { type: "error", message: payload.message };
    }
  }
}

export async function submitContact(sessionId: string, reason: string, email: string): Promise<void> {
  await fetch(`${API_BASE}/contact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, reason, email }),
  });
}
