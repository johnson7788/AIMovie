export HUNYUAN_API_KEY=sk-IqaQAQmvFqpCqbN48eZLEy8dMQanBVai3gFNkhyEpBudaBVv
语言模型
curl https://api.hunyuan.cloud.tencent.com/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $HUNYUAN_API_KEY" \
-d '{
  "model": "hunyuan-turbos-latest",
  "messages": [
        {
            "role": "user",
            "content": "Say this is a test."
        }
    ],
  "enable_enhancement": true
}'
------>
{"id":"55756dca54d01d334a468b2cda0de382","object":"chat.completion","created":1779428248,"model":"hunyuan-turbos-latest","system_fingerprint":"","choices":[{"index":0,"message":{"role":"assistant","content":"This is a test."},"finish_reason":"stop"}],"usage":{"prompt_tokens":47,"completion_tokens":6,"total_tokens":53},"note":"以上内容为AI生成，不代表开发者立场，请勿删除或修改本标记"}%



图片理解的模型
curl --location 'https://api.hunyuan.cloud.tencent.com/v1/chat/completions' \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $HUNYUAN_API_KEY" \
--data '{
  "model": "hunyuan-vision",
  "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What'\''s in this image?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://qcloudimg.tencent-cloud.cn/raw/42c198dbc0b57ae490e57f89aa01ec23.png"
                    }
                }
            ]
        }
    ]
}'

//输入为图片示例
curl -X POST 'https://tokenhub.tencentmaas.com/v1/chat/completions' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "youtu-vita",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "image_url",
            "image_url": {
              "url": "<image url>"
            }
          },
          {
            "type": "text",
            "text": "请描述这组图片的内容"
          }
        ]
      }
    ],
    "stream": false
  }'

文生图
//提交示例
curl -X POST 'https://tokenhub.tencentmaas.com/v1/api/image/submit' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy-image-v3.0",
    "prompt": "雨中, 竹林, 小路"
  }'

//查询示例
curl -X POST 'https://tokenhub.tencentmaas.com/v1/api/image/query' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy-image-v3.0",
    "id": "xxxxxxxxx"
  }'


文生成视频
//提交示例
curl -X POST 'https://tokenhub.tencentmaas.com/v1/api/video/submit' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy-video-1.5",
    "prompt": "一只小狗"
  }'

//查询示例
curl -X POST 'https://tokenhub.tencentmaas.com/v1/api/video/query' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy-video-1.5",
    "id": "xxxxxx"
  }'


图生视频
//提交示例
curl -X POST 'https://tokenhub.tencentmaas.com/v1/api/video/submit' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "yt-video-humanactor",
    "prompt": "画面中的人物正在对着镜头讲话，偶尔做些手势匹配说话的内容",
    "audioUrl": "https://cos.ap-guangzhou.myqcloud.com/xxx-audio.mp3"
  }'

//查询示例
curl -X POST 'https://tokenhub.tencentmaas.com/v1/api/video/query' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "yt-video-humanactor",
    "id": "xxxxxx"
  }'

