'use client';

import React, { useState, useEffect, useRef } from 'react';
import styles from './GeminiChat.module.css';
import { WS_URL } from '@/lib/constants';
import { useLlmProviderStore } from '@/stores/llm-provider-store';

export interface Message {
  id: string;
  sender: 'user' | 'gemini';
  text: string;
  code?: string;
}

export interface GeminiChatProps {
  messages?: Message[];
  isGenerating?: boolean;
  isConnected?: boolean;
  onSendMessage?: (text: string) => void;
}

export default function GeminiChat({
  messages: externalMessages,
  isGenerating: externalIsGenerating,
  isConnected: externalIsConnected,
  onSendMessage: externalOnSendMessage,
}: GeminiChatProps) {
  const [internalMessages, setInternalMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [internalConnected, setInternalConnected] = useState(false);
  const [internalGenerating, setInternalGenerating] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const toRequestPayload = useLlmProviderStore((s) => s.toRequestPayload);

  const isControlled = externalOnSendMessage !== undefined;
  const messages = isControlled ? (externalMessages ?? []) : internalMessages;
  const isConnected = isControlled ? (externalIsConnected ?? true) : internalConnected;
  const isGenerating = isControlled ? (externalIsGenerating ?? false) : internalGenerating;

  // Standalone connection fallback if not controlled by parent page
  useEffect(() => {
    if (isControlled) return;

    const baseWs = WS_URL || 'ws://localhost:8000';
    const wsEndpoint = `${baseWs.replace(/\/$/, '')}/ws/generate_lecture`;
    const ws = new WebSocket(wsEndpoint);

    ws.onopen = () => {
      setInternalConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'status') {
          setInternalMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'gemini',
              text: `[System] ${data.message}`,
            },
          ]);
        } else if (data.type === 'syllabus') {
          setInternalMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'gemini',
              text: `Here is the syllabus I planned:\n${(data.data || []).map((item: string, i: number) => `${i + 1}. ${item}`).join('\n')}`,
            },
          ]);
        } else if (data.type === 'slide_generated') {
          setInternalMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'gemini',
              text: data.narration,
              code: data.code,
            },
          ]);
          if (data.is_final) {
            setInternalGenerating(false);
          }
        }
      } catch (err) {
        console.error('Failed to parse websocket message', err);
      }
    };

    ws.onclose = () => {
      setInternalConnected(false);
      setInternalGenerating(false);
    };

    wsRef.current = ws;

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isControlled]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isGenerating) return;

    if (isControlled && externalOnSendMessage) {
      externalOnSendMessage(trimmed);
      setInputValue('');
      return;
    }

    if (!wsRef.current || !internalConnected) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: trimmed,
    };

    setInternalMessages((prev) => [...prev, userMsg]);
    setInternalGenerating(true);

    const payload = {
      prompt: trimmed,
      ...toRequestPayload(),
    };
    wsRef.current.send(JSON.stringify(payload));
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
            <h2>EduClaw Agentic Studio</h2>
            <p>What concept would you like to visualize in live-streamed slides?</p>
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
                  <pre>
                    <code>{msg.code}</code>
                  </pre>
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
          placeholder="e.g. Explain the Lorenz Attractor in 3 visual slides..."
          className={styles.inputField}
          disabled={!isConnected || isGenerating}
        />
        <button
          onClick={handleSend}
          className={styles.sendButton}
          disabled={!inputValue.trim() || !isConnected || isGenerating}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
  );
}
