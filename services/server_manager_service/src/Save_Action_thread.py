import os
import time
from typing import Dict, Optional
import cv2
from queue import Queue, Empty
from common_utilities import Base_Thread, get_root_path, StorageClient
from utilities import Action, Reason


class SaveAction_Thread(Base_Thread):
    def __init__(self, thread_name: str, storage_client: Optional[StorageClient] = None):
        super().__init__(thread_name=thread_name)
        self.save_action_queue: Queue[Dict[str, object]] = Queue()
        self.storage_client = storage_client
    
    def run(self):
        self.thread_started = True
        while not self.stop_thread:
            try:
                action_payload = self.save_action_queue.get(timeout=0.5)
            except Empty:
                continue
            self.save_User_Action(action_payload)
        self.thread_started = False

    def add_to_queue(
        self,
        user_name: str,
        Action_Reason: Dict[str, int],
        Action_image: Optional[cv2.typing.MatLike],
        object_key: Optional[str],
        bucket: Optional[str],
    ):
        self.save_action_queue.put(
            {
                "user_name": user_name,
                "action_reason": Action_Reason,
                "action_image": Action_image,
                "object_key": object_key,
                "bucket": bucket,
            }
        )

    def save_User_Action(self, payload: Dict[str, object]) -> None:
        user_name = payload.get("user_name") or "unknown"
        action_reason: Dict[str, int] = payload.get("action_reason", {})  # type: ignore[assignment]
        action_image = payload.get("action_image")

        if not action_reason or action_image is None:
            return

        action_key = payload.get("object_key")  # type: ignore[assignment]
        if not action_key:
            action_key = self._build_default_object_key(user_name, action_reason)

        success, buffer = cv2.imencode(".jpg", action_image)  # type: ignore[arg-type]
        if not success:
            return
        image_bytes = buffer.tobytes()

        if self.storage_client is not None:
            try:
                self.storage_client.store_object(
                    object_key=action_key,
                    data=image_bytes,
                    content_type="image/jpeg",
                )
                return
            except Exception:
                pass  # Fallback to filesystem if storage upload fails

        # Fallback to filesystem for legacy compatibility
        root_path = get_root_path(__file__, "main.py")
        action_user_dir = os.path.join(
            root_path,
            "Data",
            "Actions",
            Action(action_reason.get("action")).name.replace("ACTION_", "").capitalize(),
            user_name,
        )
        os.makedirs(action_user_dir, exist_ok=True)
        formatted_action_time = time.strftime("%d_%m_%Y-%H_%M", time.localtime())
        image_name = "___".join(
            [
                formatted_action_time,
                Action(action_reason.get("action")).name.replace("ACTION_", "").capitalize(),
                Reason(action_reason.get("reason")).name.replace("REASON_", "").capitalize(),
            ]
        )
        image_name_path = os.path.join(action_user_dir, image_name + ".jpg")
        with open(image_name_path, "wb") as outfile:
            outfile.write(image_bytes)

    def _build_default_object_key(self, user_name: str, action_reason: Dict[str, int]) -> str:
        action_enum = Action(action_reason.get("action"))
        reason_enum = Reason(action_reason.get("reason"))
        action_name = action_enum.name.replace("ACTION_", "").capitalize()
        reason_name = reason_enum.name.replace("REASON_", "").capitalize()
        safe_user = (user_name or "unknown").replace(" ", "_").lower()
        timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        return f"actions/{action_name}/{safe_user}/{timestamp}__{action_name}__{reason_name}.jpg"
