# PipeLine Module Documentation

## Overview

The `PipeLine.py` module implements individual processing pipelines that handle face recognition and phone detection tasks. Each pipeline manages a set of clients and processes their data through specialized model pipelines using multithreading for optimal performance.

## Class Diagram

```mermaid
classDiagram
    class PipeLine {
        +str pipeline_name
        +int MAX_CLIENTS
        +dict model_init_param
        +SaveAction_Thread SaveAction_Thread
        +ActionDecisionManager action_decision_manager
        +mp.Manager data_manager
        +mp.List pipeline_clients
        +int pipeline_clients_count
        +mp.Value __STOP
        +RedisHandler redis_data
        +threading.Lock lock_Data
        +__init__(pipeline_name, models_init_parameters, Max_clients, logger)
        +__del__()
        +assigned_clients(client_name) bool
        +unassigned_clients(client_name) bool
        +phone_detection_pipeline(models_manager, phone_data) void
        +recognition_anti_spoof_pipeline(models_manager, face_data) void
        +pipeline(face_data, phone_data) void
        +run() void
        +ModelsInitiation() ModelsManager
        +No_Clients: int
        +stop: bool
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
  
    class ModelsManager {
        +phone_model_pipeline(client_data) dict
        +face_model_pipeline(client_data) dict
    }
  
    class ActionDecisionManager {
        +phone_decide_action(pipeline_result) tuple
        +face_decide_action(pipeline_result) dict
    }
  
    class SaveAction_Thread {
        +add_to_queue(user_name, Action_Reason, Action_image) void
        +Start_thread() void
    }
  
    PipeLine --|> Base_process : inherits
    PipeLine *-- ModelsManager : creates
    PipeLine *-- ActionDecisionManager : contains
    PipeLine *-- SaveAction_Thread : contains
    PipeLine --> RedisHandler : uses
    PipeLine --> ClientsData : manages
```

## Architecture Overview

The PipeLine class implements a multi-threaded processing architecture where each pipeline handles multiple clients through separate processing threads for phone detection and face recognition.

## Related Component Documentation

Each pipeline integrates with multiple system components:

- **[ModelsManager](ModelsManager.md)** - AI model management for pipeline processing
- **[Object Detection Task](Object_Detection_Task.md)** - Phone detection processing
  - `ObjectDetection.py` - Core object detection
  - `PhoneDetection.py` - Phone-specific detection
- **[Face Recognition Anti-Spoof Task](Face_Recognition_Anti_Spoof_Task.md)** - Face recognition processing
  - `FaceDetectionRecognition.py` - Main face authentication pipeline
  - `DetectFaces.py` - Face detection
  - `RecognitionFace.py` - Face recognition
  - `SpoofChecker.py` - Anti-spoofing
- **[ActionDecisionManager](ActionDecisionManager.md)** - Decision logic for each pipeline
- **[Save_Action_thread](Save_Action_thread.md)** - Action logging for pipeline events
- **[PipeLinesManager](PipeLinesManager.md)** - Pipeline coordination and management
- **[Utilities](Utilities.md)** - Project utilities and support functions

## Pipeline Architecture

```mermaid
flowchart TD
    A[Client Data Input] --> B[Pipeline Distributor]
    B --> C[Phone Detection Queue]
    B --> D[Face Recognition Queue]
  
    C --> E[Phone Detection Thread]
    D --> F[Face Recognition Thread]
  
    E --> G[Phone Model Pipeline]
    F --> H[Face Model Pipeline]
  
    G --> I[Phone Decision Logic]
    H --> J[Face Decision Logic]
  
    I --> K[Action Queue]
    J --> K
  
    K --> L[Save Action Thread]
    L --> M[Action Storage]
  
    K --> N[Client Response]
```

## Core Functionality

### 1. Client Management

#### Client Assignment Flow

```mermaid
flowchart TD
    A[New Client Request] --> B{Pipeline Has Space?}
    B -->|Yes| C[Add to Pipeline Clients]
    B -->|No| D[Return False]
    C --> E[Increment Client Count]
    E --> F[Update Client List]
    F --> G[Return True]
```

#### Client Unassignment Flow

```mermaid
flowchart TD
    A[Client Disconnect] --> B{Client in Pipeline?}
    B -->|Yes| C[Remove from Pipeline]
    B -->|No| D[Return False]
    C --> E[Decrement Client Count]
    E --> F[Update Client List]
    F --> G[Return True]
```

