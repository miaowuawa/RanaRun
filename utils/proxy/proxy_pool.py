"""
代理IP池管理模块
支持缓存、测速、异步维护，确保抢票时快速获取可用代理
支持多种代理源：巨量、闪臣
"""
import requests
import time
import threading
import queue
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class ProxyInfo:
    """代理信息"""
    http: str
    https: str
    latency_ms: int = 0  # 延迟（毫秒）
    expire_time: float = 0  # 过期时间戳
    remain_seconds: int = 0  # 剩余有效期（秒）
    failed_count: int = 0  # 失败次数
    last_check_time: float = 0  # 最后检查时间
    is_valid: bool = True  # 是否有效

    @property
    def is_expired(self) -> bool:
        """检查是否已过期（提前5秒标记为过期）"""
        return time.time() >= (self.expire_time - 5)

    @property
    def proxy_dict(self) -> Dict[str, str]:
        """返回代理字典格式"""
        return {"http": self.http, "https": self.https}


class ProxyPool:
    """
    代理IP池
    - 缓存3个最优代理
    - 异步维护缓存区
    - 快速切换IP
    - 支持多种代理源：juliang(巨量)、shanchen(闪臣)
    """

    # 配置参数
    CACHE_SIZE = 3  # 缓存区大小
    FETCH_COUNT = 5  # 每次获取数量
    TEST_URL = "https://cp.allcpp.cn/"  # 测试URL
    TEST_TIMEOUT = 5  # 测试超时（秒）
    MIN_VALID_LATENCY = 3000  # 最大可接受延迟（毫秒）

    def __init__(self, proxy_type: str = "none", config: Dict[str, Any] = None):
        """
        初始化代理池
        Args:
            proxy_type: 代理类型 (none, juliang, shanchen)
            config: 配置字典
                - juliang: {api_url: str}
                - shanchen: {api_key: str, time_minutes: int, count: int}
        """
        self.proxy_type = proxy_type
        self.config = config or {}

        self._cache: List[ProxyInfo] = []  # 代理缓存区
        self._lock = threading.RLock()  # 线程锁
        self._stop_event = threading.Event()  # 停止事件
        self._maintain_thread: Optional[threading.Thread] = None
        self._proxy_queue = queue.Queue()  # 新代理队列

    def start(self):
        """启动异步维护线程"""
        if self.proxy_type == "none":
            print("[代理池] 代理已禁用，不启动维护线程")
            return

        if self._maintain_thread is None or not self._maintain_thread.is_alive():
            self._stop_event.clear()
            self._maintain_thread = threading.Thread(target=self._maintain_loop, daemon=True)
            self._maintain_thread.start()
            print(f"[代理池] 异步维护线程已启动，代理类型: {self.proxy_type}")

    def stop(self):
        """停止异步维护线程"""
        self._stop_event.set()
        if self._maintain_thread and self._maintain_thread.is_alive():
            self._maintain_thread.join(timeout=2)
            print(f"[代理池] 异步维护线程已停止")

    def is_configured(self) -> bool:
        """检查是否已配置"""
        if self.proxy_type == "none":
            return False
        if self.proxy_type == "juliang":
            return bool(self.config.get("api_url", "").strip())
        if self.proxy_type == "shanchen":
            return bool(self.config.get("api_key", "").strip())
        return False

    def set_config(self, proxy_type: str, config: Dict[str, Any]):
        """设置配置"""
        self.proxy_type = proxy_type
        self.config = config or {}

    def _maintain_loop(self):
        """异步维护循环"""
        while not self._stop_event.is_set():
            try:
                # 检查缓存区状态
                need_fetch = False
                with self._lock:
                    # 清理无效代理
                    valid_count = sum(1 for p in self._cache if p.is_valid and not p.is_expired)
                    if valid_count < self.CACHE_SIZE:
                        need_fetch = True
                        print(f"[代理池] 缓存区代理不足: {valid_count}/{self.CACHE_SIZE}，需要补充")

                if need_fetch:
                    self._fetch_and_fill_cache()

                # 每秒检查一次
                time.sleep(1)

            except Exception as e:
                print(f"[代理池] 维护循环异常: {e}")
                time.sleep(5)

    def _fetch_and_fill_cache(self):
        """获取并填充缓存区"""
        try:
            # 获取新代理
            new_proxies = self._fetch_proxies(self.FETCH_COUNT)
            if not new_proxies:
                print(f"[代理池] 获取新代理失败")
                return

            # 测试延迟
            tested_proxies = self._test_proxies_latency(new_proxies)

            # 按延迟排序，选择最优的
            tested_proxies.sort(key=lambda x: x.latency_ms if x.is_valid else float('inf'))

            # 填充缓存区
            added_count = 0
            with self._lock:
                for proxy in tested_proxies:
                    if proxy.is_valid and not proxy.is_expired:
                        if len(self._cache) < self.CACHE_SIZE:
                            self._cache.append(proxy)
                            added_count += 1
                            print(f"[代理池] 添加代理到缓存区: 延迟{proxy.latency_ms}ms，有效期{proxy.remain_seconds}秒")
                        else:
                            break

            if added_count > 0:
                print(f"[代理池] 缓存区已补充: +{added_count}个代理，当前共{len(self._cache)}个")

        except Exception as e:
            print(f"[代理池] 填充缓存区失败: {e}")

    def _fetch_proxies(self, count: int) -> List[ProxyInfo]:
        """从API获取代理"""
        if self.proxy_type == "juliang":
            return self._fetch_juliang_proxies(count)
        elif self.proxy_type == "shanchen":
            return self._fetch_shanchen_proxies(count)
        else:
            return []

    def _fetch_juliang_proxies(self, count: int) -> List[ProxyInfo]:
        """从巨量API获取代理"""
        proxies = []
        api_url = self.config.get("api_url", "")
        if not api_url:
            return proxies

        try:
            # 添加随机参数避免缓存
            if "?" in api_url:
                url = api_url + f"&_t={int(time.time() * 1000)}"
            else:
                url = api_url + f"?_t={int(time.time() * 1000)}"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get("code") != 200:
                print(f"[代理池-巨量] API返回错误: {data.get('msg', '未知错误')}")
                return proxies

            proxy_list = data.get("data", {}).get("proxy_list", [])
            if not proxy_list:
                print("[代理池-巨量] 未获取到代理列表")
                return proxies

            # 转换为ProxyInfo对象
            for proxy_info in proxy_list[:count]:
                ip = proxy_info.get("ip")
                port = proxy_info.get("port")
                user = proxy_info.get("http_user")
                password = proxy_info.get("http_pass")
                ip_remain = proxy_info.get("ip_remain", 0)

                if not all([ip, port, user, password]):
                    continue

                proxy_url = f"socks5://{user}:{password}@{ip}:{port}"
                proxy = ProxyInfo(
                    http=proxy_url,
                    https=proxy_url,
                    expire_time=time.time() + ip_remain,
                    remain_seconds=ip_remain,
                    last_check_time=time.time()
                )
                proxies.append(proxy)

            print(f"[代理池-巨量] 获取到 {len(proxies)} 个代理")
            return proxies

        except Exception as e:
            print(f"[代理池-巨量] 获取代理失败: {e}")
            return proxies

    def _fetch_shanchen_proxies(self, count: int) -> List[ProxyInfo]:
        """从闪臣API获取代理"""
        proxies = []
        api_key = self.config.get("api_key", "")
        time_minutes = self.config.get("time_minutes", 1)
        fetch_count = self.config.get("count", 3)
        province = self.config.get("province", "")
        city = self.config.get("city", "")

        if not api_key:
            return proxies

        try:
            url = "https://sch.shanchendaili.com/api.html"
            params = {
                "action": "get_ip",
                "key": api_key,
                "time": time_minutes,
                "count": fetch_count,
                "type": "json",
                "only": 0
            }

            # 添加省份和城市参数
            if province:
                params["province"] = province
            if city:
                params["city"] = city

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 检查状态码
            if data.get("status") != "0":
                error_msg = data.get("info", f"未知错误(状态码:{data.get('status')})")
                print(f"[代理池-闪臣] API返回错误: {error_msg}")
                return proxies

            proxy_list = data.get("list", [])
            if not proxy_list:
                print("[代理池-闪臣] 未获取到代理列表")
                return proxies

            # 解析过期时间
            expire_str = data.get("expire", "")
            expire_time = time.time() + time_minutes * 60
            if expire_str:
                try:
                    from datetime import datetime
                    expire_dt = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
                    expire_time = expire_dt.timestamp()
                except:
                    pass

            remain_seconds = int(expire_time - time.time())

            # 转换为ProxyInfo对象
            for proxy_info in proxy_list[:count]:
                ip = proxy_info.get("sever")
                port = proxy_info.get("port")

                if not ip or not port:
                    continue

                # 闪臣是SOCKS5代理，无认证
                proxy_url = f"socks5://{ip}:{port}"
                proxy = ProxyInfo(
                    http=proxy_url,
                    https=proxy_url,
                    expire_time=expire_time,
                    remain_seconds=remain_seconds,
                    last_check_time=time.time()
                )
                proxies.append(proxy)

            print(f"[代理池-闪臣] 获取到 {len(proxies)} 个代理，有效期{remain_seconds}秒")
            return proxies

        except Exception as e:
            print(f"[代理池-闪臣] 获取代理失败: {e}")
            return proxies

    def _test_proxies_latency(self, proxies: List[ProxyInfo]) -> List[ProxyInfo]:
        """测试代理延迟（并发）"""
        def test_single(proxy: ProxyInfo) -> ProxyInfo:
            try:
                session = requests.Session()
                session.proxies = proxy.proxy_dict

                start = time.time()
                response = session.get(
                    self.TEST_URL,
                    timeout=self.TEST_TIMEOUT,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                elapsed_ms = int((time.time() - start) * 1000)

                proxy.latency_ms = elapsed_ms
                proxy.is_valid = elapsed_ms < self.MIN_VALID_LATENCY
                proxy.last_check_time = time.time()

                status = "有效" if proxy.is_valid else "延迟过高"
                print(f"[代理池] 测试代理: {elapsed_ms}ms ({status})")

            except Exception as e:
                proxy.latency_ms = 99999
                proxy.is_valid = False
                print(f"[代理池] 测试代理失败: {e}")

            return proxy

        # 并发测试
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(test_single, p): p for p in proxies}
            results = []
            for future in as_completed(futures):
                results.append(future.result())

        return results

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        获取一个可用代理（从缓存区）
        返回: 代理字典或None
        """
        if self.proxy_type == "none":
            return None

        with self._lock:
            # 清理无效/过期代理
            self._cache = [p for p in self._cache if p.is_valid and not p.is_expired]

            if not self._cache:
                print("[代理池] 缓存区为空，尝试立即获取")
                # 缓存区为空，立即获取（阻塞式）
                return self._emergency_fetch()

            # 获取延迟最低的代理
            best_proxy = min(self._cache, key=lambda x: x.latency_ms)
            print(f"[代理池] 从缓存获取代理: 延迟{best_proxy.latency_ms}ms，剩余{best_proxy.expire_time - time.time():.0f}秒")
            return best_proxy.proxy_dict

    def _emergency_fetch(self) -> Optional[Dict[str, str]]:
        """紧急获取代理（缓存区为空时使用）"""
        try:
            new_proxies = self._fetch_proxies(3)  # 获取3个
            if not new_proxies:
                return None

            # 快速测试（只测连通性，不测延迟）
            for proxy in new_proxies:
                try:
                    session = requests.Session()
                    session.proxies = proxy.proxy_dict
                    session.get(self.TEST_URL, timeout=3)
                    proxy.is_valid = True
                    proxy.latency_ms = 0  # 未知延迟
                    with self._lock:
                        self._cache.append(proxy)
                    print(f"[代理池] 紧急获取代理成功")
                    return proxy.proxy_dict
                except:
                    continue

            return None
        except Exception as e:
            print(f"[代理池] 紧急获取失败: {e}")
            return None

    def mark_proxy_failed(self, proxy_dict: Dict[str, str]):
        """标记代理失败（从缓存中移除）"""
        with self._lock:
            http_url = proxy_dict.get("http", "")
            for p in self._cache:
                if p.http == http_url:
                    p.is_valid = False
                    p.failed_count += 1
                    print(f"[代理池] 标记代理失败: {http_url[:40]}...")
                    break
            # 清理无效代理
            self._cache = [p for p in self._cache if p.is_valid and not p.is_expired]

    def get_status(self) -> Dict[str, Any]:
        """获取缓存区状态"""
        with self._lock:
            valid_count = sum(1 for p in self._cache if p.is_valid and not p.is_expired)
            return {
                "proxy_type": self.proxy_type,
                "cache_size": len(self._cache),
                "valid_count": valid_count,
                "target_size": self.CACHE_SIZE,
                "configured": self.is_configured(),
                "proxies": [
                    {
                        "latency_ms": p.latency_ms,
                        "remain_seconds": int(p.expire_time - time.time()),
                        "is_valid": p.is_valid,
                        "failed_count": p.failed_count
                    }
                    for p in self._cache
                ]
            }


# 全局代理池实例（每个抢票进程独立一个）
_proxy_pools: Dict[str, ProxyPool] = {}


def get_proxy_pool(process_id: str = "default", proxy_type: str = "none",
                   config: Dict[str, Any] = None) -> Optional[ProxyPool]:
    """
    获取代理池实例（每个进程独立）
    Args:
        process_id: 进程ID
        proxy_type: 代理类型 (none, juliang, shanchen)
        config: 配置字典
    Returns:
        ProxyPool实例或None（如果proxy_type为none）
    """
    global _proxy_pools

    # 如果代理类型为none，返回None
    if proxy_type == "none":
        return None

    if process_id not in _proxy_pools:
        pool = ProxyPool(proxy_type, config)
        pool.start()
        _proxy_pools[process_id] = pool
    else:
        # 更新配置
        _proxy_pools[process_id].set_config(proxy_type, config)

    return _proxy_pools[process_id]


def stop_proxy_pool(process_id: str):
    """停止指定进程的代理池"""
    global _proxy_pools
    if process_id in _proxy_pools:
        _proxy_pools[process_id].stop()
        del _proxy_pools[process_id]


def stop_all_proxy_pools():
    """停止所有代理池"""
    global _proxy_pools
    for pool in _proxy_pools.values():
        pool.stop()
    _proxy_pools.clear()


def get_proxy_manager(proxy_type: str, config: Dict[str, Any] = None):
    """
    获取代理管理器（用于即时获取代理，不经过代理池）
    Args:
        proxy_type: 代理类型
        config: 配置字典
    Returns:
        代理管理器实例
    """
    if proxy_type == "juliang":
        from .juliang_proxy import get_juliang_manager
        api_url = config.get("api_url", "") if config else ""
        return get_juliang_manager(api_url)
    elif proxy_type == "shanchen":
        from .shanchen_proxy import get_shanchen_manager
        api_key = config.get("api_key", "") if config else ""
        time_minutes = config.get("time_minutes", 1) if config else 1
        count = config.get("count", 3) if config else 3
        province = config.get("province", "") if config else ""
        city = config.get("city", "") if config else ""
        return get_shanchen_manager(api_key, time_minutes, count, province, city)
    else:
        return None
