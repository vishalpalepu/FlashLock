import os
import redis
import time

from django.conf import settings

pool = redis.BlockingConnectionPool(host='localhost', port=6379, decode_responses=True,max_connections=10, timeout=5)

redis_conn = redis.Redis(connection_pool=pool)

script_path = os.path.join(settings.BASE_DIR, 'api', 'scripts','inventory.lua')


with open(script_path, 'r') as f:
    lua_code = f.read()
    
execute_inventory_script = redis_conn.register_script(lua_code)

rate_limit_script_path = os.path.join(settings.BASE_DIR, 'api', 'scripts','rate_limiter.lua')

with open(rate_limit_script_path, 'r') as f:
    rate_limit_lua_code = f.read()
    
execute_rate_limit_script = redis_conn.register_script(rate_limit_lua_code)


def attempt_purchase(user_id, item_id,timestamp):
    try:
        item_key = str(item_id)
        purchase_set_key = f"purchased:{item_id}"
        outbox_key = "orders_queue"
        print(f"Attempting purchase for user {user_id} and item {item_id}")
        
        rate_limit_key = f"rate_limit:{user_id}" #change to IP in production
        capacity = 5
        refill_rate = 20  # Refill 10 tokens every refill_interval seconds
        refill_interval = 60  # Refill every 60 seconds
        now = time.time()
        
        allowed = execute_rate_limit_script(
            keys=[rate_limit_key],
            args = [capacity,refill_rate,refill_interval,now,1]
        )
        if(allowed == 0):
            return -3 # Indicate rate limit exceeded
        
        result = execute_inventory_script(
            keys= [item_key,purchase_set_key,outbox_key],
            args = [user_id,timestamp]
        )
    
        return result
    except (redis.exceptions.RedisError, redis.exceptions.ConnectionError,TypeError) as e:
        print(f"Redis error: {str(e)}")
        return -2  # Indicate a Redis error occurred
    
