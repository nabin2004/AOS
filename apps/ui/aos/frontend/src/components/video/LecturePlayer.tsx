'use client';

import React, { useState, useEffect, useRef } from 'react';
import styles from './LecturePlayer.module.css';

interface LecturePlayerProps {
  // In a real implementation, this would receive the WebSocket connection 
  // or a stream URL from a parent component that manages the state.
  isGenerating?: boolean;
  videoUrl?: string; // Currently playing chunk or live stream URL
  showStatic?: boolean; // Signal from backend of buffer underrun
}

export default function LecturePlayer({ isGenerating, videoUrl, showStatic }: LecturePlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Simulated fallback for the prototype
  const isBufferUnderrun = showStatic || (isGenerating && !videoUrl);

  return (
    <div className={styles.playerContainer}>
      {/* TV Static Fallback layer */}
      {isBufferUnderrun && (
        <div className={styles.staticContainer}>
          <div className={styles.staticText}>... SIGNAL LOST ...</div>
          <div style={{color: 'white', marginTop: '10px', fontFamily: 'Inter', backgroundColor: 'rgba(0,0,0,0.5)', padding: '4px 8px', borderRadius: '4px'}}>
            Awaiting Next Slide
          </div>
        </div>
      )}

      {/* Actual Video Player */}
      {videoUrl ? (
        <video 
          ref={videoRef}
          src={videoUrl}
          className={styles.videoElement}
          autoPlay
          controls={!isGenerating} // Hide controls while live generating
          muted={false}
          onEnded={() => {
            // In a real sequential chunk implementation, 
            // when a chunk ends, we check if the next is ready.
            // If not, we set state to show static.
          }}
        />
      ) : (
        !isGenerating && (
          <div className={styles.placeholder}>
            <h2>Lecture Viewport</h2>
            <p>Your generated lecture will appear here.</p>
          </div>
        )
      )}
    </div>
  );
}
