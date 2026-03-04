import requests
import utils.urls
import time
import random
import json
from typing import Optional, List

# 导入URL常量
from utils.urls import GET_TICKET_TYPE_URL, GET_PURCHASER_LIST_URL, BASE_URL_WEB, TICKET_INFO_URL


def check_ip_blocked(response: requests.Response, result: dict) -> bool:
    """
    检查是否IP被风控
    """
    if response.status_code == 403:
        return True
    
    if isinstance(result, dict):
        message = str(result.get("message", ""))
        response_text = json.dumps(result, ensure_ascii=False)
        
        if "acl" in message.lower() or "custom" in message.lower():
            return True
        if "acl" in response_text.lower() and "custom" in response_text.lower():
            return True
    
    return False


def wait_if_ip_blocked(response: requests.Response, result: dict) -> bool:
    """
    如果IP被风控，等待10分钟后重试
    """
    if check_ip_blocked(response, result):
        print("\n[IP风控] ⚠️ 警告：IP已被风控！")
        print("[IP风控] 检测到403错误且响应中包含acl/custom关键字")
        print("[IP风控] 等待10分钟后重试...")
        
        # 等待10分钟
        for i in range(600, 0, -1):
            if i % 60 == 0:
                print(f"[IP风控] 剩余等待时间: {i//60}分钟")
            time.sleep(1)
        
        print("[IP风控] 等待结束，继续重试...")
        return True
    
    return False

def check_ticket_stock(session: requests.Session, ticket_id: str, event_main_id: str, base_delay: float) -> bool:
    """
    检查票种库存
    Args:
        session: requests会话
        ticket_id: 票种ID
        event_main_id: 活动ID
        base_delay: 基准延迟
    Returns:
        True: 有库存，False: 无库存
    """
    try:
        actual_delay = get_random_delay(base_delay)
        time.sleep(actual_delay)

        ticket_data = get_ticket_type_list(session, event_main_id, base_delay)
        if ticket_data and "ticketTypeList" in ticket_data:
            ticket_list = ticket_data.get("ticketTypeList", [])
            for ticket in ticket_list:
                if str(ticket.get("id")) == ticket_id:
                    return ticket.get("remainderNum", 0) > 0
        return False
    except Exception as e:
        return False

def get_random_delay(base_delay: float) -> float:
    """
    根据基准延迟生成随机延迟（±0.2秒 + 10-50ms随机延迟），确保不小于0.1秒
    Args:
        base_delay: 基准延迟
    Returns:
        随机调整后的延迟值
    """
    # 生成-0.2到+0.2之间的随机数
    random_offset = random.uniform(-0.2, 0.2)
    # 生成10-50ms的随机延迟
    ms_delay = random.uniform(0.01, 0.05)
    actual_delay = base_delay + random_offset + ms_delay
    # 确保延迟不小于0.1秒
    actual_delay = max(0.1, actual_delay)
    return round(actual_delay, 3)


def get_ticket_type_list(session: requests.Session, event_main_id: str, base_delay: float) -> Optional[dict]:
    """
    获取票种列表
    Args:
        session: requests会话
        event_main_id: 项目ID
        base_delay: 基准延迟
    Returns:
        原始响应数据 {"ticketMain": {..., "ticketTypeList": [...]}}，失败返回None
    """
    actual_delay = get_random_delay(base_delay)
    time.sleep(actual_delay)

    try:
        params = {"eventMainId": event_main_id}
        url = BASE_URL_WEB + GET_TICKET_TYPE_URL
        
        response = session.get(url, params=params, timeout=10)
        
        try:
            result = response.json()
        except:
            result = {}
        
        if wait_if_ip_blocked(response, result):
            return None
        
        response.raise_for_status()

        if session.cookies:
            new_cookies = []
            for key, value in session.cookies.items():
                new_cookies.append(f"{key}={value}")
            new_cookie_str = "; ".join(new_cookies)
        
        return result
    except Exception as e:
        return None


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
    actual_delay = get_random_delay(base_delay)
    time.sleep(actual_delay)

    try:
        params = {"ticketId": ticket_id}
        url = BASE_URL_WEB + TICKET_INFO_URL
        
        response = session.get(url, params=params, timeout=10)
        
        try:
            result = response.json()
        except:
            result = {}
        
        if wait_if_ip_blocked(response, result):
            return None
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
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
    actual_delay = get_random_delay(base_delay)
    time.sleep(actual_delay)

    try:
        url = BASE_URL_WEB + GET_PURCHASER_LIST_URL
        
        response = session.get(url, timeout=10)
        
        try:
            result = response.json()
        except:
            result = {}
        
        if wait_if_ip_blocked(response, result):
            return None
        
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data
        else:
            return None
    except Exception as e:
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
