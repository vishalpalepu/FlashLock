import redis
import orjson
from .models import InventoryItem,Order
from django.db import transaction
from django.core.management.base import BaseCommand
from django.db.models import F

class Command(BaseCommand):
    help = 'Process outbox orders and update inventory'
    
    def handle(self,*args,**kwargs):
        redis_conn = redis.Redis(host = "localhost",port = 6379, decode_responses = True)
        outbox_key = "orders_queue"
        
        BATCH_SIZE = 50
        self.stdout.write("Worker started. Waiting for orders...")
        while True:
            _ , data = redis_conn.blpop(outbox_key)
            batch = [data]
            for _ in range(BATCH_SIZE - 1):
                item = redis_conn.lpop(outbox_key)
                if item:
                    batch.append(item)
                else:
                    break
                
                
            orders_to_create = item_deductions = {}
                
            for raw_data in batch:
                if raw_data:
                    try:
                        order_data = orjson.loads(raw_data)
                        user_id = order_data.get('user_id')
                        item_id = order_data.get('item_id')
                        if user_id is None or item_id is None:
                            continue
                        orders_to_create.append(Order(user_id = user_id,item_id = item_id))
                        item_deductions[item_id] += 1
                    except Exception as e:
                        self.stdout.write(f"Error processing order data: {str(e)}")
            
            if orders_to_create:
                try:
                    with transaction.atomic():
                        Order.objects.bulk_create(orders_to_create)
                    
                        for current_item_id , sold_count in item_deductions.items():
                            InventoryItem.objects.filter(id = current_item_id).update(stock_count = F('stock_count') - sold_count)
                    self.stdout.write(f"Processed batch of {len(orders_to_create)} orders")   
                except Exception as e:
                    self.stdout.write(f"Database error processing batch: {str(e)}")
                    
                                