"""Build script for creating DeepFunGen source-based release package."""
import shutil
import sys
from pathlib import Path

# 配置
RELEASE_NAME = "DeepFunGen-v1.3.0"
SOURCE_DIR = Path(__file__).parent
BUILD_DIR = SOURCE_DIR / "build" / RELEASE_NAME
DIST_DIR = SOURCE_DIR / "dist"

# 需要复制的文件和目录
FILES_TO_COPY = [
    "backend",
    "frontend",
    "models",
    "bin",
    "main.py",
    "run.bat",
    "pyproject.toml",
    "uv.lock",
    "README.md",  # 如果存在
]

# 需要排除的文件和目录
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".gitignore",
    "build",
    "dist",
    ".venv",
    "state",  # 运行时状态，不需要包含
]

def should_exclude(path: Path) -> bool:
    """检查路径是否应该被排除"""
    path_str = str(path)
    path_parts = path.parts
    
    for pattern in EXCLUDE_PATTERNS:
        # 对于目录模式（如 "state"），只匹配目录名，不匹配文件名
        if pattern in ['state', '__pycache__', '.git', '.venv', 'build', 'dist']:
            # 只排除作为目录名的情况
            if pattern in path_parts:
                return True
        # 对于文件模式（如 "*.pyc"），匹配文件名
        elif pattern.startswith('*.'):
            ext = pattern[1:]  # 去掉 "*"
            if path.name.endswith(ext):
                return True
        # 其他情况：精确匹配文件名或路径中包含
        else:
            if path.name == pattern or f"/{pattern}/" in path_str or path_str.endswith(f"/{pattern}"):
                return True
    return False

def copy_tree(src: Path, dst: Path):
    """递归复制目录树，排除不需要的文件"""
    if src.is_file():
        if not should_exclude(src):
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return
    
    if should_exclude(src):
        return
    
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            copy_tree(item, dst / item.name)

# 清理之前的构建
print("Cleaning previous build...")
if BUILD_DIR.exists():
    try:
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        print("Previous build removed.")
    except Exception as e:
        print(f"Warning: Cannot fully remove {BUILD_DIR}: {e}")
        print("Will continue and overwrite existing files...")
if (DIST_DIR / f"{RELEASE_NAME}.zip").exists():
    (DIST_DIR / f"{RELEASE_NAME}.zip").unlink()

# 创建构建目录
BUILD_DIR.mkdir(parents=True, exist_ok=True)
DIST_DIR.mkdir(parents=True, exist_ok=True)

print(f"Building {RELEASE_NAME}...")
print(f"Source: {SOURCE_DIR}")
print(f"Build: {BUILD_DIR}")

# 复制文件
for item in FILES_TO_COPY:
    src = SOURCE_DIR / item
    dst = BUILD_DIR / item
    
    if not src.exists():
        print(f"Warning: {src} not found, skipping...")
        continue
    
    print(f"Copying {item}...")
    if src.is_file():
        shutil.copy2(src, dst)
    else:
        copy_tree(src, dst)

# 创建 README.md（如果不存在）
readme_path = BUILD_DIR / "README.md"
if not readme_path.exists():
    readme_content = """# DeepFunGen v1.3.0

## 新功能

- ✨ **智能参数推荐**：基于视频信号特征自动推荐后处理参数
- 🌐 **多语言支持**：支持中文、韩文、英文界面

## 运行要求

- Python 3.12 或更高版本
- Windows 10/11

## 快速开始

### 方式一：使用 run.bat（推荐）

1. 双击 `run.bat` 即可运行

### 方式二：手动运行

1. 确保已安装 `uv` 包管理器，或使用自带的 `bin\\uv.exe`

2. 同步依赖：
   ```bash
   uv sync
   ```

3. 运行程序：
   ```bash
   uv run main.py
   ```

## 模型文件

请将 ONNX 模型文件放置在 `models/` 目录下。

## 使用智能推荐功能

1. 打开应用
2. 在"添加文件"页面，暂存视频文件并选择模型
3. 点击"智能推荐"按钮
4. 系统会分析视频信号并推荐参数
5. 查看每个参数旁的推荐值，点击"应用"使用推荐值

## 更新日志

### v1.3.0
- 新增智能参数推荐功能
- 新增多语言支持（中文/韩文/英文）
- 优化信号分析和参数推荐算法
"""
    readme_path.write_text(readme_content, encoding='utf-8')
    print("Created README.md")

print("\nBuild complete!")
print(f"Output directory: {BUILD_DIR}")
print(f"\nTo create zip file:")
print(f"  cd {BUILD_DIR.parent}")
print(f"  Compress-Archive -Path {RELEASE_NAME} -DestinationPath {DIST_DIR / f'{RELEASE_NAME}.zip'}")

