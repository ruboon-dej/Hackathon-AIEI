"use client";
import { useEffect, useRef, useState } from "react";

export default function CameraPreview() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState("init");

  useEffect(() => {
    let stream: MediaStream | null = null;
    let mounted = true;

    (async () => {
      try {
        setStatus("requesting getUserMedia");
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (!mounted) return;

        setStatus("got stream");
        const v = videoRef.current!;
        try { v.pause(); } catch {}
        v.muted = true;
        v.playsInline = true;
        (v as any).srcObject = stream;

        // Wait for metadata, then try play (ignore autoplay block errors)
        await new Promise<void>((res) => {
          const onLoaded = () => { v.removeEventListener("loadedmetadata", onLoaded); res(); };
          v.addEventListener("loadedmetadata", onLoaded);
          setTimeout(res, 500); // safety
        });

        setStatus("loadedmetadata, trying play");
        const p = v.play();
        if (p) {
          p.then(() => setStatus("playing")).catch((e) => {
            setStatus("needs user gesture: " + (e?.message || e));
          });
        } else {
          setStatus("playing (no promise)");
        }
      } catch (e: any) {
        setStatus(`error: ${e?.name || e?.message || String(e)}`);
      }
    })();

    return () => {
      mounted = false;
      const v = videoRef.current as any;
      const s: MediaStream | undefined = v?.srcObject;
      s?.getTracks().forEach((t) => t.stop());
      if (v) v.srcObject = null;
    };
  }, []);

  return (
    <div>
      <video
        ref={videoRef}
        autoPlay
        muted
        playsInline
        width={320}
        height={240}
        style={{ background: "#000", borderRadius: 8 }}
      />
      <div style={{ color: "#888", marginTop: 8, maxWidth: 340 }}>status: {status}</div>
      {status.startsWith("needs user gesture") && (
        <button
          onClick={() => videoRef.current?.play()}
          className="px-3 py-2 rounded bg-black text-white mt-2"
        >
          Enable camera
        </button>
      )}
    </div>
  );
}
