#!/usr/bin/env python3
"""
诊断出口IP绑定问题
"""
import socket
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager


class SourceIPAdapter(HTTPAdapter):
    """自定义适配器，绑定源IP地址"""
    def __init__(self, source_ip, **kwargs):
        self.source_ip = source_ip
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs['source_address'] = (self.source_ip, 0)
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs
        )


def get_local_ips():
    """获取本机所有IP地址"""
    ips = []
    try:
        # 获取主机名
        hostname = socket.gethostname()
        # 获取本机IP
        local_ip = socket.gethostbyname(hostname)
        ips.append(("主机名解析", local_ip))
    except Exception as e:
        print(f"获取主机IP失败: {e}")

    # 尝试通过socket获取所有接口的IP
    try:
        import netifaces
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr_info in addrs[netifaces.AF_INET]:
                    ip = addr_info.get('addr')
                    if ip and ip != '127.0.0.1':
                        ips.append((interface, ip))
    except ImportError:
        print("netifaces模块未安装，跳过接口枚举")

    return ips


def test_source_ip_binding(source_ip):
    """测试源IP绑定是否可用"""
    print(f"\n测试绑定源IP: {source_ip}")
    print("-" * 50)

    # 检查IP格式
    try:
        socket.inet_aton(source_ip)
        print(f"✓ IP格式正确")
    except socket.error:
        print(f"✗ IP格式错误")
        return False

    # 检查IP是否在本机
    local_ips = get_local_ips()
    local_ip_list = [ip for _, ip in local_ips]
    if source_ip in local_ip_list:
        print(f"✓ IP {source_ip} 在本机接口中")
    else:
        print(f"✗ IP {source_ip} 不在本机接口中")
        print(f"  本机IP列表: {local_ip_list}")
        return False

    # 尝试绑定并请求
    try:
        session = requests.Session()
        session.mount('http://', SourceIPAdapter(source_ip))
        session.mount('https://', SourceIPAdapter(source_ip))

        # 测试请求
        print(f"  正在测试请求...")
        resp = session.get('https://httpbin.org/ip', timeout=10)
        print(f"✓ 请求成功")
        print(f"  返回IP: {resp.json().get('origin', 'unknown')}")
        return True
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def main():
    print("=" * 60)
    print("出口IP绑定诊断工具")
    print("=" * 60)

    # 显示本机所有IP
    print("\n本机IP地址:")
    print("-" * 50)
    local_ips = get_local_ips()
    if local_ips:
        for interface, ip in local_ips:
            print(f"  {interface}: {ip}")
    else:
        print("  未能获取IP列表")

    # 测试用户输入的IP
    import sys
    if len(sys.argv) > 1:
        test_ip = sys.argv[1]
        test_source_ip_binding(test_ip)
    else:
        print("\n使用方法: python diagnose_ip.py <要测试的IP>")
        print("例如: python diagnose_ip.py 192.168.1.100")


if __name__ == '__main__':
    main()
