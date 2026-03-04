import requests
import json
import time
import random
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from utils.signer.gen import generate_signature
from utils.urls import PAY_TICKET_URL, BASE_URL_WEB

# 创建 console 实例用于输出
console = Console()


def check_ip_blocked(response: requests.Response, result: dict) -> bool:
    """
    检查是否IP被风控
    Args:
        response: HTTP响应
        result: 解析后的JSON结果
    Returns:
        True: IP被风控, False: 正常
    """
    # 检查状态码是否为403
    if response.status_code == 403:
        return True
    
    # 检查返回内容中是否包含acl和custom关键字
    if isinstance(result, dict):
        message = str(result.get("message", ""))
        response_text = json.dumps(result, ensure_ascii=False)
        
        if "acl" in message.lower() or "custom" in message.lower():
            return True
        if "acl" in response_text.lower() and "custom" in response_text.lower():
            return True
    
    return False


def wait_if_ip_blocked(response: requests.Response, result: dict, debug_mode: bool = False) -> bool:
    """
    如果IP被风控，等待10分钟后重试
    Args:
        response: HTTP响应
        result: 解析后的JSON结果
        debug_mode: 是否开启调试模式
    Returns:
        True: IP被风控已等待, False: 正常
    """
    if check_ip_blocked(response, result):
        console.print("\n[bold red]⚠️ 警告：IP已被风控！[/bold red]")
        console.print("[yellow]检测到403错误且响应中包含acl/custom关键字[/yellow]")
        console.print("[yellow]等待10分钟后重试...[/yellow]")
        
        if debug_mode:
            console.print(f"[调试]响应状态码: {response.status_code}")
            console.print(f"[调试]响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 等待10分钟
        for i in range(600, 0, -1):
            if i % 60 == 0:
                console.print(f"[dim]剩余等待时间: {i//60}分钟[/dim]")
            time.sleep(1)
        
        console.print("[green]等待结束，继续重试...[/green]")
        return True
    
    return False


def generate_signature_params(ticket_type_id: str) -> dict:
    """
    生成签名参数
    """
    charset = "ABCDEFGHJKMNPQRSTWXYZ"
    nonce = ''.join(random.choices(charset, k=5))
    timestamp = int(time.time() * 1000)
    sign = generate_signature(timestamp, nonce, ticket_type_id)
    
    return {
        "nonce": nonce,
        "timeStamp": str(timestamp),
        "sign": sign
    }


def submit_ticket_order(session: requests.Session, ticket_id: str, purchaser_id: str, debug_mode: bool = False, count: int = 1) -> tuple[bool, bool, bool]:
    """
    提交购票订单（增加响应提示处理、随机延迟）
    Args:
        session: 请求会话
        ticket_id: 票种ID
        purchaser_id: 购买者ID
        debug_mode: 是否开启调试模式
        count: 购买数量，默认为1
    Returns:
        (是否成功, 是否需要重试, 是否应该停止)
    """
    retry_count = 0
    try:

        # 生成签名参数
        sign_params = generate_signature_params(ticket_id)

        # 构造请求数据
        request_data = {
            "timeStamp": sign_params["timeStamp"],
            "nonce": sign_params["nonce"],
            "sign": sign_params["sign"],
            "ticketTypeId": ticket_id,
            "count": count,
            "purchaserIds": purchaser_id
        }

        response = session.post(BASE_URL_WEB+PAY_TICKET_URL, json=request_data, timeout=10)
        
        # 检查是否IP被风控
        try:
            result = response.json()
        except:
            result = {}
        
        if wait_if_ip_blocked(response, result, debug_mode):
            return False, True, False  # 需要重试
        
        response.raise_for_status()
        
        # 处理响应提示
        message = result.get("message", "") if isinstance(result, dict) else str(result)
        
        # 检查是否限购/已购买
        if "限购" in message or "已购买" in message or "重复" in message:
            if debug_mode:
                console.print(f"[yellow][调试][限购提示] {message}[/yellow]")
            return False, False, True
        
        if "拥挤" in message:
            retry_count += 1
            if debug_mode:
                console.print(f"[yellow][调试][服务器卡顿] 请求阻塞，重试中（第{retry_count}次）[/yellow]")
            return False, True, False
        if "超时" in message:
            if debug_mode:
                console.print(f"[red][调试][下单报错] 请求超时，可能是网络不好，协议异常或者本地时间偏差[/red]")
            return False, False, False
        elif "余票" in message:
            if debug_mode:
                console.print(f"[yellow][调试][下单报错] 可用库存不足[/yellow]")
            return False, True, False
        elif result.get("isSuccess") == True:
            if debug_mode:
                console.print(f"[green][调试][下单成功] 抢票成功！[/green]")
                # 使用 Syntax 高亮显示 JSON
                result_json = json.dumps(result, ensure_ascii=False, indent=2)
                syntax = Syntax(result_json, "json", theme="monokai", line_numbers=False)
                console.print(Panel(syntax, title="响应内容", border_style="green"))
            
            # 获取 orderInfo 并转换为支付链接
            try:
                order_info = result.get("result", {}).get("orderInfo", "")
                if order_info:
                    from utils.payment.alipay_convert import AiliPay
                    alipay = AiliPay()
                    pay_url = alipay.convert_alipay_to_h5(order_info)
                    console.clear()
                    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
                    console.print(f"[bold blue][支付链接] {pay_url}[/bold blue]")
                    console.print(f"[bold yellow][提示] 请复制链接到浏览器打开支付，或打开手机 ALLCPP APP 支付[/bold yellow]")
                    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")
            except Exception as e:
                if debug_mode:
                    console.print(f"[red][调试][支付链接转换失败] {e}[/red]")
            
            return True, False, False
        else:
            if debug_mode:
                console.print(f"[red][调试][下单失败] 抢票失败！[/red]")
                result_json = json.dumps(result, ensure_ascii=False, indent=2)
                syntax = Syntax(result_json, "json", theme="monokai", line_numbers=False)
                console.print(Panel(syntax, title="响应内容", border_style="red"))
            return False, False, False
    except Exception as e:
        if debug_mode:
            console.print(f"[red][调试][下单失败] 提交订单失败: {e}[/red]")
        return False, True, False
