"use client";
import { useEffect, useState } from "react";

export function useEventWS() {
  const [mode, setMode] = useState<"idle" | "active">("idle");

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE!;
    const ws = new WebSocket(base.replace("http", "ws") + "/ws/events");

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "person_detected") setMode("active");
        if (msg.type === "reset_idle") setMode("idle");
      } catch {}
    };

    return () => ws.close();
  }, []);

  return { mode };
}
