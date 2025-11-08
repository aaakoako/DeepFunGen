"""Build script for creating DeepFunGen source-based release package."""
import shutil
from pathlib import Path

# 配置
RELEASE_NAME = "DeepFunGen-v1.2.0"
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
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str or path.name == pattern:
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
    shutil.rmtree(BUILD_DIR)
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

print("\nBuild complete!")
print(f"Output directory: {BUILD_DIR}")
print(f"\nTo create zip file:")
print(f"  cd {BUILD_DIR.parent}")
print(f"  Compress-Archive -Path {RELEASE_NAME} -DestinationPath {DIST_DIR / f'{RELEASE_NAME}.zip'}")

