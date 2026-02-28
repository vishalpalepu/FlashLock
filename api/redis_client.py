import os
import redis

from django.conf import settings

pool = redis.BlockingConnectionPool(host='localhost', port=6379, decode_responses=True,max_connections=10, timeout=5)

redis_conn = redis.Redis(connection_pool=pool)

script_path = os.path.join(settings.BASE_DIR, 'api', 'scripts','inventory.lua')

with open(script_path, 'r') as f:
    lua_code = f.read()
    
execute_inventory_script = redis_conn.register_script(lua_code)

def attempt_purchase(user_id, item_id,timestamp):
    try:
        item_key = str(item_id)
        purchase_set_key = f"purchased:{item_id}"
        outbox_key = "orders_queue"
    
        result = execute_inventory_script(
            keys= [item_key,purchase_set_key,outbox_key],
            args = [user_id,timestamp]
        )
    
        return result
    except (redis.exceptions.RedisError, redis.exceptions.ConnectionError,TypeError) as e:
        print(f"Redis error: {str(e)}")
        return -2  # Indicate a Redis error occurred
    
