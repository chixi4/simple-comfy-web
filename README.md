# zImage - 文生图 MVP

基于 ComfyUI 的简易文生图网页应用，支持内网穿透让多人访问。

## 功能特点

- **Web1.0 纯黑白风格**：简洁复古的界面设计
- **亮色/暗色模式**：一键切换
- **图片生成**：输入提示词，自定义分辨率
- **生图历史**：查看之前生成的图片
- **内网穿透**：使用 Cloudflare Tunnel 支持外网访问

## 前置要求

1. **Python 3.8+**
2. **ComfyUI** - 需要在本地运行 (默认端口 8188)
3. **cloudflared** - 用于内网穿透 (可选)

## 快速开始

### 1. 安装依赖

```bash
# 双击运行
install.bat

# 或手动安装
pip install -r requirements.txt
```

### 2. 确保 ComfyUI 已启动

ComfyUI 需要在 `http://127.0.0.1:8188` 运行。

### 3. 启动服务

```bash
# 双击运行
start.bat

# 或手动启动
python server.py
```

### 4. 访问网页

- 本地访问：http://localhost:8000
- 默认口令：`zimage2024`

## 内网穿透设置

### 下载 Cloudflared

1. 从 [Cloudflare 官网](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) 下载 `cloudflared-windows-amd64.exe`
2. 将文件放到项目目录下

### 启动隧道

方式一：使用 `start.bat` 会自动启动隧道

方式二：单独启动隧道
```bash
start-tunnel.bat
```

启动后会显示一个 `*.trycloudflare.com` 的地址，将此地址分享给需要访问的用户。

## 配置说明

可通过环境变量自定义配置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_PORT` | 8000 | 服务端口 |
| `AUTH_TOKEN` | zimage2024 | 登录口令 |
| `COMFY_BASE` | http://127.0.0.1:8188 | ComfyUI 地址 |
| `HISTORY_LIMIT` | 50 | 历史记录数量 |
| `TIMEOUT_SECONDS` | 120 | 生图超时时间(秒) |

修改方法（Windows）：
```batch
set AUTH_TOKEN=你的新口令
set APP_PORT=3000
start.bat
```

## 文件结构

```
zimage/
├── index.html      # 前端页面
├── style.css       # 样式文件
├── app.js          # 前端逻辑
├── server.py       # 后端服务器
├── requirements.txt
├── start.bat       # 启动脚本
├── start-tunnel.bat # 单独启动隧道
├── install.bat     # 安装依赖
├── generated/      # 生成的图片存储目录
└── README.md
```

## 工作流说明

本项目使用的工作流文件：
`E:\dev\ComfyUI-aki-v2\ComfyUI\user\default\workflows\文生图公益.json`

参数映射：
- 节点 2 (CLIPTextEncode 正向)：正向提示词
- 节点 5 (EmptyLatentImage)：图片宽度和高度
- 节点 8 (SaveImage)：保存生成的图片

## 注意事项

1. 分辨率建议不超过 2048x2048
2. 生图时间取决于显卡性能和分辨率大小
3. 历史记录仅保存在内存中，重启服务后会清空
4. Cloudflare 隧道地址每次启动都会变化（除非配置持久隧道）

## 并发支持

- 内网穿透使用 Cloudflare 的免费隧道，支持约 20 人同时访问
- 如需更高并发，可考虑配置 Cloudflare Access 或使用付费方案
