# 创建 图生视频 任务
ARK_API_KEY=ark-59bb7ade-029a-4948-b3b9-7ea847ef916e-5399b

curl -X POST https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedance-1-0-pro-fast-251015",
    "content": [
        {
            "type": "text",
            "text": "无人机以极快速度穿越复杂障碍或自然奇观，带来沉浸式飞行体验  --resolution 1080p  --duration 5 --camerafixed false --watermark true"
        },
        {
            "type": "image_url",
            "image_url": {
                "url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seepro_i2v.png"
            }
        }
    ]
}'

# 查询任务（需将id替换成第1步返回的任务id)
curl -X GET https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY"



LLM模型:
curl --location 'https://ark.cn-beijing.volces.com/api/v3/responses' \
--header "Authorization: Bearer $ARK_API_KEY" \
--header 'Content-Type: application/json' \
--data '{
    "model": "deepseek-v3-2-251201",
    "stream": true,
    "tools": [
        {
            "type": "web_search",
            "max_keyword": 3
        }
    ],
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "今天有什么热点新闻"
                }
            ]
        }
    ]
}'

curl https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedream-5-0-260128",
    "prompt": "充满活力的特写编辑肖像，模特眼神犀利，头戴雕塑感帽子，色彩拼接丰富，眼部焦点锐利，景深较浅，具有Vogue杂志封面的美学风格，采用中画幅拍摄，工作室灯光效果强烈。",
    "size": "2K",
    "output_format":"png",
    "watermark": false
}'

{"model":"doubao-seedream-5-0-260128","created":1779245246,"data":[{"url":"https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/doubao-seedream-5-0/0217792452146219af49751528187ac6ba2ea329b70143719d76f_0.png?X-Tos-Algorithm=TOS4-HMAC-SHA256&X-Tos-Credential=AKLTYWJkZTExNjA1ZDUyNDc3YzhjNTM5OGIyNjBhNDcyOTQ%2F20260520%2Fcn-beijing%2Ftos%2Frequest&X-Tos-Date=20260520T024726Z&X-Tos-Expires=86400&X-Tos-Signature=abae6255c4ae228598b467bd422ecc0e20fe831c1b9c5f4ee24d7346753365c9&X-Tos-SignedHeaders=host","size":"1664x2496"}],"usage":{"generated_images":1,"output_tokens":16224,"total_tokens":16224}}

