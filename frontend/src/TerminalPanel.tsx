import { useState } from "react";

type HistoryItem = { id: string; command: string; cwd?: string; status: string; returncode?: number | null };

export function TerminalPanel({ api }: { api: string }) {
  const [command, setCommand] = useState("");
  const [cwd, setCwd] = useState(".");
  const [policy, setPolicy] = useState("developer");
  const [output, setOutput] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [running, setRunning] = useState(false);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const run = async () => {
    if (!command.trim() || running) return;
    setRunning(true); setOutput("");
    const response = await fetch(`${api}/api/v1/terminal/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ command, cwd, policy }) });
    const data = await response.json();
    setExecutionId(data.id ?? null); setOutput(data.stdout || data.detail || data.stderr || "");
    setHistory((items) => [{ id: data.id ?? crypto.randomUUID(), command, cwd, status: response.ok ? "completed" : "blocked", returncode: data.returncode }, ...items].slice(0, 100));
    setRunning(false);
  };
  const stop = async () => { if (executionId) await fetch(`${api}/api/v1/terminal/${executionId}/stop`, { method: "POST" }); };
  return <section className="terminal-panel"><div className="terminal-toolbar"><strong>Terminal</strong><select value={policy} onChange={(event) => setPolicy(event.target.value)}><option value="restricted">restricted</option><option value="developer">developer</option><option value="trusted">trusted</option></select><input value={cwd} onChange={(event) => setCwd(event.target.value)} aria-label="Working directory" /><button onClick={() => setOutput("")}>Clear</button><button onClick={stop} disabled={!running}>Stop</button></div><div className="terminal-output" aria-live="polite">{output || "No output"}</div><div className="terminal-input"><input value={command} onChange={(event) => setCommand(event.target.value)} onKeyDown={(event) => event.key === "Enter" && run()} placeholder="Run a command..." /><button onClick={run} disabled={running}>Run</button></div><details><summary>History</summary>{history.map((item) => <div key={item.id}><code>{item.command}</code> <span>{item.status}</span></div>)}</details></section>;
}
