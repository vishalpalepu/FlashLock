local item_key = KEYS[1]
local purchase_set_key = KEYS[2]
local outbox_key = KEYS[3]

local user_id = ARGV[1]
local timestamp = ARGV[2]

if (redis.call('SISMEMBER',purchase_set_key,user_id) == 1) then
    return -1
end

local stock = tonumber(redis.call('GET',item_key))

if (stock <= 0) then
    return 0
end

redis.call('DECR',item_key)
redis.call('SADD',purchase_set_key,user_id)

local payload = '{"user_id": "' .. userId .. '","item_id": '..item_key..',"timestamp": "' .. timestamp .. '"}'

redis.call('RPUSH',outbox_key,payload)