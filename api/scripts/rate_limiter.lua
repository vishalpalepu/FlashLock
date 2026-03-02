local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local refill_interval = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local requested_tokens = tonumber(ARGV[5])

local bucket = redis.call("HMGET", key, "tokens", "last_refill")
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then 
    tokens = capacity
    last_refill = now
end

local time_passed = now - last_refill
local refills = math.floor(time_passed / refill_interval)

if(refills > 0) then
    -- refills days how may times the buckets need to be filled and refill_rate says how much tokens should be added at each refill
    tokens = math.min(capacity, tokens + (refills * refill_rate))
    -- refills * refill_internal = time_passed but as an integer multiple of refill_interval
    last_refill = last_refill + (refills * refill_interval) 
end

local allowed = 0

if(tokens >= requested_tokens) then
    allowed = 1
    tokens = tokens - requested_tokens
end

redis.call("HMSET",key , "tokens",tokens,"last_refill", last_refill)

-- Set a TTL (Time-To-Live) so inactive users don't waste Redis memory forever
redis.call("EXPIRE" ,key , math.ceil((capacity / refill_rate) * refill_interval / 1000))

return allowed


