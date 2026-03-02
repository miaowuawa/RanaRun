import requests
import json
import time
from utils.env2sess import env_to_request_session
from utils.urls import BASE_URL_WEB, GET_TICKET_TYPE_URL

# 测试事件ID（使用一个有效的事件ID）
TEST_EVENT_ID = "6198"

def test_request(session_name, session):
    """测试单个请求"""
    print(f"\n=== 测试: {session_name} ===")
    try:
        # 打印 session 信息
        print(f"Headers: {dict(session.headers)}")
        print(f"Cookies: {dict(session.cookies)}")
        
        params = {"eventMainId": TEST_EVENT_ID}
        response = session.get(BASE_URL_WEB + GET_TICKET_TYPE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data
    except Exception as e:
        print(f"错误: {e}")
        return None

def main():
    print("测试不同情况下的 API 请求")
    print("=" * 50)
    
    # 1. 从环境文件创建完整的 session（带 cookie 和 header）
    try:
        with open("environment_233.json", "r", encoding="utf-8") as f:
            env = json.load(f)
        print("环境文件内容:")
        print(f"Header: {env.get('header', {})}")
        print(f"Cookie: {env.get('cookie', {})}")
        session_full = env_to_request_session(env)
        print("环境文件加载成功")
    except Exception as e:
        print(f"加载环境文件失败: {e}")
        session_full = None
    
    # 2. 创建只带 header 的 session
    session_header_only = requests.Session()
    if session_full:
        session_header_only.headers.update(session_full.headers)
    
    # 3. 创建只带 cookie 的 session
    session_cookie_only = requests.Session()
    if session_full:
        session_cookie_only.cookies.update(session_full.cookies)
    
    # 4. 创建空 session（不带 cookie 和 header）
    session_empty = requests.Session()
    
    # 执行测试
    if session_full:
        test_request("带 cookie 和 header", session_full)
        time.sleep(1)  # 避免请求过快
    
    test_request("只带 header", session_header_only)
    time.sleep(1)
    
    if session_full:
        test_request("只带 cookie", session_cookie_only)
        time.sleep(1)
    
    test_request("不带 cookie 和 header", session_empty)

if __name__ == "__main__":
    main()