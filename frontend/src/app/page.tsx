"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";

interface Product {
  id: string;
  name: string;
  price: number;
  rating: number;
  shipping: string;
}

interface Message {
  role: "user" | "agent";
  text: string;
  products?: Product[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "agent", text: "Hello! I'm your Agentic Commerce assistant. What can I help you find today?" }
  ]);
  const [input, setInput] = useState("");
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/chat");
    ws.onmessage = (event) => {
      const response = JSON.parse(event.data);
      setMessages((prev) => [...prev, { role: "agent", text: response.text, products: response.data }]);
    };
    setSocket(ws);
    return () => ws.close();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = () => {
    if (!input.trim() || !socket) return;
    const userMsg: Message = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    socket.send(JSON.stringify({ text: input }));
    setInput("");
  };

  return (
    <div className="flex flex-col h-screen bg-black text-white font-sans overflow-hidden">
      {/* Header */}
      <header className="p-6 border-b border-zinc-800 flex justify-between items-center backdrop-blur-md bg-black/50 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center">
            <span className="text-xl font-bold">A</span>
          </div>
          <h1 className="text-xl font-bold gradient-text">Agentic Commerce</h1>
        </div>
        <div className="flex gap-4">
          <button className="px-4 py-2 rounded-full border border-zinc-700 text-sm hover:bg-zinc-900 transition-all">Profile</button>
          <button className="px-4 py-2 rounded-full bg-blue-600 text-sm font-semibold hover:bg-blue-500 transition-all shadow-lg shadow-blue-500/20">Cart (0)</button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scrollbar-hide">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"} fade-in`}>
              <div className={`max-w-[85%] p-4 ${msg.role === "user" ? "chat-bubble-user" : "chat-bubble-agent shadow-sm"}`}>
                <p className="text-sm md:text-base leading-relaxed">{msg.text}</p>
              </div>
              
              {/* Product Cards Grid */}
              {msg.products && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 w-full animate-slide-up">
                  {msg.products.map((product) => (
                    <div key={product.id} className="glass-card overflow-hidden hover:scale-[1.02] transition-transform duration-300">
                      <div className="h-32 bg-zinc-800 relative">
                        {/* Placeholder for product image */}
                        <div className="absolute inset-0 flex items-center justify-center text-zinc-600 font-bold uppercase tracking-widest text-xs">Product Image</div>
                      </div>
                      <div className="p-4 space-y-2">
                        <h3 className="font-semibold text-sm line-clamp-1">{product.name}</h3>
                        <div className="flex justify-between items-center">
                          <span className="text-lg font-bold text-blue-400">${product.price}</span>
                          <span className="text-xs text-zinc-400">★ {product.rating}</span>
                        </div>
                        <button className="w-full py-2 bg-white/10 hover:bg-white/20 rounded-lg text-xs font-medium transition-colors border border-white/5">
                          View Details
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <footer className="p-6 bg-gradient-to-t from-black to-transparent">
        <div className="max-w-4xl mx-auto relative group">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Search for products, ask for comparisons..."
            className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl py-4 px-6 pr-16 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all text-sm group-hover:border-zinc-700"
          />
          <button 
            onClick={sendMessage}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-blue-600 rounded-xl hover:bg-blue-500 transition-all"
          >
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>
        <p className="text-center text-[10px] text-zinc-600 mt-4 uppercase tracking-[0.2em]">Secure AI-Powered Intelligent Commerce Layer</p>
      </footer>

      <style jsx>{`
        .fade-in { animation: fadeIn 0.4s ease-out; }
        .animate-slide-up { animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
      `}</style>
    </div>
  );
}
