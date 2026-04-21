#!/usr/bin/env python3
"""
测试出口IP是否可用
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


def test_exit_ip(exit_ip):
    """测试出口IP是否可用"""
    print(f"测试出口IP: {exit_ip}")
    print("-" * 60)
    
    # 1. 检查IP格式
    try:
        socket.inet_aton(exit_ip)
        print(f"✓ IP格式正确")
    except socket.error:
        print(f"✗ IP格式错误")
        return False
    
    # 2. 检查IP是否在本机
    import subprocess
    result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
    if exit_ip in result.stdout:
        print(f"✓ IP {exit_ip} 在本机网卡上")
    else:
        print(f"✗ IP {exit_ip} 不在本机网卡上")
        return False
    
    # 3. 尝试绑定并请求
    try:
        session = requests.Session()
        session.mount('http://', SourceIPAdapter(exit_ip))
        session.mount('https://', SourceIPAdapter(exit_ip))
        
        print(f"  正在测试HTTP请求...")
        resp = session.get('http://httpbin.org/ip', timeout=5)
        print(f"✓ HTTP请求成功")
        print(f"  返回IP: {resp.json().get('origin', 'unknown')}")
    except Exception as e:
        print(f"✗ HTTP请求失败: {e}")
        return False
    
    # 4. 尝试HTTPS请求
    try:
        print(f"  正在测试HTTPS请求...")
        resp = session.get('https://httpbin.org/ip', timeout=5)
        print(f"✓ HTTPS请求成功")
        print(f"  返回IP: {resp.json().get('origin', 'unknown')}")
        return True
    except Exception as e:
        print(f"✗ HTTPS请求失败: {e}")
        print(f"\n可能原因：")
        print(f"  1. 辅助IP需要配置独立的路由表")
        print(f"  2. UCloud的安全组规则限制")
        print(f"  3. 辅助IP的NAT映射问题")
        return False


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        test_exit_ip(sys.argv[1])
    else:
        print("用法: python test_exit_ip.py <IP地址>")
        print("例如: python test_exit_ip.py 10.23.208.230")
