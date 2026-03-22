from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uvicorn

from graph_service import get_full_graph, get_subgraph_by_id
from llm_service import handle_chat_query

app = FastAPI(title="Context Graph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.get("/api/graph")
def graph(node_id: str = None, limit: int = None):
    try:
        if node_id:
            data = get_subgraph_by_id(node_id)
        else:
            data = get_full_graph(limit)
        return {"graph": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

class ChatRequest(BaseModel):
    query: str

@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        response = handle_chat_query(request.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount React Frontend in Production
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    
    @app.get("/{catchall:path}")
    def render_react(catchall: str):
        return FileResponse("frontend/dist/index.html")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
