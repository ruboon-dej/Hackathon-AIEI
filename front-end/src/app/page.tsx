// src/app/page.tsx
"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

export default function Page() {
  const router = useRouter();
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    timerRef.current = window.setTimeout(() => {
      router.push("/qr");
    }, 10000);

    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [router]);

  return (
    <main className="min-h-screen bg-white">
      <audio src="/assets/ding.mp3" autoPlay />
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
          <h1 className="text-black text-5xl font-bold">Please Scan the QR Code</h1>
          <h1 className="text-black text-5xl font-bold ml-20">กรุณาสแกน QR Code</h1>
        </div>
      </div>
    </main>
  );
}
