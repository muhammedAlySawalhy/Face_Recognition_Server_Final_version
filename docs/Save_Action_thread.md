# Save_Action_thread Module Documentation

## Overview

The `Save_Action_thread.py` module implements a threaded action logging system that handles the persistent storage of security actions and their associated evidence images. It provides asynchronous logging capabilities for actions such as face recognition failures, phone detections, and spoofing attempts.

## Class Diagram

```mermaid
classDiagram
    class SaveAction_Thread {
        +Queue save_action_queue
        +__init__(thread_name)
        +run() void
        +add_to_queue(user_name, Action_Reason, Action_image) void
        +save_User_Action(user_name, Action_Reason, Action_image) void
    }
    
    class Base_Thread {
        <<abstract>>
        +str thread_name
        +bool stop_thread
        +Start_thread() void
        +Stop_thread() void
        +Join_thread() void
        +is_alive() bool
    }
    
    class Queue {
        +put(item) void
        +get() any
        +empty() bool
        +full() bool
    }
    
    class Action {
        <<enumeration>>
        ACTION_LOCK_SCREEN
        ACTION_SIGN_OUT
        ACTION_WARNING
        ACTION_ERROR
        NO_ACTION
    }
    
    class Reason {
        <<enumeration>>
        REASON_NO_FACE
        REASON_SPOOF_IMAGE
        REASON_WRONG_USER
        REASON_PHONE_DETECTION
        REASON_PAUSED_CLIENT
        REASON_BLOCKED_CLIENT
        EMPTY_REASON
    }
    
    SaveAction_Thread --|> Base_Thread : inherits
    SaveAction_Thread *-- Queue : contains
    SaveAction_Thread --> Action : uses
    SaveAction_Thread --> Reason : uses
    SaveAction_Thread --> cv2 : uses
    SaveAction_Thread --> os : uses
```

## Architecture Overview

The SaveAction_Thread implements a producer-consumer pattern where security actions are queued by detection systems and processed asynchronously by the thread for persistent storage.

## Action Logging Architecture

```mermaid
flowchart TD
    A[Security Event] --> B[ActionDecisionManager]
    B --> C[Save_Action_Thread Queue]
    C --> D[Action Processing Loop]
    D --> E[Directory Creation]
    E --> F[File Naming]
    F --> G[Image Storage]
    G --> H[Evidence Archive]
    
    I[Phone Detection] --> C
    J[Spoof Detection] --> C
    K[Wrong User] --> C
    L[No Face] --> C
```

## Core Functionality

### 1. Threaded Action Processing

#### Thread Processing Flow
```mermaid
flowchart TD
    A[Thread Start] --> B[Wait for Queue Item]
    B --> C[Get Action Data]
    C --> D[Extract Components]
    D --> E[Process Action]
    E --> F[Save to File System]
    F --> G[Continue Loop]
    G --> B
```

#### Queue Management
```mermaid
flowchart LR
    A[Producer Threads] --> B[Action Queue]
    B --> C[Consumer Thread]
    C --> D[File System]
    
    A1[Phone Detection] --> B
    A2[Face Recognition] --> B
    A3[Spoof Detection] --> B
    A4[User Validation] --> B
    
    C --> D1[Action Directories]
    C --> D2[Evidence Images]
    C --> D3[Audit Trail]
```

### 2. File System Organization

#### Directory Structure
```
Data/Actions/
├── Lock_screen/
│   ├── user1/
│   │   ├── 17_07_2025-12_30_Lock_screen_No_face.jpg
│   │   └── 17_07_2025-12_31_Lock_screen_Wrong_user.jpg
│   └── user2/
├── Sign_out/
│   ├── user1/
│   │   ├── 17_07_2025-12_32_Sign_out_Spoof_image.jpg
│   │   └── 17_07_2025-12_33_Sign_out_Phone_detection.jpg
│   └── user2/
└── Warning/
    └── user1/
```

#### File Naming Convention
```
{DD_MM_YYYY-HH_MM}___{Action_Type}___{Reason_Type}.jpg
```

Example: `17_07_2025-12_30___Lock_screen___No_face.jpg`

## Key Methods

### Thread Management

#### `__init__(thread_name)`
**Purpose**: Initializes the action logging thread

**Implementation**:
```python
def __init__(self, thread_name):
    super().__init__(thread_name=thread_name)
    self.save_action_queue: Queue[Tuple[str, Dict[str, int], cv2.typing.MatLike]] = Queue()
```

#### `run()`
**Purpose**: Main thread execution loop

