import { useEffect, useState } from "react";
import {
  Bot,
  Files,
  GitBranch,
  Settings,
  Terminal,
  Wrench,
} from "lucide-react";
import "./styles.css";

type Health = {
  status: string;
  service: string;
  environment: string;
};

const navItems = [
  { label: "Projects", icon: Files },
  { label: "Agents", icon: Bot },
  { label: "Tasks", icon: Wrench },
  { label: "Git", icon: GitBranch },
  { label: "Settings", icon: Settings },
];

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const apiUrl =
    import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

  useEffect(() => {
    fetch(`${apiUrl}/health`)
      .then((response) => response.json() as Promise<Health>)
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [apiUrl]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">⌬</span>
          LocalForge <span className="muted">AI</span>
        </div>

        <div className="connection">
          <span className={`dot ${health ? "online" : ""}`} />
          {health ? "API connected" : "API offline"}
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <p className="eyebrow">WORKSPACE</p>

          {navItems.map(({ label, icon: Icon }) => (
            <button className="nav-item" key={label}>
              <Icon size={17} />
              {label}
            </button>
          ))}
        </aside>

        <section className="editor-area">
          <div className="empty-state">
            <div className="hero-icon">
              <Bot size={34} />
            </div>

            <h1>Build locally. Ship confidently.</h1>

            <p>
              LocalForge AI is ready for your repository. Phase 1 foundation
              is online.
            </p>

            <button className="primary-button">Open a project</button>
          </div>

          <div className="bottom-panel">
            <Terminal size={16} />
            Terminal
            <span className="muted">No active session</span>
          </div>
        </section>

        <aside className="inspector">
          <p className="eyebrow">LOCAL AI</p>

          <div className="panel-card">
            <strong>Agent workspace</strong>
            <p className="muted">
              Planning, tools, and execution history will appear here in later
              phases.
            </p>
          </div>

          <div className="panel-card">
            <strong>Runtime</strong>
            <p className="muted">
              {health
                ? `${health.service} · ${health.environment}`
                : "Start the FastAPI server to connect."}
            </p>
          </div>
        </aside>
      </div>
    </main>
  );
}
