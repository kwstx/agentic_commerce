from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db, SessionLocal
from backend.redis_client import set_cache, get_cache
from backend.agents.workflow import app_workflow
from langchain_core.messages import HumanMessage
import json

app = FastAPI(title="Agentic Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Agentic Commerce Backend is Running"}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            user_msg = json.loads(data)
            
            # Run the agent workflow
            initial_state = {
                "messages": [HumanMessage(content=user_msg["text"])],
                "next_step": "intent_parser"
            }
            
            # In a real app, this would be handled asynchronously
            # and might stream updates from each node
            result = app_workflow.invoke(initial_state)
            
            # Final response to user
            response = {
                "text": f"Found these for you: {result.get('comparison_summary')}",
                "data": result.get("discovery_results")
            }
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
