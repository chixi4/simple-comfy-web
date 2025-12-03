"""
zImage - Text to Image MVP Server
Connects to local ComfyUI for image generation
"""

import asyncio
import json
import os
import random
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional
from uuid import uuid4

import httpx
import websockets
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Configuration
APP_PORT = int(os.getenv("APP_PORT", "8000"))
COMFY_BASE = os.getenv("COMFY_BASE", "http://127.0.0.1:8188").rstrip("/")
SECRET_TOKEN = os.getenv("AUTH_TOKEN", "change")
WORKFLOW_PATH = Path(
    os.getenv(
        "WORKFLOW_PATH",
        r"E:\dev\ComfyUI-aki-v2\ComfyUI\user\default\workflows\文生图公益.json",
    )
)
GENERATED_DIR = Path("generated")
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "50"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "120"))

# FastAPI App
app = FastAPI(title="zImage MVP", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-user history storage: username -> deque of history items
user_history_store: Dict[str, Deque[Dict[str, Any]]] = {}


# Pydantic Models
class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    width: int = Field(..., ge=64, le=2048)
    height: int = Field(..., ge=64, le=2048)


class HistoryItem(BaseModel):
    id: str
    username: str
    prompt: str
    width: int
    height: int
    image: str
    created_at: str


# Utility Functions
def ensure_dirs(username: Optional[str] = None) -> Path:
    """Create necessary directories."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    if username:
        user_dir = GENERATED_DIR / username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    return GENERATED_DIR


def require_token(authorization: Optional[str] = Header(None)) -> str:
    """Validate authorization token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录口令",
        )

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证格式",
        )

    token = authorization.split(" ", 1)[1]
    if token != SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="口令错误",
        )

    return token


def require_username(x_username: Optional[str] = Header(None, alias="X-Username")) -> str:
    """Extract and validate username from header."""
    if not x_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要用户名",
        )

    username = x_username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要用户名",
        )

    # Validate username format: letters, numbers, underscore, hyphen, 1-32 chars
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名只允许字母、数字、下划线、短横线，长度1-32",
        )

    return username


def get_user_history(username: str) -> Deque[Dict[str, Any]]:
    """Get or create per-user history deque."""
    if username not in user_history_store:
        user_history_store[username] = deque(maxlen=HISTORY_LIMIT)
    return user_history_store[username]


def load_workflow() -> Dict[str, Any]:
    """Load and parse workflow JSON file."""
    if not WORKFLOW_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"工作流文件不存在: {WORKFLOW_PATH}",
        )

    try:
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"工作流JSON解析失败: {e}",
        )


