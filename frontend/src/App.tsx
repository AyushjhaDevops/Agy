import { useEffect, useState } from "react";
import { Bot, ChevronDown, ChevronRight, FileCode2, Folder, Search } from "lucide-react";
import "./styles.css";

type Node = { name: string; path: string; kind: "file" | "directory"; children?: Node[]; language?: string };
type Summary = { file_count: number; languages: Record<string, number>; frameworks: string[]; git_branch?: string | null; entry_points: string[]; test_files: string[] };

function TreeNode({ node, onSelect }: { node: Node; onSelect: (path: string) => void }) {
  const [open, setOpen] = useState(node.path === "");
  if (node.kind === "file") return <button className="tree-item" onClick={() => onSelect(node.path)}><FileCode2 size={14} />{node.name}</button>;
  return <div><button className="tree-item folder" onClick={() => setOpen(!open)}>{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}<Folder size={14} />{node.name}</button>{open && <div className="tree-children">{node.children?.map((child) => <TreeNode key={child.path} node={child} onSelect={onSelect} />)}</div>}</div>;
}

export default function App() {
  const api = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
  const [tree, setTree] = useState<Node | null>(null); const [summary, setSummary] = useState<Summary | null>(null); const [content, setContent] = useState(""); const [selected, setSelected] = useState(""); const [query, setQuery] = useState(""); const [results, setResults] = useState<{file: string; line: number; snippet: string}[]>([]);
  const load = () => { Promise.all([fetch(`${api}/api/v1/projects/current/tree`).then((r) => r.json()), fetch(`${api}/api/v1/projects/current/summary`).then((r) => r.json())]).then(([nextTree, nextSummary]) => { setTree(nextTree); setSummary(nextSummary); }); };
  useEffect(() => { load(); }, []);
  const openFile = (path: string) => { setSelected(path); fetch(`${api}/api/v1/projects/current/file?path=${encodeURIComponent(path)}`).then((r) => r.json()).then((data) => setContent(data.content ?? data.detail ?? "")); };
  const search = () => { if (!query.trim()) return; fetch(`${api}/api/v1/projects/current/search?q=${encodeURIComponent(query)}`).then((r) => r.json()).then((data) => setResults(data.results ?? [])); };
  return <main className="app-shell"><header className="topbar"><div className="brand"><span className="brand-mark">⌬</span> LocalForge <span className="muted">AI</span></div><div className="connection"><span className="dot online" />Repository indexed</div></header><div className="workspace phase3"><aside className="sidebar"><p className="eyebrow">EXPLORER</p><div className="search-box"><Search size={14} /><input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} placeholder="Search repository" /></div>{tree ? <TreeNode node={tree} onSelect={openFile} /> : <p className="muted">Start the API to index a project.</p>}</aside><section className="code-area"><div className="code-header">{selected || "Project overview"}</div>{selected ? <pre className="code-preview">{content}</pre> : <div className="overview"><h1>Project overview</h1>{summary && <><p>{summary.file_count} indexed files · branch: {summary.git_branch ?? "not a Git repository"}</p><h3>Languages</h3><p>{Object.entries(summary.languages).map(([name, count]) => `${name} (${count})`).join(" · ") || "None detected"}</p><h3>Entry points</h3><ul>{summary.entry_points.map((item) => <li key={item}>{item}</li>)}</ul><h3>Test files</h3><p>{summary.test_files.length || "No"} detected</p></>}</div>}</section><aside className="inspector"><p className="eyebrow">SEARCH RESULTS</p>{results.length ? results.map((item) => <button className="result" key={`${item.file}:${item.line}`} onClick={() => openFile(item.file)}><strong>{item.file}:{item.line}</strong><span>{item.snippet}</span></button>) : <div className="panel-card"><strong>Context engine</strong><p className="muted">Repository files are ranked for future AI tasks without sending the whole project to Ollama.</p></div>}</aside></div></main>;
}
