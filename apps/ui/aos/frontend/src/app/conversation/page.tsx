import React from 'react';
import GeminiChat from '../../components/chat/GeminiChat';
import LecturePlayer from '../../components/video/LecturePlayer';
import styles from './page.module.css';

export default function ConversationPage() {
  return (
    <div className={styles.pageContainer}>
      <div className={styles.leftColumn}>
        <div className={styles.header}>
          <h1>EduClaw Studio</h1>
          <p>Agentic Lecture Generation Pipeline</p>
        </div>
        <GeminiChat />
      </div>
      <div className={styles.rightColumn}>
        {/* For the prototype, we assume we aren't passing state up from GeminiChat yet, 
            but in a full implementation, the WS state would live in a context or here 
            and feed down to both Chat and Player. */}
        <LecturePlayer />
      </div>
    </div>
  );
}
