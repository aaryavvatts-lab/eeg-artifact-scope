"use client";

import { useEffect, useState } from "react";

/* Text theme control. The label is driven by CSS (only-light / only-dark) so it is right before
   hydration; aria-pressed is set once the component mounts. Also adds the `settled` class three
   seconds after load so no entrance animation can leave content hidden. */
export default function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const current = () => {
      const t = root.getAttribute("data-theme");
      return t ? t === "dark" : mq.matches;
    };
    const paint = () => {
      setDark(current());
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", getComputedStyle(root).getPropertyValue("--bg").trim());
    };
    paint();
    mq.addEventListener("change", paint);
    document.addEventListener("themechange", paint);
    const t = window.setTimeout(() => root.classList.add("settled"), 3000);
    return () => {
      mq.removeEventListener("change", paint);
      document.removeEventListener("themechange", paint);
      window.clearTimeout(t);
    };
  }, []);

  const toggle = () => {
    const root = document.documentElement;
    const next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch { /* storage may be unavailable */ }
    document.dispatchEvent(new CustomEvent("themechange", { detail: { theme: next } }));
  };

  return (
    <button
      type="button"
      className="theme"
      onClick={toggle}
      aria-pressed={dark === true}
      aria-label={dark ? "Theme: dark. Switch to light" : "Theme: light. Switch to dark"}
    >
      <span className="only-light">Light</span>
      <span className="only-dark">Dark</span>
    </button>
  );
}
