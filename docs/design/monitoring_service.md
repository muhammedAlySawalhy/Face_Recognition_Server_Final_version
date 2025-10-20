# Monitoring Service Design

## 1. Context & Goals
- **Current system**: Gateway accepts WebSocket clients, pushes payloads to RabbitMQ. Pipeline workers consume tasks, publish results, and Server Manager/Redis track client state. Logs are the primary source of operational insight today.
- **Pain point**: Operators lack a consolidated view of connected clients, resource health (CPU/Mem/GPU), processing throughput, and action outcomes (pause/block/deactivate queues).
- **Goal**: Introduce a dedicated monitoring service that aggregates runtime metrics and state, exposes APIs/feeds for GUI dashboards, and raises alerts for abnormal conditions.

### 1.1 Functional Requirements
1. Track active clients (per gateway, per pipeline worker), pause/block/deactivation states, and action queues.
2. Report system utilisation: CPU, memory, disk, GPU (per device), network IO.
3. Collect pipeline processing stats: request counts, latency, success/failure, backlog depth.
4. Surface history of recent actions (e.g. saved actions queue, blocked clients changes).
5. Provide REST endpoints and an optional WebSocket push channel for the GUI.
6. Persist short-term history (e.g. last 60 minutes) for trend visualisation.

### 1.2 Non-Functional Requirements
- Lightweight footprint (<200 MB RAM).
- Collect metrics at configurable intervals (default 5 seconds).
- Resilient to individual data source failures (degraded mode with warnings).
- Extensible to additional metrics without redesign.
- Remains read-only; should not mutate existing workflow data.

## 2. Observability Targets & Data Sources
| Concern | Data Source | Access Pattern |
|---------|-------------|----------------|
| Connected clients | Redis `Clients_status`, `deactivate_clients`, `blocked_clients` | Poll Redis via existing `RedisHandler` |
| Gateway sessions | Gateway emits heartbeat events on new queue (`monitoring.gateway_events`) | Consume from RabbitMQ |
| Pipeline throughput | Subscribe to `face_pipeline_results`, `phone_pipeline_results`, measure latency | RabbitMQ consumer |
| Action outcomes | Server Manager publishes saved actions (`saved_actions`) | RabbitMQ consumer |
| Hardware metrics | Host OS via `psutil`, `pynvml` | Local polling |
| Storage usage | MinIO stats (via REST) | Optional HTTP requests |

## 3. High-level Architecture
```
 +----------------------+        +----------------------+
 |  Gateway / Workers   |        |   Server Manager      |
 |                      |        |                      |
 |  ├─ pushes RMQ msgs  |        |  ├─ Redis updates     |
 +----------+-----------+        +----------+-----------+
            |                               |
            v                               v
      RabbitMQ Exchanges              Redis Datastore
            |                               |
            +---------------+---------------+
                            |
                            v
                +-------------------------+
                | Monitoring Service      |
                |-------------------------|
                | Collectors (Strategy)   |
                |  - RMQCollector         |
                |  - RedisCollector       |
                |  - SystemCollector      |
                |  - StorageCollector     |
                | Aggregator (Observer)   |
                | API Gateway (FastAPI)   |
                +-------------------------+
                            |
                REST / WS endpoints, Prometheus scrape
```

### Key Components
1. **Collector Interfaces** (`IMetricCollector`): Pluggable strategy classes, each responsible for fetching a metric bundle. Implemented as asyncio tasks with structured error reporting.
2. **Aggregation Layer** (`MetricRegistry`): Maintains latest snapshot and time series buffers (ring buffers). Implements Observer pattern—collectors push updates which trigger downstream notifications (API cache, WebSocket broadcast).
3. **API Layer**: FastAPI service exposing:
   - `/metrics/system`, `/metrics/pipelines`, `/metrics/clients`
   - `/healthz`, `/readyz`
   - WebSocket `/ws/metrics` (optional real-time feed)
   - `/prometheus` endpoint exposing counters using `prometheus_client`.
4. **Alert Engine** (Phase 2): Rule-based evaluator on aggregated data to raise warnings (e.g. GPU >90%, queue backlog > N).
5. **Persistence**: In-memory ring buffer for short-term history. Optional Redis stream for persistence beyond process lifetime (Phase 3).

### Technology Choices
- **Language**: Python 3.10 (consistent with existing services).
- **Framework**: FastAPI + Uvicorn for async APIs.
- **Metrics**: `prometheus_client` for integration with Prometheus/Grafana.
- **System Stats**: `psutil`, `gpustat`/`nvidia-ml-py3`.
- **Messaging**: Existing `common_utilities.Sync_RMQ` and `RedisHandler` for consistency.
- **Configuration**: Environment variables via `pydantic-settings`.

## 4. Detailed Component Design
### 4.1 Collectors
- `BaseCollector`: defines `name`, `interval`, `start()/stop()` coroutine, error handling.
- `RedisCollector`: Reads client status hashes/lists (`Clients_status`, `deactivate_clients`, `blocked_clients`), normalises into `ClientStateSnapshot`.
- `RMQCollector`: Consumes from RMQ queues with manual ack, records counts, latency (ingest vs process time stamp from payload). Uses durable queue/consumer tag for resilience.
- `SystemCollector`: Polls `psutil` for CPU %, load average, memory usage, disk usage, network rates; uses `pynvml` for GPU.
- `StorageCollector`: Queries MinIO health endpoints and enumerates buckets for availability and capacity snapshots.

### 4.2 Data Model
- `SystemMetrics`: cpu_percent, mem_percent, disk_percent, pod uptime.
- `GpuMetrics`: per device stats (utilisation, memory, temperature).
- `PipelineMetrics`: counts, avg latency, success/error ratio per pipeline ID.
- `ClientStateSnapshot`: {active_clients, paused_clients, blocked_clients, deactivated_clients}.
- `ActionMetrics`: last N actions with timestamp and outcome.
- Data classes built with `pydantic.BaseModel` for validation and JSON serialization.

### 4.3 Aggregation & Storage
- `MetricRegistry` stores latest snapshot plus time-series (`collections.deque(maxlen=n)`).
- Exposes subscription hooks for API layer; when collectors push data, registry notifies watchers (Observer pattern).
- `TimeSeriesRepository` handles ring buffer updates with timestamps to support trend charts.

### 4.4 API & Integrations
- REST endpoints deliver both latest snapshot and optional windowed aggregates.
- WebSocket stream pushes differential updates for UI dashboards.
- Prometheus handler exports counters/gauges: `fr_gateway_client_count`, `fr_pipeline_latency_seconds`, etc.
- Future integration: push updates to existing GUI via RMQ or direct HTTP fetch.

### 4.5 Resilience & Error Handling
- Each collector runs in dedicated asyncio task with jittered scheduling to avoid thundering herd.
- Failures recorded in registry (`collector_status`) and surfaced via `/healthz`.
- Use circuit-breaker style backoff on persistent failures (e.g. RMQ unreachable).

## 5. Deployment Considerations
- New Docker image `fr-server-monitoring_service`.
- Environment:
- `MONITORING_RMQ_URL`
- `MONITORING_REDIS_HOST`
- `MONITORING_REDIS_DB`
- `MONITORING_POLL_INTERVAL` (seconds)
- `MONITORING_HISTORY_WINDOW` (minutes)
- `MONITORING_GPU_ENABLED` (bool)
- `MONITORING_MINIO_ENDPOINT`
- `MONITORING_MINIO_ACCESS_KEY`
- `MONITORING_MINIO_SECRET_KEY`
- `MONITORING_MINIO_SECURE`
- `PROMETHEUS_ENABLED` (bool)
- Compose: attach to `rmq_network`, `redis_network`, `storage_network`, optional host PID namespace for system stats (or mount `/proc` read-only).
- RBAC: ensure service has read-only credentials for MinIO if storage metrics are enabled.

## 6. Implementation Roadmap
1. **Foundations**
   - Create `services/monitoring_service` scaffold (Dockerfile, requirements, FastAPI entry point).
   - Implement configuration loader, registry, and API skeleton.
   - Add service to `docker-compose_main.yaml` (behind feature flag env `ENABLE_MONITORING`).
2. **Collectors (Phase 1)**
   - `SystemCollector` (CPU/Mem/GPU) + `/metrics/system`.
   - `RedisCollector` for client states + `/metrics/clients`.
   - `StorageCollector` for MinIO health/bucket summaries + `/metrics/storage`.
   - Expose Prometheus metrics.
3. **Collectors (Phase 2)**
   - `RMQCollector` for pipeline throughput/latency.
   - `ActionCollector` for saved actions.
   - WebSocket streaming API and GUI integration.
4. **Alerting & Persistence (Phase 3)**
   - Rule engine with configurable thresholds.
   - Optional write-through to Redis stream or timeseries DB.
   - CLI or webhook integration for alerts.

### Definition of Done (Phase 1)
- Monitoring service container starts via compose and registers `/healthz`, `/metrics/system`, `/metrics/clients`, `/metrics/storage`.
- Metrics reflect actual test load (validate during Locust run).
- Documentation updated (`README`, service run script).

## 7. Risks & Mitigations
- **Host metrics accuracy in containers**: Use host PID namespace or privileged read-only mounts; alternatively run monitoring service on host.
- **RabbitMQ load**: Use separate queues with low prefetch; ensure monitoring consumers have `ack` to avoid interfering with processing.
- **GPU stats access**: Requires NVIDIA persistence daemon / `nvidia-smi` availability; gate behind configuration.
- **Data consistency**: Poll intervals may miss transient states. Mitigate by combining polling with event streams (gateway events queue).

## 8. Next Steps
1. Implement scaffold per roadmap.
2. Extend existing services to publish lightweight monitoring events (gateway heartbeats, pipeline timestamps).
3. Integrate GUI dashboard consuming new endpoints.
