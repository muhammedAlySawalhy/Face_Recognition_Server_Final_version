#!/usr/bin/env python3.10

import os
import time
import traceback
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np

from common_utilities import Base_process, LOGGER, LOG_LEVEL, Sync_RMQ, StorageClient
from utilities.Datatypes import Action, Reason
from .ActionDecisionManager import ActionDecisionManager


class ActionDecisionManager_Process(Base_process):
    """
    Standalone ActionDecisionManager process that consumes separate face and phone pipeline results
    and produces actions and saved_actions for logging.
    """

    def __init__(
        self,
        process_name: str = "ActionDecisionManager",
        process_arg: tuple = None,
        logger = None,
        storage_client: Optional[StorageClient] = None,
    ):
        """
        Initialize the ActionDecisionManager process.

        Args:
            process_name (str): Name of the process
            process_arg (tuple): Additional arguments for the base process
            logger: Logger instance or string for logging
        """
        super().__init__(process_name, process_arg)
        
        # Initialize logging
        if isinstance(logger, str):
            self.logs = LOGGER(logger)
            self.logs.create_File_logger(f"{logger}", log_levels=["DEBUG", "ERROR", "CRITICAL", "WARNING"])
            self.logs.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
        elif isinstance(logger, LOGGER):
            self.logs = logger
        else:
            self.logs = LOGGER(None)
        
        self.logs.write_logs(f"Initializing ActionDecisionManager_Process: {process_name}", LOG_LEVEL.DEBUG)
        
        # Initialize RMQ handler
        self.__rmq_handler = Sync_RMQ( logger=self.logs)
        # Configure RMQ for better memory management
        self.__rmq_handler.max_retries = 3
        self.__rmq_handler.retry_delay = 1
        self.__rmq_handler.prefetch_count = 1  # Limit concurrent processing
        self.__rmq_handler.durable_queues = True  # Ensure queue durability
        self.__rmq_handler.persistent_messages = False  # Don't persist messages to reduce disk usage
        
        # Initialize ActionDecisionManager
        self.action_decision_manager = ActionDecisionManager()
        self.storage_client = storage_client
        if self.storage_client is None:
            raise ValueError("storage_client must be provided for ActionDecisionManager_Process")

    def _load_frame(self, payload: dict) -> Optional[np.ndarray]:
        """Retrieve the current frame either from payload or object storage."""
        image = payload.get("user_image")
        if image is not None:
            return image

        object_key = payload.get("image_object_key")
        if not object_key:
            return None

        try:
            frame_bytes = self.storage_client.fetch_object(object_key)
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"Failed to fetch frame '{object_key}' from storage: {exc}",
                LOG_LEVEL.ERROR,
            )
            return None

        array = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            self.logs.write_logs(
                f"Unable to decode frame '{object_key}' from storage",
                LOG_LEVEL.ERROR,
            )
        return frame

    def _prepare_action_image(self, payload: dict, detection_type: str) -> Optional[np.ndarray]:
        """Fetch and annotate the frame for saved actions."""
        frame = self._load_frame(payload)
        if frame is None:
            return None

        annotated = frame.copy()
        if detection_type == "face":
            bbox = payload.get("face_bbox")
            if bbox:
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        elif detection_type == "phone":
            bbox = payload.get("phone_bbox")
            if bbox:
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
        return annotated

    def _build_action_object_key(self, user_name: str, action_reason: dict) -> str:
        """Generate deterministic object storage key for saved actions."""
        action_enum = Action(action_reason.get("action"))
        reason_enum = Reason(action_reason.get("reason"))

        action_name = action_enum.name.replace("ACTION_", "").capitalize()
        reason_name = reason_enum.name.replace("REASON_", "").capitalize()
        safe_user = (user_name or "unknown").replace(" ", "_").lower()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

        return f"actions/{action_name}/{safe_user}/{timestamp}__{action_name}__{reason_name}.jpg"

    def _cleanup_frame(self, payload: dict) -> None:
        """Remove the original frame from storage once processing is complete."""
        object_key = payload.get("image_object_key")
        if not object_key or not self.storage_client:
            return
        try:
            self.storage_client.delete_object(object_key)
            self.logs.write_logs(
                f"Cleaned up processed frame '{object_key}' from storage",
                LOG_LEVEL.DEBUG,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"Failed to delete processed frame '{object_key}': {exc}",
                LOG_LEVEL.WARNING,
            )

    def setup_rmq_connections(self):
        """Setup RabbitMQ connections and queues"""
        retries = int(os.getenv("RMQ_SETUP_RETRIES", "10"))
        delay = float(os.getenv("RMQ_SETUP_DELAY_SECONDS", "3"))
        for attempt in range(1, retries + 1):
            try:
                # Create producer for outgoing messages
                self.__rmq_handler.create_producer()

                # Create consumer for face and phone pipeline results
                self.__rmq_handler.create_consumer(
                    exchange_name="pipeline_results", exchange_type="direct"
                )

                # Create queues
                self.__rmq_handler.create_queues("actions")  # For action decisions
                self.__rmq_handler.create_queues("saved_actions")  # For action logging
                self.__rmq_handler.create_queues(
                    "face_pipeline_results",
                    routing_key="face_results",
                    exchange_name="pipeline_results",
                )
                self.__rmq_handler.create_queues(
                    "phone_pipeline_results",
                    routing_key="phone_results",
                    exchange_name="pipeline_results",
                )

                self.logs.write_logs("RMQ connections setup completed", LOG_LEVEL.DEBUG)
                self.logs.write_logs(
                    "Created queues: actions, saved_actions, face_pipeline_results, phone_pipeline_results",
                    LOG_LEVEL.INFO,
                )
                return
            except Exception as e:
                self.logs.write_logs(
                    f"Error setting up RMQ connections (attempt {attempt}/{retries}): {e}",
                    LOG_LEVEL.WARNING if attempt < retries else LOG_LEVEL.ERROR,
                )
                if attempt >= retries:
                    raise
                time.sleep(delay)

    def setup_consumers(self):
        """Setup RMQ consumers for face and phone pipeline results"""
        self.logs.write_logs("Setting up RMQ consumers for face and phone pipeline results", LOG_LEVEL.DEBUG)
        
        @self.__rmq_handler.consume_messages(queue_name="face_pipeline_results")
        def process_face_pipeline_results(payload):
            try:
                self.logs.write_logs(f"Processing face pipeline results for client: {payload.get('client_name', 'unknown')}", LOG_LEVEL.DEBUG)
                
                # Use existing ActionDecisionManager face decision logic
                action_result = self.action_decision_manager.face_decide_action(payload)
                
                # Publish lightweight action result to actions queue
                self.__rmq_handler.publish_data(action_result, "actions")
                self.logs.write_logs(f"Action decision for face detection: {action_result}", LOG_LEVEL.DEBUG)
                
                # If action needs logging (not NO_ACTION), publish to saved_actions queue
                if action_result.get("action") != self.action_decision_manager.default_action["action"]:
                    user_name = payload.get("client_name")
                    action_image = self._prepare_action_image(payload, detection_type="face")
                    action_object_key = (
                        self._build_action_object_key(user_name, action_result)
                        if action_image is not None
                        else None
                    )
                    saved_action_data = {
                        "user_name": user_name,
                        "Action_Reason": {
                            "action": action_result.get("action"),
                            "reason": action_result.get("reason")
                        },
                        "Action_image": action_image,
                        "action_image_object_key": action_object_key,
                        "action_image_bucket": self.storage_client.frames_bucket if action_object_key else None,
                        "image_object_key": payload.get("image_object_key"),
                        "image_bucket": payload.get("image_bucket"),
                        "image_content_type": payload.get("image_content_type"),
                        "storage_provider": payload.get("storage_provider"),
                    }
                    self.__rmq_handler.publish_data(saved_action_data, "saved_actions")
                    self.logs.write_logs(f"Published action for saving: {action_result.get('action')}", LOG_LEVEL.DEBUG)
                    
            except Exception as e:
                track_error = traceback.format_exc()
                self.logs.write_logs(f"Error processing face pipeline results: {e}\n{track_error}", LOG_LEVEL.ERROR)
            finally:
                self._cleanup_frame(payload)

        @self.__rmq_handler.consume_messages(queue_name="phone_pipeline_results")
        def process_phone_pipeline_results(payload):
            try:
                self.logs.write_logs(f"Processing phone pipeline results for client: {payload.get('client_name', 'unknown')}", LOG_LEVEL.DEBUG)
                
                # Use existing ActionDecisionManager phone decision logic
                found_phone, action_result = self.action_decision_manager.phone_decide_action(payload)
                if found_phone:
                    # Publish lightweight action result to actions queue
                    self.__rmq_handler.publish_data(action_result, "actions")
                    self.logs.write_logs(f"Action decision for phone detection: {action_result}", LOG_LEVEL.DEBUG)
                    
                    # Publish to saved_actions queue for logging
                    user_name = payload.get("client_name")
                    action_image = self._prepare_action_image(payload, detection_type="phone")
                    action_object_key = (
                        self._build_action_object_key(user_name, action_result)
                        if action_image is not None
                        else None
                    )
                    saved_action_data = {
                        "user_name": user_name,
                        "Action_Reason": {
                            "action": action_result.get("action"),
                            "reason": action_result.get("reason")
                        },
                        "Action_image": action_image,
                        "action_image_object_key": action_object_key,
                        "action_image_bucket": self.storage_client.frames_bucket if action_object_key else None,
                        "image_object_key": payload.get("image_object_key"),
                        "image_bucket": payload.get("image_bucket"),
                        "image_content_type": payload.get("image_content_type"),
                        "storage_provider": payload.get("storage_provider"),
                    }
                    self.__rmq_handler.publish_data(saved_action_data, "saved_actions")
                    self.logs.write_logs(f"Published action for saving: {action_result.get('action')}", LOG_LEVEL.DEBUG)
                    
            except Exception as e:
                track_error = traceback.format_exc()
                self.logs.write_logs(f"Error processing phone pipeline results: {e}\n{track_error}", LOG_LEVEL.ERROR)
            finally:
                self._cleanup_frame(payload)

    def run(self):
        """Main process loop"""
        try:
            self.logs.write_logs(f"Starting ActionDecisionManager Process with PID: {self.pid}", LOG_LEVEL.INFO)
            
            # Setup RMQ connections
            self.setup_rmq_connections()
            
            # Setup consumers
            self.setup_consumers()
            
            self.logs.write_logs("ActionDecisionManager process is ready and waiting for pipeline results", LOG_LEVEL.INFO)
            
            # Start consuming messages
            self.__rmq_handler.start_consuming()
            
        except Exception as e:
            track_error = traceback.format_exc()
            self.logs.write_logs(f"Error in ActionDecisionManager process: {e}\n{track_error}", LOG_LEVEL.ERROR)
        except KeyboardInterrupt:
            self.logs.write_logs("ActionDecisionManager process interrupted by user", LOG_LEVEL.INFO)
        finally:
            # Cleanup RMQ connections
            try:
                self.__rmq_handler.close()
                self.logs.write_logs("ActionDecisionManager process cleanup completed", LOG_LEVEL.INFO)
            except Exception as e:
                self.logs.write_logs(f"Error during cleanup: {e}", LOG_LEVEL.ERROR)


if __name__ == "__main__":
    # Test the ActionDecisionManager process
    decision_manager = ActionDecisionManager_Process(
        process_name="ActionDecisionManager",
        logger="ActionDecisionManager_logs"
    )
    
    try:
        decision_manager.Start_process()
        while True:
            time.sleep(1)
            if not decision_manager.is_alive():
                decision_manager.Start_process()
    except KeyboardInterrupt:
        decision_manager.Stop_process()
        decision_manager.Join_process()
