# PipeLinesManager Module Documentation

## Overview

The `PipeLinesManager.py` module manages multiple processing pipelines for handling face recognition and object detection tasks. It provides dynamic pipeline creation, client assignment, and resource management to ensure optimal performance and scalability.

## Class Diagram

```mermaid
classDiagram
    class PipeLinesManager {
        +int MaxClientPerPipeline
        +dict models_parameters
        +int No_pipelines
        +int Max_System_Clients
        +dict pipelines_process
        +dict Clients2pipelines
        +list active_clients
        +threading.Lock lock
        +dict pipelines
        +RedisHandler redis_data
        +int current_gpu_index
        +float GPU_MEM_THRESHOLD
        +set full_space_pipelines
        +set unregister_clients
        +threading.Lock data_lock
        +__init__(manager_name, MaxClientPerPipeline, MaxPipeline, Models_Parameters, logger)
        +__Is_system_capacity_full() bool
        +__Is_GPUs_FULL() bool
        +__assigned_clients() void
        +__unassigned_clients() void
        +__initialize_pipeline_if_needed(pipeline_no) bool
        +__assigned_client(pipeline_no, client_name) bool
        +__unassigned_client(pipeline_no, client_name) bool
        +Manager() void
        +Stop_process() void
        +run() void
    }
    
    class Base_process {
        <<abstract>>
        +str process_name
        +bool stop_process
        +Start_process() void
        +Stop_process() void
        +Join_process() void
        +is_alive() bool
    }
    
    class PipeLine {
        +str pipeline_name
        +int MAX_CLIENTS
        +dict model_init_param
        +assigned_clients(client_name) bool
        +unassigned_clients(client_name) bool
        +run() void
    }
    
    PipeLinesManager --|> Base_process : inherits
    PipeLinesManager *-- PipeLine : creates
    PipeLinesManager --> RedisHandler : uses
    PipeLinesManager --> LOGGER : logs
```

## Architecture Overview

The PipeLinesManager acts as a central coordinator for multiple processing pipelines, managing client assignment, resource allocation, and system capacity monitoring.

## Related Component Documentation

The PipeLinesManager coordinates with various system components:

- **[PipeLine](PipeLine.md)** - Individual pipeline processing logic
- **[ModelsManager](ModelsManager.md)** - AI model management for each pipeline
- **[Object Detection Task](Object_Detection_Task.md)** - Phone detection components
- **[Face Recognition Anti-Spoof Task](Face_Recognition_Anti_Spoof_Task.md)** - Face recognition components
- **[ActionDecisionManager](ActionDecisionManager.md)** - Decision logic for each pipeline
- **[Server](Server.md)** - WebSocket server coordination
- **[Save_Action_thread](Save_Action_thread.md)** - Action logging coordination

## Core Functionality

### 1. Pipeline Management

#### Pipeline Creation Flow
```mermaid
flowchart TD
    A[New Client Request] --> B{Available Pipeline?}
    B -->|Yes| C[Assign to Existing Pipeline]
    B -->|No| D{GPU Available?}
    D -->|Yes| E[Create New Pipeline]
    D -->|No| F[System Full - Reject]
    E --> G[Initialize Models]
    G --> H[Start Pipeline Process]
    H --> I[Assign Client]
    C --> I
    I --> J[Update Client Status]
    F --> K[Set System Full Flag]
```

#### Pipeline Lifecycle
```mermaid
flowchart LR
    A[Created] --> B[Initializing]
    B --> C[Active]
    C --> D[Full]
    D --> E[Reducing]
    E --> F[Empty]
    F --> G[Terminated]
    C --> F
```

### 2. Client Assignment System

#### Client Assignment Flow
```mermaid
flowchart TD
    A[Active Client Request] --> B{System at Capacity?}
    B -->|Yes| C[Add to Close Queue]
    B -->|No| D[Find Available Pipeline]
    D --> E{Pipeline Found?}
    E -->|Yes| F[Initialize if Needed]
    E -->|No| G[Wait for Pipeline]
    F --> H{Initialization Success?}
    H -->|Yes| I[Assign Client]
    H -->|No| J[Log Error]
    I --> K[Update Pipeline Status]
    C --> L[Set System Full Flag]
```

## Key Methods

