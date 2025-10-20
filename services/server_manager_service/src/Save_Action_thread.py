import os
import time
from typing import Tuple,Dict
import cv2
from queue import Queue
from common_utilities import Base_Thread,get_root_path
from utilities import Action,Reason


class SaveAction_Thread(Base_Thread):
    def __init__(self,thread_name):
        super().__init__(thread_name=thread_name)
        self.save_action_queue:Queue[Tuple[str,Dict[str,int],cv2.typing.MatLike]]=Queue()
    
    def run(self):
        self.thread_started = True
        while(not self.stop_thread):
            tuple_action_data=self.save_action_queue.get()
            self.save_User_Action(user_name=tuple_action_data[0],Action_Reason=tuple_action_data[1],Action_image=tuple_action_data[2])
        self.thread_started = False

    def add_to_queue(self, user_name: str, Action_Reason: Dict[str, int], Action_image: cv2.typing.MatLike):
        self.save_action_queue.put((user_name, Action_Reason, Action_image))

    def save_User_Action(self,user_name:str,Action_Reason:Dict[str,int],Action_image:cv2.typing.MatLike)->None:
        root_path=get_root_path(__file__,"main.py")
        Action_name=Action_Reason['action']
        Reason_name=Action_Reason['reason']
        action_user_dir=os.path.join(root_path,"Data","Actions",Action(Action_name).name.replace("ACTION_", "").capitalize(),user_name)
        os.makedirs(action_user_dir,exist_ok=True)
        action_time = time.localtime() 
        formatted_action_time = time.strftime("%d_%m_%Y-%H_%M", action_time)
        image_name="___".join([formatted_action_time,Action(Action_name).name.replace("ACTION_", "").capitalize(),Reason(Reason_name).name.replace("REASON_", "").capitalize()])
        image_name_path=os.path.join(action_user_dir,image_name+".jpg")
        cv2.imwrite(image_name_path,Action_image)
