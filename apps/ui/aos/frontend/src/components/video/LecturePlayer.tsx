'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import styles from './LecturePlayer.module.css';
import { BACKEND_URL } from '@/lib/constants';

export interface VideoChunk {
  type: 'intro' | 'slide';
  slideNum?: number;
  url: string;
}

export interface LecturePlayerProps {
  playlist?: VideoChunk[];
  isGenerating?: boolean;
  isComplete?: boolean;
  statusMessage?: string;
  videoUrl?: string; // Legacy fallback
  showStatic?: boolean; // Legacy fallback / force flag
}

export default function LecturePlayer({
  playlist = [],
  isGenerating = false,
  isComplete = false,
  statusMessage = '',
  videoUrl,
  showStatic: externalShowStatic,
}: LecturePlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [internalStatic, setInternalStatic] = useState<boolean>(false);
  const [isFinished, setIsFinished] = useState<boolean>(false);

  // Normalize effective playlist
  const effectivePlaylist: VideoChunk[] = React.useMemo(() => {
    if (playlist && playlist.length > 0) return playlist;
    if (videoUrl) return [{ type: 'slide', slideNum: 1, url: videoUrl }];
    return [];
  }, [playlist, videoUrl]);

  // Helper to resolve absolute or backend URL
  const resolveUrl = useCallback((url: string) => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('blob:')) {
      return url;
    }
    const base = BACKEND_URL || 'http://localhost:8000';
    return `${base.replace(/\/$/, '')}/${url.replace(/^\//, '')}`;
  }, []);

  // When playlist receives initial item, start playing first track
  useEffect(() => {
    if (currentIndex === -1 && effectivePlaylist.length > 0) {
      setCurrentIndex(0);
      setInternalStatic(false);
      setIsFinished(false);
    }
  }, [effectivePlaylist.length, currentIndex]);

  // If player was waiting in buffer underrun static and next chunk arrives, resume!
  useEffect(() => {
    if (internalStatic && currentIndex + 1 < effectivePlaylist.length) {
      setCurrentIndex((prev) => prev + 1);
      setInternalStatic(false);
    }
  }, [effectivePlaylist.length, internalStatic, currentIndex]);

  // Video track onEnded handler: orchestrates smooth transition or TV static loop
  const handleTrackEnded = () => {
    if (currentIndex + 1 < effectivePlaylist.length) {
      // Next slide already rendered and buffered
      setCurrentIndex((prev) => prev + 1);
      setInternalStatic(false);
    } else if (isComplete) {
      // Entire lecture finished
      setIsFinished(true);
      setInternalStatic(false);
    } else {
      // BUFFER UNDERRUN: Next slide is still rendering in the background.
      // Next.js frontend orchestrator displays seamless TV static noise in browser!
      setInternalStatic(true);
    }
  };

  const handleReplay = () => {
    setIsFinished(false);
    setInternalStatic(false);
    setCurrentIndex(0);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play().catch(() => {});
    }
  };

  const currentChunk = effectivePlaylist[currentIndex] as VideoChunk | undefined;
  const currentResolvedUrl = currentChunk ? resolveUrl(currentChunk.url) : '';

  // Determine if TV static should be active
  const isBufferUnderrun =
    externalShowStatic ??
    (internalStatic || (isGenerating && effectivePlaylist.length === 0));

  const currentLabel = currentChunk
    ? currentChunk.type === 'intro'
      ? 'Intro (RUKUMINI)'
      : `Slide ${currentChunk.slideNum ?? currentIndex}`
    : 'Awaiting Stream';

  return (
    <div className={styles.playerContainer}>
      {/* TV Static Noise Fallback Layer */}
      {isBufferUnderrun && (
        <div className={styles.staticContainer}>
          <div className={styles.scanlines} />
          <div className={styles.staticBadge}>
            <div className={styles.staticText}>SIGNAL LOST</div>
            <div className={styles.staticSubtext}>
              <span className={styles.pulseDot} />
              {statusMessage ||
                (effectivePlaylist.length === 0
                  ? 'Connecting to EduClaw Neural Stream...'
                  : `Awaiting Slide ${currentIndex + 1}... Rendering in background`)}
            </div>
          </div>
        </div>
      )}

      {/* Finished Overlay */}
      {isFinished && !isBufferUnderrun && (
        <div className={styles.completeOverlay}>
          <div className={styles.completeTitle}>Lecture Complete</div>
          <div className={styles.completeSubtext}>
            All visual slides rendered and synchronized with voiceover.
          </div>
          <button onClick={handleReplay} className={styles.replayButton}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 4v6h6M23 20v-6h-6" />
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
            </svg>
            Replay Lecture
          </button>
        </div>
      )}

      {/* Top HUD Bar */}
      {effectivePlaylist.length > 0 && !isBufferUnderrun && !isFinished && (
        <div className={styles.hudTopBar}>
          <div className={styles.liveBadge}>
            <span className={styles.liveDot} />
            {isGenerating ? 'LIVE GENERATION' : 'PLAYBACK'} &bull; {currentLabel}
          </div>
        </div>
      )}

      {/* Video Viewport */}
      {currentResolvedUrl ? (
        <video
          key={currentResolvedUrl}
          ref={videoRef}
          src={currentResolvedUrl}
          className={styles.videoElement}
          autoPlay
          controls={!isGenerating}
          playsInline
          muted={false}
          onEnded={handleTrackEnded}
        />
      ) : (
        !isGenerating &&
        !isBufferUnderrun && (
          <div className={styles.placeholder}>
            <h2>Lecture Viewport</h2>
            <p>
              Enter a lecture topic on the left to start live chunked streaming with
              synchronized voiceover.
            </p>
          </div>
        )
      )}

      {/* Bottom Track Pills */}
      {effectivePlaylist.length > 0 && (
        <div className={styles.hudBottomBar}>
          {effectivePlaylist.map((chunk, idx) => {
            const isActive = idx === currentIndex && !internalStatic;
            const isDone = idx < currentIndex;
            const title =
              chunk.type === 'intro' ? 'Intro' : `Slide ${chunk.slideNum ?? idx}`;
            return (
              <button
                key={chunk.url || idx}
                onClick={() => {
                  setCurrentIndex(idx);
                  setInternalStatic(false);
                  setIsFinished(false);
                }}
                className={`${styles.trackPill} ${isActive ? styles.trackPillActive : ''} ${isDone ? styles.trackPillDone : ''}`}
              >
                {isDone && '✓ '}
                {title}
              </button>
            );
          })}
          {isGenerating && (
            <div className={styles.trackPill} style={{ opacity: 0.7 }}>
              <span className={styles.pulseDot} style={{ width: 6, height: 6 }} />
              Rendering...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
