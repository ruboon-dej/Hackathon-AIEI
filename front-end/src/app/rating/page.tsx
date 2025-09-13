"use client";

import { useState } from "react";

type Score = 1 | 2 | 3 | 4 | 5;

export default function Page() {
  const [status, setStatus] = useState<"idle" | "sending" | "ok" | "error">(
    "idle"
  );
  const [last, setLast] = useState<Score | null>(null);

  async function send(score: Score) {
    try {
      setStatus("sending");
      setLast(score);
      const res = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          score,
          ua:
            typeof navigator !== "undefined" ? navigator.userAgent : "",
        }),
      });
      if (!res.ok) throw new Error("bad");
      setStatus("ok");
    } catch {
      setStatus("error");
    } finally {
      setTimeout(() => setStatus("idle"), 2000);
    }
  }

  const btn =
    "flex flex-col items-center justify-center gap-2 rounded-2xl border p-6 sm:p-7 md:p-8 xl:p-10 transition active:scale-95 hover:shadow";

  return (
    <main className="min-h-screen flex flex-col items-center px-4 py-10 md:py-16">
      <h1 className="text-2xl md:text-3xl font-bold tracking-tight mb-6 md:mb-8">
        คะแนนความพึงพอใจเท่าไหร่
      </h1>

      <section className="grid grid-cols-5 gap-4 sm:gap-5 md:gap-6 w-full max-w-5xl">
        <button
          onClick={() => send(5)}
          className={`${btn} border-green-200`}
          aria-label="พึงพอใจมาก (5)"
        >
          <span className="text-5xl md:text-6xl" aria-hidden>
            😀
          </span>
          <span className="text-sm md:text-base font-medium">
            พึงพอใจมาก
          </span>
          <span className="text-xs opacity-70">5</span>
        </button>
        <button
          onClick={() => send(4)}
          className={`${btn} border-green-200`}
          aria-label="พึงพอใจ (4)"
        >
          <span className="text-5xl md:text-6xl" aria-hidden>
            😊
          </span>
          <span className="text-sm md:text-base font-medium">
            พึงพอใจ
          </span>
          <span className="text-xs opacity-70">4</span>
        </button>
        <button
          onClick={() => send(3)}
          className={`${btn} border-yellow-200`}
          aria-label="ปานกลาง (3)"
        >
          <span className="text-5xl md:text-6xl" aria-hidden>
            😐
          </span>
          <span className="text-sm md:text-base font-medium">ปานกลาง</span>
          <span className="text-xs opacity-70">3</span>
        </button>
        <button
          onClick={() => send(2)}
          className={`${btn} border-red-200`}
          aria-label="พึงพอใจมาก (2)"
        >
          <span className="text-5xl md:text-6xl" aria-hidden>
            🙁
          </span>
          <span className="text-sm md:text-base font-medium">
            พึงพอใจมาก
          </span>
          <span className="text-xs opacity-70">2</span>
        </button>
        <button
          onClick={() => send(1)}
          className={`${btn} border-red-200`}
          aria-label="ไม่พึงพอใจ (1)"
        >
          <span className="text-5xl md:text-6xl" aria-hidden>
            😠
          </span>
          <span className="text-sm md:text-base font-medium">
            ไม่พึงพอใจ
          </span>
          <span className="text-xs opacity-70">1</span>
        </button>
      </section>

      <div className="mt-6 h-6">
        {status === "sending" && (
          <p className="text-sm md:text-base opacity-80">
            กำลังส่งคะแนน {last} …
          </p>
        )}
        {status === "ok" && (
          <p className="text-sm md:text-base text-green-600">
            ส่งสำเร็จ 🙏
          </p>
        )}
        {status === "error" && (
          <p className="text-sm md:text-base text-red-600">
            ส่งไม่สำเร็จ ลองใหม่
          </p>
        )}
      </div>
    </main>
  );
}