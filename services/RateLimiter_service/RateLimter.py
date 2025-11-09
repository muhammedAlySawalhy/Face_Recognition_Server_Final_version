from src.RateLimiterManager import RateLimiterManager
from src.RateLimiter import RateLimiter
client_id = "Aly"
maxClients = 1
windowsSize = 2000
 

def main():
    config = {
            "max_clients": maxClients,
            "window_size_in_millis": windowsSize,
            "cleanup_interval_in_millis": windowsSize,
    }
    manager = RateLimiterManager.get_instance(RateLimiter, config)
    try:
        manager.allow_request(client_id)
    finally:
        manager.shutdown()
if __name__ == "__main__":
    main()
