from locust import HttpUser, task, between
import random

class FlashSaleUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def view_product(self):
        random_user = random.randint(1, 1000000)
        self.client.post("/api/purchase_high_speed/" , json={'user_id' : random_user,'item_id' : 1})