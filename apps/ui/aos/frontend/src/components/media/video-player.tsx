'use client';

import '@videojs/react/video/skin.css';
import { createPlayer, videoFeatures } from '@videojs/react';
import { VideoSkin, Video } from '@videojs/react/video';

const Player = createPlayer({ features: videoFeatures });

interface AppVideoPlayerProps {
  src: string;
  className?: string;
}

export function AppVideoPlayer({ src, className }: AppVideoPlayerProps) {
  return (
    <div className={className}>
      <Player.Provider>
        <VideoSkin>
          <Video src={src} playsInline />
        </VideoSkin>
      </Player.Provider>
    </div>
  );
}
