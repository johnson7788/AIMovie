curl -X POST "https://api.gpugeek.com/predictions" \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Volcengine/Doubao-Seedance-2.0-fast",
    "input": {
      "task_type": "reference",
      "prompt": "Your prompt",
      "images": [
        "https://example.com/assets/seedance-fast-reference-image-1.png",
        "https://example.com/assets/seedance-fast-reference-image-2.png"
      ],
      "videos": [
        "https://example.com/assets/seedance-fast-reference-video-1.mp4",
        "https://example.com/assets/seedance-fast-reference-video-2.mp4"
      ],
      "audios": [
        "https://example.com/assets/seedance-fast-reference-audio-1.wav",
        "https://example.com/assets/seedance-fast-reference-audio-2.wav"
      ],
      "duration": 4,
      "resolution": "720p",
      "ratio": "adaptive",
      "seed": 11,
      "execution_expires_after": 3600,
      "generate_audio": true,
      "return_last_frame": true,
      "watermark": false,
      "tools": [
        {
          "type": "web_search"
        }
      ]
    }
  }'


curl -X POST "https://api.gpugeek.com/predictions" \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Volcengine/Doubao-Seedance-2.0-fast",
    "input": {
      "task_type": "reference",
      "prompt": "Your prompt",
      "images": [
        "https://example.com/assets/seedance-fast-reference-image-1.png",
        "https://example.com/assets/seedance-fast-reference-image-2.png"
      ],
      "videos": [
        "https://example.com/assets/seedance-fast-reference-video-1.mp4",
        "https://example.com/assets/seedance-fast-reference-video-2.mp4"
      ],
      "audios": [
        "https://example.com/assets/seedance-fast-reference-audio-1.wav",
        "https://example.com/assets/seedance-fast-reference-audio-2.wav"
      ],
      "duration": 4,
      "resolution": "720p",
      "ratio": "adaptive",
      "seed": 11,
      "execution_expires_after": 3600,
      "generate_audio": true,
      "return_last_frame": true,
      "watermark": false,
      "tools": [
        {
          "type": "web_search"
        }
      ]
    }
  }'


文生图
curl --location 'https://api.gpugeek.com/predictions' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer {{API_KEY}}' \
  --data '{
    "input": {
    "prompt": "充满活力的特写编辑肖像，模特眼神犀利，头戴雕塑感帽子，色彩拼接丰富，眼部焦点锐利，景深较浅，具有Vogue杂志封面的美学风格，采用中画幅拍摄，工作室灯光效果强烈。",
    "size": "2K",
    "output_format":"png",
    "watermark": false
    },
    "model": "Volcengine/Doubao-Seedream-5.0-lite"
}'



图生图
curl --location 'https://api.gpugeek.com/predictions' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer {{API_KEY}}' \
  --data '{
    "input": {
    "prompt": "充满活力的特写编辑肖像，模特眼神犀利，头戴雕塑感帽子，色彩拼接丰富，眼部焦点锐利，景深较浅，具有Vogue杂志封面的美学风格，采用中画幅拍摄，工作室灯光效果强烈。",
    "size": "2K",
    "output_format":"png",
    "watermark": false
    },
    "model": "Volcengine/Doubao-Seedream-5.0-lite"
}'

# $YOUR_API_KEY 需替换为你的API_KEY

curl --request POST \
  --url https://api.gpugeek.com/v1/chat/completions \
  --header 'Authorization: Bearer $YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "Vendor3/DeepSeek-V4-Flash",
    "messages": [
      {
        "role": "user",
        "content": "你好，请介绍一下自己"
      }
    ]
  }'