### System Capacity Management

#### `__Is_system_capacity_full() -> bool`
**Purpose**: Monitors system capacity and manages client overflow

**Logic**:
```mermaid
flowchart TD
    A[Check Capacity] --> B{Current Clients == Max?}
    B -->|Yes| C{Unregistered Clients > 0?}
    B -->|No| D[Clear System Full Flag]
    C -->|Yes| E[Set System Full Flag]
    C -->|No| F[Return True]
    E --> G[Log Capacity Warning]
    G --> H[Return True]
    D --> I[Return False]
    F --> I
```

#### `__Is_GPUs_FULL() -> bool`
**Purpose**: Monitors GPU resource availability

**Logic**:
```mermaid
flowchart TD
    A[Check GPU Memory] --> B{Available GPU?}
    B -->|Yes| C[Clear GPU Full Flag]
    B -->|No| D[Set GPU Full Flag]
    C --> E[Update Current GPU Index]
    E --> F[Return False]
    D --> G[Log GPU Warning]
    G --> H[Return True]
```

### Client Management Threads

#### `__assigned_clients()`
**Purpose**: Manages assignment of new clients to pipelines

**Flow**:
```mermaid
flowchart TD
    A[Start Assignment Thread] --> B[Get Active Clients]
    B --> C[Calculate Unregistered Clients]
    C --> D{System Full?}
    D -->|Yes| E[Queue Clients for Closure]
    D -->|No| F[Find Free Pipeline]
    F --> G{Pipeline Available?}
    G -->|Yes| H[Assign Clients]
    G -->|No| I[Wait for Pipeline]
    H --> J[Update Client Status]
    E --> K[Update Redis Status]
    I --> L[Sleep 1s]
    J --> L
    K --> L
    L --> B
```

#### `__unassigned_clients()`
**Purpose**: Removes clients no longer active from pipelines

**Flow**:
```mermaid
flowchart TD
    A[Start Unassignment Thread] --> B[Get Active Clients]
    B --> C[Check Assigned Clients]
    C --> D{Client Still Active?}
    D -->|No| E[Remove from Pipeline]
    D -->|Yes| F[Continue]
    E --> G{Pipeline Empty?}
    G -->|Yes| H[Terminate Pipeline]
    G -->|No| I[Update Pipeline Status]
    H --> J[Clean Resources]
    I --> K[Update Full Space Status]
    J --> K
    F --> L[Sleep 0.1s]
    K --> L
    L --> B
```

### Pipeline Operations

#### `__initialize_pipeline_if_needed(pipeline_no) -> bool`
**Purpose**: Creates and initializes a new pipeline if required

**Implementation**:
```mermaid
flowchart TD
    A[Check Pipeline Status] --> B{Pipeline Exists?}
    B -->|Yes| C[Return True]
    B -->|No| D{GPU Available?}
    D -->|Yes| E[Configure GPU Device]
    D -->|No| F[Update Max Clients]
    E --> G[Create Pipeline Instance]
    G --> H[Start Pipeline Process]
    H --> I[Store Pipeline Reference]
    I --> J[Return True]
    F --> K[Return False]
```

#### `__assigned_client(pipeline_no, client_name) -> bool`
**Purpose**: Assigns a specific client to a pipeline

**Logic**:
```mermaid
flowchart TD
    A[Initialize Pipeline] --> B{Pipeline Ready?}
    B -->|Yes| C[Assign Client]
    B -->|No| D[Return False]
    C --> E[Update Client Mapping]
    E --> F{Pipeline Full?}
    F -->|Yes| G[Mark as Full]
    F -->|No| H[Return True]
    G --> I[Return False]
```

#### `__unassigned_client(pipeline_no, client_name) -> bool`
**Purpose**: Removes a client from a pipeline

**Logic**:
```mermaid
flowchart TD
    A[Check Pipeline] --> B{Pipeline Exists?}
    B -->|Yes| C[Remove Client]
    B -->|No| D[Return False]
    C --> E[Update Client Mapping]
    E --> F[Return True]
```

## Resource Management

