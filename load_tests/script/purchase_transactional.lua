math.randomseed(os.time())

request = function()
    local random_user = math.random(1,10000000)
    local item_id = 1

    local path = "/api/purchase_transactional/"
    local body = '{"item_id": '.. item_id .. ', "user_id": '.. random_user .. '}'
    
    local headers = {
        = "application/json"
    }

    return wrk.format("POST",path,headers,body);
end
