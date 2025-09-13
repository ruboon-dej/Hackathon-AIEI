// src/app/page.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

export default function Page() {
  const audioRef = useRef<HTMLAudioElement>(null);
  const timeoutRef = useRef<number | null>(null);
  const [blocked, setBlocked] = useState(false);
  const router = useRouter();

  // Try autoplay on mount
  useEffect(() => {
    const a = audioRef.current!;
    a.volume = 1;
    a.preload = "auto";
    a.load();

    (async () => {
      try {
        await a.play();          // try to play on entry
        setBlocked(false);
      } catch {
        setBlocked(true);        // autoplay blocked → need manual unlock
      }
    })();

    // cleanup any pending timer on unmount
    return () => {
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    };
  }, []);

  // Unlock audio
  const unlock = async () => {
    try {
      await audioRef.current!.play();
      setBlocked(false);
    } catch (err) {
      console.log("Still blocked:", err);
    }
  };

  // Spacebar → unlock + start 3s redirect
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!blocked) return;
      if (e.code !== "Space") return;

      e.preventDefault();
      unlock().then(() => {
        if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
        timeoutRef.current = window.setTimeout(() => {
          router.push("/qr");
        }, 5000);
      });
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [blocked, router]);

  return (
    <main className="min-h-screen relative bg-white">
      <audio ref={audioRef} src="/assets/ding.mp3" />

      {blocked && (
        <div className="fixed inset-0">
          {/* Optional: click can also unlock; keep if you want mobile support */}
          <button
            onClick={unlock}
            aria-label="Enable sound"
            className="absolute inset-0"
          />

          {/* Your video backdrop / instructions */}
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
      <div className="flex-col items-center justify-center w-full pt-20">
        <video
          src="/assets/QR.mov"
          autoPlay
          muted
          loop
          playsInline
          className="w-3/5 items-center justify-center ml-80 mb-20"
        />
        <div className="flex mt-10 items-center justify-center w-full">
          <h1 className="text-black text-5xl text-bold">Please Scan the QR Code</h1>
          <h1 className="text-black text-5xl text-bold ml-20">กรุณาสแกน QR Code</h1>
        </div>
      </div>
    </main>
  );
}
