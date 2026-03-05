# Project FlashLock: High-Frequency Atomic Inventory Engine

## Overview

Project FlashLock is a Proof of Concept (PoC) designed to solve the fundamental "Race Condition" and "Dual Write" problems inherent in high-concurrency systems, such as a sneaker flash sale or ticket booking platform.

Traditional database locking (like PostgreSQL's SELECT FOR UPDATE) creates massive latency bottlenecks by forcing concurrent requests to queue up sequentially. If no locks are used, the system suffers from the "Lost Update" anomaly, resulting in oversold inventory.

This project bypasses the traditional Django Rest Framework (DRF) overhead and shifts the "Decision Engine" entirely into Redis. By leveraging atomic Lua scripts to handle inventory deduction and utilizing a Transactional Outbox pattern to asynchronously sync completed orders to PostgreSQL, this architecture allows a single-core Django application to process thousands of requests per second with sub-millisecond decision latency.

## System Requirements

- Python 3.12+
- PostgreSQL
- Docker Desktop (for Redis)
- Windows Subsystem for Linux (WSL) - _Only required if benchmarking with wrk_

## 1\. Local Environment & Database Setup

**Initialize the Virtual Environment:**

```Bash

python -m venv venv  
venv\\Scripts\\activate  
pip install -r requirements.txt  
```

**Set Up PostgreSQL:**

Ensure PostgreSQL is installed and running. Create the database via psql:

```SQL

CREATE DATABASE flashlock;  
```

Run Django migrations to build the schemas:

```Bash

python manage.py migrate  
```

**Seed Initial Data (Django Shell):**

```Bash

python manage.py shell  
```

```Python

from api.models import InventoryItem, Order  
Order.objects.all().delete()  
InventoryItem.objects.create(name="Limited Edition Sneaker", stock_count=10000)  
exit()  
```  
<br/>

## 2\. Redis Setup (Via Docker)

Start a Redis container in the background:

```Bash

docker run --name local-redis -p 6379:6379 -d redis  
```

Access the Redis CLI to flush old data and set the starting inventory:

```Bash

docker exec -it local-redis redis-cli  
FLUSHALL  
SET 1 10000  
```

## 3\. Running the Application & Worker

To properly test the Transactional Outbox pattern, you must run the web server and the background worker in **two separate terminal windows**.

**Terminal 1: Start the Waitress WSGI Server**

Waitress is used to handle high concurrency on Windows without dropping TCP connections.

```Bash

venv\\Scripts\\activate  
python -m waitress --listen=127.0.0.1:8000 --threads=50 --connection-limit=1000 FlashLock.wsgi:application  
```

### Terminal 2: The Background Worker

Start a background worker to relay data from the Redis outbox queue into PostgreSQL.

**⚠️ Important: Use ONLY ONE of the following worker commands at a time**, depending on which behavior you want to test or demonstrate:

- **The Perfect Worker (Optimized):** Safely moves data using batching and a crash-resilient brpoplpush/blmove strategy. This is the intended solution for the PoC.  
    ```Bash  
    python manage.py process_outbox  
    ```
- **The Error-Prone Worker:** Demonstrates what happens when using a basic LPOP approach. It will result in inconsistent data (lost orders) if the worker thread suddenly crashes before committing the transaction to PostgreSQL.  
    ```Bash  
    python manage.py error_process_outbox
    ```

- **The Slow Worker:** Demonstrates the bottleneck of executing a separate database transaction for every single row in the batch, resulting in high latency.  
    ```Bash  
    python manage.py slow_process_outbox  
    ```

## 4\. Benchmarking & Testing

You can benchmark this architecture using either **Locust** (for Python-based UI testing) or **wrk** (for raw HTTP throughput testing in Linux/WSL).

### Option A: Testing with Locust

Update your load_tests/locustfile.py to target the specific API endpoint you want to test. Uncomment the path you wish to evaluate:

```Python

import random  
from locust.contrib.fasthttp import FastHttpUser  
from locust import task  
<br/>class FlashSaleUser(FastHttpUser):  
@task  
def benchmark_api(self):  
random_user = random.randint(1, 1000000)  
payload = {'item_id': 1, 'user_id': random_user}  
<br/>\# 1. The Naive API (Will cause race conditions & overselling)  
\# self.client.post("/api/purchase_naive_wrong/", json=payload)  
<br/>\# 2. Traditional DB Lock API (Will cause severe latency bottlenecks)  
\# self.client.post("/api/purchase_transactional/", json=payload)  
<br/>\# 3. PoC Redis API (High speed, mathematically consistent)  
self.client.post("/api/purchase_high_speed/", json=payload)  
```

Run the Locust headless attack (500 users spawning instantly):

```Bash

python -m locust -f load_tests/locustfile.py --headless -u 500 -r 500 -t 30s --host <http://127.0.0.1:8000>  
```

### Option B: Testing with wrk (WSL / Linux)

If you want to test the absolute raw throughput limits, use wrk via your WSL terminal. Make sure you have created the three separate Lua scripts to dynamically generate payloads for each endpoint.

**Test the Naive Implementation:**

```Bash

wrk -t4 -c500 -d30s -s load_tests/script/purchase_naive_wrong.lua --latency <http://172.x.x.x:8000>  
```

**Test the Transactional (DB Lock) Implementation:**

```Bash

wrk -t4 -c500 -d30s -s load_tests/script/purchase_transactional.lua --latency <http://172.x.x.x:8000>
``` 

**Test the High-Speed Redis Implementation:**

```Bash

wrk -t4 -c500 -d30s -s load_tests/script/purchase_high_speed.lua --latency <http://172.x.x.x:8000>  
```

_(Note: If running wrk inside WSL against Waitress on Windows, replace 172.x.x.x with your Windows host IP found via cat /etc/resolv.conf.)_