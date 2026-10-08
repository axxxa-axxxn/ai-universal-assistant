import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "http://127.0.0.1:5000/api";

async function api(path, options = {}) {
  const token = localStorage.getItem("token");
  const headers = {...(options.headers || {})};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(API + path, {...options, headers});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || data.msg || "Request failed");
  return data;
}

function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({name:"", email:"", password:""});
  const [error, setError] = useState("");
  const submit = async e => {
    e.preventDefault(); setError("");
    try {
      const data = await api(`/auth/${mode}`, {
        method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(form)
      });
      localStorage.setItem("token", data.token);
      onLogin(data.user);
    } catch(e) { setError(e.message); }
  };
  return <div className="auth-page">
    <div className="auth-card">
      <div className="brand">✦ AI Universal</div>
      <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
      <p className="muted">Your personal AI workspace for questions, files and images.</p>
      <form onSubmit={submit}>
        {mode === "register" && <input placeholder="Full name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required />}
        <input type="email" placeholder="Email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required />
        <input type="password" placeholder="Password (6+ characters)" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required minLength="6" />
        {error && <div className="error">{error}</div>}
        <button className="primary">{mode === "login" ? "Log in" : "Create account"}</button>
      </form>
      <button className="link" onClick={()=>{setMode(mode==="login"?"register":"login");setError("")}}>
        {mode === "login" ? "Create a new account" : "I already have an account"}
      </button>
    </div>
  </div>
}

function App({user, logout}) {
  const [convos,setConvos]=useState([]);
  const [active,setActive]=useState(null);
  const [messages,setMessages]=useState([]);
  const [text,setText]=useState("");
  const [web,setWeb]=useState(false);
  const [file,setFile]=useState(null);
  const [image,setImage]=useState(null);
  const [loading,setLoading]=useState(false);
  const [status,setStatus]=useState("");
  const bottom=useRef();

  const loadConvos=async()=>{try{const d=await api("/conversations");setConvos(d.conversations)}catch(e){setStatus(e.message)}};
  useEffect(()=>{loadConvos()},[]);
  useEffect(()=>{bottom.current?.scrollIntoView({behavior:"smooth"})},[messages]);

  const newChat=async()=>{
    const d=await api("/conversations",{method:"POST"}); setConvos([d.conversation,...convos]); setActive(d.conversation.id); setMessages([]);
  };
  const openChat=async(id)=>{
    const d=await api(`/conversations/${id}`); setActive(id); setMessages(d.conversation.messages);
  };
  const upload=async()=>{
    if(!file)return;
    const fd=new FormData(); fd.append("file",file);
    setStatus("Uploading and indexing...");
    try{const d=await api("/files",{method:"POST",body:fd});setStatus(`${d.document.name} indexed (${d.document.chunks} chunks)`);setFile(null)}
    catch(e){setStatus(e.message)}
  };
  const send=async()=>{
    if(!text.trim() && !image)return;
    const q=text.trim() || "Please analyze this image.";
    setMessages(m=>[...m,{role:"user",content:q}]); setText(""); setLoading(true); setStatus("");
    const fd=new FormData(); fd.append("message",q); fd.append("use_web",String(web));
    if(active)fd.append("conversation_id",String(active));
    if(image)fd.append("image",image);
    try{
      const d=await api("/chat",{method:"POST",body:fd});
      setActive(d.conversation_id);
      setMessages(m=>[...m,{role:"assistant",content:d.answer}]);
      loadConvos();
    }catch(e){setMessages(m=>[...m,{role:"assistant",content:"Error: "+e.message}])}
    finally{setLoading(false);setImage(null)}
  };

  return <div className="app">
    <aside className="sidebar">
      <div className="brand">✦ AI Universal</div>
      <button className="newchat" onClick={newChat}>＋ New chat</button>
      <div className="side-title">Your conversations</div>
      <div className="conversation-list">
        {convos.map(c=><button key={c.id} className={active===c.id?"conv active":"conv"} onClick={()=>openChat(c.id)}>{c.title}</button>)}
      </div>
      <div className="profile">
        <div><b>{user.name}</b><small>{user.email}</small></div>
        <button onClick={logout}>Logout</button>
      </div>
    </aside>
    <main className="main">
      <header><div><h2>AI Assistant</h2><span>Ask questions, search your knowledge, or upload files and images.</span></div></header>
      <section className="messages">
        {messages.length===0 && <div className="welcome">
          <div className="spark">✦</div><h1>What can I help you with?</h1>
          <p>Ask anything, upload a document, or attach an image.</p>
          <div className="suggestions">
            <button onClick={()=>setText("Explain artificial intelligence in simple words.")}>Explain AI simply</button>
            <button onClick={()=>setText("Help me understand this topic step by step.")}>Learn a topic</button>
            <button onClick={()=>setWeb(true)}>Search the web</button>
          </div>
        </div>}
        {messages.map((m,i)=><div key={i} className={"msg "+m.role}><div className="avatar">{m.role==="user"?"You":"✦"}</div><div className="bubble">{m.content}</div></div>)}
        {loading && <div className="msg assistant"><div className="avatar">✦</div><div className="bubble typing">Thinking…</div></div>}
        <div ref={bottom}/>
      </section>
      <div className="composer-wrap">
        {status && <div className="status">{status}</div>}
        {image && <div className="attachment">🖼️ {image.name} <button onClick={()=>setImage(null)}>×</button></div>}
        <div className="composer">
          <label className="attach">📎<input type="file" accept=".pdf,.txt,.md,.csv,.docx" onChange={e=>{setFile(e.target.files[0]);}} hidden /></label>
          <label className="attach">🖼️<input type="file" accept="image/*" onChange={e=>setImage(e.target.files[0])} hidden /></label>
          <textarea value={text} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}}} placeholder="Message AI Universal..." />
          <button className="send" onClick={send} disabled={loading}>↑</button>
        </div>
        <div className="tools">
          <button className={web?"tool selected":"tool"} onClick={()=>setWeb(!web)}>🌐 Web search {web?"ON":"OFF"}</button>
          {file && <button className="tool selected" onClick={upload}>Upload: {file.name}</button>}
          <span>Files stay associated with your account.</span>
        </div>
      </div>
    </main>
  </div>
}

function Root(){
  const [user,setUser]=useState(null);
  useEffect(()=>{if(localStorage.getItem("token"))api("/auth/me").then(d=>setUser(d.user)).catch(()=>localStorage.removeItem("token"))},[]);
  if(!user)return <Auth onLogin={setUser}/>;
  return <App user={user} logout={()=>{localStorage.removeItem("token");setUser(null)}}/>;
}
createRoot(document.getElementById("root")).render(<Root/>);
