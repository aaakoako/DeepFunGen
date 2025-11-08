# DeepFunGen Quick Start

**DeepFunGen** is a Windows-based Python application that uses ONNX-format inference models to enqueue videos for background inference and post-processing.  
Follow the steps below to quickly set it up, run it, and view your results.

## Requirements
- Windows 10 or 11  
- [uv](https://github.com/astral-sh/uv)  
- One or more ONNX models inside the `models/` folder (the default model `conv_tcn_56.onnx` is included)

## How to Run
1. Run `run.bat`.  
   This will automatically install dependencies via **uv** and start the application.
2. **Add Files Screen**
   - By default, the model `models/conv_tcn_56.onnx` is selected at startup.  
     To switch to another model, choose a different ONNX file from the dropdown menu on the right.
   - Drag and drop your video files (e.g., `.mp4`) or click **Browse Files** to add them.
   - Adjust the options as needed, then click **Add to Queue** to enqueue the video for processing.
3. **Queue Screen**
   - Monitor processing progress here.
   - When inference is complete, prediction results are saved as `<video_name>.<model_name>.csv`, and a `<video_name>.funscript` file is generated in the same folder.
   - If you re-add a previously processed video, the saved CSV file will be reused to save reprocessing time.
   - Select an item in the queue and click **Open Viewer** to launch the Viewer and visualize the step-by-step graphs.

## Model Management & Acceleration
- Any ONNX models placed in the `models/` folder will automatically appear in the dropdown list.
- If your GPU supports **DirectML (DirectX 12)**, hardware acceleration will be enabled automatically; otherwise, the app will fall back to CPU execution.  
  You can check the current execution provider in the **Provider** section at the bottom.

---

_DeepFunGen aims to make ONNX-based functional signal generation and inference pipelines simple, efficient, and easy to visualize._


# DeepFunGen Quick Start

DeepFunGen은 ONNX 포맷의 간섭도 예측 모델을 사용해 비디오를 큐에 넣고 백그라운드로 추론 및 후처리를 수행하는 Windows용 python 앱입니다. 아래 단계만 따라 하면 바로 실행하고 결과를 확인할 수 있습니다.

## 준비물
- Windows 10/11
- uv (https://github.com/astral-sh/uv)
- `models/` 폴더에 추론에 사용할 ONNX 모델 여러 개(기본 `conv_tcn_56.onnx` 포함)

## 실행 방법
1. `run.bat`를 실행하면 uv가 종속성을 설치하고 프로그램이 시작됩니다
2. Add Files 화면
   - 시작시 기본 모델(`models/conv_tcn_56.onnx`)이 선택됩니다. 모델을 바꾸고 싶다면 우측 드롭다운에서 다른 ONNX 파일을 선택하세요.
   - 영상 파일(`.mp4` 등)을 드래그 앤 드랍하거나 `Browse Files` 버튼을 눌러 동영상을 추가할 수 있습니다.
   - 옵션을 조절한 다음 Add to queue 버튼을 대기열에 추가 할 수 있습니다.
3. Queue 화면
   - 처리 진행 상황을 확인할 수 있습니다.
   - 추론이 끝나면 `<영상이름>.<모델이름>.csv` 로 예측 결과가 저장되고, 같은 폴더에 `<영상이름>.funscript` 파일이 생성됩니다.
   - 이미 예측된 영상을 다시 추가하면 저장된 csv를 불러와 재처리 시간을 절약합니다.
   - 큐에서 항목을 선택 후 `Open Viewer`를 누르면 Viewer가 열려 단계별 그래프를 확인할 수 있습니다.

## 모델 교체 & 가속
- ONNX 모델은 `models/` 폴더에 넣으면 자동으로 드롭다운에 표시됩니다.
- GPU가 DirectML(DirectX 12)를 지원하면 자동으로 가속을 사용하며, 지원하지 않을 경우 CPU로 폴백됩니다. 하단의 Provider에서 현재 사용 중인 실행 프로바이더를 확인할 수 있습니다.

---

# DeepFunGen 快速开始

**DeepFunGen** 是一个基于 Windows 的 Python 应用程序，使用 ONNX 格式的推理模型对视频进行后台推理和后处理。  
按照以下步骤快速设置、运行并查看结果。

## 系统要求
- Windows 10 或 11
- [uv](https://github.com/astral-sh/uv)
- `models/` 文件夹中有一个或多个 ONNX 模型（默认包含 `conv_tcn_56.onnx`）

## 运行方法
1. 运行 `run.bat`。  
   这将通过 **uv** 自动安装依赖并启动应用程序。
2. **添加文件界面**
   - 默认情况下，启动时会选择模型 `models/conv_tcn_56.onnx`。  
     要切换到其他模型，请从右侧下拉菜单中选择不同的 ONNX 文件。
   - 拖放视频文件（如 `.mp4`）或点击 **浏览文件** 来添加它们。
   - 根据需要调整选项，然后点击 **加入队列** 将视频加入处理队列。
3. **队列界面**
   - 在此处监控处理进度。
   - 推理完成后，预测结果将保存为 `<视频名称>.<模型名称>.csv`，并在同一文件夹中生成 `<视频名称>.funscript` 文件。
   - 如果重新添加之前处理过的视频，将重用保存的 CSV 文件以节省重新处理时间。
   - 在队列中选择一个项目，然后点击 **打开查看器** 启动查看器并可视化分步图表。

## 模型管理与加速
- 放置在 `models/` 文件夹中的任何 ONNX 模型都会自动出现在下拉列表中。
- 如果您的 GPU 支持 **DirectML (DirectX 12)**，将自动启用硬件加速；否则，应用程序将回退到 CPU 执行。  
  您可以在底部的 **Provider** 部分查看当前使用的执行引擎。

## 主要特点

### 🌐 多语言支持
- **中文界面**：完整的中文界面支持，操作更便捷
- **多语言切换**：支持英语、韩语、中文三种语言，可在设置中自由切换
- **国际化设计**：所有界面文本均支持多语言

### 🚀 高性能处理
- **GPU 加速**：自动检测并使用 DirectML (DirectX 12) 进行硬件加速
- **后台处理**：支持队列管理，可批量处理多个视频
- **智能缓存**：自动重用已处理的结果，节省重复处理时间

### 📊 可视化分析
- **实时进度**：队列界面实时显示处理状态和进度
- **结果查看器**：可视化预测结果的分步图表
- **详细统计**：显示预处理、推理、预计时间等详细信息

### 🎯 灵活配置
- **多模型支持**：轻松切换不同的 ONNX 模型
- **处理选项**：可配置平滑窗口、峰值检测、FFT 降噪等参数
- **VR 模型**：支持 VR 专用模型的筛选和选择

---

_DeepFunGen 旨在使基于 ONNX 的功能信号生成和推理管道变得简单、高效且易于可视化。_