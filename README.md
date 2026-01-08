# 🚀 Auto Paper Digest (APD)

<p align="center">
  <strong>自动获取 AI 前沿论文 → 下载 PDF → 生成视频讲解 → 周报汇总</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/NotebookLM-Automation-orange.svg" alt="NotebookLM">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 📚 **论文获取** | 自动抓取 Hugging Face 每周热门 AI 论文 |
| 📄 **PDF 下载** | 从 arXiv 下载论文 PDF（幂等操作，SHA256 校验） |
| 🎬 **视频生成** | 通过 NotebookLM 自动生成论文视频讲解 |
| 📝 **周报生成** | 输出 Markdown 和 JSON 格式的周报 |
| 💾 **断点续传** | SQLite 状态追踪，支持中断后继续 |
| 🔐 **登录复用** | Google 登录状态持久化，一次登录长期使用 |

---

## 📐 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        Auto Paper Digest                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │   HF    │───▶│   arXiv     │───▶│ NotebookLM  │            │
│   │ Papers  │    │   PDFs      │    │   Videos    │            │
│   └─────────┘    └─────────────┘    └─────────────┘            │
│        │               │                  │                     │
│        ▼               ▼                  ▼                     │
│   ┌─────────────────────────────────────────────────┐          │
│   │              SQLite Database                     │          │
│   │   (status: NEW → PDF_OK → NBLM_OK → VIDEO_OK)   │          │
│   └─────────────────────────────────────────────────┘          │
│                          │                                      │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │   Weekly    │                               │
│                   │   Digest    │                               │
│                   └─────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 📦 模块说明

| 模块 | 文件 | 职责 |
|------|------|------|
| **CLI** | `cli.py` | 命令行接口，所有用户交互入口 |
| **Fetcher** | `hf_fetcher.py` | 抓取 Hugging Face Papers 页面 |
| **Downloader** | `pdf_downloader.py` | 下载 arXiv PDF，SHA256 校验 |
| **Bot** | `nblm_bot.py` | Playwright 自动化 NotebookLM |
| **Digest** | `digest.py` | 生成 Markdown/JSON 周报 |
| **Database** | `db.py` | SQLite 状态追踪 |

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

### 2. 首次登录 Google

```bash
apd login
```

> 浏览器会打开 NotebookLM 登录页面，完成 Google 登录后，会话将被保存。

### 3. 两阶段工作流（推荐）

为避免视频生成超时，推荐使用两阶段工作流：

#### 阶段一：上传并触发生成

```bash
apd upload --week 2026-01 --headful --max 10
```

该命令会：
1. ✅ 获取 Hugging Face 本周论文
2. ✅ 下载 arXiv PDF
3. ✅ 上传到 NotebookLM
4. ✅ 触发视频生成（不等待完成）

#### 阶段二：下载生成的视频

等待几分钟后（视频生成需要时间），运行：

```bash
apd download-video --week 2026-01 --headful
```

#### 阶段三：生成周报

```bash
apd digest --week 2026-01
```

---

## 📖 命令大全

| 命令 | 说明 |
|------|------|
| `apd login` | 打开浏览器完成 Google 登录 |
| `apd fetch` | 仅获取论文列表（不下载） |
| `apd download` | 仅下载 PDF |
| `apd upload` | **阶段一**：获取 + 下载 + 上传 + 触发生成 |
| `apd download-video` | **阶段二**：下载已生成的视频 |
| `apd digest` | 生成周报 |
| `apd run` | 完整流程（一键执行，需等待视频生成） |
| `apd status` | 查看论文处理状态 |

### 常用参数

```bash
--week, -w     指定周 ID（如 2026-01），默认当前周
--max, -m      最大论文数量
--headful      显示浏览器窗口（调试时使用）
--force, -f    强制重新处理
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
│   ├── hf_fetcher.py       # HF 论文抓取
│   ├── pdf_downloader.py   # PDF 下载器
│   ├── nblm_bot.py         # NotebookLM 自动化
│   ├── digest.py           # 周报生成
│   └── utils.py            # 工具函数
├── data/
│   ├── apd.db              # SQLite 数据库
│   ├── pdfs/               # 下载的 PDF（按周分目录）
│   │   └── 2026-01/
│   ├── videos/             # 生成的视频（按周分目录）
│   │   └── 2026-01/
│   ├── digests/            # 周报文件
│   │   └── 2026-01.md
│   └── profiles/           # 浏览器配置（含登录态）
└── pyproject.toml
```

---

## 📊 状态追踪

论文在数据库中的状态流转：

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
# 重新登录
apd login
```

在浏览器中完成登录后，等待 "Login successful!" 提示。

### NotebookLM 界面变化

如果自动化失败，查看截图：

```bash
ls data/profiles/screenshots/
```

### 视频未生成

视频生成需要几分钟时间。如果 `download-video` 失败，请稍后重试：

```bash
# 等待后重试
apd download-video --week 2026-01 --headful
```

---

## 🤝 技术栈

- **Python 3.11+** - 核心语言
- **Playwright** - 浏览器自动化
- **SQLite** - 状态持久化
- **Click** - CLI 框架
- **Requests + BeautifulSoup** - 网页抓取

---

## 📄 License

MIT License © 2026
