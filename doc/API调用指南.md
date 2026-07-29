# 创意视频生成 API 调用指南

两个接口即可完成视频生成：**提交任务** → **查询结果**。无需鉴权。

## 接口列表

| 接口 | 方法 | 说明 |
|------|------|------|
| `/app/shortplay/api/Creative/video` | POST | 提交视频生成任务 |
| `/app/model/api/Task/index` | GET | 查询任务列表/状态 |

---

## 1. 提交视频生成任务

```
POST /app/shortplay/api/Creative/video
```

### 请求参数 (JSON body)

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image_url` | string | **是** | - | 参考图 URL |
| `prompt` | string | 否 | `""` | 提示词，描述视频内容 |
| `duration` | int | 否 | `5` | 视频时长，支持 `5` 或 `10` 秒 |
| `resolution` | string | 否 | `"1080p"` | 分辨率：`"1080p"` 或 `"720p"` |
| `model_id` | string | 否 | `"1"` | 模型 ID，见下方模型列表 |

### 模型列表

| model_id | 名称 | 供应商 |
|----------|------|--------|
| `"1"` | Seedance 1.5 Pro | volcengine |
| `"2"` | Veo 3 | google |
| `"3"` | Seedance 2.0 | gpugeek |
| `"4"` | Agnes Video V2.0 | agnes |

### 响应格式

```json
{
  "code": 200,
  "data": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "pending"
  },
  "msg": "success"
}
```

**code=200 表示成功**（非 0），拿到 `task_id` 后轮询查询结果。

---

## 2. 查询任务状态

```
GET /app/model/api/Task/index?scene=creative_video
```

### 请求参数 (query string)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `scene` | string | `"creative_video"` | 场景标识，固定值 |
| `limit` | int | `20` | 每页条数 |
| `page` | int | `1` | 页码 |

### 响应格式

```json
{
  "code": 200,
  "data": {
    "data": [
      {
        "task_id": "a1b2c3d4-...",
        "mode": "creative_video",
        "status": "completed",
        "result": "/path/to/output.mp4",
        "error": null,
        "created_at": "2026-07-29 10:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20
  }
}
```

### 状态说明

| status | 含义 |
|--------|------|
| `pending` | 排队中，等待生成 |
| `completed` | 生成完成，`result` 字段为视频路径 |
| `failed` | 生成失败，`error` 字段含错误信息 |

---

## 调用示例

### curl

```bash
# 1. 提交任务
curl -X POST http://127.0.0.1:8666/app/shortplay/api/Creative/video \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/reference.jpg",
    "prompt": "人物微笑转身，背景虚化",
    "duration": 5,
    "resolution": "1080p",
    "model_id": "1"
  }'

# 2. 轮询查询（用上面返回的 task_id）
curl "http://127.0.0.1:8666/app/model/api/Task/index?scene=creative_video&limit=5"
```

### Python

```python
import time
import requests

BASE = "http://127.0.0.1:8666"

# 1. 提交任务
resp = requests.post(f"{BASE}/app/shortplay/api/Creative/video", json={
    "image_url": "https://example.com/reference.jpg",
    "prompt": "人物微笑转身，背景虚化",
    "duration": 5,
    "resolution": "1080p",
    "model_id": "1",
})
task = resp.json()
assert task["code"] == 200  # 注意：成功是 200，不是 0
task_id = task["data"]["task_id"]
print(f"任务已提交: {task_id}")

# 2. 轮询等待完成
while True:
    resp = requests.get(
        f"{BASE}/app/model/api/Task/index",
        params={"scene": "creative_video", "limit": 5},
    )
    tasks = resp.json()["data"]["data"]
    for t in tasks:
        if t["task_id"] == task_id:
            status = t["status"]
            if status == "completed":
                print(f"生成完成: {t['result']}")
                exit(0)
            elif status == "failed":
                print(f"生成失败: {t['error']}")
                exit(1)
    print(f"等待中... 当前状态={status}")
    time.sleep(5)
```

### JavaScript (Node)

```js
const BASE = "http://127.0.0.1:8666";

async function main() {
  // 1. 提交任务
  const resp = await fetch(`${BASE}/app/shortplay/api/Creative/video`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_url: "https://example.com/reference.jpg",
      prompt: "人物微笑转身",
      duration: 5,
      resolution: "1080p",
      model_id: "1",
    }),
  });
  const task = await resp.json();
  const taskId = task.data.task_id;
  console.log("任务已提交:", taskId);

  // 2. 轮询
  while (true) {
    const resp = await fetch(
      `${BASE}/app/model/api/Task/index?scene=creative_video&limit=5`
    );
    const body = await resp.json();
    const found = body.data.data.find((t) => t.task_id === taskId);
    if (found?.status === "completed") {
      console.log("完成:", found.result);
      break;
    } else if (found?.status === "failed") {
      console.log("失败:", found.error);
      break;
    }
    console.log("等待中...");
    await new Promise((r) => setTimeout(r, 5000));
  }
}
main();
```

---

## 注意事项

1. **code 字段**: 成功为 `200`（不是 `0`），不要用 `code == 0` 判断成功。
2. **参考图来源**: `image_url` 可以是任意公网/服务器本地可访问的图片 URL。当前 `Uploads/upload` 接口暂未实现，需自行提供已上传的图片 URL。
3. **生成耗时**: 视频生成是异步的，提交后立即返回 `task_id`，需轮询 `Task/index` 获取结果。
4. **API Key**: 后端生成依赖配置好的模型供应商密钥，若密钥未配置则任务会标记为 `failed`。
