'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import GeminiChat, { Message } from '../../components/chat/GeminiChat';
import LecturePlayer, { VideoChunk } from '../../components/video/LecturePlayer';
import styles from './page.module.css';
import { WS_URL } from '@/lib/constants';
import { useLlmProviderStore } from '@/stores/llm-provider-store';

export default function ConversationPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [playlist, setPlaylist] = useState<VideoChunk[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const wsRef = useRef<WebSocket | null>(null);
  const toRequestPayload = useLlmProviderStore((s) => s.toRequestPayload);

  // Establish persistent WebSocket connection for real-time lecture streaming
  const connectWebSocket = useCallback(() => {
    const baseWs = WS_URL || 'ws://localhost:8000';
    const wsEndpoint = `${baseWs.replace(/\/$/, '')}/ws/generate_lecture`;

    try {
      const ws = new WebSocket(wsEndpoint);

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'status') {
            setStatusMessage(data.message || '');
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now().toString() + Math.random(),
                sender: 'gemini',
                text: `[System] ${data.message}`,
              },
            ]);
          } else if (data.type === 'syllabus') {
            const syllabusItems = (data.data || []) as string[];
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now().toString() + Math.random(),
                sender: 'gemini',
                text: `Here is the pedagogical syllabus planned:\n${syllabusItems.map((item, i) => `${i + 1}. ${item}`).join('\n')}`,
              },
            ]);
          } else if (data.type === 'play_intro') {
            // Push RUKUMINI branding intro chunk into playlist
            if (data.url) {
              setPlaylist((prev) => {
                if (prev.some((item) => item.type === 'intro')) return prev;
                return [{ type: 'intro', url: data.url }, ...prev];
              });
            }
          } else if (data.type === 'slide_generated') {
            // Push narration and Manim code into chat stream
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now().toString() + Math.random(),
                sender: 'gemini',
                text: data.narration || '',
                code: data.code || '',
              },
            ]);
          } else if (data.type === 'video_chunk') {
            // Push newly rendered discrete MP4 chunk into playlist
            if (data.url) {
              const newChunk: VideoChunk = {
                type: 'slide',
                slideNum: data.slide_num,
                url: data.url,
              };
              setPlaylist((prev) => {
                // Deduplicate by URL or slideNum
                if (prev.some((c) => c.type === 'slide' && c.slideNum === data.slide_num)) {
                  return prev.map((c) =>
                    c.type === 'slide' && c.slideNum === data.slide_num ? newChunk : c
                  );
                }
                return [...prev, newChunk];
              });
            }
          } else if (data.type === 'complete') {
            setIsGenerating(false);
            setIsComplete(true);
            setStatusMessage('All slides rendered and synchronized.');
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now().toString() + Math.random(),
                sender: 'gemini',
                text: `[System] 🎉 Lecture complete! All video chunks rendered successfully.`,
              },
            ]);
          }
        } catch (err) {
          console.error('Error handling WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
      };

      ws.onerror = (err) => {
        console.error('WebSocket connection error:', err);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to instantiate WebSocket:', err);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const handleSendPrompt = (prompt: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      return;
    }

    // Reset playlist and state for fresh lecture stream
    setPlaylist([]);
    setIsGenerating(true);
    setIsComplete(false);
    setStatusMessage(`Initializing lecture generation for "${prompt}"...`);

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: prompt,
    };
    setMessages((prev) => [...prev, userMessage]);

    // Send payload with user BYOK configuration
    const byok = toRequestPayload();
    const payload = {
      prompt,
      ...byok,
    };
    wsRef.current.send(JSON.stringify(payload));
  };

  return (
    <div className={styles.pageContainer}>
      <div className={styles.leftColumn}>
        <div className={styles.header}>
          <h1>EduClaw Studio</h1>
          <p>Agentic Lecture Generation Pipeline &bull; Live Sequential Chunk Stream</p>
        </div>
        <GeminiChat
          messages={messages}
          isGenerating={isGenerating}
          isConnected={isConnected}
          onSendMessage={handleSendPrompt}
        />
      </div>
      <div className={styles.rightColumn}>
        <LecturePlayer
          playlist={playlist}
          isGenerating={isGenerating}
          isComplete={isComplete}
          statusMessage={statusMessage}
        />
      </div>
    </div>
  );
}
