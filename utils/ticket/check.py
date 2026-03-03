import requests
import utils.urls
import time
import random
from typing import Optional, List

# 导入URL常量
from utils.urls import GET_TICKET_TYPE_URL, GET_PURCHASER_LIST_URL, BASE_URL_WEB, TICKET_INFO_URL

def check_ticket_stock(session: requests.Session, ticket_id: str, event_main_id: str, base_delay: float) -> bool:
    """
    检查票种库存（增加随机延迟和提示）
    Args:
        session: requests会话
        ticket_id: 票种ID
        event_main_id: 活动ID
        base_delay: 基准延迟
    Returns:
        True: 有库存，False: 无库存
    """
    try:
        # 生成并输出本次延迟
        actual_delay = get_random_delay(base_delay)
        print(f"[调试][检查库存]此次延迟：{actual_delay}秒")
        time.sleep(actual_delay)

        # 重新获取票种信息检查库存
        ticket_data = get_ticket_type_list(session, event_main_id, base_delay)
        if ticket_data and "ticketTypeList" in ticket_data.get("result", {}):
            for ticket in ticket_data["result"]["ticketTypeList"]:
                if str(ticket["id"]) == ticket_id:
                    # remainderNum > 0 表示有库存
                    return ticket.get("remainderNum", 0) > 0
        return False
    except Exception as e:
        print(f"[调试][检查库存失败]检查库存失败: {e}")
        return False

def get_random_delay(base_delay: float) -> float:
    """
    根据基准延迟生成随机延迟（±0.2秒），确保不小于0.1秒
    Args:
        base_delay: 基准延迟
    Returns:
        随机调整后的延迟值
    """
    # 生成-0.2到+0.2之间的随机数
    random_offset = random.uniform(-0.2, 0.2)
    actual_delay = base_delay + random_offset
    # 确保延迟不小于0.1秒
    actual_delay = max(0.1, actual_delay)
    return round(actual_delay, 3)


def get_ticket_type_list(session: requests.Session, event_main_id: str, base_delay: float) -> Optional[dict]:
    """
    获取票种列表（增加随机延迟和提示）
    Args:
        session: requests会话
        event_main_id: 项目ID
        base_delay: 基准延迟
    Returns:
        票种列表响应数据，失败返回包含错误信息的字典
    """
    # 生成并输出本次延迟
    actual_delay = get_random_delay(base_delay)
    # 关闭调试信息输出
    # print(f"[调试][获取票种列表]此次延迟：{actual_delay}秒")
    time.sleep(actual_delay)

    try:
        params = {"eventMainId": event_main_id}
        url = BASE_URL_WEB + GET_TICKET_TYPE_URL
        
        # 关闭调试信息输出
        # print(f"[调试][获取票种列表]请求URL: {url}")
        # print(f"[调试][获取票种列表]请求参数: {params}")
        # print(f"[调试][获取票种列表]请求Headers: {dict(session.headers)}")
        # try:
        #     print(f"[调试][获取票种列表]请求Cookies: {dict(session.cookies)}")
        # except Exception:
        #     # 处理可能的CookieConflictError
        #     cookie_dict = {}
        #     for cookie in session.cookies:
        #         cookie_dict[cookie.name] = cookie.value
        #     print(f"[调试][获取票种列表]请求Cookies: {cookie_dict}")
        
        response = session.get(url, params=params, timeout=10)
        
        # 关闭调试信息输出
        # print(f"[调试][获取票种列表]响应状态码: {response.status_code}")
        # print(f"[调试][获取票种列表]响应Headers: {dict(response.headers)}")
        # print(f"[调试][获取票种列表]响应内容: {response.text}")
        
        response.raise_for_status()

        # 检查是否有新cookie需要更新
        if session.cookies:
            new_cookies = []
            for key, value in session.cookies.items():
                new_cookies.append(f"{key}={value}")
            new_cookie_str = "; ".join(new_cookies)
        return response.json()
    except Exception as e:
        # 关闭调试信息输出
        # print(f"[调试][获取票种列表失败]获取票种列表失败: {e}")
        # 返回包含错误信息的字典
        return {"isSuccess": False, "message": str(e)}


