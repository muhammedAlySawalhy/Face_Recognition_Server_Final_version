# Server Module Documentation

## Overview

The `Server.py` module implements the WebSocket server that handles client connections and manages real-time communication between clients and the face recognition system. It provides connection management, client validation, and message routing functionality.

## Class Diagram

```mermaid
classDiagram
    class ClientChecks {
        +LOGGER logs
        +__init__(logger)
        +client_is_paused(websocket, client_name, paused_clients) bool
        +client_is_blocked(websocket, client_name, blocked_clients, active_clients) bool
        +client_is_available(websocket, client_name, active_clients) bool
        +add_to_active_clients(client_name, active_clients) void
    }
  
    class Server {
        +str serve_ip
        +int server_port
        +set activate_clients
        +dict clients_join_time
        +dict clients2pipeline
        +asyncio.Semaphore semaphore
        +dict ws
        +dict clients_date
        +ClientChecks client_checks
        +RedisHandler redis_data
        +asyncio.Event system_full_event
        +__init__(process_name, serve_ip, server_port, logger)
        +signal_monitor() void
        +send_message(client_name) void
        +_register_new_client(client_name, websocket) bool
        +__cleanup_client(client_name) void
        +handle_connection(websocket) void
        +run_server() void
        +stop_server() void
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
  
    Server --|> Base_process : inherits
    Server *-- ClientChecks : contains
    Server --> RedisHandler : uses
    Server --> ClientsData : manages
    Server --> LOGGER : logs
```

## Architecture Overview

The Server module implements a multi-threaded WebSocket server with the following key components:

## Related Component Documentation

The Server module coordinates with various system components for complete functionality:

- **[ModelsManager](ModelsManager.md)** - AI model management and inference
- **[PipeLinesManager](PipeLinesManager.md)** - Pipeline creation and management
- **[PipeLine](PipeLine.md)** - Individual pipeline processing
- **[Object Detection Task](Object_Detection_Task.md)** - Phone detection components
- **[Face Recognition Anti-Spoof Task](Face_Recognition_Anti_Spoof_Task.md)** - Face recognition components
- **[ActionDecisionManager](ActionDecisionManager.md)** - Decision logic system
- **[Server_Manager](Server_Manager.md)** - File and data management
- **[Save_Action_thread](Save_Action_thread.md)** - Action logging system
- **[Utilities](Utilities.md)** - Project utilities and support functions

## Core Classes

### 1. ClientChecks Class

Handles client validation and status checking.

#### Methods

##### `client_is_paused(websocket, client_name, paused_clients) -> bool`

**Purpose**: Checks if a client is in paused state

**Flow**:

```mermaid
flowchart TD
    A[Client Connection] --> B{Is Client Paused?}
    B -->|Yes| C[Send Pause Warning]
    B -->|No| D[Continue Processing]
    C --> E[Return True]
    D --> F[Return False]
```

##### `client_is_blocked(websocket, client_name, blocked_clients, active_clients) -> bool`

**Purpose**: Validates if client is blocked and handles cleanup

**Flow**:

```mermaid
flowchart TD
    A[Check Client Status] --> B{Is Client Blocked?}
    B -->|Yes| C[Send Error Message]
    B -->|No| D[Return False]
    C --> E[Remove from Active Clients]
    E --> F[Close Connection]
    F --> G[Return True]
```

##### `client_is_available(websocket, client_name, active_clients) -> bool`

**Purpose**: Verifies client availability in user database

**Flow**:

```mermaid
flowchart TD
    A[Client Validation] --> B{Is Client Available?}
    B -->|Yes| C[Add to Active Clients]
    B -->|No| D[Send Error Message]
    C --> E[Return True]
    D --> F[Close Connection]
    F --> G[Return False]
```

### 2. Server Class

Main server implementation extending Base_process.

#### Key Attributes

- `serve_ip`: Server IP address
- `server_port`: Server port number
- `activate_clients`: Set of active client connections
- `clients_join_time`: Dictionary tracking client join timestamps
- `ws`: WebSocket connections mapping
- `clients_date`: Client data management
- `system_full_event`: Event for system capacity management

#### Core Methods

##### `signal_monitor()`

**Purpose**: Monitors system capacity and manages client connections

**Flow**:

```mermaid
flowchart TD
    A[Start Monitoring] --> B[Check System Full Signal]
    B --> C{System Full?}
    C -->|Yes| D[Set Event]
    C -->|No| E[Clear Event]
    D --> F[Get Clients to Close]
    F --> G[Close Connections]
    G --> H[Update Client Status]
    E --> I[Sleep 0.1s]
    H --> I
    I --> B
```

