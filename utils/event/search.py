"""
活动搜索模块
"""
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.urls import BASE_URL_WEB


def search_event_allcpp(keyword: str, city: str = "", page: int = 1, size: int = 20) -> list:
    """
    搜索ALLCPP活动
    Args:
        keyword: 搜索关键词
        city: 城市代码
        page: 页码
        size: 每页数量
    Returns:
        活动列表
    """
    try:
        url = f"{BASE_URL_WEB}allcpp/event/eventMainListV2.do"
        params = {
            "city": city if city else "",
            "isWannaGo": 0,
            "keyword": keyword if keyword else "",
            "pageNo": page,
            "pageSize": size,
            "sort": 1
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        result = response.json()

        if result.get("isSuccess"):
            # API返回的是 list 字段
            event_list = result.get("result", {}).get("list", [])
            return event_list
        else:
            return []
    except Exception as e:
        print(f"搜索活动失败: {e}")
        return []


if __name__ == "__main__":
    # 测试
    results = search_event_allcpp("CP")
    print(f"找到 {len(results)} 个活动")
    for event in results[:3]:
        print(f"- {event.get('eventName')} (ID: {event.get('id')})")
