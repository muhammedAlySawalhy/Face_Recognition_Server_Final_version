from pydantic import BaseModel
from typing import List

class KeysRequest(BaseModel):
    keys: List[str]
