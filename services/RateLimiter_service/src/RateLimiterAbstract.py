from abc import ABC, abstractmethod

class AbstractRatelimiter(ABC):
    @abstractmethod
    def allowRequest(self,client_id:str)->bool:
        pass