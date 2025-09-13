export const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

export async function fetchPatient(qr: string) {
  const r = await fetch(`${API_BASE}/api/patient/${encodeURIComponent(qr)}`, { cache: "no-store" });
  return r.json();
}

export async function saveSession(payload: any) {
  const r = await fetch(`${API_BASE}/api/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return r.json();
}

export async function tts(text: string) {
  const r = await fetch(`${API_BASE}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return r.json(); // { url: string }
}
