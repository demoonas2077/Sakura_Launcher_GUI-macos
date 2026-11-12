import sys
import os


def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        return os.path.join(os.path.abspath("."), relative_path)


def get_self_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        # 当前文件的绝对路径的上一级目录
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CURRENT_DIR = get_self_path()
ICON_FILE = "icon.ico"
GHPROXY_URL = "ghfast.top"
SAKURA_LAUNCHER_GUI_VERSION = "v1.2.0-beta-patched"
DEBUG_BUILD = False


def get_data_dir():
    """用户数据目录：macOS 放 Application Support，其它平台仍留在程序目录。"""
    if sys.platform == "darwin":
        base_dir = os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "SakuraLauncher"
        )
    else:
        base_dir = CURRENT_DIR
    try:
        os.makedirs(base_dir, exist_ok=True)
    except OSError:
        base_dir = CURRENT_DIR
    return base_dir


def get_log_dir():
    """日志目录：macOS 放 ~/Library/Logs，其它平台放数据目录下的 logs。"""
    if sys.platform == "darwin":
        base_dir = os.path.join(
            os.path.expanduser("~"), "Library", "Logs", "SakuraLauncher"
        )
    else:
        base_dir = os.path.join(get_data_dir(), "logs")
    try:
        os.makedirs(base_dir, exist_ok=True)
    except OSError:
        base_dir = get_data_dir()
    return base_dir


DATA_DIR = get_data_dir()
LLAMA_DIR = os.path.join(DATA_DIR, "llama")
MODELS_DIR = os.path.join(DATA_DIR, "models")
LOG_DIR = get_log_dir()


def get_llama_dir():
    """llama.cpp 所在目录，兼容旧版放在程序目录下的情况。"""
    if os.path.isdir(LLAMA_DIR):
        return LLAMA_DIR
    legacy_dir = os.path.join(CURRENT_DIR, "llama")
    if os.path.isdir(legacy_dir):
        return legacy_dir
    return LLAMA_DIR


# 本地补丁构建：版本号保持与上游一致，不自行递增
PATCHED_BUILD = True
# 禁用上游更新检查，避免把补丁覆盖成原版
DISABLE_LAUNCHER_UPDATE = PATCHED_BUILD

processes = []