### GPU Management
```mermaid
flowchart TD
    A[GPU Selection] --> B[Check Memory Usage]
    B --> C{Usage < Threshold?}
    C -->|Yes| D[Select GPU]
    C -->|No| E[Check Next GPU]
    D --> F[Update Current GPU Index]
    E --> G{More GPUs?}
    G -->|Yes| B
    G -->|No| H[Set GPU Full Flag]
    F --> I[Configure Models]
    H --> J[Limit System Capacity]
```

### Memory Management
- **Pipeline Cleanup**: Automatic cleanup of terminated pipelines
- **Client Mapping**: Efficient client-to-pipeline mapping
- **Resource Monitoring**: Continuous monitoring of system resources

## Configuration Parameters

### System Limits
- `MaxClientPerPipeline`: Maximum clients per pipeline (default: 30)
- `MaxPipeline`: Maximum number of pipelines (default: 5)
- `GPU_MEM_THRESHOLD`: GPU memory threshold (default: 0.8)

### Model Parameters
```python
Models_Parameters = {
    "Models_Weights_dir": "Models_Weights",
    "ObjectDetection_model_weights": "phone_detection.pt",
    "FaceDetection_model_weights": "yolov8_model.pt",
    "FaceRecognition_model_weights": None,
    "FaceSpoofChecker_model_weights": None,
    "Object_Detection_Models_device": "cuda",
    "Face_Detection_Model_device": "cuda",
    "Face_Recognition_Model_device": "GPU",
    "spoof_Models_device": "cuda",
    "Recognition_model_name": "VGG-Face",
    "Recognition_Metric": "cosine_similarity",
    "Object_class_number": 67,
    "Recognition_Threshold": 0.3,
    "Object_threshold": 65,
    "Anti_Spoof_threshold": 0.99
}
```

## Performance Metrics

### Capacity Calculations
- **Max System Clients**: `MaxPipeline × MaxClientPerPipeline`
- **Pipeline Utilization**: Clients per pipeline / MaxClientPerPipeline
- **System Utilization**: Total clients / Max System Clients

### Monitoring Points
1. **Active Clients**: Number of currently connected clients
2. **Pipeline Count**: Number of active pipelines
3. **GPU Usage**: GPU memory utilization
4. **System Capacity**: Current vs maximum capacity

## Error Handling

### Pipeline Errors
- **Initialization Failure**: GPU unavailable or model loading error
- **Process Crash**: Automatic pipeline restart
- **Resource Exhaustion**: Graceful degradation

### Client Errors
- **Assignment Failure**: Client queuing for retry
- **Timeout**: Client disconnection handling
- **Invalid State**: Client state synchronization

## Thread Safety

The PipeLinesManager uses multiple synchronization mechanisms:

### Locks
- `data_lock`: Protects pipeline data structures
- `lock`: General synchronization lock

### Thread-Safe Operations
- Client assignment and unassignment
- Pipeline creation and termination
- Resource status updates

## Usage Example

```python
# Initialize pipeline manager
pipe_lines_manager = PipeLinesManager(
    "PipeLinesManager",
    MaxClientPerPipeline=30,
    MaxPipeline=5,
    Models_Parameters=Models_Parameters,
    logger="pipelines_logs"
)

# Start pipeline manager
pipe_lines_manager.Start_process()

# Monitor pipeline manager
while pipe_lines_manager.is_alive():
    time.sleep(1)
```

## Dependencies

- **torch.multiprocessing**: Pipeline process management
- **threading**: Thread synchronization
- **redis**: Client state management
- **common_utilities**: GPU monitoring and logging
- **PipeLine**: Individual pipeline implementation

## Performance Optimization

### Strategies
1. **Lazy Loading**: Pipelines created on demand
2. **Resource Pooling**: Efficient GPU utilization
3. **Load Balancing**: Even client distribution
4. **Automatic Scaling**: Dynamic pipeline creation

### Best Practices
1. **Monitor GPU Memory**: Prevent OOM errors
2. **Client Batching**: Efficient client processing
3. **Pipeline Reuse**: Minimize initialization overhead
4. **Resource Cleanup**: Prevent memory leaks

## Future Enhancements

1. **Advanced Load Balancing**: Weighted client assignment
2. **Pipeline Prioritization**: Priority-based processing
3. **Health Monitoring**: Pipeline health checks
4. **Auto-scaling**: Dynamic capacity adjustment
5. **Metrics Dashboard**: Real-time monitoring interface
