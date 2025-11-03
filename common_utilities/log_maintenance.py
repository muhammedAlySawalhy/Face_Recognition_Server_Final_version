#!/usr/bin/env python3.10
from __future__ import annotations
import os
import threading
import time
from pathlib import Path
from typing import Mapping, Optional, Union

DEFAULT_SWEEP_INTERVAL_SECONDS = 30 * 60  # 30 minutes by default


def _coerce_positive_int(value: Optional[str], fallback: int) -> int:
    if value is None:
        return fallback
    try:
        coerced = int(float(value))
    except (TypeError, ValueError):
        return fallback
    return max(1, coerced)


PathInput = Union[str, Path]


def _prune_log_file(file_path: Path) -> bool:
    """
    Attempt to remove a log file. When the operating system prevents deletion
    (notably on Windows when another process keeps the file handle open), fall
    back to truncating the file so the disk usage is reclaimed on the next write.

    Returns ``True`` when the file entry was removed or truncated successfully,
    ``False`` otherwise.
    """

    try:
        file_path.unlink(missing_ok=True)
        if not file_path.exists():
            return True
    except FileNotFoundError:
        return True
    except PermissionError:
        pass
    except OSError:
        return False

    try:
        with file_path.open("wb"):
            pass
        return True
    except OSError:
        return False


def start_log_cleanup_worker(
    log_root: str,
    max_age_hours: Optional[float] = None,
    sweep_interval_seconds: Optional[int] = None,
) -> Optional[threading.Thread]:
    """
    Spawn a background worker that prunes ``*.log`` files underneath ``log_root``.

    The worker honours two environment variables when explicit arguments are not
    provided:
      * LOG_CLEANUP_MAX_AGE_HOURS      -> retention window (hours)
      * LOG_CLEANUP_SWEEP_SECONDS      -> sleep interval between sweeps

    Returns the thread instance, or ``None`` when cleanup is disabled.
    """

    env_max_age = os.getenv("LOG_CLEANUP_MAX_AGE_HOURS")
    if max_age_hours is None:
        try:
            max_age_hours = float(env_max_age) if env_max_age is not None else 3.0
        except ValueError:
            max_age_hours = 3.0
    else:
        try:
            max_age_hours = float(max_age_hours)
        except (TypeError, ValueError):
            max_age_hours = 0.5

    if max_age_hours <= 0:
        return None

    retention_seconds = max(1, int(max_age_hours * 3600))

    env_sweep = os.getenv("LOG_CLEANUP_SWEEP_SECONDS")
    if sweep_interval_seconds is None:
        sweep_interval_seconds = _coerce_positive_int(
            env_sweep,
            min(retention_seconds, DEFAULT_SWEEP_INTERVAL_SECONDS),
        )
    else:
        sweep_interval_seconds = max(1, int(sweep_interval_seconds))

    log_path = Path(log_root).expanduser().resolve()
    os.makedirs(log_path, exist_ok=True)

    def _cleanup_loop() -> None:
        while True:
            cutoff = time.time() - retention_seconds
            removed_any = False
            for file_path in log_path.rglob("*.log"):
                try:
                    if file_path.stat().st_mtime < cutoff:
                        if _prune_log_file(file_path):
                            removed_any = True
                except (FileNotFoundError, PermissionError):
                    continue
                except Exception:
                    continue

            if removed_any:
                # Drop empty directories created for per-namespace log segregation.
                for candidate in sorted(log_path.rglob("*"), reverse=True):
                    if not candidate.is_dir():
                        continue
                    try:
                        next(candidate.iterdir())
                    except (StopIteration, FileNotFoundError):
                        try:
                            candidate.rmdir()
                        except OSError:
                            continue
                    except Exception:
                        continue

                # Remove the log root itself (and its namespace container) when now empty.
                for candidate in (log_path, log_path.parent):
                    if not candidate.exists() or not candidate.is_dir():
                        continue
                    try:
                        next(candidate.iterdir())
                    except (StopIteration, FileNotFoundError):
                        try:
                            candidate.rmdir()
                        except OSError:
                            continue
                    except Exception:
                        continue

            time.sleep(sweep_interval_seconds)

    thread = threading.Thread(
        target=_cleanup_loop,
        name="log_cleanup_worker",
        daemon=True,
    )
    thread.start()
    return thread


def start_log_cleanup_worker_from_paths(
    paths: Mapping[str, PathInput],
    *,
    namespace: Optional[str] = None,
    log_subdir: str = "logs",
    max_age_hours: Optional[float] = None,
    sweep_interval_seconds: Optional[int] = None,
) -> Optional[threading.Thread]:
    """Resolve the log directory from an application path mapping and start the cleanup worker.

    Parameters
    ----------
    paths:
        Mapping populated via ``set_paths`` during service initialisation. The function looks for
        ``LOGS_ROOT_PATH`` first and falls back to ``APPLICATION_ROOT_PATH`` when missing.
    namespace:
        Optional namespace injected by ``set_namespace``. When provided the namespace is inserted
        between the logs root and the final ``log_subdir``.
    log_subdir:
        Final segment appended to the log root that holds individual service logs. Defaults to
        ``"logs"`` to match existing on-disk layout.
    max_age_hours / sweep_interval_seconds:
        Optional overrides passed through to :func:`start_log_cleanup_worker`.

    Returns
    -------
    threading.Thread | None
        The worker thread instance when cleanup is active, otherwise ``None``.
    """

    base_path_value = paths.get("LOGS_ROOT_PATH") or paths.get("APPLICATION_ROOT_PATH")
    if base_path_value is None:
        return None

    candidate_path = Path(base_path_value).expanduser().resolve()
    if namespace:
        candidate_path = candidate_path / namespace
    if log_subdir:
        candidate_path = candidate_path / log_subdir

    return start_log_cleanup_worker(
        str(candidate_path),
        max_age_hours=max_age_hours,
        sweep_interval_seconds=sweep_interval_seconds,
    )
