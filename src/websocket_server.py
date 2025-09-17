import json
import logging
import asyncio
from typing import Dict, Set
import uuid
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .agent import Agent, Message, MessageType

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_agents: Dict[str, Agent] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        if session_id not in self.session_agents:
            self.session_agents[session_id] = Agent()
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(json.dumps(message))

    async def send_stream(self, session_id: str, stream_generator):
        """Send a stream of messages to a specific session"""
        if session_id in self.active_connections:
            async for message in stream_generator:
                await self.send_message(session_id, message)

app = FastAPI(title="AI App Builder API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection manager
manager = ConnectionManager()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    logger.info(f"!!! WebSocket endpoint ENTERED for session {session_id}")
    
    try:
        logger.info(f"!!! About to call manager.connect for session {session_id}")
        await manager.connect(websocket, session_id)
        logger.info(f"!!! Manager.connect completed for session {session_id}")
        
        agent = manager.session_agents[session_id]
        logger.info(f"!!! Got agent for session {session_id}")
        
        logger.info(f"WebSocket endpoint started for session {session_id}")
        
        while True:
            # Wait for message from client
            logger.info(f"Waiting for message from client on session {session_id}")
            data = await websocket.receive_text()
            logger.info(f"Raw message received on session {session_id}: {data}")
            
            try:
                logger.info(f"Received WebSocket message for session {session_id}: {data}")
                message = json.loads(data)
                message_type = message.get("type")
                logger.info(f"Message type: {message_type}")
                
                if message_type == MessageType.INIT.value:
                    # Initialize agent session
                    logger.info(f"Processing INIT message for session {session_id}")
                    try:
                        logger.info(f"About to call agent.init for session {session_id}")
                        exists = await agent.init(session_id)
                        logger.info(f"Agent init completed for session {session_id}, exists: {exists}")
                        
                        session_data = agent.session_data.get(session_id, {})
                        logger.info(f"Session data for {session_id}: {session_data}")
                        
                        response = Message.new(
                            MessageType.INIT,
                            {**session_data, "exists": exists},
                            session_id=session_id
                        )
                        logger.info(f"Sending INIT response: {response.to_dict()}")
                        await manager.send_message(session_id, response.to_dict())
                        logger.info(f"INIT response sent successfully for session {session_id}")
                    except Exception as e:
                        logger.error(f"Error during INIT processing for session {session_id}: {e}")
                        import traceback
                        logger.error(f"INIT error traceback: {traceback.format_exc()}")
                        error_response = Message.new(
                            MessageType.INIT,
                            {"error": str(e)},
                            session_id=session_id
                        )
                        await manager.send_message(session_id, error_response.to_dict())
                
                elif message_type == MessageType.USER.value:
                    # Handle user feedback - this returns a generator for streaming
                    feedback = message["data"]["text"]
                    stream_generator = agent.send_feedback(
                        session_id=session_id, 
                        feedback=feedback
                    )
                    
                    # Stream messages to client
                    await manager.send_stream(session_id, stream_generator)
                
                elif message_type == MessageType.LOAD_CODE.value:
                    # Load current code
                    code_map, package_json = await agent.load_code(session_id=session_id)
                    response = Message.new(
                        MessageType.LOAD_CODE,
                        {"code_map": code_map, "package_json": package_json},
                        session_id=session_id
                    )
                    await manager.send_message(session_id, response.to_dict())
                
                elif message_type == MessageType.PING.value:
                    # Handle ping
                    pong = Message.new(MessageType.PING, {}, session_id=session_id)
                    await manager.send_message(session_id, pong.to_dict())
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received from client for session {session_id}: {e}")
            except Exception as e:
                logger.error(f"Error processing message for session {session_id}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                error_msg = Message.new(
                    MessageType.AGENT_FINAL,
                    {"error": str(e)},
                    session_id=session_id
                )
                await manager.send_message(session_id, error_msg.to_dict())
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        import traceback
        logger.error(f"WebSocket traceback: {traceback.format_exc()}")
        manager.disconnect(session_id)

@app.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get the status of a specific session"""
    if session_id in manager.session_agents:
        agent = manager.session_agents[session_id]
        return {
            "session_id": session_id,
            "connected": session_id in manager.active_connections,
            "has_sandbox": session_id in agent.session_data,
            "sandbox_data": agent.session_data.get(session_id, {}),
            "history_length": len(agent.history)
        }
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.delete("/sessions/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up a session and its resources"""
    if session_id in manager.session_agents:
        agent = manager.session_agents[session_id]
        # Clean up sandbox resources if any
        if session_id in agent.session_data:
            # TODO: Add proper sandbox cleanup
            pass
        
        # Remove from manager
        del manager.session_agents[session_id]
        manager.disconnect(session_id)
        
        return {"message": f"Session {session_id} cleaned up"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "websocket_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )