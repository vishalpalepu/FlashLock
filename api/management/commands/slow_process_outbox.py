import orjson
import redis
from ...models import InventoryItem, Order
from django.db import transaction
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help  = 'Process outbox orders and update inventory'
    
    def handle(self, *args, **kwargs):
        redis_conn = redis.Redis(host='localhost', port=6379, decode_responses=True)
        outbox_key = "orders_queue"
        while True:
            
            _ , data = redis_conn.blpop(outbox_key)
            if(data):
                try:
                    order_data = orjson.loads(data)
                    user_id = order_data.get('user_id')
                    item_id = order_data.get('item_id')
                    
                    if(user_id is None or item_id is None):
                        raise ValueError("Invalid order data, missing user_id or item_id")
                    with transaction.atomic():
                        # select_for_update locks the row until the transaction is complete, preventing race conditions
                        item = InventoryItem.objects.select_for_update().get(id=item_id)
                        if(item.stock_count > 0):
                            item.stock_count -= 1
                            item.save(update_fields=['stock_count'])
                            Order.objects.create(user_id=user_id, item_id=item_id)
                            print(f"Processed order for user {user_id} and item {item_id}")
                        else:
                            print(f"Not enough stock for item {item_id} to process order for user {user_id}")
                except InventoryItem.DoesNotExist:
                    print(f"Item with id {item_id} does not exist, cannot process order for user {user_id}")
                except Exception as e:
                    print(f"Error processing order for user {user_id} and item {item_id}: {str(e)}")
                
                    
                        