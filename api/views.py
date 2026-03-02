import json
import time
import timeit
import orjson
from django.views import View
from django.http import JsonResponse
from .models import InventoryItem ,Order
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .redis_client import attempt_purchase
from django.db import transaction


# We exempt CSRF so you can easily test this API from your terminal without frontend tokens
@method_decorator(csrf_exempt, name='dispatch')
class NaivePurchaseView(View):
    def post(self, request):
        data = orjson.loads(request.body)
        item_id = data.get('item_id')
        user_id = data.get('user_id')  # Get user_id from the request body
        try:
            if(user_id is None):
                return JsonResponse({'status': 'error', 'message': 'User ID is required'}, status=400)
            user = Order.objects.get(user_id=user_id, item_id=item_id)  # get an order record if exists
            if(user is not None):
                return JsonResponse({'status': 'error', 'message': 'User has already purchased this item'}, status=400)
            item = InventoryItem.objects.get(id=item_id)
            if item.stock_count > 0:
                time.sleep(0.5)
                item.stock_count -= 1
                item.save(update_fields=['stock_count'])
                
                Order.objects.create(user_id=user_id, item_id=item_id)  # create an order record for the user
                
                return JsonResponse({'status': 'success', 'message': 'Purchase successful'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Not enough stock'}, status=400)
        except InventoryItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')      
class TransactionalPurchaseView(View):
    def post(self,request):
        data = orjson.loads(request.body)
        item_id = data.get('item_id')
        user_id = data.get('user_id')  # Get user_id from the request body
        try:
            
            if (user_id is None or item_id is None):
                return JsonResponse({'status': 'error', 'message': 'User ID and Item ID are required'}, status=400)
            
            user = Order.objects.filter(user_id=user_id, item_id=item_id)  # get an order record if exists
            if user.exists():
                return JsonResponse({'status': 'error', 'message': 'User has already purchased this item'}, status=400)
            
            with transaction.atomic():
                
                item = InventoryItem.objects.select_for_update().get(id=item_id)
                if item.stock_count > 0:
                    time.sleep(0.5)
                    item.stock_count -=1
                    item.save(update_fields=["stock_count"])
                    Order.objects.create(item_id=item_id,user_id=user_id)
                    return JsonResponse({'status': 'success', 'message': 'Purchase successful'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Not enough stock'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
                    
        
@method_decorator(csrf_exempt, name='dispatch')      
class HighSpeedPurchaseView(View):
    def post(self, request):
        try:
            data = orjson.loads(request.body)
            user_id = data.get('user_id')
            item_id = data.get('item_id')
        
            if user_id is None:
                return JsonResponse({'status': 'error', 'message': 'User ID is required'}, status=400)
            
            result = attempt_purchase(user_id,item_id,str(time.time()))
        
            if(result == 1):
                return JsonResponse({'status': 'success', 'message': 'Purchase successful'})
            elif(result == -1):
                print()(f"User {user_id} attempted to purchase item {item_id} but has already purchased it")
                return JsonResponse({'status': 'duplicate', 'message': 'User already purchased this item'}, status=409)
            elif(result == 0):
                return JsonResponse({'status': 'failed', 'message': 'Sold Out'}, status=400)
            elif (result == -2):
                return JsonResponse({'status': 'error', 'message': 'Redis error occurred'}, status=500)
            elif(result == -3):
                return JsonResponse({'status': 'error', 'message': 'Rate limit exceeded'}, status=429)
        
        except Exception as e:
            print(f"CRASH REASON: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)