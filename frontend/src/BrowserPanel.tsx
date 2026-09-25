import { useState } from "react";

type BrowserResult = { status: string; error?: string; actions: unknown[]; evidence: { screenshots: string[]; console_errors: string[]; network_failures: string[]; visible_errors: string[]; urls: string[] } };

export function BrowserPanel({ api }: { api: string }) {
  const [url, setUrl] = useState("http://localhost:5173");
  const [result, setResult] = useState<BrowserResult | null>(null);
  const [running, setRunning] = useState(false);
  const run = async () => {
    setRunning(true);
    const response = await fetch(`${api}/api/v1/browser/tests`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url, actions: [{ type: "inspect" }, { type: "screenshot", name: "initial" }] }) });
    setResult(await response.json()); setRunning(false);
  };
  return <section className="browser-panel"><div className="browser-toolbar"><strong>Browser tests</strong><input value={url} onChange={(event) => setUrl(event.target.value)} aria-label="Application URL" /><button onClick={run} disabled={running}>{running ? "Running..." : "Run test"}</button></div>{result && <div><p>Status: <strong>{result.status}</strong></p>{result.error && <pre>{result.error}</pre>}<h4>URLs</h4>{result.evidence.urls.map((item) => <div key={item}>{item}</div>)}<h4>Console errors</h4><pre>{result.evidence.console_errors.join("\n") || "None"}</pre><h4>Network failures</h4><pre>{result.evidence.network_failures.join("\n") || "None"}</pre><h4>Visible errors</h4><pre>{result.evidence.visible_errors.join("\n") || "None"}</pre></div>}</section>;
}
