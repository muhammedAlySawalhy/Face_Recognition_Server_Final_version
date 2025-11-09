# ModelsManager Module Documentation

## Overview

The `ModelsManager.py` module serves as the central hub for managing AI models used in face recognition, phone detection, and anti-spoofing tasks. It provides a unified interface for model initialization, configuration, and inference operations while handling GPU resource management and memory optimization.

**⚠️ CRITICAL REQUIREMENT**: TensorFlow-based models (used for face recognition) in this system require GPU hardware and cannot run on CPU. This is a fundamental constraint that must be considered for deployment.

## Class Diagram

```mermaid
classDiagram
    class ModelsManager {
        +bool __IS_INITIALIZE
        +PhoneDetection __phone_model
        +FaceDetectionRecognition __face_model
        +LOGGER logs
        +__init__(Models_Weights_dir, ObjectDetection_model_weights, FaceDetection_model_weights, FaceRecognition_model_weights, FaceSpoofChecker_model_weights, Object_Detection_Models_device, Face_Detection_Model_device, Face_Recognition_Model_device, spoof_Models_device, Recognition_model_name, Recognition_Threshold, Anti_Spoof_threshold, Recognition_Metric, Object_class_number, Object_threshold, logger)
        +__del__()
        +phone_model_pipeline(client_data) dict
        +face_model_pipeline(client_data) dict
        +models_pipeline(client_data) dict
        +IS_INITIALIZE: bool
    }
  
    class PhoneDetection {
        +str Models_Weights_dir
        +str ObjectDetection_model_weights
        +str torch_Models_device
        +int Object_class_number
        +int Object_threshold
        +pipeline(client_data) dict
    }
  
    class FaceDetectionRecognition {
        +str Models_Weights_dir
        +str Detection_model_weights
        +str Recognition_model_weights
        +str SpoofChecker_model_weights
        +str Detection_Model_device
        +str Recognition_Model_device
        +str Spoof_Model_device
        +str Recognition_model_name
        +float Recognition_Threshold
        +str Recognition_Metric
        +float Anti_Spoof_threshold
        +pipeline(client_data) dict
    }
  
    ModelsManager *-- PhoneDetection : contains
    ModelsManager *-- FaceDetectionRecognition : contains
    ModelsManager --> LOGGER : uses
  
    PhoneDetection --> YOLOv8 : uses
    FaceDetectionRecognition --> YOLOv8 : uses
    FaceDetectionRecognition --> VGGFace : uses
    FaceDetectionRecognition --> AntiSpoofModel : uses
```

## Hardware Requirements

### GPU Requirements

**⚠️ MANDATORY**: This system requires GPU hardware for proper operation. The face recognition models are built using TensorFlow and are configured to run exclusively on GPU devices.

#### Minimum Requirements:

- **GPU**: NVIDIA GPU with CUDA support
- **CUDA Version**: 11.0 or higher
- **GPU Memory**: Minimum 4GB VRAM
- **Driver**: NVIDIA drivers supporting CUDA

#### Recommended Requirements:

- **GPU**: NVIDIA RTX 3060 or higher
- **GPU Memory**: 8GB+ VRAM
- **CUDA Version**: 11.8 or higher
- **Multi-GPU**: Supported for distributed processing

#### CPU-Only Limitation:

- **Face Recognition Models**: Cannot run on CPU due to TensorFlow configuration
- **Phone Detection Models**: Can run on CPU but performance will be significantly degraded
- **Deployment Impact**: System will fail to initialize without GPU support

### Memory Requirements:

- **System RAM**: Minimum 16GB, recommended 48GB+
- **GPU Memory**: Varies by model complexity
- **Storage**: SSD recommended for model loading

## Architecture Overview

The ModelsManager implements a composite pattern where different model types are encapsulated within specialized classes, providing a unified interface for model operations.

## Detailed Component Documentation

For comprehensive documentation of the underlying components, refer to:

- **[Object Detection Task](Object_Detection_Task.md)** - Detailed documentation for phone detection components

  - `ObjectDetection.py` - Core YOLO-based object detection
  - `PhoneDetection.py` - Phone-specific detection wrapper
