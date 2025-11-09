#!/usr/bin/env python3.10
import importlib.util
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock


def _load_log_maintenance_module():
    module_path = Path(__file__).resolve().parents[2] / "common_utilities" / "log_maintenance.py"
    spec = importlib.util.spec_from_file_location("log_maintenance", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LogMaintenanceWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log_maintenance = _load_log_maintenance_module()

    @staticmethod
    def _load_common_module(module_name: str):
        package_name = "common_utilities"
        if package_name not in sys.modules:
            pkg = types.ModuleType(package_name)
            pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "common_utilities")]
            sys.modules[package_name] = pkg

        full_name = f"{package_name}.{module_name}"
        if full_name in sys.modules:
            return sys.modules[full_name]

        module_path = Path(__file__).resolve().parents[2] / "common_utilities"
        module_path = module_path / (module_name.replace(".", "/") + ".py")
        spec = importlib.util.spec_from_file_location(full_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[full_name] = module
        spec.loader.exec_module(module)
        return module

    def test_old_logs_are_removed_and_directories_pruned(self):
        module = self.log_maintenance
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            nested = tmp_path / "namespace" / "logs"
            nested.mkdir(parents=True, exist_ok=True)
            old_log = nested / "stale.log"
            old_log.write_text("stale")
            stale_time = time.time() - 5
            os.utime(old_log, (stale_time, stale_time))

            worker = module.start_log_cleanup_worker(
                str(tmp_path),
                max_age_hours=1 / 3600,  # roughly 1 second retention
                sweep_interval_seconds=1,
            )
            self.assertIsNotNone(worker)

            for _ in range(20):
                if not old_log.exists():
                    break
                time.sleep(0.2)

            self.assertFalse(old_log.exists(), "stale log should be deleted by the cleanup worker")
            # Allow the worker to prune empty directories created for namespace segregation.
            time.sleep(0.5)
            self.assertFalse(nested.exists(), "empty namespace directory should be removed after log deletion")

    def test_helper_uses_paths_and_namespace_to_resolve_log_root(self):
        module = self.log_maintenance
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            nested = tmp_path / "tenant" / "logs"
            nested.mkdir(parents=True, exist_ok=True)
            old_log = nested / "stale.log"
            old_log.write_text("stale")
            stale_time = time.time() - 5
            os.utime(old_log, (stale_time, stale_time))

            worker = module.start_log_cleanup_worker_from_paths(
                {"APPLICATION_ROOT_PATH": tmp_path},
                namespace="tenant",
                max_age_hours=1 / 3600,
                sweep_interval_seconds=1,
            )
            self.assertIsNotNone(worker)

            for _ in range(20):
                if not old_log.exists():
                    break
                time.sleep(0.2)

            self.assertFalse(
                old_log.exists(),
                "stale log should be deleted by cleanup worker configured via helper",
            )
            time.sleep(0.5)
            self.assertFalse(
                nested.exists(),
                "helper should allow the worker to prune empty namespace directory",
            )

    def test_permission_error_results_in_truncated_log(self):
        module = self.log_maintenance
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            nested = tmp_path / "namespace" / "logs"
            nested.mkdir(parents=True, exist_ok=True)
            stubborn_log = nested / "locked.log"
            stubborn_log.write_text("stale")
            stale_time = time.time() - 5
            os.utime(stubborn_log, (stale_time, stale_time))

            with mock.patch("pathlib.Path.unlink", side_effect=PermissionError):
                worker = module.start_log_cleanup_worker(
                    str(tmp_path),
                    max_age_hours=1 / 3600,
                    sweep_interval_seconds=1,
                )
                self.assertIsNotNone(worker)

                for _ in range(20):
                    if stubborn_log.exists() and stubborn_log.stat().st_size == 0:
                        break
                    time.sleep(0.2)
                else:
                    self.fail("log file should have been truncated when deletion was denied")

    def test_logger_recreates_log_file_after_removal(self):
        files_handler = self._load_common_module("files_handler")
        logger_module = self._load_common_module("logger")

        if hasattr(files_handler.get_paths, "cache_clear"):
            files_handler.get_paths.cache_clear()
        if hasattr(files_handler.get_namespace, "cache_clear"):
            files_handler.get_namespace.cache_clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            files_handler.set_paths(
                {
                    "APPLICATION_ROOT_PATH": tmp_path,
                    "LOGS_ROOT_PATH": tmp_path,
                }
            )
            files_handler.set_namespace(None)

            service_logger = logger_module.LOGGER("TestLogger")
            service_logger.create_File_logger(
                "TestLogger",
                log_levels=["DEBUG", "INFO", "ERROR", "CRITICAL", "WARNING"],
            )

            log_file = tmp_path / "logs" / "TestLogger.log"
            service_logger.write_logs("first message", logger_module.LOG_LEVEL.INFO)
            self.assertTrue(log_file.exists(), "logger should create log file on first write")

            log_file.unlink()
            service_logger.write_logs("second message", logger_module.LOG_LEVEL.INFO)
            self.assertTrue(log_file.exists(), "logger should recreate log file after deletion")
            contents = log_file.read_text()
            self.assertIn("second message", contents)

            for handler in list(service_logger._LOGGER__logger.handlers):  # cleanup handler resources
                handler.close()
                service_logger._LOGGER__logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
