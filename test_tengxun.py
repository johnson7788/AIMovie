"""
Test script for Tencent Hunyuan API keys.
"""
import os
import sys
import json
import requests
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / "backend" / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"❌ .env not found at {env_path}")
    sys.exit(1)

LANG_KEY = os.environ.get("HUNYUAN_API_KEY", "")
VISION_KEY = os.environ.get("HUNYUAN_VISION_API_KEY", "")

BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def test(name: str, method: str, url: str, headers: dict, body: dict, expect_status: int = 200):
    print(f"\n{BOLD}--- {name} ---{RESET}")
    print(f"{method} {url}")
    print(f"Body: {json.dumps(body, ensure_ascii=False, indent=2)}")
    try:
        resp = requests.request(method, url, headers=headers, json=body, timeout=30)
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
        if resp.status_code == expect_status:
            print(f"{GREEN}✅ PASS{RESET}")
            return True
        else:
            print(f"{YELLOW}⚠️  Expected {expect_status}, got {resp.status_code}{RESET}")
            return False
    except Exception as e:
        print(f"{RED}❌ ERROR: {e}{RESET}")
        return False


# ---------------------------------------------------------
# 1. 语言模型 - api.hunyuan.cloud.tencent.com
# ---------------------------------------------------------
test(
    name="语言模型 (hunyuan-turbos-latest)",
    method="POST",
    url="https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LANG_KEY}",
    },
    body={
        "model": "hunyuan-turbos-latest",
        "messages": [{"role": "user", "content": "Say this is a test."}],
        "enable_enhancement": True,
    },
)

# ---------------------------------------------------------
# 2. 视觉模型 key - tokenhub.tencentmaas.com (图像生成)
# ---------------------------------------------------------
test(
    name="文生图提交 (hy-image-v3.0) - VISION KEY",
    method="POST",
    url="https://tokenhub.tencentmaas.com/v1/api/image/submit",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VISION_KEY}",
    },
    body={
        "model": "hy-image-v3.0",
        "prompt": "雨中, 竹林, 小路",
    },
)

# ---------------------------------------------------------
# 3. 语言模型 key 能否调用 tokenhub（理论上不应该）
# ---------------------------------------------------------
test(
    name="文生图提交 (hy-image-v3.0) - LANG KEY (预期失败)",
    method="POST",
    url="https://tokenhub.tencentmaas.com/v1/api/image/submit",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LANG_KEY}",
    },
    body={
        "model": "hy-image-v3.0",
        "prompt": "雨中, 竹林, 小路",
    },
)

print(f"\n{BOLD}=== Summary ==={RESET}")
print(f"Language key: {LANG_KEY[:12]}...{LANG_KEY[-8:]}")
print(f"Vision key:   {VISION_KEY[:12]}...{VISION_KEY[-8:]}")