##### `send_message(client_name)`

**Purpose**: Sends queued messages to specific client

**Flow**:

```mermaid
flowchart TD
    A[Start Message Sending] --> B{Client Exists?}
    B -->|Yes| C[Get Queued Response]
    B -->|No| D[Exit]
    C --> E{Response Available?}
    E -->|Yes| F[Send Message]
    E -->|No| G[Sleep 0.1s]
    F --> H[Log Response]
    H --> C
    G --> C
```

##### `_register_new_client(client_name, websocket)`

**Purpose**: Registers new client connection

**Flow**:

```mermaid
flowchart TD
    A[New Client Registration] --> B[Create Client Metadata]
    B --> C[Set Join Time]
    C --> D[Get Reference Image]
    D --> E{Image Available?}
    E -->|Yes| F[Store WebSocket Connection]
    E -->|No| G[Log Warning & Return False]
    F --> H[Create Client Data Handler]
    H --> I[Start Send Message Task]
    I --> J[Update Redis Status]
    J --> K[Return True]
```

##### `handle_connection(websocket)`

**Purpose**: Main connection handler for WebSocket clients

**Flow**:

```mermaid
flowchart TD
    A[New Connection] --> B{System Full?}
    B -->|Yes| C[Get Client Name]
    B -->|No| D[Start Processing Loop]
    C --> E[Close Connection]
    D --> F[Wait for Message]
    F --> G[Parse Client Data]
    G --> H[Validate Client]
    H --> I{Validation Passed?}
    I -->|Yes| J[Process User Image]
    I -->|No| K[Break Connection]
    J --> L[Register Client if New]
    L --> M[Queue Client Data]
    M --> F
    K --> N[Cleanup Client]
    E --> N
```

## Message Flow

The server handles the following message flow:

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant ClientChecks
    participant Redis
    participant PipelineManager
  
    Client->>Server: WebSocket Connection
    Server->>ClientChecks: Validate Client
    ClientChecks->>Server: Validation Result
  
    alt Client Valid
        Server->>Redis: Update Client Status
        Client->>Server: Send Image Data
        Server->>Server: Register Client
        Server->>PipelineManager: Queue for Processing
        PipelineManager->>Server: Processing Result
        Server->>Client: Send Response
    else Client Invalid
        Server->>Client: Error Message
        Server->>Server: Close Connection
    end
```

## Error Handling

The server implements comprehensive error handling:

### Connection Errors

- **ConnectionClosed**: Graceful handling of client disconnections
- **ConnectionClosedOK**: Normal connection closure
- **Timeout**: Client timeout handling with configurable limits

### Client Validation Errors

- **Blocked Client**: Immediate disconnection with error message
- **Paused Client**: Warning message with continued monitoring
- **Unavailable Client**: Error response with connection closure

### System Errors

- **System Full**: Rejection of new connections when capacity reached
- **GPU Full**: Resource management when GPU memory exhausted

## Configuration

### Environment Variables

- `MaxClientPerPipeline`: Maximum clients per processing pipeline
- `MaxPipeline`: Maximum number of processing pipelines
- `NAMESPACE`: System namespace identifier

### Redis Keys

- `SYSTEM_FULL`: System capacity status
- `GPUs_FULL`: GPU resource availability
- `Clients_status`: Client state management

## Performance Considerations

### Concurrency

- **Asynchronous Processing**: All I/O operations are asynchronous
- **Semaphore Control**: Limits concurrent operations
- **Event-driven Architecture**: Efficient resource utilization

### Memory Management

- **Client Cleanup**: Automatic cleanup of disconnected clients
- **Resource Monitoring**: GPU and system resource tracking
- **Connection Pooling**: Efficient WebSocket connection management

## Security Features

### Authentication

- **Client Validation**: Database-based client verification
- **Reference Image Check**: Validates client reference images
- **Session Management**: Secure client session handling

### Access Control

- **Blocking**: Permanent client blocking capability
- **Pausing**: Temporary client suspension
- **Rate Limiting**: Connection rate limiting through semaphore

## Usage Example

```python
# Initialize server
server = Server(
    process_name="Server",
    serve_ip="0.0.0.0",
    server_port=8000,
    logger="Server_logs"
)

# Start server process
server.Start_process()

# Monitor server
while server.is_alive():
    time.sleep(1)
```

## Dependencies

- **websockets**: WebSocket server implementation
- **asyncio**: Asynchronous I/O operations
- **redis**: Client state management
- **cv2**: Image processing
- **json**: Message serialization
- **common_utilities**: Logging and base process functionality

## Testing

The server can be tested using WebSocket clients that send properly formatted JSON messages with user images.