- **[Face Recognition Anti-Spoof Task](Face_Recognition_Anti_Spoof_Task.md)** - Detailed documentation for face recognition components

  - `FaceDetectionRecognition.py` - Main face authentication pipeline
  - `DetectFaces.py` - YOLO-based face detection
  - `RecognitionFace.py` - Face recognition and verification
  - `SpoofChecker.py` - Anti-spoofing detection
  - `FasNet.py` - FasNet anti-spoofing model
  - `VGGFace.py` - VGG-Face model implementation
  - `model.py` - IResNet model architectures

These documents provide detailed class diagrams, method descriptions, usage examples, and integration guidelines for each component.

## Model Architecture

```mermaid
flowchart TD
    A[Client Image Input] --> B[ModelsManager]
    B --> C[Phone Detection Model]
    B --> D[Face Detection Model]
  
    C --> E[Phone Bounding Box]
    D --> F[Face Bounding Box]
  
    F --> G[Face Recognition Model]
    F --> H[Anti-Spoof Model]
  
    G --> I[Identity Verification]
    H --> J[Spoof Detection]
  
    E --> K[Combined Results]
    I --> K
    J --> K
  
    K --> L[Action Decision]
```

## Core Functionality

### 1. Model Initialization

#### Initialization Flow

```mermaid
flowchart TD
    A[ModelsManager Init] --> B[Configure Parameters]
    B --> C[Initialize Phone Detection]
    B --> D[Initialize Face Detection]
  
    C --> E[Load YOLO Phone Model]
    D --> F[Load YOLO Face Model]
    D --> G[Load Recognition Model]
    D --> H[Load Anti-Spoof Model]
  
    E --> I[Set Device Configuration]
    F --> I
    G --> I
    H --> I
  
    I --> J[Set Initialization Flag]
    J --> K[Ready for Inference]
```

#### Model Configuration

```python
Models_Parameters = {
    # Model Weights
    "Models_Weights_dir": "Models_Weights",
    "ObjectDetection_model_weights": "phone_detection.pt",
    "FaceDetection_model_weights": "yolov8_model.pt",
    "FaceRecognition_model_weights": "arcface_r100.pth",
    "FaceSpoofChecker_model_weights": None,
  
    # Device Configuration
    "Object_Detection_Models_device": "cuda:0",
    "Face_Detection_Model_device": "GPU:0",
    "Face_Recognition_Model_device": "GPU:0",
    "spoof_Models_device": "cuda:0",
  
    # Model Parameters
    "Recognition_model_name": "r100",
    "Recognition_Threshold": 0.25,
    "Anti_Spoof_threshold": 65,
    "Recognition_Metric": "cosine_similarity",
    "Object_class_number": 67,
    "Object_threshold": 65
}
```

### 2. Pipeline Operations

#### Phone Detection Pipeline

```mermaid
flowchart TD
    A[Client Data] --> B[Extract Image]
    B --> C[Phone Detection Model]
    C --> D[Process Detection Results]
    D --> E{Phone Detected?}
    E -->|Yes| F[Extract Bounding Box]
    E -->|No| G[Return No Detection]
    F --> H[Calculate Confidence]
    H --> I[Apply Threshold]
    I --> J[Return Detection Results]
```

#### Face Recognition Pipeline

```mermaid
flowchart TD
    A[Client Data] --> B[Extract Image]
    B --> C[Face Detection Model]
    C --> D{Face Detected?}
    D -->|Yes| E[Extract Face ROI]
    D -->|No| F[Return No Face]
    E --> G[Face Recognition Model]
    E --> H[Anti-Spoof Model]
    G --> I[Calculate Similarity]
    H --> J[Spoof Score]
    I --> K[Apply Recognition Threshold]
    J --> L[Apply Spoof Threshold]
    K --> M[Combine Results]
    L --> M
    M --> N[Return Results]
```

## Key Methods

### Model Pipeline Methods

#### `phone_model_pipeline(client_data) -> dict`

**Purpose**: Processes phone detection for client data

**Input**:

```python
client_data = {
    "user_image": cv2_image,
    "actual_username": "client_name",
    "send_time": "timestamp"
}
```

**Output**:

```python
{
    "phone_bbox": [x1, y1, x2, y2] or None,
    "phone_confidence": float,
    "phone_detected": bool
}
```