**Implementation**:
```python
def run(self):
    while(True):
        tuple_action_data = self.save_action_queue.get()
        self.save_User_Action(
            user_name=tuple_action_data[0],
            Action_Reason=tuple_action_data[1],
            Action_image=tuple_action_data[2]
        )
```

### Queue Operations

#### `add_to_queue(user_name, Action_Reason, Action_image)`
**Purpose**: Adds action data to the processing queue

**Parameters**:
- `user_name`: Client identifier
- `Action_Reason`: Dictionary containing action and reason codes
- `Action_image`: OpenCV image with evidence

**Implementation**:
```python
def add_to_queue(self, user_name: str, Action_Reason: Dict[str, int], Action_image: cv2.typing.MatLike):
    self.save_action_queue.put((user_name, Action_Reason, Action_image))
```

### File System Operations

#### `save_User_Action(user_name, Action_Reason, Action_image)`
**Purpose**: Saves action evidence to the file system

**Process Flow**:
```mermaid
flowchart TD
    A[Action Data] --> B[Get Root Path]
    B --> C[Extract Action Details]
    C --> D[Create Directory Structure]
    D --> E[Generate Timestamp]
    E --> F[Create File Name]
    F --> G[Save Image]
    G --> H[Complete Action Logging]
```

**Implementation**:
```python
def save_User_Action(self, user_name: str, Action_Reason: Dict[str, int], Action_image: cv2.typing.MatLike) -> None:
    root_path = get_root_path(__file__, "main.py")
    Action_name = Action_Reason['action']
    Reason_name = Action_Reason['reason']
    
    # Create directory structure
    action_user_dir = os.path.join(
        root_path, "Data", "Actions",
        Action(Action_name).name.replace("ACTION_", "").capitalize(),
        user_name
    )
    os.makedirs(action_user_dir, exist_ok=True)
    
    # Generate timestamp and filename
    action_time = time.localtime()
    formatted_action_time = time.strftime("%d_%m_%Y-%H_%M", action_time)
    image_name = "___".join([
        formatted_action_time,
        Action(Action_name).name.replace("ACTION_", "").capitalize(),
        Reason(Reason_name).name.replace("REASON_", "").capitalize()
    ])
    
    # Save image
    image_name_path = os.path.join(action_user_dir, image_name + ".jpg")
    cv2.imwrite(image_name_path, Action_image)
```

## Action Types and Processing

### Action Categories

#### Lock Screen Actions
```mermaid
flowchart TD
    A[Lock Screen Action] --> B[No Face Detected]
    A --> C[Wrong User Detected]
    A --> D[Authentication Failure]
    
    B --> E[Save Evidence Image]
    C --> E
    D --> E
    
    E --> F[Create Lock_screen Directory]
    F --> G[User-specific Subdirectory]
    G --> H[Timestamped Evidence File]
```

#### Sign Out Actions
```mermaid
flowchart TD
    A[Sign Out Action] --> B[Spoof Image Detected]
    A --> C[Phone Detected]
    A --> D[Security Violation]
    
    B --> E[Save Evidence Image]
    C --> E
    D --> E
    
    E --> F[Create Sign_out Directory]
    F --> G[User-specific Subdirectory]
    G --> H[Timestamped Evidence File]
```

### Evidence Processing

#### Image Processing Flow
```mermaid
flowchart TD
    A[Original Image] --> B[Bounding Box Overlay]
    B --> C[Security Annotation]
    C --> D[Compression Optimization]
    D --> E[File System Storage]
    
    F[Action Metadata] --> G[Timestamp Generation]
    G --> H[File Name Creation]
    H --> I[Directory Structure]
    I --> E
```

#### Bounding Box Visualization
- **Phone Detection**: Red bounding boxes around detected phones
- **Face Detection**: Blue bounding boxes for spoof faces
- **Annotation**: Clear visual indication of security violations

## File Organization

### Directory Hierarchy
```
Data/Actions/
├── {Action_Type}/          # Action category (Lock_screen, Sign_out, etc.)
│   ├── {User_Name}/        # User-specific subdirectory
│   │   ├── {Timestamp}___{Action}___{Reason}.jpg
│   │   └── {Timestamp}___{Action}___{Reason}.jpg
│   └── {User_Name}/
└── {Action_Type}/
```

### File Naming Components
1. **Timestamp**: `DD_MM_YYYY-HH_MM` format
2. **Action Type**: Cleaned action name (e.g., "Lock_screen")
3. **Reason**: Cleaned reason name (e.g., "No_face")
4. **Extension**: `.jpg` for images

## Performance Considerations

