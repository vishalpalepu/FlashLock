import orjson
import redis
from collections import defaultdict
from api.models import InventoryItem, Order
from django.db import transaction
from django.db.models import F
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Process outbox orders reliably using modern BLMOVE crash recovery'
    
    def handle(self, *args, **kwargs):
        redis_conn = redis.Redis(host='localhost', port=6379, decode_responses=True)
        outbox_key = "orders_queue"
        processing_key = "processing_queue"
        BATCH_SIZE = 50  
        
        self.stdout.write("Reliable worker started. Waiting for orders...")
        
        while True:

            data = redis_conn.blmove(outbox_key, processing_key, 'RIGHT', 'LEFT',0)
            if not data:
                continue
            batch = [data]
            
            # 2. The Fast Gather (Non-Blocking)
            # lmove is the non-blocking equivalent. We use it to instantly grab the rest of the batch.
            for _ in range(BATCH_SIZE - 1):
                item = redis_conn.lmove(outbox_key, processing_key, 'RIGHT', 'LEFT')
                if item:
                    batch.append(item)
                else:
                    break 
            
            # 3. Prepare data in Python memory
            orders_to_create = []
            item_deductions = defaultdict(int)
            
            for raw_data in batch:
                try:
                    order_data = orjson.loads(raw_data)
                    user_id = order_data.get('user_id')
                    item_id = order_data.get('item_id')
                    
                    if user_id is None or item_id is None:
                        continue
                        
                    orders_to_create.append(Order(user_id=user_id, item_id=item_id))
                    item_deductions[item_id] += 1
                    
                except Exception as e:
                    self.stdout.write(f"Error parsing order: {str(e)}")
            
            # 4. Atomic Database Execution
            if orders_to_create:
                try:
                    with transaction.atomic():
                        # Save to Postgres
                        Order.objects.bulk_create(orders_to_create)
                        
                        # Deduct from DB stock
                        for current_item_id, total_sold in item_deductions.items():
                            InventoryItem.objects.filter(id=current_item_id).update(
                                stock_count=F('stock_count') - total_sold
                            )
                            
                    # 5. EXPLICIT DELETION (The Acknowledgment)
                    # This code ONLY runs if the Postgres transaction was 100% successful.
                    for raw_data in batch:
                        redis_conn.rpop(processing_key, 1, raw_data)
                        
                    self.stdout.write(f"Successfully processed and cleared a batch of {len(orders_to_create)} orders.")
                    
                except Exception as e:
                    self.stdout.write(f"Database error during batch save: {str(e)}")
                    # If this triggers, the items remain safely inside 'processing_queue' in Redis.