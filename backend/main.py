from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db, SessionLocal
from backend.redis_client import set_cache, get_cache
from backend.agents.workflow import app_workflow
from backend.routers import auth, profile, orders, webhooks
from backend.websocket_manager import manager
from backend.monitoring import setup_monitoring
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from langchain_core.messages import HumanMessage
import json
import bleach

app = FastAPI(title="Agentic Commerce API")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

setup_monitoring(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(orders.router)
app.include_router(webhooks.router)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Agentic Commerce Backend is Running"}

@app.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            user_msg = json.loads(data)
            
            # Sanitize User Input to prevent injection
            sanitized_text = bleach.clean(user_msg["text"])
            
            # Run the agent workflow
            initial_state = {
                "messages": [HumanMessage(content=sanitized_text)],
                "next_step": "intent_parser",
                "user_id": user_id # Pass user_id to state
            }
            
            # Use the workflow. The coordinator node will use the manager to send updates.
            result = await app_workflow.ainvoke(initial_state)
            
            # Final response to user
            response = {
                "text": result.get('comparison_summary') or "Process complete.",
                "data": result.get("discovery_results")
            }
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f"User {user_id} disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
