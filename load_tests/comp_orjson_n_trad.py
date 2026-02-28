import timeit
import json
import orjson


data = b'{"item_id": 1, "user_id": 123}'
def test_traditional_json():
     return json.loads(data)
 
def test_orjson():
    return orjson.loads(data)

if __name__ == "__main__":
    
    traditional_time = timeit.timeit(test_traditional_json,number= 100000)
    orjson_time = timeit.timeit(test_orjson,number=100000)
    
    print(f"Traditional JSON parsing time: {traditional_time:.4f} seconds")
    print(f"orjson parsing time: {orjson_time:.4f} seconds")
    print(f"Speedup: {traditional_time/orjson_time:.2f}x faster")