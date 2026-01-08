# 🚀 Auto Paper Digest (APD)

<p align="center">
  <strong>自动获取 AI 前沿论文 → 下载 PDF → 生成视频讲解 → 发布到 HuggingFace → 门户网站展示</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/NotebookLM-Automation-orange.svg" alt="NotebookLM">
  <img src="https://img.shields.io/badge/HuggingFace-Spaces-yellow.svg" alt="HuggingFace">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 📚 **论文获取** | 自动抓取 Hugging Face 每周热门 AI 论文（支持周 URL） |
| 📄 **PDF 下载** | 从 arXiv 下载论文 PDF（幂等操作，SHA256 校验） |
| 🎬 **视频生成** | 通过 NotebookLM 自动生成论文视频讲解 |
| � **自动发布** | 上传视频到 HuggingFace Dataset |
| 🌐 **门户网站** | Gradio 门户网站，在线播放视频 |
| 💾 **断点续传** | SQLite 状态追踪，支持中断后继续 |
| 🔐 **登录复用** | Google 登录状态持久化，一次登录长期使用 |

---

## 📐 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Auto Paper Digest                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Phase 1: Upload            Phase 2: Download      Phase 3: Publish │
│   ┌─────────┐    ┌─────────┐    ┌─────────────┐    ┌──────────────┐ │
│   │   HF    │───▶│  arXiv  │───▶│ NotebookLM  │───▶│  HuggingFace │ │
│   │ Papers  │    │  PDFs   │    │   Videos    │    │   Dataset    │ │
│   └─────────┘    └─────────┘    └─────────────┘    └──────────────┘ │
│        │               │               │                   │         │
│        ▼               ▼               ▼                   ▼         │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    SQLite Database                           │   │
│   │      (status: NEW → PDF_OK → NBLM_OK → VIDEO_OK)            │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                    │                                 │
│                                    ▼                                 │
│                        ┌─────────────────────┐                       │
│                        │   Portal Website    │                       │
│                        │   (HF Spaces)       │                       │
│                        └─────────────────────┘                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/brianxiadong/auto-paper-digest.git
cd auto-paper-digest

# 安装依赖
pip install -e .

# 安装浏览器
playwright install chromium
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 填入 HuggingFace 配置
# HF_TOKEN=hf_xxx
# HF_USERNAME=your-username
# HF_DATASET_NAME=paper-digest-videos
```

### 3. 首次登录 Google

```bash
apd login
```

> 浏览器会打开 NotebookLM 登录页面，完成 Google 登录后，会话将被保存。

---

## 📖 三阶段工作流

### Phase 1: 上传并触发视频生成

```bash
apd upload --week 2026-01 --headful --max 10
```

该命令会：
- ✅ 获取 HuggingFace 本周论文（使用 `/week/YYYY-WXX` URL）
- ✅ 下载 arXiv PDF（支持缓存，已下载的跳过）
- ✅ 上传到 NotebookLM
- ✅ 触发视频生成（不等待完成）

### Phase 2: 下载生成的视频

等待几分钟后（视频生成需要时间），运行：

```bash
apd download-video --week 2026-01 --headful
```

支持缓存！已下载的视频会自动跳过，使用 `--force` 强制重新下载。

### Phase 3: 发布到 HuggingFace

```bash
apd publish --week 2026-01
```

该命令会：
- ✅ 上传视频到 HuggingFace Dataset
- ✅ 更新 metadata.json
- ✅ 生成 Markdown 摘要

### 🌐 门户网站

视频发布后，可在 HuggingFace Spaces 门户网站直接观看：

```
https://huggingface.co/spaces/your-username/paper-digest
```

---

## 📖 命令大全

| 命令 | 说明 |
|------|------|
| `apd login` | 打开浏览器完成 Google 登录 |
| `apd fetch` | 仅获取论文列表（不下载） |
| `apd download` | 仅下载 PDF（支持缓存） |
| `apd upload` | **Phase 1**：获取 + 下载 + 上传 + 触发生成 |
| `apd download-video` | **Phase 2**：下载已生成的视频（支持缓存） |
| `apd publish` | **Phase 3**：发布到 HuggingFace |
| `apd digest` | 生成本地周报 |
| `apd run` | 完整流程（一键执行，需等待视频生成） |
| `apd status` | 查看论文处理状态 |

### 常用参数

```bash
--week, -w     指定周 ID（如 2026-01），默认当前周
--max, -m      最大论文数量
--headful      显示浏览器窗口（调试时使用）
--force, -f    强制重新处理（忽略缓存）
--debug        开启调试日志
```

---

## 📁 目录结构

```
auto-paper-digest/
├── apd/                    # 主程序包
│   ├── cli.py              # 命令行入口
│   ├── config.py           # 配置常量
│   ├── db.py               # SQLite 数据库
│   ├── hf_fetcher.py       # HF 论文抓取（支持周 URL）
│   ├── pdf_downloader.py   # PDF 下载器
│   ├── nblm_bot.py         # NotebookLM 自动化
│   ├── publisher.py        # HuggingFace 发布
│   ├── digest.py           # 周报生成
│   └── utils.py            # 工具函数
├── portal/                 # HuggingFace Spaces 门户
│   ├── app.py              # Gradio 应用
│   ├── requirements.txt
│   └── README.md
├── data/
│   ├── apd.db              # SQLite 数据库
│   ├── pdfs/               # 下载的 PDF（按周分目录）
│   ├── videos/             # 生成的视频（按周分目录）
│   ├── digests/            # 周报文件
│   └── profiles/           # 浏览器配置（含登录态）
├── .env.example            # 环境变量模板
└── pyproject.toml
```

---

## � 缓存机制

### PDF 缓存
- 已下载的 PDF 通过 SHA256 校验
- 相同文件自动跳过

### 视频缓存
- 使用文件名前缀匹配（`{paper_id}_*.mp4`）
- 支持新的命名格式：`{paper_id}_{video_title}.mp4`
- 使用 `--force` 强制重新下载

### 发布缓存
- metadata.json 中记录已发布的论文
- 重复发布自动跳过

---

## 📊 状态追踪

```
NEW → PDF_OK → NBLM_OK → VIDEO_OK
 │                          │
 └──────── ERROR ◄──────────┘
```

| 状态 | 含义 |
|------|------|
| `NEW` | 论文已抓取，待处理 |
| `PDF_OK` | PDF 已下载 |
| `NBLM_OK` | 已上传到 NotebookLM，视频生成中 |
| `VIDEO_OK` | 视频已下载 |
| `ERROR` | 处理失败（会自动重试） |

查看状态：

```bash
apd status --week 2026-01
apd status --week 2026-01 --status ERROR
```

---

## 🔧 故障排除

### 登录问题

```bash
apd login
```

### NotebookLM 界面变化

查看截图：

```bash
ls data/profiles/screenshots/
```

### 视频未生成

视频生成需要几分钟时间，请稍后重试：

```bash
apd download-video --week 2026-01 --headful
```

### HuggingFace Token 问题

确保 `.env` 文件配置正确：

```bash
cat .env
# 检查 HF_TOKEN 和 HF_USERNAME
```

---

## 🤝 技术栈

- **Python 3.11+** - 核心语言
- **Playwright** - 浏览器自动化
- **SQLite** - 状态持久化
- **Click** - CLI 框架
- **Requests + BeautifulSoup** - 网页抓取
- **huggingface_hub** - HF API
- **Gradio** - 门户网站
- **python-dotenv** - 环境变量管理

---

## 📄 License

MIT License © 2026
