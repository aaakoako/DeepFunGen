# DeepFunGen 发布流程说明

## 仓库文件 vs Release 文件的区别

### 仓库文件（Repository）
- **源代码**：包含所有 `.py`、`.js`、`.html`、`.css` 等源文件
- **配置文件**：`pyproject.toml`、`uv.lock` 等
- **开发依赖**：需要用户安装 Python、uv 等工具
- **运行方式**：通过 `run.bat` 或 `uv run main.py` 运行

### Release 文件（发布包）
- **可执行文件**：打包成 `.exe` 文件，用户无需安装 Python
- **包含依赖**：所有依赖库都已打包进去
- **便携版**：通常是一个文件夹，包含所有必要的文件
- **模型文件**：需要包含 `models/` 目录中的 ONNX 模型
- **资源文件**：前端静态文件、图标等

## 发布流程

### 1. 准备工作

确保所有改动已提交：
```bash
git status
git add .
git commit -m "你的提交信息"
git push
```

### 2. 使用 PyInstaller 打包（推荐）

#### 安装 PyInstaller
```bash
uv add --dev pyinstaller
```

#### 创建打包脚本 `build_release.py`
```python
import PyInstaller.__main__
import shutil
from pathlib import Path

# 清理之前的构建
for dir_name in ['build', 'dist']:
    if Path(dir_name).exists():
        shutil.rmtree(dir_name)

# PyInstaller 配置
PyInstaller.__main__.run([
    'main.py',
    '--name=DeepFunGen',
    '--windowed',  # 无控制台窗口
    '--onefile',  # 单文件模式（或使用 --onedir 创建文件夹）
    '--icon=frontend/icon.png',  # 如果有图标
    '--add-data=frontend;frontend',  # 包含前端文件
    '--add-data=models;models',  # 包含模型文件
    '--hidden-import=webview',
    '--hidden-import=uvicorn',
    '--hidden-import=fastapi',
    '--hidden-import=onnxruntime',
    '--collect-all=webview',
    '--collect-all=uvicorn',
    '--collect-all=fastapi',
    '--noconfirm',
    '--clean',
])
```

#### 或者使用 `--onedir` 模式（推荐，更稳定）
```python
PyInstaller.__main__.run([
    'main.py',
    '--name=DeepFunGen',
    '--windowed',
    '--onedir',  # 文件夹模式
    '--icon=frontend/icon.png',
    '--add-data=frontend;frontend',
    '--add-data=models;models',
    '--hidden-import=webview',
    '--collect-all=webview',
    '--noconfirm',
    '--clean',
])
```

#### 执行打包
```bash
cd DeepFunGen.py
python build_release.py
```

打包后的文件会在 `dist/DeepFunGen/` 目录中。

### 3. 创建发布包结构

```
DeepFunGen-v1.2.0/
├── DeepFunGen.exe          # 主程序（onedir模式）
├── _internal/              # 依赖库（onedir模式）
├── models/                 # ONNX 模型文件
│   ├── conv_tcn_56.onnx
│   └── ...
└── README.txt             # 使用说明
```

### 4. 创建 GitHub Release

#### 步骤 1：创建标签
```bash
git tag -a v1.2.0 -m "Release version 1.2.0 with Chinese localization"
git push origin v1.2.0
```

#### 步骤 2：在 GitHub 上创建 Release
1. 进入仓库页面
2. 点击 "Releases" → "Draft a new release"
3. 选择标签 `v1.2.0`
4. 填写发布标题和说明
5. 上传打包好的文件（可以压缩成 zip）

### 5. 发布说明模板

```markdown
## DeepFunGen v1.2.0

### 新功能
- ✨ 添加中文界面支持
- 🌐 支持多语言切换（英语、韩语、中文）

### 改进
- 优化了界面文本的国际化处理
- 修复了部分硬编码文本问题

### 使用方法
1. 下载 `DeepFunGen-v1.2.0.zip`
2. 解压到任意目录
3. 运行 `DeepFunGen.exe`
4. 在设置中选择语言

### 系统要求
- Windows 10/11
- DirectX 12 兼容的 GPU（可选，用于硬件加速）
```

## 打包注意事项

### 1. 模型文件
确保 `models/` 目录中的 ONNX 模型文件被正确包含。

### 2. 前端资源
确保所有前端文件（HTML、CSS、JS）都被包含。

### 3. 依赖库
PyInstaller 会自动检测大部分依赖，但某些动态导入的模块可能需要手动指定：
- `--hidden-import=模块名`
- `--collect-all=包名`（收集所有子模块）

### 4. 测试
打包后务必在干净的 Windows 系统上测试，确保：
- 程序能正常启动
- 所有功能正常工作
- 模型文件能正确加载
- 界面显示正常

### 5. 文件大小
- 单文件模式（`--onefile`）：文件较大，启动稍慢
- 文件夹模式（`--onedir`）：文件分散，启动较快，推荐使用

## 自动化发布（可选）

可以使用 GitHub Actions 自动化打包和发布流程，创建 `.github/workflows/release.yml`：

```yaml
name: Build Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Install PyInstaller
        run: uv add --dev pyinstaller
      - name: Build
        run: python build_release.py
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: DeepFunGen-release
          path: dist/
```

## 总结

- **仓库**：源代码，供开发者使用
- **Release**：打包好的可执行文件，供最终用户使用
- **主要区别**：Release 包含所有依赖，用户无需安装 Python 环境即可运行