#### `face_model_pipeline(client_data) -> dict`

**Purpose**: Processes face recognition and anti-spoofing

**Input**:

```python
client_data = {
    "user_image": cv2_image,
    "actual_username": "client_name",
    "ref_image": reference_image,
    "send_time": "timestamp"
}
```

**Output**:

```python
{
    "face_bbox": [x1, y1, x2, y2] or None,
    "face_confidence": float,
    "recognition_score": float,
    "spoof_score": float,
    "check_client": bool,
    "check_spoof": bool
}
```

#### `models_pipeline(client_data) -> dict`

**Purpose**: Combined processing for all models

**Processing Flow**:

```mermaid
flowchart TD
    A[Client Data] --> B[Phone Model Pipeline]
    A --> C[Face Model Pipeline]
    B --> D[Phone Results]
    C --> E[Face Results]
    D --> F[Merge Results]
    E --> F
    F --> G[Combined Output]
```

## Model Configurations

### Phone Detection Model

- **Architecture**: YOLOv8
- **Input**: RGB image
- **Output**: Bounding boxes with confidence scores
- **Classes**: 67 object classes including phones
- **Threshold**: Configurable confidence threshold

### Face Detection Model

- **Architecture**: YOLOv8 (customized for faces)
- **Input**: RGB image
- **Output**: Face bounding boxes
- **Preprocessing**: Image normalization
- **Postprocessing**: NMS for duplicate removal

### Face Recognition Model

- **Architecture**: VGG-Face / ArcFace
- **Framework**: TensorFlow
- **Hardware Requirement**: GPU ONLY - Cannot run on CPU
- **Input**: Cropped face image
- **Output**: Face embedding vector
- **Similarity Metric**: Cosine similarity
- **Threshold**: Configurable recognition threshold
- **CUDA Support**: Required for model execution

### Anti-Spoofing Model

- **Architecture**: CNN-based classifier
- **Input**: Face ROI
- **Output**: Spoof probability score
- **Detection**: Live face vs. photo/video
- **Threshold**: Configurable spoof threshold

## Device Management

### GPU Configuration

**⚠️ IMPORTANT**: TensorFlow-based face recognition models require GPU and will fail on CPU-only systems.

```mermaid
flowchart TD
    A[Device Configuration] --> B{GPU Available?}
    B -->|Yes| C[Configure CUDA Device]
    B -->|No| D[SYSTEM FAILURE - TensorFlow models require GPU]
    C --> E[Set Device Index]
    E --> F[Load Models to GPU]
    F --> G[Optimize for Inference]
    D --> H[Error: Cannot initialize face recognition models]
    G --> J[Ready for Processing]
    H --> K[System Shutdown]
```

### Device Assignment Strategy:

- **Face Recognition Models**: Must use GPU (TensorFlow requirement)
- **Phone Detection Models**: GPU preferred, CPU fallback available
- **Anti-Spoofing Models**: GPU required for optimal performance
- **Multi-GPU Support**: Models can be distributed across multiple GPUs

### Memory Management

```python
def __del__(self):
    if hasattr(self, "__phone_model"):
        del self.__phone_model
    if hasattr(self, "__face_model"):
        del self.__face_model
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()
    tf.keras.backend.clear_session()
    gc.collect()
```

## Performance Optimization

### Inference Optimization

```mermaid
flowchart TD
    A[Model Loading] --> B[Model Compilation]
    B --> C[Memory Allocation]
    C --> D[Batch Processing]
    D --> E[GPU Utilization]
    E --> F[Result Caching]
    F --> G[Memory Cleanup]
```

### Optimization Strategies

1. **Model Quantization**: Reduced precision for faster inference
2. **Batch Processing**: Process multiple images simultaneously
3. **Memory Pooling**: Reuse memory allocations
4. **Pipeline Parallelism**: Concurrent model execution
5. **Result Caching**: Cache frequently accessed results

## Error Handling

### Model Loading Errors

```mermaid
flowchart TD
    A[Model Loading] --> B{Load Successful?}
    B -->|Yes| C[Continue Initialization]
    B -->|No| D[Log Error]
    D --> E[Check File Existence]
    E --> F[Validate Model Format]
    F --> G[Fallback Strategy]
    G --> H[Return Error Status]
```

