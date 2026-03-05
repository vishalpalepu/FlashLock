import redis
import orjson
from ...models import InventoryItem,Order
from django.db import transaction
from django.core.management.base import BaseCommand
from django.db.models import F
from collections import defaultdict

class Command(BaseCommand):
    help = 'Process outbox orders and update inventory'
    
    def handle(self,*args,**kwargs):
        redis_conn = redis.Redis(host = "localhost",port = 6379, decode_responses = True)
        outbox_key = "orders_queue"
        processing_key = "processing_orders"
        
        BATCH_SIZE = 50
        self.stdout.write("Worker started. Waiting for orders...")
        while True:
            data = redis_conn.brpoplpush(outbox_key,processing_key,timeout = 0)
            batch = [data]
            for _ in range(BATCH_SIZE - 1):
                item = redis_conn.rpoplpush(outbox_key,processing_key) #donot use timeout=0 because it blocks until it gets 50 orders which is not ideal for less than 50 orders scenario
                if item:
                    batch.append(item)
                else:
                    break
                
                
            orders_to_create = []
            item_deductions = defaultdict(int)
                
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
                    
                    for raw_data in batch:
                        redis_conn.lrem(processing_key,1,raw_data)
                    self.stdout.write(f"Successfully processed and cleared a batch of {len(orders_to_create)} orders.")   
                except Exception as e:
                    self.stdout.write(f"Database error processing batch: {str(e)}")
                    
                                