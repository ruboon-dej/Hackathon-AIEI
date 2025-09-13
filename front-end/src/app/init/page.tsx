"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import { useRouter } from "next/navigation";

export default function FaceDetectRoute() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [modelLoaded, setModelLoaded] = useState(false);

  // autoplay/audio unlock
  const audioRef = useRef<HTMLAudioElement>(null);
  const [blocked, setBlocked] = useState(false);

  // detection → 3s redirect
  const [detected, setDetected] = useState(false);
  const routedRef = useRef(false);
  const timeoutRef = useRef<number | null>(null);

  const router = useRouter();

  // --- audio autoplay try ---
  useEffect(() => {
    const a = audioRef.current!;
    a.volume = 1;
    a.preload = "auto";
    a.load();
    (async () => {
      try {
        await a.play();
        setBlocked(false);
      } catch {
        setBlocked(true);
      }
    })();
    return () => {
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    };
  }, []);

  const unlock = async () => {
    try {
      await audioRef.current!.play();
      setBlocked(false);
    } catch (err) {
      console.log("Still blocked:", err);
    }
  };

  // --- camera start ---
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const v = videoRef.current!;
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (cancelled) return;
        v.srcObject = stream;
        v.onloadedmetadata = () => {
          v.play();
          const c = canvasRef.current!;
          c.width = v.videoWidth;
          c.height = v.videoHeight;
        };
      } catch (e) {
        console.error("Camera error:", e);
      }
    })();
    return () => {
      cancelled = true;
      const v = videoRef.current;
      const s = v?.srcObject as MediaStream | null;
      s?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // --- detection loop ---
  const AREA_THRESHOLD = 0.06; // 6% of frame area

  useEffect(() => {
    if (!modelLoaded || detected) return; // stop scanning once detected
    let id: number | undefined;

    const tick = async () => {
      const v = videoRef.current, c = canvasRef.current, f = (window as any).faceapi;
      if (!v || !c || !f) return;
      if (v.readyState !== 4) return;

      const ctx = c.getContext("2d");
      if (!ctx) return;

      if (c.width !== v.videoWidth || c.height !== v.videoHeight) {
        c.width = v.videoWidth;
        c.height = v.videoHeight;
      }

      const detections = await f.detectAllFaces(
        v,
        new f.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: 0.5 })
      );

      ctx.clearRect(0, 0, c.width, c.height);
      ctx.strokeStyle = "#00FF00";
      ctx.lineWidth = 2;
      ctx.textBaseline = "top";
      ctx.font = "24px Arial";

      const frameArea = v.videoWidth * v.videoHeight;
      let closeFound = false;

      detections.forEach((det: any) => {
        const { x, y, width, height } = det.box;
        ctx.strokeRect(x, y, width, height);
        const areaRatio = (width * height) / frameArea;
        if (areaRatio >= AREA_THRESHOLD) {
          ctx.fillStyle = "red";
          ctx.fillText("arrive", Math.max(0, x), Math.max(0, y - 28));
          closeFound = true;
        }
      });

      if (closeFound && !routedRef.current) {
        routedRef.current = true;    // lock
        setDetected(true);           // show blocker
        timeoutRef.current = window.setTimeout(() => {
          router.push("/");          // redirect after 3s
        }, 3000);
      }
    };

    id = window.setInterval(tick, 200);
    return () => { if (id) window.clearInterval(id); };
  }, [modelLoaded, detected, router]);

  return (
    <>
      {/* face-api */}
      <Script
        src="https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.15/dist/face-api.min.js"
        strategy="afterInteractive"
        onLoad={async () => {
          try {
            await (window as any).faceapi.nets.tinyFaceDetector.loadFromUri(
              "https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.15/model"
            );
            setModelLoaded(true);
          } catch (e) {
            console.error("Model load error:", e);
          }
        }}
      />

      {/* optional audio element */}
      <audio ref={audioRef} src="/assets/ding.mp3" />

      {/* overlay to unlock audio if autoplay blocked */}
      {blocked && (
        <div className="fixed inset-0">
          <button
            onClick={unlock}
            aria-label="Enable sound"
            className="absolute inset-0"
          />
          <div className="h-full bg-black flex items-center justify-center">
            <div className="w-full max-w-5xl flex flex-col items-center gap-4">
              <video
                src="/assets/blink.mp4"
                autoPlay
                muted
                loop
                playsInline
                className="w-4/5"
              />
            </div>
          </div>
        </div>
      )}

      {/* overlay after detection → blocks view for 3s */}
      {detected && !blocked && (
        <div className="fixed inset-0 z-50 bg-black flex items-center justify-center" style={{zIndex: 2}}>
          <video
            src="/assets/blink.mp4"
            autoPlay
            muted
            loop
            playsInline
            className="w-4/5"
          />
        </div>
      )}

      <main className="min-h-screen flex flex-col items-center justify-center bg-white">
        <div style={{ position: "relative", opacity: 0 }}>
          <video ref={videoRef} muted playsInline style={{ display: "block" }} />
          <canvas ref={canvasRef} style={{ position: "absolute", top: 0, left: 0 }} />
        </div>
        <p className="mt-4 text-gray-600">
          Move closer until the red <b>arrive</b> appears — then we’ll show a blocker and route in 3s.
        </p>
      </main>
    </>
  );
}
