"""
闪臣代理管理模块
支持从闪臣API获取SOCKS5代理
"""
import requests
import time
import threading
from typing import Optional, Dict, Any


class ShanchenProxyManager:
    """
    闪臣代理管理器
    管理单个代理的获取、验证和过期处理
    """

    def __init__(self, api_key: str = "", time_minutes: int = 1, count: int = 1, province: str = "", city: str = ""):
        """
        初始化闪臣代理管理器
        Args:
            api_key: API密钥
            time_minutes: 代理时长(1, 3, 5, 10分钟)，默认1分钟
            count: 获取数量，默认1
            province: 省份编号，默认空（不指定）
            city: 城市编号，默认空（不指定）
        """
        self.api_key = api_key
        self.time_minutes = time_minutes
        self.count = count
        self.province = province
        self.city = city
        self.base_url = "https://sch.shanchendaili.com/api.html"

        self.current_proxy: Optional[Dict[str, str]] = None
        self.proxy_expire_time: float = 0
        self.proxy_remain_seconds: int = 0
        self._lock = threading.Lock()

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key and self.api_key.strip())

    def set_api_key(self, api_key: str):
        """设置API密钥"""
        self.api_key = api_key

    def fetch_proxy(self) -> Optional[Dict[str, str]]:
        """
        从API获取新代理
        Returns:
            代理字典 {"http": "socks5://ip:port", "https": "socks5://ip:port"} 或 None
        """
        if not self.is_configured():
            return None

        try:
            params = {
                "action": "get_ip",
                "key": self.api_key,
                "time": self.time_minutes,
                "count": self.count,
                "type": "json",
                "only": 0
            }

            # 添加省份和城市参数（如果指定）
            if self.province:
                params["province"] = self.province
            if self.city:
                params["city"] = self.city

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 检查状态码
            if data.get("status") != "0":
                error_msg = data.get("info", f"未知错误(状态码:{data.get('status')})")
                print(f"[闪臣代理] API返回错误: {error_msg}")
                return None

            proxy_list = data.get("list", [])
            if not proxy_list:
                print("[闪臣代理] 未获取到代理列表")
                return None

            # 取第一个代理
            proxy_info = proxy_list[0]
            ip = proxy_info.get("sever")
            port = proxy_info.get("port")

            if not ip or not port:
                print("[闪臣代理] 代理信息不完整")
                return None

            # 构建代理URL (闪臣是SOCKS5代理，无认证)
            proxy_url = f"socks5://{ip}:{port}"

            with self._lock:
                self.current_proxy = {
                    "http": proxy_url,
                    "https": proxy_url
                }
                # 解析过期时间
                expire_str = data.get("expire", "")
                if expire_str:
                    try:
                        from datetime import datetime
                        expire_time = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
                        self.proxy_expire_time = expire_time.timestamp()
                        self.proxy_remain_seconds = int(self.proxy_expire_time - time.time())
                    except:
                        self.proxy_expire_time = time.time() + self.time_minutes * 60
                        self.proxy_remain_seconds = self.time_minutes * 60
                else:
                    self.proxy_expire_time = time.time() + self.time_minutes * 60
                    self.proxy_remain_seconds = self.time_minutes * 60

            print(f"[闪臣代理] 获取成功: {proxy_url}，有效期{self.proxy_remain_seconds}秒")
            return self.current_proxy

        except Exception as e:
            print(f"[闪臣代理] 获取代理失败: {e}")
            return None

    def get_current_proxy(self) -> Optional[Dict[str, str]]:
        """获取当前代理（如果不存在则获取新的）"""
        with self._lock:
            if self.current_proxy and time.time() < self.proxy_expire_time - 5:
                return self.current_proxy
        return self.fetch_proxy()

    def is_proxy_expiring(self) -> bool:
        """检查代理是否即将过期（剩余不足10秒）"""
        with self._lock:
            if not self.current_proxy:
                return True
            remaining = self.proxy_expire_time - time.time()
            self.proxy_remain_seconds = int(remaining)
            return remaining < 10

    def rotate_proxy(self) -> Optional[Dict[str, str]]:
        """强制更换新代理"""
        print("[闪臣代理] 强制更换代理...")
        return self.fetch_proxy()

    def mark_proxy_failed(self):
        """标记当前代理失败（获取新代理）"""
        print("[闪臣代理] 标记代理失败，获取新代理...")
        self.fetch_proxy()


# 全局管理器实例
_shanchen_manager: Optional[ShanchenProxyManager] = None


def get_shanchen_manager(api_key: str = "", time_minutes: int = 1, count: int = 1,
                         province: str = "", city: str = "") -> ShanchenProxyManager:
    """获取闪臣代理管理器实例"""
    global _shanchen_manager
    if _shanchen_manager is None:
        _shanchen_manager = ShanchenProxyManager(api_key, time_minutes, count, province, city)
    elif api_key:
        _shanchen_manager.set_api_key(api_key)
    return _shanchen_manager
