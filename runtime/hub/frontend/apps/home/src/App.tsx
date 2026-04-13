import { useState, useEffect, useCallback } from "react";
import type { UserQuotaInfo } from "@auplc/shared";
import { getMyQuota } from "@auplc/shared";
import { CodeLabView } from "./components/CodeLabView";

type Theme = "light" | "dark";
function getInitialTheme(): Theme {
  const stored =
    (localStorage.getItem("auplc-theme") as Theme | null) ??
    (localStorage.getItem("jupyterhub-bs-theme") as Theme | null);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function applyTheme(t: Theme) {
  document.documentElement.setAttribute("data-bs-theme", t);
  localStorage.setItem("auplc-theme", t);
  localStorage.setItem("jupyterhub-bs-theme", t);
}
applyTheme(getInitialTheme());

interface HomeData {
  server_active: boolean;
  server_url: string;
}

declare global {
  interface Window {
    HOME_DATA?: HomeData;
    AVAILABLE_RESOURCES?: string[];
  }
}

const jhdata = window.jhdata ?? {
  base_url: "/hub/",
  xsrf_token: "",
  user: "student",
};

const baseUrl = jhdata.base_url ?? "/hub/";

const homeData: HomeData = window.HOME_DATA ?? {
  server_active: false,
  server_url: `${baseUrl.replace(/\/?$/, "/")}user/${jhdata.user ?? "student"}/`,
};

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export interface SharedState {
  jhdata: typeof jhdata;
  baseUrl: string;
  homeData: HomeData;
  serverActive: boolean;
  setServerActive: (v: boolean) => void;
  stopping: boolean;
  setStopping: (v: boolean) => void;
  quota: UserQuotaInfo | null;
  theme: Theme;
  toggleTheme: () => void;
  greeting: string;
}

function App() {
  const [serverActive, setServerActive] = useState(homeData.server_active);
  const [stopping, setStopping] = useState(false);
  const [quota, setQuota] = useState<UserQuotaInfo | null>(null);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  const toggleTheme = useCallback(() => {
    setTheme((t) => {
      const next = t === "light" ? "dark" : "light";
      applyTheme(next);
      return next;
    });
  }, []);

  useEffect(() => {
    getMyQuota().then(setQuota).catch(() => {});
  }, []);

  useEffect(() => {
    const poll = () => {
      fetch(`${baseUrl}api/users/${jhdata.user ?? "student"}`, {
        headers: { Accept: "application/json" },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (data) setServerActive(Boolean(data.server));
        })
        .catch(() => {});
    };
    const id = setInterval(poll, 15_000);
    return () => clearInterval(id);
  }, []);

  const shared: SharedState = {
    jhdata,
    baseUrl,
    homeData,
    serverActive,
    setServerActive,
    stopping,
    setStopping,
    quota,
    theme,
    toggleTheme,
    greeting: getGreeting(),
  };

  return (
    <div className="home-page">
      <CodeLabView shared={shared} />
      <div className="home-footer">
        <div className="container">
          &copy; 2025–2026 Advanced Micro Devices, Inc. All rights reserved.
          &middot; AUP Learning Cloud
        </div>
      </div>
    </div>
  );
}

export default App;
