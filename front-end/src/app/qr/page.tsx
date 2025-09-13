"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000").replace(/\/$/, "");

type Cam = { id: string; label: string };

export default function QRScanPage() {
  const mountId = "qr-reader";
  const scannerRef = useRef<any>(null);
  const startedRef = useRef(false);      // guard Strict Mode double init
  const handledRef = useRef(false);      // ensure we handle first scan only
  const stoppingRef = useRef(false);     // prevent double stop()

  const [cams, setCams] = useState<Cam[]>([]);
  const [camId, setCamId] = useState("");
  const [status, setStatus] = useState("idle");
  const [hn, setHn] = useState<string | null>(null);
  const [sent, setSent] = useState<"" | "waiting" | "ok" | "fail">("");

  // stop/clear but ignore "not running" errors
  const safeStop = async () => {
    const s = scannerRef.current;
    if (!s || stoppingRef.current) return;
    stoppingRef.current = true;
    try {
      // Some versions expose isScanning(); if not, just try/await stop().
      const maybeFn = (s as any).isScanning;
      const isScanning = typeof maybeFn === "function" ? maybeFn.call(s) : true;
      if (isScanning) await s.stop();
    } catch (_) { /* ignore "not running" */ }
    try { await s.clear?.(); } catch (_) {}
    stoppingRef.current = false;
  };

  useEffect(() => {
    let mounted = true;
    if (startedRef.current) return; // Strict Mode guard
    startedRef.current = true;

    (async () => {
      try {
        setStatus("starting");
        const { Html5Qrcode, Html5QrcodeSupportedFormats } = await import("html5-qrcode");

        const list = await (Html5Qrcode as any).getCameras?.();
        const available: Cam[] = (list || []).map((c: any) => ({ id: c.id, label: c.label || "Camera" }));
        if (!mounted) return;

        setCams(available);
        const preferred = available.find(c => /back|rear/i.test(c.label))?.id || available[0]?.id;
        if (!preferred) { setStatus("no-camera"); return; }
        setCamId(prev => prev || preferred);

        const s = new Html5Qrcode(mountId, { verbose: false });
        scannerRef.current = s;

        await s.start(
          camId || preferred,
          { fps: 10, qrbox: { width: 250, height: 250 }, formatsToSupport: [(Html5QrcodeSupportedFormats as any).QR_CODE] },
          async (decodedText: string) => {
            if (!mounted || handledRef.current) return;
            handledRef.current = true;

            const code = decodedText.trim();
            if (!code) return;

            setHn(code);
            setStatus("scanned");
            setSent("waiting");

            await safeStop(); // stop safely; ignore if already stopped

            // Send HN to backend so other pages update via WS
            try {
              const r = await fetch(`${API_BASE}/trigger/qr`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ hn: code }),
              });
              setSent(r.ok ? "ok" : "fail");
            } catch {
              setSent("fail");
            }
          },
          () => {} // ignore per-frame decode errors
        );

        if (!mounted) return;
        setStatus("scanning");
      } catch (e) {
        console.error(e);
        setStatus("error");
      }
    })();

    return () => {
      mounted = false;
      safeStop();               // cleanup tries once, safely
      startedRef.current = false;
    };
  }, [camId]); // you can remove camId here if you don't need camera switching

  const rescan = () => {
    // simplest: full reload to re-init scanner cleanly
    window.location.reload();
  };

  return (
    <main style={{ maxWidth: 760, margin: "40px auto", padding: 16 }}>
      <h1>QR Scan → Send HN to Backend</h1>

      <div style={{ marginTop: 12 }}>
        <label style={{ fontSize: 14, color: "#666" }}>Camera:&nbsp;</label>
        <select value={camId} onChange={(e) => setCamId(e.target.value)} style={{ padding: 6 }}>
          {cams.length === 0 && <option value="">(no camera)</option>}
          {cams.map((c) => <option key={c.id} value={c.id}>{c.label || c.id}</option>)}
        </select>
      </div>

      {status !== "scanned" && <div id="qr-reader" style={{ marginTop: 16 }} />}

      <p style={{ color: "#777", marginTop: 8 }}>
        status: {status}{hn ? ` · HN: ${hn}` : ""}{sent ? ` · POST: ${sent}` : ""}
      </p>

      {hn && (
        <div style={{ marginTop: 16, padding: 12, border: "1px solid #eee", borderRadius: 8 }}>
          <div><b>Decoded HN:</b> <code>{hn}</code></div>
          <button onClick={rescan} style={{ marginTop: 12, padding: "8px 12px" }}>Scan again</button>
        </div>
      )}
    </main>
  );
}