### 2. Processing Threads

#### Phone Detection Pipeline

```mermaid
flowchart TD
    A[Phone Detection Thread] --> B[Check Queue]
    B --> C{Data Available?}
    C -->|Yes| D[Get Client Data]
    C -->|No| E[Sleep 0.1s]
    D --> F[Process Phone Model]
    F --> G[Make Decision]
    G --> H[Queue Action]
    H --> I[Update Client]
    E --> B
    I --> B
```

#### Face Recognition Pipeline

```mermaid
flowchart TD
    A[Face Recognition Thread] --> B[Check Queue]
    B --> C{Data Available?}
    C -->|Yes| D[Get Client Data]
    C -->|No| E[Sleep 0.1s]
    D --> F[Process Face Model]
    F --> G[Anti-Spoof Check]
    G --> H[Recognition Check]
    H --> I[Make Decision]
    I --> J[Queue Action]
    J --> K[Update Client]
    E --> B
    K --> B
```

## Key Methods

### Client Management

#### `assigned_clients(client_name) -> bool`

**Purpose**: Assigns a new client to the pipeline

**Implementation**:

```python
def assigned_clients(self, client_name) -> bool:
    if self.pipeline_clients_count < self.MAX_CLIENTS:
        with self.lock_Data:
            self.pipeline_clients_count += 1
            self.pipeline_clients.append(client_name)
        return True
    else:
        return False
```

#### `unassigned_clients(client_name) -> bool`

**Purpose**: Removes a client from the pipeline

**Implementation**:

```python
def unassigned_clients(self, client_name) -> bool:
    if client_name in self.pipeline_clients:
        with self.lock_Data:
            self.pipeline_clients_count -= 1
            self.pipeline_clients.remove(client_name)
        return True
    else:
        return False
```

### Processing Methods

#### `phone_detection_pipeline(models_manager, phone_data)`

**Purpose**: Processes phone detection requests

**Flow**:

```mermaid
flowchart TD
    A[Start Phone Detection] --> B[Wait for Data]
    B --> C{Queue Empty?}
    C -->|Yes| D[Sleep 0.1s]
    C -->|No| E[Get Phone Data]
    E --> F[Extract Client Info]
    F --> G[Run Phone Model]
    G --> H[Make Decision]
    H --> I{Action Required?}
    I -->|Yes| J[Queue Action]
    I -->|No| K[Continue]
    J --> L[Update Client]
    K --> B
    L --> B
    D --> B
```

#### `recognition_anti_spoof_pipeline(models_manager, face_data)`

**Purpose**: Processes face recognition and anti-spoofing

**Flow**:

```mermaid
flowchart TD
    A[Start Face Recognition] --> B[Wait for Data]
    B --> C{Queue Empty?}
    C -->|Yes| D[Sleep 0.1s]
    C -->|No| E[Get Face Data]
    E --> F[Extract Client Info]
    F --> G[Run Face Model]
    G --> H[Anti-Spoof Check]
    H --> I[Recognition Check]
    I --> J[Make Decision]
    J --> K[Queue Action]
    K --> L[Update Client]
    L --> B
    D --> B
```

#### `pipeline(face_data, phone_data)`

**Purpose**: Main pipeline coordinator that distributes client data

**Flow**:

```mermaid
flowchart TD
    A[Get Pipeline Clients] --> B[Sort Client List]
    B --> C[For Each Client]
    C --> D[Get Client Data]
    D --> E[Get Client Metadata]
    E --> F{Data Available?}
    F -->|Yes| G[Merge Data]
    F -->|No| H[Next Client]
    G --> I[Add to Phone Queue]
    I --> J[Add to Face Queue]
    J --> K{More Clients?}
    K -->|Yes| C
    K -->|No| L[End Cycle]
    H --> K
```

## Data Flow

### Client Data Processing

```mermaid
sequenceDiagram
    participant Client
    participant Pipeline
    participant PhoneThread
    participant FaceThread
    participant ActionManager
    participant SaveThread
  
    Client->>Pipeline: Send Image Data
    Pipeline->>Pipeline: Get Client Metadata
    Pipeline->>PhoneThread: Queue Phone Data
    Pipeline->>FaceThread: Queue Face Data
  
    PhoneThread->>PhoneThread: Process Phone Detection
    FaceThread->>FaceThread: Process Face Recognition
  
    PhoneThread->>ActionManager: Phone Decision
    FaceThread->>ActionManager: Face Decision
  
    ActionManager->>SaveThread: Save Action
    ActionManager->>Client: Send Response
```

