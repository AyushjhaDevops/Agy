import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, Copy, Send, Square } from "lucide-react";
import "./styles.css";

type Message = { role: "user" | "assistant"; content: string };

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [generating, setGenerating] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const apiUrl = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
  const wsUrl = apiUrl.replace(/^http/, "ws");

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/models`)
      .then((response) => response.json())
      .then((payload: { models: string[]; available: boolean }) => {
        setModels(payload.models);
        setModel(payload.models[0] ?? "");
        setConnected(payload.available);
      })
      .catch(() => setConnected(false));
    return () => socket.current?.close();
  }, [apiUrl]);

  const send = () => {
    const message = input.trim();
    if (!message || generating) return;
    setMessages((current) => [...current, { role: "user", content: message }, { role: "assistant", content: "" }]);
    setInput("");
    setGenerating(true);
    const connection = new WebSocket(`${wsUrl}/api/v1/chat/stream`);
    socket.current = connection;
    connection.onopen = () => connection.send(JSON.stringify({ message, model: model || undefined }));
    connection.onmessage = (event) => {
      const payload = JSON.parse(event.data) as { type: string; content?: string };
      if (payload.type === "token") {
        setMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, content: item.content + (payload.content ?? "") } : item));
      }
      if (payload.type === "done" || payload.type === "error") { setGenerating(false); connection.close(); }
    };
    connection.onerror = () => { setConnected(false); setGenerating(false); };
  };

  return <main className="app-shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">⌬</span> LocalForge <span className="muted">AI</span></div><div className="connection"><span className={`dot ${connected ? "online" : ""}`} />{connected ? "Ollama connected" : "Ollama offline"}</div></header>
    <div className="workspace">
      <aside className="sidebar"><p className="eyebrow">WORKSPACE</p><button className="nav-item"><Bot size={17} /> AI Chat</button><button className="nav-item">Projects</button><button className="nav-item">Agents</button><button className="nav-item">Settings</button></aside>
      <section className="chat-area"><div className="chat-header"><div><strong>Local AI Assistant</strong><span className="muted"> · Phase 2</span></div><select value={model} onChange={(event) => setModel(event.target.value)}><option value="">Configured model</option>{models.map((item) => <option key={item} value={item}>{item}</option>)}</select></div><div className="messages">{messages.length === 0 && <div className="empty-state"><div className="hero-icon"><Bot size={34} /></div><h1>Talk to your local model.</h1><p>Ask a question and receive a streamed response from Ollama.</p></div>}{messages.map((item, index) => <article className={`message ${item.role}`} key={`${index}-${item.role}`}><div className="message-label">{item.role === "user" ? "You" : "LocalForge AI"}</div><div className="markdown"><ReactMarkdown>{item.content || "▌"}</ReactMarkdown></div>{item.role === "assistant" && item.content && <button className="copy-button" onClick={() => navigator.clipboard.writeText(item.content)} title="Copy response"><Copy size={14} /></button>}</article>)}</div><div className="composer"><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask your local AI assistant..." disabled={generating} /><button className="send-button" onClick={generating ? () => socket.current?.close() : send} title={generating ? "Stop generation" : "Send"}>{generating ? <Square size={17} /> : <Send size={17} />}</button></div></section>
      <aside className="inspector"><p className="eyebrow">RUNTIME</p><div className="panel-card"><strong>Ollama</strong><p className="muted">{connected ? "Connected and ready" : "Start Ollama and configure a model"}</p></div><div className="panel-card"><strong>Streaming</strong><p className="muted">WebSocket responses are shown incrementally.</p></div></aside>
    </div>
  </main>;
}
