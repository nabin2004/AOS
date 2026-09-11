from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import threading
from queue import Queue
from manim import config
import os
import subprocess

from apps.educlaw.streaming_engine.producer import LectureProducer
# The consumer script will be executed via a subprocess to isolate Manim rendering

router = APIRouter()

# Global registry for the queue, used by consumer if running in the same process
# but since Manim is tricky with threads, we'll keep it here just in case.
active_queue = None

@router.websocket("/ws/generate_lecture")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global active_queue
    active_queue = Queue()
    
    producer = LectureProducer(active_queue)
    
    try:
        data = await websocket.receive_text()
        # Expecting JSON or simple string. For demo, it's just the topic string
        topic = data
        
        await websocket.send_json({"type": "status", "message": f"Generating outline for: {topic}"})
        syllabus = producer.generate_syllabus(topic)
        await websocket.send_json({"type": "syllabus", "data": syllabus})
        
        # Start producer thread
        producer_thread = threading.Thread(target=producer.run_production_loop, args=(syllabus,))
        producer_thread.start()
        
        # Start Manim consumer thread/subprocess
        # For this PoC, since Manim works best as a main thread process, 
        # we will simulate the consumer streaming back by polling the queue here,
        # but in reality Manim needs to consume this queue directly.
        # To make it work in FastAPI: We can run the consumer in a thread IF it doesn't crash OpenGL.
        # Let's write the Manim code to a temp file or run it via sub-process.
        # But wait, our consumer.py uses `active_queue` from this module.
        # If we run it in a thread:
        def run_manim():
            # Set Manim config to low quality for fast generation
            config.quality = "low_quality"
            # It's safer to run Manim via subprocess and use IPC, but to adhere to the architecture 
            # we planned where Manim accesses the queue directly, we import here.
            from apps.educlaw.streaming_engine.consumer import EduClawStreamingScene
            scene = EduClawStreamingScene()
            scene.render()

        # manim_thread = threading.Thread(target=run_manim)
        # manim_thread.start()
        
        # Since Manim rendering might block or crash FastAPI in same process, 
        # we will stream the text directly back to the UI for the "Conversation"
        while True:
            # Poll the queue (which is also being polled by Manim in reality)
            # For this UI prototype, we'll just intercept the items and send to frontend
            # Note: in a true architecture, Manim consumes the queue, and a separate 
            # mechanism watches Manim's output folder to stream MP4s to UI.
            
            # Since this is a prototype/plan execution, let's stream the generated markdown back.
            slide_data = active_queue.get()
            await websocket.send_json({
                "type": "slide_generated",
                "narration": slide_data.narration,
                "code": slide_data.python_code,
                "is_final": slide_data.is_final_slide
            })
            
            if slide_data.is_final_slide:
                await websocket.send_json({"type": "status", "message": "Generation complete."})
                break
                
    except WebSocketDisconnect:
        print("Client disconnected")
