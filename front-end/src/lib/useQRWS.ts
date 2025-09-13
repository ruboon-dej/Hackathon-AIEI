"use client";
import { useEffect, useState } from "react";

export function useQRWS() {
  const [connected, setConnected] = useState(false);
  const [lastQR, setLastQR] = useState<string | null>(null);
  const [patient, setPatient] = useState<any>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE!;
    const ws = new WebSocket(base.replace("http", "ws") + "/ws/events");

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "qr_found") {
          setPatient(msg.patient);
          setLastQR(String(msg.patient?.HN ?? ""));
        } else if (msg.type === "qr_not_found") {
          setPatient({ found: false, hn: msg.hn });
          setLastQR(String(msg.hn ?? ""));
        }
      } catch {}
    };

    return () => ws.close();
  }, []);

  return { connected, lastQR, patient };
}
