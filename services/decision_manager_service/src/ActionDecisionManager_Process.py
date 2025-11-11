#!/usr/bin/env python3.10
import asyncio
import traceback
from datetime import datetime, timezone
from typing import Optional
import cv2
import numpy as np
from common_utilities import Base_process, LOGGER, LOG_LEVEL, Async_RMQ, StorageClient
from utilities.Datatypes import Action, Reason
from .ActionDecisionManager import ActionDecisionManager


class ActionDecisionManager_Process(Base_process):
    def __init__(
        self,
        process_name: str = "ActionDecisionManager",
        process_arg: tuple = None,
        logger=None,
        storage_client: Optional[StorageClient] = None,
    ):
        super().__init__(process_name, process_arg)
        if isinstance(logger, str):
            self.logs = LOGGER(logger)
            self.logs.create_File_logger(
                f"{logger}", log_levels=["DEBUG", "ERROR", "CRITICAL", "WARNING"]
            )
            self.logs.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
        elif isinstance(logger, LOGGER):
            self.logs = logger
        else:
            self.logs = LOGGER(None)
        self._rmq = Async_RMQ(logger=self.logs)
        self.action_decision_manager = ActionDecisionManager()
        self.storage_client = storage_client
        if self.storage_client is None:
            raise ValueError(
                "storage_client must be provided for ActionDecisionManager_Process"
            )

    def _build_action_object_key(self, user_name: str, action_reason: dict) -> str:
        action_enum = Action(action_reason.get("action"))
        reason_enum = Reason(action_reason.get("reason"))
        action_name = action_enum.name.replace("ACTION_", "").capitalize()
        reason_name = reason_enum.name.replace("REASON_", "").capitalize()
        safe_user = (user_name or "unknown").replace(" ", "_").lower()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"actions/{action_name}/{safe_user}/{timestamp}__{action_name}__{reason_name}.jpg"

    def _load_frame(self, payload: dict) -> Optional[np.ndarray]:
        image = payload.get("user_image")
        if image is not None:
            return image
        object_key = payload.get("image_object_key")
        if not object_key:
            return None
        try:
            frame_bytes = self.storage_client.fetch_object(object_key)
        except Exception as exc:
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


    async def _publish_saved_action(
        self,
        payload: dict,
        action_result: dict,
        detection_type: str,
        *,
        capture_image: bool = True,
    ) -> None:
        user_name = payload.get("client_name")
        action_image = None
        action_object_key = None
        if capture_image:
            action_image = await asyncio.to_thread(
                self._prepare_action_image, payload, detection_type
            )
            action_object_key = (
                self._build_action_object_key(user_name, action_result)
                if action_image is not None
                else None
            )
        saved_action_data = {
            "user_name": user_name,
            "Action_Reason": {
                "action": action_result.get("action"),
                "reason": action_result.get("reason"),
            },
            "Action_image": action_image,
            "action_image_object_key": action_object_key,
            "action_image_bucket": self.storage_client.frames_bucket
            if action_object_key
            else None,
            "detection_type": detection_type,
            "image_object_key": payload.get("image_object_key"),
            "image_bucket": payload.get("image_bucket"),
            "image_content_type": payload.get("image_content_type"),
            "storage_provider": payload.get("storage_provider"),
            "recognition_metric_value": payload.get("recognition_metric_value"),
            "recognition_threshold": payload.get("recognition_threshold"),
        }
        await self._rmq.publish_data(saved_action_data, "saved_actions")

    async def _process_face_payload(self, payload: dict):
        try:
            action_result = await asyncio.to_thread(
                self.action_decision_manager.face_decide_action, payload
            )
            await self._rmq.publish_data(action_result, "actions")
            await self._publish_saved_action(
                payload,
                action_result,
                "face",
                capture_image=action_result.get("action")
                != self.action_decision_manager.default_action["action"],
            )
        except Exception as exc:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error processing face pipeline results: {exc}\n{track_error}",
                LOG_LEVEL.ERROR,
            )
  

    async def _process_phone_payload(self, payload: dict):
        try:
            found_phone, action_result = await asyncio.to_thread(
                self.action_decision_manager.phone_decide_action, payload
            )
            if found_phone:
                await self._rmq.publish_data(action_result, "actions")
            await self._publish_saved_action(
                payload,
                action_result,
                "phone",
                capture_image=found_phone,
            )
        except Exception as exc:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error processing phone pipeline results: {exc}\n{track_error}",
                LOG_LEVEL.ERROR,
            )

    def _register_consumers(self):
        @self._rmq.consume_messages(queue_name="face_pipeline_results")
        async def face_handler(payload):
            await self._process_face_payload(payload)

        @self._rmq.consume_messages(queue_name="phone_pipeline_results")
        async def phone_handler(payload):
            await self._process_phone_payload(payload)

    async def _declare_rmq(self):
        await self._rmq.create_producer()
        await self._rmq.create_consumer(
            exchange_name="pipeline_results", exchange_type="direct"
        )
        await self._rmq.create_queues("actions")
        await self._rmq.create_queues("saved_actions")
        await self._rmq.create_queues(
            "face_pipeline_results",
            routing_key="face_results",
            exchange_name="pipeline_results",
        )
        await self._rmq.create_queues(
            "phone_pipeline_results",
            routing_key="phone_results",
            exchange_name="pipeline_results",
        )

    async def _run_async(self):
        await self._declare_rmq()
        self._register_consumers()
        try:
            await self._rmq.start_consuming()
        finally:
            await self._rmq.close()

    def run(self):
        asyncio.run(self._run_async())
