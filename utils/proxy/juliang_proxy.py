"""
巨量代理管理模块
支持从巨量代理API获取SOCKS5代理并轮换使用
支持代理有效期管理（ip_remain），过期前自动更换
"""
import requests
import json
import time
import random
from typing import Optional, Dict, Any


class JuliangProxyManager:
    """巨量代理管理器"""
    
    # 提前更换代理的时间（秒）
    EXPIRE_ADVANCE_SECONDS = 5
    
    def __init__(self, api_url: str = ""):
        self.api_url = api_url
        self.current_proxy: Optional[Dict[str, str]] = None
        self.proxy_failed_count = 0
        self.max_failed_attempts = 3  # 单个代理最大失败次数
        
        # 代理有效期管理
        self.proxy_expire_time: float = 0  # 代理过期时间戳
        self.proxy_remain_seconds: int = 0  # 代理剩余有效期（秒）
        
    def set_api_url(self, api_url: str):
        """设置API地址"""
        self.api_url = api_url
        
    def is_configured(self) -> bool:
        """检查是否已配置API"""
        return bool(self.api_url and self.api_url.strip())
        
    def is_proxy_expiring(self) -> bool:
        """
        检查代理是否即将过期
        返回: True表示即将过期或已过期，需要更换
        """
        if not self.current_proxy:
            return True
            
        current_time = time.time()
        # 提前EXPIRE_ADVANCE_SECONDS秒就标记为即将过期
        if current_time >= (self.proxy_expire_time - self.EXPIRE_ADVANCE_SECONDS):
            print(f"[巨量代理] 代理即将过期，剩余有效期: {max(0, self.proxy_expire_time - current_time):.1f}秒")
            return True
        return False
        
    def fetch_proxy(self) -> Optional[Dict[str, str]]:
        """
        从巨量API获取新代理
        返回: {"http": "socks5://user:pass@ip:port", "https": "socks5://user:pass@ip:port"}
        """
        if not self.is_configured():
            return None
            
        try:
            # 添加随机参数避免缓存
            url = self.api_url
            if "?" in url:
                url += f"&_t={int(time.time() * 1000)}"
            else:
                url += f"?_t={int(time.time() * 1000)}"
                
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查返回码
            if data.get("code") != 200:
                print(f"[巨量代理] API返回错误: {data.get('msg', '未知错误')}")
                return None
                
            proxy_list = data.get("data", {}).get("proxy_list", [])
            if not proxy_list:
                print("[巨量代理] 未获取到代理列表")
                return None
                
            # 取第一个代理
            proxy_info = proxy_list[0]
            ip = proxy_info.get("ip")
            port = proxy_info.get("port")
            user = proxy_info.get("http_user")
            password = proxy_info.get("http_pass")
            ip_remain = proxy_info.get("ip_remain", 0)  # 代理剩余有效期（秒）
            
            if not all([ip, port, user, password]):
                print(f"[巨量代理] 代理信息不完整: {proxy_info}")
                return None
                
            # 构建socks5代理URL
            proxy_url = f"socks5://{user}:{password}@{ip}:{port}"
            
            proxy_dict = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            self.current_proxy = proxy_dict
            self.proxy_failed_count = 0
            
            # 记录代理有效期
            self.proxy_remain_seconds = ip_remain
            self.proxy_expire_time = time.time() + ip_remain
            
            print(f"[巨量代理] 获取新代理成功: {ip}:{port}，有效期: {ip_remain}秒")
            return proxy_dict
            
        except Exception as e:
            print(f"[巨量代理] 获取代理失败: {e}")
            return None
            
    def get_current_proxy(self, check_expire: bool = True) -> Optional[Dict[str, str]]:
        """
        获取当前代理
        Args:
            check_expire: 是否检查代理过期时间，默认True
        返回: 当前代理或新获取的代理
        """
        # 检查代理是否即将过期
        if check_expire and self.is_proxy_expiring():
            print("[巨量代理] 代理已过期或即将过期，获取新代理...")
            return self.fetch_proxy()
            
        if self.current_proxy is None:
            return self.fetch_proxy()
        return self.current_proxy
        
    def mark_proxy_failed(self, check_expire: bool = True) -> Optional[Dict[str, str]]:
        """
        标记当前代理失败，如果失败次数过多或代理过期则换新代理
        Args:
            check_expire: 是否检查代理过期时间，默认True
        返回: 新代理或None
        """
        # 先检查是否过期
        if check_expire and self.is_proxy_expiring():
            print("[巨量代理] 代理已过期，获取新代理...")
            return self.fetch_proxy()
            
        self.proxy_failed_count += 1
        print(f"[巨量代理] 当前代理失败次数: {self.proxy_failed_count}/{self.max_failed_attempts}")
        
        if self.proxy_failed_count >= self.max_failed_attempts:
            print("[巨量代理] 代理失败次数过多，获取新代理...")
            return self.fetch_proxy()
            
        return self.current_proxy
        
    def rotate_proxy(self) -> Optional[Dict[str, str]]:
        """强制轮换新代理"""
        print("[巨量代理] 强制轮换新代理...")
        return self.fetch_proxy()


# 全局代理管理器实例
_juliang_manager: Optional[JuliangProxyManager] = None


def get_juliang_manager(api_url: str = "") -> JuliangProxyManager:
    """获取巨量代理管理器实例"""
    global _juliang_manager
    if _juliang_manager is None:
        _juliang_manager = JuliangProxyManager(api_url)
    elif api_url:
        _juliang_manager.set_api_url(api_url)
    return _juliang_manager


def reset_juliang_manager():
    """重置代理管理器"""
    global _juliang_manager
    _juliang_manager = None
