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



Vira生成视频
# 发送生成请求 YOUR_API_KEY需替换为你创建的API_KEY
curl -X POST https://api.gpugeek.com/predictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
	"model": "Vira/text2video",
	"input": {
		"model": "q3-turbo",
		"prompt": "dance",
		"style": "anime",
		"duration": 16,
		"aspect_ratio": "16:9",
		"resolution": "720p",
		"movement_amplitude": "auto",
		"seed": 0
	}
}'

# 查询处理状态 当 status 为 succeeded 时output 字段里会出现视频下载链接 (用浏览器下载需将'\u0026'替换为'&')
# YOUR_API_KEY 需替换请求所用的API_KEY, REQUEST_BACK_ID需替换为请求返回的'id'
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.gpugeek.com/predictions/REQUEST_BACK_ID


图生成视频
# 发送生成请求 YOUR_API_KEY需替换为你创建的API_KEY
curl -X POST https://api.gpugeek.com/predictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @- <<'EOF'
{
	"model": "Vira/image2video",
	"input": {
		"duration": 5,
		"images": ["your_reference_picture"],
		"model": "q2-turbo",
		"movement_amplitude": "auto",
		"prompt": "your_prompt",
		"resolution": "720p"
	}
}
EOF

# 查询处理状态 当 status 为 succeeded 时output 字段里会出现视频下载链接 (用浏览器下载需将'\u0026'替换为'&')
# YOUR_API_KEY 需替换请求所用的API_KEY, REQUEST_BACK_ID需替换为请求返回的'id'
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.gpugeek.com/predictions/REQUEST_BACK_ID


参考图片生成视频
# 发送生成请求 YOUR_API_KEY需替换为你创建的API_KEY
curl -X POST https://api.gpugeek.com/predictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @- <<'EOF'
{
	"model": "Vira/reference2video",
	"input": {
		"aspect_ratio": "16:9",
		"duration": 5,
		"images": ["your_reference_picture1, your_reference_picture2"],
		"model": "q2",
		"movement_amplitude": "auto",
		"prompt": "your_prompt",
		"resolution": "720p"
	}
}
EOF

# 查询处理状态 当 status 为 succeeded 时output 字段里会出现视频下载链接 (用浏览器下载需将'\u0026'替换为'&')
# YOUR_API_KEY 需替换请求所用的API_KEY, REQUEST_BACK_ID需替换为请求返回的'id'
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.gpugeek.com/predictions/REQUEST_BACK_ID


模版生成视频
# 发送生成请求 YOUR_API_KEY需替换为你创建的API_KEY
curl -X POST https://api.gpugeek.com/predictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @- <<'EOF'
{
  "model": "Vira/template2video",
  "input": {
    "aspect_ratio": "9:16",
    "bgm": false,
    "images": ["your_reference_picture"],
    "prompt": "Identify the expressions of each subject in the image, and ensure that their movements match their initial expression settings.\\nRequirement: \\nFixed camera.\\nMake the character's movements more expansive.\\nProhibited:\\nNo zooming in on any individual quadrant of the image",
    "seed": 0,
    "template": "漫画表情包"
  }
}
EOF

# 查询处理状态 当 status 为 succeeded 时output 字段里会出现视频下载链接 (用浏览器下载需将'\u0026'替换为'&')
# YOUR_API_KEY 需替换请求所用的API_KEY, REQUEST_BACK_ID需替换为请求返回的'id'
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.gpugeek.com/predictions/REQUEST_BACK_ID

首尾帧生成视频
# 发送生成请求 YOUR_API_KEY需替换为你创建的API_KEY
curl -X POST https://api.gpugeek.com/predictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @- <<'EOF'
{
	"model": "Vira/startEnd2video",
	"input": {
		"duration": 4,
		"images": ["your_reference_picture1, your_reference_picture2"],
		"model": "q2-pro",
		"prompt": "your_prompt",
		"resolution": "1080p",
		"seed": null
	}
}
EOF

# 查询处理状态 当 status 为 succeeded 时output 字段里会出现视频下载链接 (用浏览器下载需将'\u0026'替换为'&')
# YOUR_API_KEY 需替换请求所用的API_KEY, REQUEST_BACK_ID需替换为请求返回的'id'
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.gpugeek.com/predictions/REQUEST_BACK_ID

