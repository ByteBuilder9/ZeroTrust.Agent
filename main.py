import time
import json
import logging
import asyncio
from typing import List, Optional, Any, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

import ledger
import scanner
import validator
import scrubber
import telemetry
from config_manager import config_manager
from admin import router as admin_router

# ==============================================================================
# Observability Configuration
# Structured JSON logging for Datadog/Splunk compatibility
# ==============================================================================
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "extra_info"):
            log_record.update(record.extra_info)
        return json.dumps(log_record)

logger = logging.getLogger("ZeroTrust.Agent")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# ==============================================================================
# FastAPI Application setup
# ==============================================================================
# Global HTTP client for proxying
http_client = httpx.AsyncClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 3: Configuration and Telemetry Initialization
    config_manager.load("config.yaml")
    scanner.init_scanner()
    scrubber.init_scrubber()
    validator.init_validator()
    
    await ledger.init_redis()
    await telemetry.init_db()
    
    yield
    
    await ledger.close_redis()
    await http_client.aclose()

app = FastAPI(
    title="ZeroTrust.Agent", 
    description="Semantic Firewall MVP for Multi-Agent LLMs",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 3: Include the Admin Dashboard
app.include_router(admin_router)

# ==============================================================================
# Pydantic Schemas
# ==============================================================================
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 1.0
    tools: Optional[List[Dict[str, Any]]] = None

async def intercept_request(body: bytes) -> ChatCompletionRequest:
    try:
        data = json.loads(body)
        return ChatCompletionRequest(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Schema validation failed: {str(e)}")

# ==============================================================================
# API Endpoints
# ==============================================================================
@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request, 
    x_agent_session_id: str = Header(default="anonymous_session")
):
    start_time = time.perf_counter()
    
    # --- PHASE 1: INBOUND INTERCEPTION ---
    body = await request.body()
    try:
        validated_payload = await intercept_request(body)
    except HTTPException as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.fire_event(x_agent_session_id, "inbound", "blocked", "Schema validation failed", latency_ms)
        raise e

    is_tainted = await ledger.is_session_tainted(x_agent_session_id)
    latest_user_message = next((msg.content for msg in reversed(validated_payload.messages) if msg.role == "user"), "")
    
    is_high_risk, reason = scanner.analyze_intent(latest_user_message)
    if is_high_risk:
        latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.fire_event(x_agent_session_id, "inbound", "blocked", reason, latency_ms)
        raise HTTPException(status_code=403, detail="Semantic Firewall blocked request: High-risk intent detected.")

    if is_tainted and validated_payload.tools is not None and len(validated_payload.tools) > 0:
        latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.fire_event(x_agent_session_id, "inbound", "blocked", "Tainted session attempting tool execution", latency_ms)
        raise HTTPException(status_code=403, detail="Semantic Firewall blocked request: Session tainted. Tool execution denied.")

    inbound_latency = (time.perf_counter() - start_time) * 1000
    telemetry.fire_event(x_agent_session_id, "inbound", "allowed", "Benign", inbound_latency)

    # --- PROXY TO UPSTREAM ---
    upstream_url = "http://127.0.0.1:8000/mock_llm/v1/chat/completions"
    upstream_req = http_client.build_request("POST", upstream_url, content=body, headers={"Content-Type": "application/json"})
    
    try:
        response = await http_client.send(upstream_req)
        response.raise_for_status()
        upstream_json = response.json()
    except Exception as e:
        logger.error(f"Upstream request failed: {str(e)}")
        raise HTTPException(status_code=502, detail="Bad Gateway")

    # --- PHASE 2: OUTBOUND INTERCEPTION ---
    outbound_start = time.perf_counter()

    if "choices" in upstream_json and len(upstream_json["choices"]) > 0:
        choice = upstream_json["choices"][0]
        message = choice.get("message", {})
        
        # 1. DLP Scrubber (Text Content)
        if message.get("content"):
            scrubbed_text, was_redacted, reason = scrubber.redact_sensitive_data(message["content"])
            message["content"] = scrubbed_text
            if was_redacted:
                out_latency = (time.perf_counter() - outbound_start) * 1000
                telemetry.fire_event(x_agent_session_id, "outbound", "redacted", reason, out_latency)

        # 2. Tool Validation (Tool Calls)
        tool_calls = message.get("tool_calls", [])
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name")
            arguments = function.get("arguments", "{}")
            
            is_valid, reason = validator.validate_tool_call(name, arguments)
            if not is_valid:
                out_latency = (time.perf_counter() - outbound_start) * 1000
                telemetry.fire_event(x_agent_session_id, "outbound", "blocked", f"Unauthorized tool: {reason}", out_latency)
                raise HTTPException(status_code=403, detail=f"Semantic Firewall blocked response: Unauthorized tool call payload for {name}.")

    out_latency = (time.perf_counter() - outbound_start) * 1000
    telemetry.fire_event(x_agent_session_id, "outbound", "allowed", "Benign output", out_latency)

    logger.info(
        "Request inspected, proxied, and scrubbed successfully",
        extra={"extra_info": {"inbound_latency_ms": f"{inbound_latency:.2f}", "outbound_latency_ms": f"{out_latency:.2f}", "action": "ALLOWED"}}
    )

    return JSONResponse(content=upstream_json)

# ==============================================================================
# Mock Upstream LLM for Testing
# ==============================================================================
@app.post("/mock_llm/v1/chat/completions")
async def mock_llm(request: Request):
    """
    Simulates the upstream LLM. 
    """
    payload = await request.json()
    messages = payload.get("messages", [])
    latest_msg = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), "")
    
    response = {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": payload.get("model", "gpt-4"),
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a clean response."
            },
            "finish_reason": "stop"
        }]
    }

    if "leak aws" in latest_msg.lower():
        response["choices"][0]["message"]["content"] = "Here is my key: AKIA1234567890ABCDEF"
    elif "leak card" in latest_msg.lower():
        response["choices"][0]["message"]["content"] = "Billing card: 4111 1111 1111 1111"
    elif "tool bad" in latest_msg.lower():
        response["choices"][0]["message"]["content"] = None
        response["choices"][0]["message"]["tool_calls"] = [{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "read_users_db",
                "arguments": '{"query": "DROP TABLE users;"}'
            }
        }]
    elif "tool good" in latest_msg.lower():
        response["choices"][0]["message"]["content"] = None
        response["choices"][0]["message"]["tool_calls"] = [{
            "id": "call_124",
            "type": "function",
            "function": {
                "name": "read_users_db",
                "arguments": '{"query": "SELECT * FROM users LIMIT 10;"}'
            }
        }]
    
    return JSONResponse(content=response)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