### Runtime Errors

- **CUDA Out of Memory**: Automatic fallback to CPU for PyTorch models only
- **TensorFlow GPU Errors**: System failure - no CPU fallback available
- **Model Inference Errors**: Graceful error handling where possible
- **Device Switching**: Limited to PyTorch models only
- **Memory Leaks**: Automatic cleanup
- **GPU Unavailable**: Critical system failure for TensorFlow models

## Deployment Considerations

### Critical Hardware Requirements

1. **GPU Mandatory**: System will not function without GPU support
2. **TensorFlow Constraint**: Face recognition models cannot run on CPU
3. **Resource Planning**: Ensure adequate GPU memory for model loading
4. **Fallback Strategy**: No CPU fallback available for core functionality

### Deployment Checklist

- [ ] NVIDIA GPU with CUDA support installed
- [ ] CUDA drivers and runtime properly configured
- [ ] Sufficient GPU memory (minimum 16GB VRAM)
- [ ] TensorFlow-GPU installation verified
- [ ] Model weights accessible and valid
- [ ] GPU device permissions configured

### Common Deployment Issues

- **No GPU Detected**: System initialization failure
- **Insufficient GPU Memory**: Model loading errors
- **CUDA Version Mismatch**: TensorFlow compatibility issues
- **Driver Problems**: GPU not accessible to TensorFlow

## Configuration Examples

### Basic Configuration

```python
models_manager = ModelsManager(
    Models_Weights_dir="Models_Weights",
    ObjectDetection_model_weights="phone_detection.pt",
    FaceDetection_model_weights="yolov8_model.pt",
    Object_Detection_Models_device="cuda:0",
    Face_Detection_Model_device="cuda:0",
    Recognition_Threshold=0.3,
    Object_threshold=65,
    logger="models_logs"
)
```

### Advanced Configuration

```python
models_manager = ModelsManager(
    # Model paths
    Models_Weights_dir="Models_Weights",
    ObjectDetection_model_weights="phone_detection.pt",
    FaceDetection_model_weights="yolov8_model.pt",
    FaceRecognition_model_weights="arcface_r100.pth",
    FaceSpoofChecker_model_weights="spoof_model.pth",
  
    # Device configuration
    Object_Detection_Models_device="cuda:0",
    Face_Detection_Model_device="cuda:1",
    Face_Recognition_Model_device="cuda:0",
    spoof_Models_device="cuda:1",
  
    # Model parameters
    Recognition_model_name="ArcFace",
    Recognition_Threshold=0.4,
    Anti_Spoof_threshold=0.7,
    Recognition_Metric="cosine_similarity",
    Object_class_number=80,
    Object_threshold=70,
  
    logger="models_logs"
)
```

## Usage Example

```python
# Initialize models manager
models_manager = ModelsManager(
    Models_Weights_dir="Models_Weights",
    ObjectDetection_model_weights="phone_detection.pt",
    FaceDetection_model_weights="yolov8_model.pt",
    Object_Detection_Models_device="cuda:0",
    Face_Detection_Model_device="cuda:0",
    Recognition_Threshold=0.3,
    Object_threshold=65,
    logger="models_logs"
)

# Process client data
client_data = {
    "user_image": image,
    "actual_username": "client_1",
    "ref_image": reference_image,
    "send_time": "12:00:00"
}

# Run combined pipeline
results = models_manager.models_pipeline(client_data)

# Process individual pipelines
phone_results = models_manager.phone_model_pipeline(client_data)
face_results = models_manager.face_model_pipeline(client_data)
```

## Dependencies

- **tensorflow**: Deep learning framework (GPU version required)
- **tensorflow-gpu**: GPU acceleration for TensorFlow models
- **torch**: PyTorch framework (GPU support recommended)
- **opencv-python**: Image processing
- **numpy**: Numerical computations
- **ultralytics**: YOLO models
- **deepface**: Face recognition framework
- **cuda-toolkit**: NVIDIA CUDA development toolkit
- **gc**: Garbage collection
- **common_utilities**: Logging utilities

### GPU-Specific Dependencies

- **CUDA Runtime**: Required for GPU operations
- **cuDNN**: Deep learning GPU acceleration
- **NVIDIA Drivers**: GPU hardware interface
