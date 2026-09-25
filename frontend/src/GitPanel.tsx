import { useState } from "react";

type GitStatus = { branch: string; ahead: number; behind: number; modified: string[]; added: string[]; deleted: string[]; untracked: string[] };
type Commit = { hash: string; author: string; timestamp: string; message: string };

export function GitPanel({ api }: { api: string }) {
  const [status, setStatus] = useState<GitStatus | null>(null);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [message, setMessage] = useState("");
  const [approveCommit, setApproveCommit] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    const [statusRes, logsRes] = await Promise.all([fetch(`${api}/api/v1/git/status`), fetch(`${api}/api/v1/git/log`)]);
    setStatus(await statusRes.json());
    const logData = await logsRes.json();
    setCommits(logData.commits || []);
    setLoading(false);
  };

  const doCommit = async () => {
    if (!message.trim() || !approveCommit) return;
    setLoading(true);
    const response = await fetch(`${api}/api/v1/git/commit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, approved: true }) });
    if (response.ok) { setMessage(""); setApproveCommit(false); await fetchStatus(); }
    setLoading(false);
  };

  return (
    <section className="git-panel">
      <div className="git-toolbar">
        <strong>Git</strong>
        <button onClick={fetchStatus} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>
      {status && (
        <div className="git-status">
          <div>
            <strong>Branch:</strong> {status.branch}
          </div>
          <div>
            <strong>Sync:</strong> {status.ahead} ahead, {status.behind} behind
          </div>
          {(status.modified.length > 0 || status.added.length > 0 || status.deleted.length > 0 || status.untracked.length > 0) && (
            <details>
              <summary>Changes</summary>
              {status.modified.length > 0 && (
                <div>
                  <strong>Modified:</strong> {status.modified.map((f) => <code key={f}>{f}</code>)}
                </div>
              )}
              {status.added.length > 0 && (
                <div>
                  <strong>Added:</strong> {status.added.map((f) => <code key={f}>{f}</code>)}
                </div>
              )}
              {status.deleted.length > 0 && (
                <div>
                  <strong>Deleted:</strong> {status.deleted.map((f) => <code key={f}>{f}</code>)}
                </div>
              )}
              {status.untracked.length > 0 && (
                <div>
                  <strong>Untracked:</strong> {status.untracked.map((f) => <code key={f}>{f}</code>)}
                </div>
              )}
            </details>
          )}
        </div>
      )}
      <div className="git-commit">
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Commit message..." />
        <label>
          <input type="checkbox" checked={approveCommit} onChange={(e) => setApproveCommit(e.target.checked)} />
          Approve commit
        </label>
        <button onClick={doCommit} disabled={!message.trim() || !approveCommit || loading}>
          Commit
        </button>
      </div>
      {commits.length > 0 && (
        <details>
          <summary>History</summary>
          {commits.slice(0, 10).map((c) => (
            <div key={c.hash} className="git-commit-entry">
              <code>{c.hash.slice(0, 7)}</code> {c.author} <time>{new Date(c.timestamp).toLocaleString()}</time>
              <pre>{c.message.slice(0, 100)}</pre>
            </div>
          ))}
        </details>
      )}
    </section>
  );
}