def convert_to_api_format(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert ComfyUI frontend workflow format to API format.

    Frontend format has 'nodes' array with node objects.
    API format uses node IDs as keys with 'inputs' and 'class_type'.
    """
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])

    # Build link mapping: link_id -> (source_node_id, source_slot)
    link_map = {}
    for link in links:
        # link format: [link_id, source_node_id, source_slot, target_node_id, target_slot, type]
        link_id = link[0]
        source_node_id = link[1]
        source_slot = link[2]
        link_map[link_id] = (source_node_id, source_slot)

    api_workflow = {}

    for node in nodes:
        node_id = str(node["id"])
        node_type = node["type"]
        widgets_values = node.get("widgets_values", [])
        node_inputs = node.get("inputs", [])

        # Build inputs dict
        inputs = {}

        # First, add widget values based on node type
        if node_type == "CLIPTextEncode":
            # text is the first widget value (may have additional flags)
            if widgets_values:
                inputs["text"] = widgets_values[0] if isinstance(widgets_values[0], str) else ""

        elif node_type == "EmptyLatentImage":
            # width, height, batch_size
            if len(widgets_values) >= 3:
                inputs["width"] = widgets_values[0]
                inputs["height"] = widgets_values[1]
                inputs["batch_size"] = widgets_values[2]

        elif node_type == "KSampler":
            # seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise
            if len(widgets_values) >= 7:
                inputs["seed"] = widgets_values[0]
                inputs["steps"] = widgets_values[2]
                inputs["cfg"] = widgets_values[3]
                inputs["sampler_name"] = widgets_values[4]
                inputs["scheduler"] = widgets_values[5]
                inputs["denoise"] = widgets_values[6]

        elif node_type == "CheckpointLoaderSimple":
            if widgets_values:
                inputs["ckpt_name"] = widgets_values[0]

        elif node_type == "VAELoader":
            if widgets_values:
                inputs["vae_name"] = widgets_values[0]

        elif node_type == "CLIPLoader":
            if len(widgets_values) >= 2:
                inputs["clip_name"] = widgets_values[0]
                inputs["type"] = widgets_values[1]

        elif node_type == "SaveImage":
            if widgets_values:
                inputs["filename_prefix"] = widgets_values[0] if isinstance(widgets_values[0], str) else "ComfyUI"

        elif node_type == "VAEDecode":
            pass  # VAEDecode has no widget inputs

        # Then, add linked inputs (connections from other nodes)
        for inp in node_inputs:
            input_name = inp["name"]
            link_id = inp.get("link")
            if link_id is not None and link_id in link_map:
                source_node_id, source_slot = link_map[link_id]
                # Format: [node_id_str, slot_index]
                inputs[input_name] = [str(source_node_id), source_slot]

        api_workflow[node_id] = {
            "class_type": node_type,
            "inputs": inputs,
        }

    return api_workflow


def patch_workflow(
    api_workflow: Dict[str, Any],
    prompt: str,
    width: int,
    height: int,
    username: str,
) -> Dict[str, Any]:
    """
    Patch the API workflow with user inputs.

    Node mapping (from workflow analysis):
    - Node 2: CLIPTextEncode (正向/positive prompt)
    - Node 5: EmptyLatentImage (width, height)
    - Node 8: SaveImage
    """
    import copy
    patched = copy.deepcopy(api_workflow)

    # Patch positive prompt (Node 2)
    if "2" in patched:
        patched["2"]["inputs"]["text"] = prompt

    # Patch dimensions (Node 5)
    if "5" in patched:
        patched["5"]["inputs"]["width"] = width
        patched["5"]["inputs"]["height"] = height

    # Randomize seed (Node 4 - KSampler)
    if "4" in patched:
        patched["4"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)

    # Set unique filename prefix with username (Node 8)
    if "8" in patched:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patched["8"]["inputs"]["filename_prefix"] = f"{username}_zimage_{timestamp}"

    return patched


async def submit_prompt(prompt_data: Dict[str, Any], client_id: str) -> str:
    """Submit prompt to ComfyUI and return prompt_id."""
    url = f"{COMFY_BASE}/prompt"

    payload = {
        "prompt": prompt_data,
        "client_id": client_id,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        try:
            response = await client.post(url, json=payload)
        except httpx.ConnectError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="无法连接到ComfyUI，请确保ComfyUI已启动",
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ComfyUI提交失败: {response.text}",
            )

        result = response.json()
        return result.get("prompt_id", "")


async def wait_for_result(client_id: str, timeout: int = TIMEOUT_SECONDS) -> List[Dict[str, str]]:
    """
    Wait for ComfyUI to complete execution via WebSocket.
    Returns list of generated images.
    """
    ws_url = COMFY_BASE.replace("http", "ws") + f"/ws?clientId={client_id}"
    images: List[Dict[str, str]] = []

    try:
        async with websockets.connect(ws_url, open_timeout=10) as ws:
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="生图超时，请重试",
                    )

                # Skip binary messages (preview images)
                if isinstance(raw, bytes):
                    continue

                msg = json.loads(raw)
                msg_type = msg.get("type")

                if msg_type == "executed":
                    data = msg.get("data", {})
                    node = data.get("node")
                    # Node 8 is SaveImage - compare as string (ComfyUI may return int or str)
                    if str(node) == "8":
                        output = data.get("output", {})
                        images = output.get("images", [])
                        break

                elif msg_type == "execution_error":
                    error_data = msg.get("data", {})
                    error_msg = error_data.get("exception_message", "未知错误")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"ComfyUI执行错误: {error_msg}",
                    )

                elif msg_type == "execution_cached":
                    # Check if SaveImage node was cached
                    data = msg.get("data", {})
                    cached_nodes = data.get("nodes", [])
                    # Convert to strings for comparison
                    cached_str = [str(n) for n in cached_nodes]
                    if "8" in cached_str:
                        # Node was cached, we need to fetch from history
                        pass

                elif msg_type == "execution_interrupted":
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="生成被中断",
                    )

    except websockets.exceptions.WebSocketException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"WebSocket连接失败: {e}",
        )

    if not images:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未生成图片",
        )

    return images


async def download_image(image_info: Dict[str, str], username: str) -> str:
    """Download image from ComfyUI and save to user's directory."""
    user_dir = ensure_dirs(username)

    filename = image_info.get("filename", "")
    subfolder = image_info.get("subfolder", "")
    img_type = image_info.get("type", "output")

    url = f"{COMFY_BASE}/view"
    params = {
        "filename": filename,
        "subfolder": subfolder,
        "type": img_type,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="下载图片失败",
            )

        # Save with timestamp prefix
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = f"{timestamp}_{filename}"
        save_path = user_dir / safe_name
        save_path.write_bytes(response.content)

        return f"/generated/{username}/{safe_name}"


def add_to_history(username: str, prompt: str, width: int, height: int, image_url: str) -> None:
    """Add generation to user's history."""
    user_history = get_user_history(username)
    user_history.appendleft({
        "id": str(uuid4()),
        "username": username,
        "prompt": prompt[:200],
        "width": width,
        "height": height,
        "image": image_url,
        "created_at": datetime.utcnow().isoformat() + "Z",
    })


# API Endpoints
@app.post("/api/generate")
async def generate_image(
    request: GenerateRequest,
    token: str = Depends(require_token),
    username: str = Depends(require_username),
):
    """Generate an image from text prompt."""
    print(f"[Generate] User: {username}, Prompt: {request.prompt[:50]}...")

    # Load and convert workflow
    raw_workflow = load_workflow()
    api_workflow = convert_to_api_format(raw_workflow)

    # Patch with user inputs
    patched = patch_workflow(
        api_workflow,
        request.prompt,
        request.width,
        request.height,
        username,
    )

    # Submit to ComfyUI
    client_id = str(uuid4())
    await submit_prompt(patched, client_id)

    # Wait for result
    images = await wait_for_result(client_id)

    # Download first image to user's directory
    image_url = await download_image(images[0], username)

    # Add to user's history
    add_to_history(username, request.prompt, request.width, request.height, image_url)

    return {
        "success": True,
        "image": image_url,
        "width": request.width,
        "height": request.height,
    }


@app.get("/api/history")
async def get_history(
    token: str = Depends(require_token),
    username: str = Depends(require_username),
):
    """Get user's generation history."""
    return {"history": list(get_user_history(username))}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    comfy_ok = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{COMFY_BASE}/system_stats")
            comfy_ok = resp.status_code == 200
    except Exception:
        pass

    return {
        "status": "ok",
        "comfy_connected": comfy_ok,
        "comfy_url": COMFY_BASE,
    }


# Static file serving
@app.get("/")
async def serve_index():
    return FileResponse("index.html", media_type="text/html")


@app.get("/style.css")
async def serve_css():
    return FileResponse("style.css", media_type="text/css")


@app.get("/app.js")
async def serve_js():
    return FileResponse("app.js", media_type="application/javascript")


# Mount generated images directory
@app.on_event("startup")
async def startup_event():
    ensure_dirs()
    app.mount("/generated", StaticFiles(directory=str(GENERATED_DIR)), name="generated")


if __name__ == "__main__":
    import uvicorn

    print(f"Starting zImage server on port {APP_PORT}")
    print(f"ComfyUI endpoint: {COMFY_BASE}")
    print(f"Workflow: {WORKFLOW_PATH}")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=APP_PORT,
        reload=False,
    )
