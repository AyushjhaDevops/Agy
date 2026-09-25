import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, FileCode2, Folder, Search } from "lucide-react";
import "./styles.css";

type Node = { name: string; path: string; kind: "file" | "directory"; children?: Node[] };
type Task = { id: string; goal: string; status: string; plan: string[]; diff: string; changed_files: string[] };

function TreeNode({ node, onSelect }: { node: Node; onSelect: (path: string) => void }) {
  const [open, setOpen] = useState(node.path === "");
  if (node.kind === "file") return <button className="tree-item" onClick={() => onSelect(node.path)}><FileCode2 size={14} />{node.name}</button>;
  return <div><button className="tree-item" onClick={() => setOpen(!open)}>{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}<Folder size={14} />{node.name}</button>{open && <div className="tree-children">{node.children?.map((child) => <TreeNode key={child.path} node={child} onSelect={onSelect} />)}</div>}</div>;
}

export default function App() {
  const api = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
  const [tree, setTree] = useState<Node | null>(null); const [content, setContent] = useState(""); const [selected, setSelected] = useState(""); const [goal, setGoal] = useState(""); const [task, setTask] = useState<Task | null>(null); const [query, setQuery] = useState("");
  useEffect(() => { fetch(`${api}/api/v1/projects/current/tree`).then((r) => r.json()).then(setTree).catch(() => setTree(null)); }, [api]);
  const openFile = (path: string) => { setSelected(path); fetch(`${api}/api/v1/projects/current/file?path=${encodeURIComponent(path)}`).then((r) => r.json()).then((data) => setContent(data.content ?? data.detail ?? "")); };
  const createTask = () => { if (!goal.trim()) return; fetch(`${api}/api/v1/tasks`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ goal, project_id: "current" }) }).then((r) => r.json()).then(setTask); };
  const approve = () => { if (!task) return; fetch(`${api}/api/v1/tasks/${task.id}/approve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: "", new_content: "" }) }).then((r) => r.json()).then(setTask); };
  return <main className="app-shell"><header className="topbar"><div className="brand"><span className="brand-mark">⌬</span> LocalForge <span className="muted">AI</span></div><div className="connection"><span className="dot online" />Phase 4 agent ready</div></header><div className="workspace phase4"><aside className="sidebar"><p className="eyebrow">EXPLORER</p><div className="search-box"><Search size={14} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter files" /></div>{tree ? <TreeNode node={tree} onSelect={openFile} /> : <p className="muted">Start the API to index a project.</p>}</aside><section className="code-area"><div className="code-header">{selected || "Read-only code preview"}</div><pre className="code-preview">{content || "Select a file to inspect it. Agent changes require an explicit proposal and approval."}</pre></section><aside className="inspector"><p className="eyebrow">TASK PANEL</p><textarea className="task-input" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Describe a coding task..." /><button className="primary-button task-button" onClick={createTask}>Plan task</button>{task && <div className="panel-card"><strong>{task.goal}</strong><p>Status: {task.status}</p><h4>Plan</h4><ol>{task.plan.map((step) => <li key={step}>{step}</li>)}</ol>{task.diff && <pre className="diff-preview">{task.diff}</pre>}<button className="primary-button" onClick={approve}>Approve patch</button></div>}</aside></div></main>;
}
