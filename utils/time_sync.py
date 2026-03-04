import time
import subprocess
import socket
import struct
from typing import Optional
from rich.console import Console

console = Console()


def get_ntp_offset(ntp_server: str = "ntp.aliyun.com") -> Optional[float]:
    """
    获取本地时间与阿里云NTP服务器的时间差（秒）
    Args:
        ntp_server: NTP服务器地址
    Returns:
        时间差（秒），失败返回None
    """
    try:
        NTP_PACKET_FORMAT = "!12I"
        NTP_DELTA = 2208988800
        NTP_QUERY = b'\x1b' + 47 * b'\0'

        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(5)
        
        client.sendto(NTP_QUERY, (ntp_server, 123))
        data, _ = client.recvfrom(1024)
        client.close()

        if len(data) < 48:
            return None

        unpacked = struct.unpack(NTP_PACKET_FORMAT, data[:48])
        ntp_time = unpacked[10] + unpacked[11] / 2.0 ** 32 - NTP_DELTA
        
        local_time = time.time()
        offset = ntp_time - local_time
        
        return offset
    except Exception as e:
        console.print(f"[red]获取NTP时间差失败: {e}[/red]")
        return None


def tc_ping(host: str, count: int = 10) -> Optional[float]:
    """
    使用TCP Ping测试到指定主机的延迟，返回平均延迟（毫秒）
    Args:
        host: 目标主机
        count: 测试次数
    Returns:
        平均延迟（毫秒），失败返回None
    """
    try:
        delays = []
        port = 443
        
        for i in range(count):
            start_time = time.time()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((host, port))
                sock.close()
                end_time = time.time()
                delay_ms = (end_time - start_time) * 1000
                delays.append(delay_ms)
            except Exception:
                delays.append(None)
        
        valid_delays = [d for d in delays if d is not None]
        if not valid_delays:
            return None
        
        avg_delay = sum(valid_delays) / len(valid_delays)
        return avg_delay
    except Exception as e:
        console.print(f"[red]TCP Ping失败: {e}[/red]")
        return None


def calculate_time_offset() -> Optional[float]:
    """
    计算总时间偏移量：NTP时间差 + TCP Ping平均延迟
    Returns:
        总时间偏移量（秒），失败返回None
    """
    console.print("\n[cyan]开始计算时间偏移量...[/cyan]")
    
    # 1. 获取NTP时间差
    console.print("[yellow]正在同步阿里云NTP时间...[/yellow]")
    ntp_offset = get_ntp_offset()
    if ntp_offset is None:
        console.print("[red]NTP时间同步失败[/red]")
        return None
    
    console.print(f"[green]NTP时间差: {ntp_offset*1000:.2f}ms[/green]")
    
    # 2. TCP Ping测试
    console.print("[yellow]正在TCP Ping www.allcpp.cn...[/yellow]")
    tcp_delay_ms = tc_ping("www.allcpp.cn", 10)
    if tcp_delay_ms is None:
        console.print("[red]TCP Ping失败[/red]")
        return None
    
    console.print(f"[green]TCP Ping平均延迟: {tcp_delay_ms:.2f}ms[/green]")
    
    # 3. 计算总偏移量
    total_offset = ntp_offset + (tcp_delay_ms / 1000)
    console.print(f"[cyan]总时间偏移量: {total_offset*1000:.2f}ms[/cyan]")
    
    return total_offset