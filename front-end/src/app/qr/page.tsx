"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

const QRBOX = 300;
const DEDUPE_MS = 1500;

function parseHN(text: string): string {
  const t = String(text).trim();
  const m = t.match(/^[A-Z0-9-]{3,20}$/i);
  if (m) return m[0];
  const m2 = t.match(/\bHN[:\s#-]*([A-Z0-9-]{3,20})\b/i);
  return m2 ? m2[1] : "";
}

type CamDev = { id: string; label: string };

export default function QRScanPage() {
  const router = useRouter();

  const statusRef = useRef<HTMLSpanElement | null>(null);
  const hnRef = useRef<HTMLSpanElement | null>(null);
  const rawRef = useRef<HTMLSpanElement | null>(null);

  const [candidates, setCandidates] = useState<CamDev[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  const scannerRef = useRef<any>(null);
  const redirectedRef = useRef(false);
  const lastTextRef = useRef<string>("");
  const lastTsRef = useRef<number>(0);

  function setStatus(msg: string, err = false) {
    if (statusRef.current) {
      statusRef.current.textContent = msg;
      statusRef.current.className = err ? "err" : "ok";
    }
  }

  async function getHtml5Qrcode() {
    const mod: any = await import("html5-qrcode");
    return mod.Html5Qrcode ?? mod.default?.Html5Qrcode ?? mod;
  }

  async function buildCameraList() {
    try {
      const mod: any = await import("html5-qrcode");
      const Html5Qrcode = mod.Html5Qrcode ?? mod.default?.Html5Qrcode ?? mod;
      const devs = await Html5Qrcode.getCameras();
      if (!devs.length) {
        setStatus("No camera found", true);
        return;
      }
      const cleaned: CamDev[] = devs.map((d: any, i: number) => ({
        id: d.id,
        label: d.label || `Camera ${i + 1}`,
      }));
      setCandidates(cleaned);
    } catch {
      setStatus("Camera unavailable", true);
    }
  }

  async function stopScan() {
    if (!scannerRef.current) return;
    try {
      await scannerRef.current.stop();
      await scannerRef.current.clear();
    } catch {}
    scannerRef.current = null;
  }

  async function tryStartOn(id: string) {
    const Html5Qrcode: any = await getHtml5Qrcode();
    const s = new Html5Qrcode("reader");
    try {
      await s.start(
        { deviceId: { exact: id } },
        { fps: 10, qrbox: QRBOX },
        onScanSuccess,
        () => {}
      );
      scannerRef.current = s;
      setActiveId(id);
      setStatus(`Scanning…`);
      return true;
    } catch {
      await s.clear().catch(() => {});
      return false;
    }
  }

  async function startFirstWorkingCamera() {
    setStatus("Starting camera…");
    for (const dev of candidates) {
      const ok = await tryStartOn(dev.id);
      if (ok) return;
    }
    setStatus("Failed to start any camera", true);
  }

  function onScanSuccess(decodedText: string) {
    const now = Date.now();
    if (decodedText === lastTextRef.current && now - lastTsRef.current < DEDUPE_MS) return;
    lastTextRef.current = decodedText;
    lastTsRef.current = now;

    if (rawRef.current) rawRef.current.textContent = decodedText;
    const hn = parseHN(decodedText);
    if (hnRef.current) hnRef.current.textContent = hn || "Not found";
    if (!hn || redirectedRef.current) return;

    redirectedRef.current = true;
    stopScan().finally(() => {
      // Redirect to another page with HN in query
      router.push(`/patient?hn=${encodeURIComponent(hn)}`);
    });
  }

  useEffect(() => {
    buildCameraList();
    return () => { stopScan(); };
  }, []);

  useEffect(() => {
    if (candidates.length) startFirstWorkingCamera();
    return () => { stopScan(); };
  }, [candidates]);

  return (
    <main className="screen">
      <h1 className="title">Scan QR</h1>
      <div id="reader" className="reader" />
      <div className="status">
        <span ref={statusRef}>Idle</span>
        <span> | HN: <b ref={hnRef}>—</b></span>
        <span> | Raw: <span ref={rawRef}>—</span></span>
      </div>

      <style jsx>{`
        .screen {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          background: #0e0e0f;
          color: #fff;
          padding: 16px;
        }
        .title { font-weight: 600; }
        .reader {
          width: min(90vw, 420px);
          height: min(90vw, 420px);
          background: #111;
          border-radius: 14px;
          overflow: hidden;
          box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        }
        .status {
          width: min(90vw, 720px);
          padding: 10px 14px;
          color: #111;
          background: #f3f4f6;
          border-radius: 10px;
        }
        .ok { color: #10b981 } .err { color: #ef4444 }
      `}</style>
    </main>
  );
}
