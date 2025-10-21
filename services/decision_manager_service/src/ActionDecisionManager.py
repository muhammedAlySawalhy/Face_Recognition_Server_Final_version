#!/usr/bin/env python3.10
import cv2
from typing import Dict
# from common_utilities import LOGGER
from utilities.Datatypes import Action, Reason
import time


class ActionDecisionManager:
    def __init__(self):
        self.default_action={"action": Action.NO_ACTION.value, "reason": Reason.EMPTY_REASON.value}
    #//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __face_decide_action(self, models_results: Dict[str, str]) -> Dict[str, str]:
        # Initialize the action dictionary with default values
        __action = {"action": Action.NO_ACTION.value, "reason": Reason.EMPTY_REASON.value}
        face_bbox = models_results.get("face_bbox")
        # Check if no face is detected
        if face_bbox is None:
            __action.update({"action": Action.ACTION_LOCK_SCREEN.value, "reason": Reason.REASON_NO_FACE.value})
            return __action
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
        image = models_results.get("user_image")  # Extract the face image if available
        x1, y1, x2, y2 = face_bbox
        # Check if the detected face is marked as a spoof
        if models_results.get("check_spoof"):
            if image is not None:
                cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 2)
            __action = {"action": Action.ACTION_SIGN_OUT.value, "reason": Reason.REASON_SPOOF_IMAGE.value}
            return __action
        # Check if the predicted username does not match the actual username
        if not models_results.get("check_client"):
            __action = {"action": Action.ACTION_LOCK_SCREEN.value, "reason": Reason.REASON_WRONG_USER.value}
            return __action
        return __action
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __phone_decide_action(self, models_results: Dict[str, str]) -> Dict[str, str]:
        __action = {"action": Action.NO_ACTION.value, "reason": Reason.EMPTY_REASON.value}
        image = models_results.get("user_image")  # Get the face image to draw on
        # Check if a phone is detected
        phone_bbox = models_results.get("phone_bbox")
        if phone_bbox is not None:
            x1, y1, x2, y2 = phone_bbox
            if image is not None:
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red box for phone
            # Update action to sign out due to phone detection
            __action = {"action": Action.ACTION_SIGN_OUT.value, "reason": Reason.REASON_PHONE_DETECTION.value}
        return __action
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def phone_decide_action(self,model_result):
        p__decide_action= self.__phone_decide_action(model_result)
        if p__decide_action["action"] != Action.NO_ACTION.value:
            p__decide_action['client_name']=model_result['client_name']
            p__decide_action['send_time']=model_result['send_time']
            p__decide_action['finish_time']=time.strftime("%H-%M-%S",time.localtime())
            return   (True,p__decide_action)
        else:
            return (False,None)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def face_decide_action(self,model_result):
        f__decide_action= self.__face_decide_action(model_result)
        f__decide_action['client_name']=model_result['client_name']
        f__decide_action['send_time']=model_result['send_time']
        f__decide_action['finish_time']=time.strftime("%H-%M-%S",time.localtime())
        return f__decide_action
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def decide_action(self,models_results):
        found_action,p__decide_action=self.phone_decide_action(models_results)
        if(found_action):
            return p__decide_action
        else:
            return self.face_decide_action(models_results)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