### Queue Management
```mermaid
flowchart TD
    A[Queue Performance] --> B[Memory Usage]
    A --> C[Processing Speed]
    A --> D[Thread Safety]
    
    B --> E[Bounded Queue Size]
    C --> F[Async Processing]
    D --> G[Thread-Safe Operations]
    
    E --> H[Memory Optimization]
    F --> I[Non-blocking Operations]
    G --> J[Concurrent Access Safety]
```

### Optimization Strategies
1. **Asynchronous Processing**: Non-blocking action logging
2. **Memory Efficiency**: Minimal memory footprint for queue items
3. **File System Optimization**: Efficient directory creation and file writing
4. **Error Handling**: Graceful error recovery for file operations

## Error Handling

### File System Errors
```mermaid
flowchart TD
    A[File Operation] --> B{Directory Exists?}
    B -->|No| C[Create Directory]
    B -->|Yes| D[Write File]
    
    C --> E{Creation Success?}
    E -->|No| F[Log Error]
    E -->|Yes| D
    
    D --> G{Write Success?}
    G -->|No| H[Log Error]
    G -->|Yes| I[Complete]
    
    F --> J[Continue Processing]
    H --> J
    I --> K[Next Action]
```

### Recovery Mechanisms
- **Directory Creation**: Automatic creation of missing directories
- **Error Logging**: Comprehensive error tracking
- **Graceful Degradation**: Continue processing despite individual failures
- **Retry Logic**: Automatic retry for transient errors

## Security and Compliance

### Evidence Integrity
- **Timestamp Accuracy**: Precise time recording for audit trails
- **Image Integrity**: Unmodified evidence images
- **Access Control**: Secure file system permissions
- **Audit Trail**: Complete action logging history

### Privacy Considerations
- **Data Minimization**: Only necessary data is stored
- **Secure Storage**: Protected file system access
- **Retention Policy**: Configurable evidence retention
- **Access Logging**: Track access to evidence files

## Configuration

### Thread Configuration
```python
save_action_thread = SaveAction_Thread("SaveAction_Thread")
save_action_thread.Start_thread()
```

### Storage Configuration
- **Root Path**: Automatically determined from application structure
- **Directory Structure**: Organized by action type and user
- **File Format**: JPEG for optimal storage efficiency
- **Naming Convention**: Standardized timestamp and metadata format

## Monitoring

### Performance Metrics
```mermaid
flowchart LR
    A[Monitoring Metrics] --> B[Queue Depth]
    A --> C[Processing Time]
    A --> D[Storage Usage]
    A --> E[Error Rates]
    
    B --> F[Queue size monitoring]
    C --> G[Action processing speed]
    D --> H[Disk space usage]
    E --> I[File operation failures]
```

### Health Indicators
- **Queue Size**: Number of pending actions
- **Processing Rate**: Actions processed per second
- **Storage Growth**: Evidence storage consumption
- **Error Frequency**: File operation failure rate

## Usage Example

```python
# Initialize save action thread
save_action_thread = SaveAction_Thread("SaveAction_Thread")
save_action_thread.Start_thread()

# Add action to queue
action_data = {
    "action": Action.ACTION_SIGN_OUT.value,
    "reason": Reason.REASON_PHONE_DETECTION.value
}

save_action_thread.add_to_queue(
    user_name="user1",
    Action_Reason=action_data,
    Action_image=evidence_image
)

# Thread processes actions asynchronously
# Files are saved to: Data/Actions/Sign_out/user1/17_07_2025-12_30___Sign_out___Phone_detection.jpg
```

## Dependencies

- **os**: File system operations
- **time**: Timestamp generation
- **typing**: Type hints for better code documentation
- **cv2**: Image processing and file writing
- **queue**: Thread-safe queue operations
- **common_utilities**: Base thread functionality and path utilities
- **utilities.project_utilities**: Action and Reason enumerations

## Thread Safety

### Synchronization
- **Thread-Safe Queue**: Built-in thread safety for queue operations
- **Atomic Operations**: File system operations are atomic
- **Error Isolation**: Thread-level error handling
- **Resource Management**: Proper resource cleanup

## Future Enhancements

1. **Database Integration**: Store action metadata in database
2. **Compression**: Implement image compression for storage efficiency
3. **Backup System**: Automated backup of evidence files
4. **Encryption**: Encrypt sensitive evidence data
5. **Retention Policy**: Automated cleanup of old evidence
6. **Real-time Monitoring**: Live monitoring of action logging
7. **Batch Processing**: Optimize for high-volume action logging
8. **Cloud Storage**: Integration with cloud storage services
9. **Advanced Analytics**: Analysis of action patterns and trends
10. **Notification System**: Real-time alerts for critical actions
