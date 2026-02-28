from django.db import models

# Create your models here.
class InventoryItem(models.Model):
    stock_count = models.IntegerField(default=0)
    name = models.CharField(max_length=255)
    

class Order(models.Model):
    user_id  = models.IntegerField() # Assuming you have a user model, you can replace this with a ForeignKey to the User model
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    