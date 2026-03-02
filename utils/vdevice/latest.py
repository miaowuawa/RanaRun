import requests
from utils.urls import BASE_URL_WEB, GET_CURR_ANDROID_VERSION_URL
from utils.vdevice.generate_env import generate_browser_ua
#randomua，使用一个edge手机端的ua，随机版本号
def get_latest_ver():
    #随机ua
    ua = generate_browser_ua()
    # 拼接完整的URL
    url = BASE_URL_WEB + GET_CURR_ANDROID_VERSION_URL
    resp = requests.get(url, headers={"user-agent": ua})
    if resp.status_code == 200:
        response_json = resp.json()
        if response_json.get("isSuccess"):
            latest_ver = response_json["result"]["version"]
            return latest_ver
    return None