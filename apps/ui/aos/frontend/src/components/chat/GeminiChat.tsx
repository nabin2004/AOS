'use client';

import React, { useState, useEffect, useRef } from 'react';
import styles from './GeminiChat.module.css';

interface Message {
  id: string;
  sender: 'user' | 'gemini';
  text: string;
  code?: string;
}

export default function GeminiChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // In a real app, you'd handle connection lifecycle better
    const connectWs = () => {
      // Connect to the FastAPI backend. Update port if necessary.
      const ws = new WebSocket('ws://localhost:8000/ws/generate_lecture');
      
      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'status') {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            sender: 'gemini',
            text: `[System] ${data.message}`
          }]);
        } else if (data.type === 'syllabus') {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            sender: 'gemini',
            text: `Here is the syllabus I planned:\n${data.data.map((item: string, i: number) => `${i + 1}. ${item}`).join('\n')}`
          }]);
        } else if (data.type === 'slide_generated') {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            sender: 'gemini',
            text: data.narration,
            code: data.code
          }]);
          
          if (data.is_final) {
            setIsGenerating(false);
          }
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsGenerating(false);
      };

      wsRef.current = ws;
    };

    connectWs();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!inputValue.trim() || !wsRef.current || !isConnected || isGenerating) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: inputValue
    };

    setMessages(prev => [...prev, userMsg]);
    setIsGenerating(true);
    
    // Send prompt to backend
    wsRef.current.send(inputValue);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={styles.chatContainer}>
      <div className={styles.messagesArea}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#888', marginTop: '2rem' }}>
            <h2>Conversation with Gemini</h2>
            <p>What would you like to create a lecture about?</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div 
              key={msg.id} 
              className={`${styles.message} ${msg.sender === 'user' ? styles.userMessage : styles.geminiMessage}`}
            >
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
              {msg.code && (
                <div className={styles.geminiCode}>
                  <pre><code>{msg.code}</code></pre>
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className={styles.inputArea}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Explain the Fourier Transform..."
          className={styles.inputField}
          disabled={!isConnected || isGenerating}
        />
        <button 
          onClick={handleSend} 
          className={styles.sendButton}
          disabled={!inputValue.trim() || !isConnected || isGenerating}
        >
          {/* Simple Send Icon SVG */}
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
  );
}