def get_ticket_info(session: requests.Session, ticket_id: str, base_delay: float) -> Optional[dict]:
    """
    获取票种详细信息（增加随机延迟和提示）
    Args:
        session: requests会话
        ticket_id: 票种ID
        base_delay: 基准延迟
    Returns:
        票种详细信息响应数据，失败返回None
    """
    # 生成并输出本次延迟
    actual_delay = get_random_delay(base_delay)
    print(f"[调试][获取票种详细信息]此次延迟：{actual_delay}秒")
    time.sleep(actual_delay)

    try:
        params = {"ticketId": ticket_id}
        url = BASE_URL_WEB + TICKET_INFO_URL
        
        # 打印请求信息
        print(f"[调试][获取票种详细信息]请求URL: {url}")
        print(f"[调试][获取票种详细信息]请求参数: {params}")
        print(f"[调试][获取票种详细信息]请求Headers: {dict(session.headers)}")
        try:
            print(f"[调试][获取票种详细信息]请求Cookies: {dict(session.cookies)}")
        except Exception:
            # 处理可能的CookieConflictError
            cookie_dict = {}
            for cookie in session.cookies:
                cookie_dict[cookie.name] = cookie.value
            print(f"[调试][获取票种详细信息]请求Cookies: {cookie_dict}")
        
        response = session.get(url, params=params, timeout=10)
        
        # 打印响应信息
        print(f"[调试][获取票种详细信息]响应状态码: {response.status_code}")
        print(f"[调试][获取票种详细信息]响应Headers: {dict(response.headers)}")
        print(f"[调试][获取票种详细信息]响应内容: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[调试][获取票种详细信息失败]获取票种详细信息失败: {e}")
        return None
    
def get_purchaser_list(session: requests.Session, base_delay: float) -> Optional[List[dict]]:
    """
    获取购票人列表（增加随机延迟和提示）
    Args:
        session: requests会话
        base_delay: 基准延迟
    Returns:
        购票人列表，失败返回None
    """
    # 生成并输出本次延迟
    actual_delay = get_random_delay(base_delay)
    print(f"[调试][获取购票人列表]此次延迟：{actual_delay}秒")
    time.sleep(actual_delay)

    try:
        url = BASE_URL_WEB + GET_PURCHASER_LIST_URL
        
        # 打印请求信息
        print(f"[调试][获取购票人列表]请求URL: {url}")
        print(f"[调试][获取购票人列表]请求Headers: {dict(session.headers)}")
        try:
            print(f"[调试][获取购票人列表]请求Cookies: {dict(session.cookies)}")
        except Exception:
            # 处理可能的CookieConflictError
            cookie_dict = {}
            for cookie in session.cookies:
                cookie_dict[cookie.name] = cookie.value
            print(f"[调试][获取购票人列表]请求Cookies: {cookie_dict}")
        
        response = session.get(url, timeout=10)
        
        # 打印响应信息
        print(f"[调试][获取购票人列表]响应状态码: {response.status_code}")
        print(f"[调试][获取购票人列表]响应Headers: {dict(response.headers)}")
        print(f"[调试][获取购票人列表]响应内容: {response.text}")
        
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data
        else:
            print(f"[调试][获取购票人列表失败]未获取到购票人信息")
            return None
    except Exception as e:
        print(f"[调试][获取购票人列表失败]获取购票人列表失败: {e}")
        return None


def check_ticket_status(ticket_info: dict) -> str:
    """
    检查票种状态
    Returns:
        - "ended": 已结束销售
        - "presale": 预售（未到开售时间）
        - "selling": 可售（正在销售）
    """
    now = int(time.time() * 1000)
    sell_start = ticket_info.get("sellStartTime", 0)
    sell_end = ticket_info.get("sellEndTime", 0)

    if now > sell_end:
        return "ended"
    elif now < sell_start:
        return "presale"
    else:
        return "selling"
