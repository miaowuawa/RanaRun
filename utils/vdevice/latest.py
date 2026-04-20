import requests
import rich

from utils.vdevice.generate_env import generate_browser_ua

# 你要查询的 App ID（你提供的那个）
APPLE_APP_ID = "982817844"

PROTOCAL_LATEST = "3.25.10"

def get_latest_ver():
    # 随机UA（保持你原来的逻辑）
    ua = generate_browser_ua()

    # 苹果官方 iTunes Lookup API
    url = f"https://itunes.apple.com/cn/lookup?id={APPLE_APP_ID}"

    try:
        resp = requests.get(
            url,
            headers={"user-agent": ua},
            timeout=10
        )

        if resp.status_code == 200:
            response_json = resp.json()
            results = response_json.get("results", [])

            if results:
                # 直接取出最新版本号
                latest_ver = results[0].get("version")
                if latest_ver != PROTOCAL_LATEST:
                    rich.print("\n[yellow]检测到app版本有更新，请务必在使用前进行下单测试，以防协议失效影响下单！[/yellow]")
                return latest_ver

    except Exception as e:
        print(f"获取iOS版本失败: {e}")

    return None