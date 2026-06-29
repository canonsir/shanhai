"use client";

import * as React from "react";

/**
 * Dark / light theme, persisted to localStorage and applied via the `.dark`
 * class on <html> (matching design-system/tokens/shanhai-tokens.css).
 *
 * The initial class is set by an inline script in layout.tsx to avoid a flash;
 * this hook only handles runtime toggling and state read-back.
 */
export type Theme = "light" | "dark";

const KEY = "shanhai.console.theme";

function current(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.classList.contains("dark")
    ? "dark"
    : "light";
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = React.useState<Theme>("light");

  React.useEffect(() => {
    setTheme(current());
  }, []);

  const toggle = React.useCallback(() => {
    const next: Theme = current() === "dark" ? "light" : "dark";
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      /* ignore quota / privacy-mode errors */
    }
    setTheme(next);
  }, []);

  return [theme, toggle];
}

/**
 * Inline, render-blocking script that applies the stored theme before paint.
 * Defaults to light: only an explicit stored 'dark' preference enables dark mode
 * (the system color-scheme is intentionally ignored).
 */
export const themeBootstrapScript = `(function(){try{if(localStorage.getItem('${KEY}')==='dark'){document.documentElement.classList.add('dark')}}catch(e){}})();`;