### Model Processing Flow

```mermaid
flowchart LR
    A[Client Image] --> B[Phone Detection Model]
    A --> C[Face Detection Model]
  
    B --> D[Phone Bounding Box]
    C --> E[Face Bounding Box]
  
    E --> F[Face Recognition Model]
    E --> G[Anti-Spoof Model]
  
    F --> H[Identity Verification]
    G --> I[Spoof Detection]
  
    D --> J[Action Decision]
    H --> J
    I --> J
  
    J --> K[Client Response]
    J --> L[Action Logging]
```

## Threading Architecture

### Thread Management

```mermaid
flowchart TD
    A[Pipeline Process] --> B[Main Thread]
    B --> C[Phone Detection Thread]
    B --> D[Face Recognition Thread]
    B --> E[Save Action Thread]
  
    C --> F[Phone Queue Processing]
    D --> G[Face Queue Processing]
    E --> H[Action Logging]
  
    F --> I[Models Manager]
    G --> I
  
    I --> J[Action Decision Manager]
    J --> K[Client Response Queue]
```

### Thread Synchronization

- **Lock_Data**: Protects client list modifications
- **Queue Management**: Thread-safe queue operations
- **Shared State**: Multiprocessing shared variables

## Error Handling

### Pipeline Errors

```mermaid
flowchart TD
    A[Pipeline Error] --> B{Error Type}
    B -->|Model Error| C[Log Error]
    B -->|Queue Error| D[Skip Processing]
    B -->|Client Error| E[Remove Client]
  
    C --> F[Continue Processing]
    D --> F
    E --> G[Update Client Count]
    G --> F
    F --> H[Set Stop Flag if Critical]
```

### Recovery Mechanisms

- **Graceful Degradation**: Continue processing other clients
- **Error Logging**: Comprehensive error tracking
- **State Recovery**: Automatic client state restoration

## Performance Optimization

### Queue Management

- **Queue Size**: Limited to MAX_CLIENTS to prevent memory issues
- **Non-blocking Operations**: Prevents thread deadlocks
- **Batch Processing**: Efficient data processing

### Resource Management

- **Memory Cleanup**: Automatic cleanup of client data
- **GPU Memory**: Efficient GPU resource utilization
- **Thread Pools**: Optimized thread management

## Configuration

### Pipeline Parameters

```python
pipeline = PipeLine(
    pipeline_name="pipeline_0",
    Max_clients=30,
    models_init_parameters=Models_Parameters,
    logger=logger
)
```

### Model Parameters

- **Recognition Threshold**: Face recognition confidence threshold
- **Anti-Spoof Threshold**: Spoofing detection threshold
- **Object Threshold**: Phone detection confidence threshold

## Usage Example

```python
# Initialize pipeline
pipeline = PipeLine(
    pipeline_name="pipeline_0",
    Max_clients=30,
    models_init_parameters=Models_Parameters,
    logger="pipeline_logs"
)

# Assign clients
pipeline.assigned_clients("client_1")
pipeline.assigned_clients("client_2")

# Start pipeline
pipeline.start()

# Monitor pipeline
while pipeline.is_alive():
    print(f"Active clients: {pipeline.No_Clients}")
    time.sleep(1)
```

## Dependencies

- **torch.multiprocessing**: Process management
- **threading**: Thread synchronization
- **queue**: Thread-safe queues
- **redis**: Client state management
- **ModelsManager**: AI model management
- **ActionDecisionManager**: Decision logic
- **SaveAction_Thread**: Action logging

## Memory Management

### Resource Cleanup

```python
def __del__(self):
    if hasattr(self, "action_decision_manager"):
        del self.action_decision_manager
    if hasattr(self, "pipeline_clients"):
        del self.pipeline_clients
    self.data_manager.shutdown()
```

### Memory Optimization

- **Shared Memory**: Efficient inter-process communication
- **Resource Pooling**: Reuse of expensive resources
- **Garbage Collection**: Automatic memory cleanup

## Future Enhancements

1. **Dynamic Load Balancing**: Automatic queue balancing
2. **Advanced Error Recovery**: Automatic error recovery
3. **Performance Profiling**: Detailed performance analysis
4. **Adaptive Thresholds**: Dynamic threshold adjustment
5. **Health Monitoring**: Real-time health checks
