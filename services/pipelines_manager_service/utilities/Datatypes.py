#!/usr/bin/env python3.10
from enum import Enum
from common_utilities import RedisHandler

class Action(Enum):
    NO_ACTION = 0
    ACTION_LOCK_SCREEN = 1
    ACTION_SIGN_OUT = 2
    ACTION_WARNING = 3
    ACTION_ERROR = 4


class Reason(Enum):
    EMPTY_REASON = 0
    REASON_PHONE_DETECTION = 1
    REASON_CABLE_REMOVE = 2
    REASON_CAMERA_NOT_ATTACH = 3
    REASON_CONNECT_TO_INTERNET = 4
    REASON_SPOOF_IMAGE = 5
    REASON_WRONG_USER = 6
    REASON_NO_FACE = 7
    REASON_BLOCKED_CLIENT = 8
    REASON_PAUSED_CLIENT = 9
    REASON_RESUME_CLIENT = 10
    REASON_CLIENT_NOT_AVAILABLE = 11
    REASON_RATE_LIMIT_EXCEEDED = 12

class ClientsData:
    def __init__(self, client_id, redis_store: RedisHandler):
        self.client_id = client_id
        self.redis = redis_store
        self.received_data_key = f"{client_id}:received_data"
        self.action_key = f"{client_id}:action"
        self.exists_key = f"{client_id}:exits"
        self.metadata_key = f"{client_id}:metadata"
        self.redis.set_value(self.exists_key, 1)

    def client_exists(self):
        return self.redis.redis.exists(self.exists_key) > 0

    def enqueue_received_data(self, data):
        self.redis.push_to_list(self.received_data_key, data)

    def dequeue_received_data(self):
        return self.redis.pop_from_list(self.received_data_key)

    def enqueue_action(self, action):
        self.redis.push_to_list(self.action_key, action)

    def dequeue_action(self):
        return self.redis.pop_from_list(self.action_key)

    def set_metadata(self, metadata):
        self.redis.set_dict(self.metadata_key, metadata)

    def get_metadata(self):
        return self.redis.get_dict(self.metadata_key)

    def deleteClient(self):
        self.redis.del_key(self.received_data_key)
        self.redis.del_key(self.action_key)
        self.redis.del_key(self.exists_key)
        self.redis.del_key(self.metadata_key)
