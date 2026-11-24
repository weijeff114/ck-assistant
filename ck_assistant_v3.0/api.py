# Cf 助手 / ck-assistant
# Copyright (c) 2026 Wei Qiguang (weijeff114)
# SPDX-License-Identifier: GPL-3.0-only

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from engine import (
    load_config, save_config, analyze_chat, load_history, clear_history, 
    clear_context, load_saves, create_save, delete_save, clear_saves
)

app = FastAPI(title="Cf 助手 Web API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class AnalyzeRequest(BaseModel):
    chat_text: str
    session_name: str
    image_base64: str = None
    user_mood: str = "平静"
    user_context: str = ""

class ConfigRequest(BaseModel):
    config_data: dict

class SaveRequest(BaseModel):
    session_name: str
    note: str
    scene: dict

class BackgroundRequest(BaseModel):
    session_name: str
    background: str

@app.get("/")
async def serve_index(): return FileResponse("index.html")

@app.get("/galgame")
async def serve_galgame(): return FileResponse("galgame.html")

@app.get("/api/config")
async def get_config(): return load_config()

@app.post("/api/config")
async def update_config(request: ConfigRequest):
    save_config(request.config_data)
    return {"status": "success"}

@app.get("/api/sessions")
async def get_sessions():
    config = load_config()
    return {"sessions": config.get("sessions", ["默认单聊"]), "current_session": config.get("current_session", "默认单聊")}

@app.post("/api/background")
async def update_background(request: BackgroundRequest):
    config = load_config()
    config.setdefault("session_backgrounds", {})[request.session_name] = request.background
    save_config(config)
    return {"status": "success"}

@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        result = analyze_chat(request.chat_text, request.session_name, request.image_base64, request.user_mood, request.user_context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{session_name}")
async def get_history(session_name: str): return load_history(session_name)

@app.post("/api/clear_context/{session_name}")
async def clear_context_api(session_name: str):
    clear_context(session_name)
    return {"status": "success"}

@app.get("/api/saves/{session_name}")
async def get_saves(session_name: str): return load_saves(session_name)

@app.post("/api/saves")
async def save_scene(request: SaveRequest):
    save_id = create_save(request.session_name, request.note, request.scene)
    if save_id: return {"status": "success", "id": save_id}
    raise HTTPException(status_code=500, detail="保存失败")

@app.delete("/api/saves/{session_name}/{save_id}")
async def remove_save(session_name: str, save_id: str):
    success = delete_save(session_name, save_id)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="删除失败")

@app.post("/api/saves/{session_name}/clear")
async def clear_all_saves(session_name: str):
    clear_saves(session_name)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
