# zImage - 文生图 MVP

基于 ComfyUI 的简易文生图网页应用，支持多用户隔离和内网穿透。

## 功能特点

- **Web1.0 纯黑白风格**：简洁复古的界面设计
- **亮色/暗色模式**：一键切换
- **多用户隔离**：每个用户有独立的生图历史和存储目录
- **ComfyUI 集成**：连接本地 ComfyUI 进行图片生成
- **内网穿透**：支持 Cloudflare Tunnel，可分享给外部用户访问

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制你的 ComfyUI 工作流文件到项目目录，命名为 `workflow.json`。

设置环境变量（Windows）：
```batch
set AUTH_TOKEN=你的口令
set WORKFLOW_PATH=workflow.json
```

### 3. 启动

确保 ComfyUI 已运行（默认 http://127.0.0.1:8188），然后：

```bash
# Windows
start.bat

# 或手动启动
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

### 4. 访问

- 本地：http://localhost:8000
- 输入用户名和口令即可使用

## 配置说明

通过环境变量配置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_PORT` | 8000 | 服务端口 |
| `AUTH_TOKEN` | changeme | 登录口令（请修改！） |
| `COMFY_BASE` | http://127.0.0.1:8188 | ComfyUI 地址 |
| `WORKFLOW_PATH` | workflow.json | ComfyUI 工作流文件路径 |
| `HISTORY_LIMIT` | 50 | 每用户历史记录数量 |
| `TIMEOUT_SECONDS` | 120 | 生图超时时间(秒) |

## 内网穿透（可选）

使用 Cloudflare Tunnel：

1. 下载 [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
2. 登录：`cloudflared login`
3. 创建隧道：`cloudflared tunnel create zimage`
4. 配置 `cloudflared-config.yml`
5. 启动：`start-tunnel-named.bat`

## 工作流要求

ComfyUI 工作流需要包含以下节点：
- **节点 2** (CLIPTextEncode)：正向提示词
- **节点 5** (EmptyLatentImage)：图片尺寸
- **节点 8** (SaveImage)：保存图片

## 项目结构

```
zimage/
├── index.html          # 前端页面
├── style.css           # 样式文件
├── app.js              # 前端逻辑
├── server.py           # FastAPI 后端
├── requirements.txt    # Python 依赖
├── start.bat           # Windows 启动脚本
├── workflow.json       # ComfyUI 工作流（需自行添加）
└── generated/          # 生成的图片（按用户分目录）
```

## License

MIT
