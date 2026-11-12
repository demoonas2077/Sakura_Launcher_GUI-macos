

# Sakura Launcher GUI

> ## 🍎 macOS 适配分支（v1.2.0-beta-patched）
>
> 本仓库是上游 [PiDanShouRouZhouXD/Sakura_Launcher_GUI](https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI)
> `v1.2.0-beta` 的 **macOS 适配分支**，只改代码、不碰模型与协议。分支名 `macos-patched`。
>
> ### 改了什么
>
> **窗口与系统集成**
> - 使用 macOS 原生标题栏（红黄绿在左上角，标题进系统标题栏），双击标题栏即可缩放
> - 修复原生标题栏切换后窗口无法拖动的问题
> - 退出时等待后台线程结束，修复退出瞬间的 `SIGABRT`（`QThread: Destroyed while thread is still running`）
>
> **数据目录外置（不再写进 `.app`）**
>
> | 内容 | 路径 |
> |---|---|
> | 配置 | `~/Library/Application Support/SakuraLauncher/sakura-launcher_config.json` |
> | llama.cpp | `~/Library/Application Support/SakuraLauncher/llama/` |
> | 下载的模型 | `~/Library/Application Support/SakuraLauncher/models/` |
> | 日志 | `~/Library/Logs/SakuraLauncher/launcher.log` |
>
> 好处：App 包内只有程序本体（约 91 MB），`codesign -v` 干净、升级不丢数据。
>
> **模型管理**
> - 支持直接引用 Ollama 模型仓库：`Ollama` 的 `blobs` 目录下没有 `.gguf` 扩展名的文件，
>   现在按 `GGUF` 文件头识别，无需复制或改名
> - 模型下拉框改为只读下拉框，修复长模型名与下拉箭头重叠、清空按钮挤压的问题
> - 名称过长时中间省略（如 `sakura-14b-…-v1.0-iq4xs.gguf`），悬停显示全名
> - 按 `sha256` 匹配内置模型配置，不再依赖文件名
>
> **功能修复**
> - 性能测试按 `(npp + ntg) * max(npl)` 自动抬升上下文，修复 `find_slot` / `llama_decode() failed`
> - Apple Silicon 上按统一内存的 75% 自动推荐并发数与上下文
> - 设置页加滚动区，窗口较矮时不再裁掉底部选项；新增目录浏览按钮
> - 禁用上游自动更新（`-patched` 构建），避免升级时覆盖本地补丁
> - `CFBundleShortVersionString` 由 `0.0.0` 修正为 `1.2.0`（补丁不抬版本号，保持与上游 `v1.2.0-beta` 同代，避免被当成新版本）
>
> ### 从源码构建
>
> ```bash
> uv venv --python 3.12
> uv pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
>   PySide6-Essentials==6.9.1 shiboken6==6.9.1 darkdetect \
>   PySide6-Fluent-Widgets --no-deps PySideSix-Frameless-Window \
>   aiohttp requests pyinstaller pillow
> .venv/bin/pyinstaller main.spec --noconfirm
> ```
>
> 产物在 `dist/SakuraLauncher.app`。首次运行前建议：
>
> ```bash
> xattr -cr dist/SakuraLauncher.app
> codesign --force --deep --sign - dist/SakuraLauncher.app
> ```
>
> （未做 Apple 公证，从网络下载的包需要「右键 → 打开」或在系统设置里放行。）
>
> ### 协议
>
> 与上游一致，遵循 **GPLv3**。SakuraLLM 模型为 **CC-BY-NC-SA 4.0**，禁止商用。

<!-- PROJECT LOGO -->
<br />

<p align="center">
  <a href="https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI/">
    <img src="icon.ico" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Sakura Launcher GUI</h3>
  <p align="center">
    一个简单的Sakura启动器
    <br />
    <a href="https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI/issues">报告Bug</a>
    ·
    <a href="https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI/issues">提出新特性</a>
    ·
    <a href="https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI/pulls">贡献代码</a>
  </p>

</p>

 本篇README.md主要面向开发者，如需使用指南，请查看[用户手册](https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI/blob/main/Sakura%20Launcher%20GUI%20%E7%94%A8%E6%88%B7%E6%89%8B%E5%86%8C.md)。

## 目录

- [Sakura Launcher GUI](#sakura-launcher-gui)
  - [目录](#目录)
    - [**界面预览**](#界面预览)
    - [**安装步骤**](#安装步骤)
    - [**代码结构**](#代码结构)
    - [**打包**](#打包)
    - [**注意事项**](#注意事项)
    - [**基于项目**](#基于项目)


### **界面预览**

<div align=center><img src="assets\PixPin_2024-11-13_02-15-00.png" width="540px"></div>

### **安装步骤**

1. Clone 仓库并进入仓库目录

```sh
git clone https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI.git
cd Sakura_Launcher_GUI
```

2. 安装依赖

```sh
pip install -r requirements.txt
```

3. 运行

```sh
python main.py
```

### **代码结构**

```python
main.py                     # 主程序入口,初始化窗口和导航界面

src/:
├── common.py              # 通用工具函数,包含路径处理和版本信息
├── gpu.py                 # GPU管理器实现,负责检测和管理显卡资源
├── llamacpp.py           # llama.cpp管理,包含版本检测和下载功能
├── sakura.py             # Sakura模型类定义,处理模型信息和配置
├── sakura_share_api.py   # Sakura共享功能的API实现
├── sakura_share_cli.py   # Sakura共享功能的命令行工具
├── setting.py            # 程序设置管理,处理配置的保存和加载
├── ui.py                 # 通用UI组件和界面工具函数

页面实现:
├── section_about.py      # "关于"页面,显示版本信息和项目链接
├── section_download.py   # "下载"页面,管理模型和llama.cpp下载
├── section_run_server.py # "启动"页面,处理服务启动和性能测试
├── section_settings.py   # "设置"页面,提供程序配置界面
├── section_share.py      # "共享"页面,实现模型共享功能

工具类(src/utils/):
├── gpu/
│   ├── __init__.py       # GPU相关数据结构定义
│   └── nvidia.py         # NVIDIA GPU 已占用显存获取
├── model_size_cauculator.py  # 模型大小计算器
├── windows.py            # Windows下初始化GPU的工具
└── __init__.py
```

### **打包**

```sh
pyinstaller --clean --noconfirm main.spec
```

### **注意事项**

- 请确保已安装 Python 3.x 环境（推荐3.12）
- 建议使用包管理器安装依赖，如 [miniforge](https://github.com/conda-forge/miniforge)

### **基于项目**

- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [SakuraLLM](https://github.com/SakuraLLM/SakuraLLM)
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
