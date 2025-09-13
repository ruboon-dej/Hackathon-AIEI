// src/app/page.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

type Score = 1 | 2 | 3 | 4 | 5;

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:5000").replace(/\/$/, "");

export default function Page() {
  const sp = useSearchParams();
  const router = useRouter();
  const statusParam = sp.get("status") || "Register";

  const [qLoading, setQLoading] = useState(true);
  const [qError, setQError] = useState<string | null>(null);
  const [qPayload, setQPayload] = useState<any>(null);

  const [sendStatus, setSendStatus] = useState<"idle" | "sending" | "ok" | "error">("idle");
  const [last, setLast] = useState<Score | null>(null);

  // Extract question text
  const questionText = useMemo(() => {
    const q = qPayload?.data ?? qPayload ?? {};
    if (typeof q === "string") return q.trim();
    return (
      (q.question?.toString().trim()) ||
      (q.th?.toString().trim()) ||
      (q.en?.toString().trim()) ||
      "วันนี้ได้รับบริการส่วนนี้เป็นอย่างไร?"
    );
  }, [qPayload]);

  // Fetch question once
  useEffect(() => {
    const ac = new AbortController();
    (async () => {
      setQLoading(true);
      setQError(null);
      try {
        const res = await fetch(`${API_BASE}/api/question`, {
          signal: ac.signal,
          cache: "no-store",
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setQPayload(json);
      } catch (e: any) {
        if (e?.name === "AbortError") return;
        setQError(e?.message || "load failed");
        setQPayload({ question: "" });
      } finally {
        setQLoading(false);
      }
    })();
    return () => ac.abort();
  }, []);

  // Submit evaluation
  async function send(score: Score) {
    try {
      setSendStatus("sending");
      setLast(score);
      const res = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          score,
          status: statusParam,
          question: questionText,
          ua: typeof navigator !== "undefined" ? navigator.userAgent : "",
        }),
      });
      if (!res.ok) throw new Error("bad");
      setSendStatus("ok");

      // ✅ Route to another page after success
      setTimeout(() => {
        router.push("/thank");
      }, 1000);
    } catch {
      setSendStatus("error");
    } finally {
      setTimeout(() => setSendStatus("idle"), 2000);
    }
  }

  const btn =
    "flex flex-col items-center justify-center gap-2 rounded-2xl border p-6 sm:p-7 md:p-8 xl:p-10 transition active:scale-95 hover:shadow";

  return (
    <main className="min-h-screen flex flex-col items-center px-4 py-10 md:py-14">
      {/* Play audio if question exists */}
      {questionText && (
        <audio src={`/assets/${encodeURIComponent(questionText)}.mp3`} autoPlay />
      )}

      <div className="w-full max-w-5xl">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
          {qLoading ? "กำลังโหลดคำถาม…" : questionText}
        </h1>
        <div className="mt-2 text-sm text-gray-500">
          สถานี: <b>{statusParam}</b>
          {qError ? <span className="text-red-600 ml-2">({qError})</span> : null}
        </div>
      </div>

      {/* Buttons */}
      <div className="w-full max-w-5xl mt-8 md:mt-10">
        <section className="grid grid-cols-5 gap-4 sm:gap-5 md:gap-6">
          <button onClick={() => send(5)} className={`${btn} border-green-200`} aria-label="พึงพอใจมาก (5)">
            <span className="text-5xl md:text-6xl" aria-hidden>😀</span>
            <span className="text-sm md:text-base font-medium">พึงพอใจมาก</span>
            <span className="text-xs opacity-70">5</span>
          </button>
          <button onClick={() => send(4)} className={`${btn} border-green-200`} aria-label="พึงพอใจ (4)">
            <span className="text-5xl md:text-6xl" aria-hidden>😊</span>
            <span className="text-sm md:text-base font-medium">พึงพอใจ</span>
            <span className="text-xs opacity-70">4</span>
          </button>
          <button onClick={() => send(3)} className={`${btn} border-yellow-200`} aria-label="ปานกลาง (3)">
            <span className="text-5xl md:text-6xl" aria-hidden>😐</span>
            <span className="text-sm md:text-base font-medium">ปานกลาง</span>
            <span className="text-xs opacity-70">3</span>
          </button>
          <button onClick={() => send(2)} className={`${btn} border-red-200`} aria-label="น้อย (2)">
            <span className="text-5xl md:text-6xl" aria-hidden>🙁</span>
            <span className="text-sm md:text-base font-medium">น้อย</span>
            <span className="text-xs opacity-70">2</span>
          </button>
          <button onClick={() => send(1)} className={`${btn} border-red-200`} aria-label="ไม่พึงพอใจ (1)">
            <span className="text-5xl md:text-6xl" aria-hidden>😠</span>
            <span className="text-sm md:text-base font-medium">ไม่พึงพอใจ</span>
            <span className="text-xs opacity-70">1</span>
          </button>
        </section>

        <div className="mt-6 h-6">
          {sendStatus === "sending" && (
            <p className="text-sm md:text-base opacity-80">กำลังส่งคะแนน {last} …</p>
          )}
          {sendStatus === "ok" && (
            <p className="text-sm md:text-base text-green-600">ส่งสำเร็จ 🙏</p>
          )}
          {sendStatus === "error" && (
            <p className="text-sm md:text-base text-red-600">ส่งไม่สำเร็จ ลองใหม่</p>
          )}
        </div>
      </div>
    </main>
  );
}
