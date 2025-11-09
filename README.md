# Face Recognition & Object Detection Server

## Overview

This is a comprehensive Face Recognition and Object Detection server built with Python that provides real-time monitoring capabilities for client authentication and security enforcement. The server uses computer vision and machine learning models to detect faces, recognize users, identify phones, and prevent spoofing attacks.

## 🏗️ Architecture

The server follows a multi-process architecture with the following main components:

### Core Components

1. **Server**: WebSocket server handling client connections
2. **Pipeline Manager**: Manages multiple processing pipelines for scalability
3. **Pipeline**: Individual processing units for face recognition and phone detection
4. **Models Manager**: Handles AI model initialization and inference
5. **Action Decision Manager**: Determines appropriate actions based on detection results
6. **Server Manager**: Manages client files and server data

## 📁 Project Structure

```
├── main.py                     # Application entry point
├── Scripts/                    # Core application modules
│   ├── Server.py              # WebSocket server implementation
│   ├── PipeLinesManager.py    # Pipeline management system
│   ├── PipeLine.py            # Individual pipeline processing
│   ├── ModelsManager.py       # AI model management
│   ├── ActionDecisionManager.py # Decision making logic
│   ├── Server_Manager.py      # Server data management
│   └── Save_Action_thread.py  # Action logging thread
├── Models_Weights/            # AI model weights
├── Data/                      # Application data
│   ├── Users_DataBase/        # User database
│   ├── Actions/               # Action logs
│   └── Server_Data/           # Server configuration
├── docker/                    # Docker configuration
├── docs/                      # Documentation
└── utilities/                 # Utility modules
```

## 🔧 Installation

### Prerequisites

- Python 3.10+
- CUDA-compatible GPU (recommended)
- Redis server
- Docker (optional)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configuration

1. Set up Redis server
2. Configure model paths in `main.py`
3. Set environment variables:
   - `MaxClientPerPipeline`: Maximum clients per pipeline (default: 30)
   - `MaxPipeline`: Maximum number of pipelines (default: 5)
   - `NAMESPACE`: System namespace identifier

## 🚀 Usage

### Run the Server

```bash
python main.py
```

### Using Docker

```bash
docker-compose up
```

---

## 📖 Documentation

Detailed documentation for each component can be found in the `docs/` folder:

### System Documentation

- [System Architecture](docs/System_Architecture.md) - Complete system overview and component interactions
- [API Documentation](docs/API_Documentation.md) - WebSocket API reference and client implementation

### Core Components

- [Server Documentation](docs/Server.md) - WebSocket server implementation
- [Pipeline Manager Documentation](docs/PipeLinesManager.md) - Pipeline management system
- [Pipeline Documentation](docs/PipeLine.md) - Individual pipeline processing
- [Models Manager Documentation](docs/ModelsManager.md) - AI model management
- [Action Decision Manager Documentation](docs/ActionDecisionManager.md) - Decision making logic
- [Server Manager Documentation](docs/Server_Manager.md) - Server data management
- [Save Action Thread Documentation](docs/Save_Action_thread.md) - Action logging system

### AI Model Components

- [Object Detection Task](docs/Object_Detection_Task.md) - Phone detection components
  - ObjectDetection.py - Core YOLO-based object detection
  - PhoneDetection.py - Phone-specific detection wrapper
- [Face Recognition Anti-Spoof Task](docs/Face_Recognition_Anti_Spoof_Task.md) - Face recognition components
  - FaceDetectionRecognition.py - Main face authentication pipeline
  - DetectFaces.py - YOLO-based face detection
  - RecognitionFace.py - Face recognition and verification
  - SpoofChecker.py - Anti-spoofing detection
  - FasNet.py - FasNet anti-spoofing model
  - VGGFace.py - VGG-Face model implementation
  - model.py - IResNet model architectures

### Utilities and Support

- [Utilities Documentation](docs/Utilities.md) - Project utilities and support functions
  - files_handler.py - File and directory management utilities
  - Datatypes.py - Enumerations and data structures
  - ClientsData class - Redis-based client data management
# FC-Running-Case
