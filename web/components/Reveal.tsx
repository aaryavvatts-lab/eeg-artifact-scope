"use client";

import React, { useEffect, useRef } from "react";

type Tag = "section" | "div" | "article" | "li" | "figure" | "aside";

/* Reveal once as it scrolls into view. Content is only hidden under html.js, and the `settled`
   class (added three seconds after load) shows everything regardless. */
export default function Reveal({
  as = "section", className, children, index, ...rest
}: { as?: Tag; className?: string; children: React.ReactNode; index?: number } & React.HTMLAttributes<HTMLElement>) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!("IntersectionObserver" in window)) { el.classList.add("is-in"); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { el.classList.add("is-in"); io.disconnect(); } });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.08 });
    io.observe(el);
    const t = window.setTimeout(() => {
      const r = el.getBoundingClientRect();
      if (r.top < window.innerHeight && r.bottom > 0) el.classList.add("is-in");
    }, 2500);
    return () => { io.disconnect(); window.clearTimeout(t); };
  }, []);
  const style = index != null ? ({ ...(rest.style || {}), ["--i" as string]: index } as React.CSSProperties) : rest.style;
  return React.createElement(as, { ...rest, ref, className, "data-reveal": "", style }, children);
}
