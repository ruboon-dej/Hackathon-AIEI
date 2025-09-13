"use client";

import dynamic from "next/dynamic";
import { useEventWS } from "@/lib/useEventWS";

// browser-only camera preview (triggers permission in the browser)
const CameraPreview = dynamic(() => import("./CameraPreview"), { ssr: false });

export default function Home() {
  const { mode } = useEventWS(); // "idle" | "active"

  if (mode === "idle") {
    return (
      <main className="min-h-screen grid place-items-center bg-black">
        <div className="text-center">
          <video
            src="/eye-blink.mp4"
            autoPlay
            muted
            loop
            playsInline
            className="w-[300px] h-[300px] object-contain mx-auto"
          />
          <p className="text-white mt-4 opacity-70">Looking for a visitor…</p>

          {/* Optional: show the camera preview to request browser permission */}
          <div className="mt-6 mx-auto">
            <CameraPreview />
          </div>
        </div>
      </main>
    );
  }

  // ACTIVE: switch UI (e.g., QR prompt)
  return (
    <main className="min-h-screen grid place-items-center bg-white">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Welcome!</h1>
        <p className="mt-2">Please scan your QR to continue.</p>
        {/* Put your QR scanner or buttons here */}
      </div>
    </main>
  );
}
