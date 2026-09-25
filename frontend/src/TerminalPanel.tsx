import { useEffect, useState } from "react";

export type TerminalEvent = { channel: "stdout" | "stderr"; text: string };

export function TerminalPanel({ api }: { api: string }) {
  const [command, setCommand] = useState("");
  const [cwd, setCwd] = useState(".");
  const [output, setOutput] = useState("");
  const [history, setHistory] = useState<Array<{ command: string; status: string }>>([]);
  const [running, setRunning] = useState(false);

  const run = async () => {
    if (!command.trim()) return;
    setRunning(true); setOutput("");
    const response = await fetch(`${api}/api/v1/terminal/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ command, cwd, policy: "developer" }) });
    const data = await response.json();
    setOutput(data.stdout || data.detail || data.stderr || "");
    setHistory((items) => [{ command, status: response.ok ? `${data.returncode}` : "blocked" }, ...items].slice(0, 20));
    setRunning(false);
  };

  return <section className="terminal-panel"><div className="terminal-toolbar"><strong>Terminal</strong><input value={cwd} onChange={(event) => setCwd(event.target.value)} aria-label="Working directory" /><button onClick={() => setOutput("")}>Clear</button><button disabled={!running}>Stop</button></div><div className="terminal-output" aria-live="polite">{output || "No output"}</div><div className="terminal-input"><input value={command} onChange={(event) => setCommand(event.target.value)} onKeyDown={(event) => event.key === "Enter" && run()} placeholder="Run a command..." /><button onClick={run} disabled={running}>Run</button></div><details><summary>History</summary>{history.map((item, index) => <div key={`${item.command}-${index}`}><code>{item.command}</code> <span>{item.status}</span></div>)}</details></section>;
}
