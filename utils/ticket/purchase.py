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
    检查是否IP被风控 (ACL)
    注意：必须是403状态码 + 包含acl/custom关键字才是ACL
    只有403可能是登录过期或其他问题
    Args:
        response: HTTP响应
        result: 解析后的JSON结果
    Returns:
        True: IP被ACL风控, False: 正常
    """
    # 必须是403状态码
    if response.status_code != 403:
        return False
    
    # 检查返回内容中是否包含acl和custom关键字
    if isinstance(result, dict):
        message = str(result.get("message", "")).lower()
        response_text = json.dumps(result, ensure_ascii=False).lower()
        
        # 必须同时包含acl和custom关键字
        if ("acl" in message and "custom" in message) or \
           ("acl" in response_text and "custom" in response_text):
            return True
    
    return False


def wait_if_ip_blocked(response: requests.Response, result: dict, debug_mode: bool = False, notifier=None) -> bool:
    """
    如果IP被风控，等待10分钟后重试
    Args:
        response: HTTP响应
        result: 解析后的JSON结果
        debug_mode: 是否开启调试模式
        notifier: 可选的通知器，用于发送ACL通知
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
        
        # 发送ACL通知
        if notifier and hasattr(notifier, 'enabled') and notifier.enabled:
            try:
                notifier.notify_acl_blocked(wait_minutes=10)
            except Exception:
                pass  # 通知失败不影响主流程
        
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
    result, retry, should_stop, _ = submit_ticket_order_with_details(session, ticket_id, purchaser_id, debug_mode, count)
    return result, retry, should_stop


def submit_ticket_order_with_details(session: requests.Session, ticket_id: str, purchaser_id: str, debug_mode: bool = False, count: int = 1, notifier=None, juliang_api_url: str = "") -> tuple[bool, bool, bool, dict]:
    """
    提交购票订单（增加响应提示处理、随机延迟），返回详细信息包括支付链接
    Args:
        session: 请求会话
        ticket_id: 票种ID
        purchaser_id: 购买者ID
        debug_mode: 是否开启调试模式
        count: 购买数量，默认为1
        notifier: 可选的通知器，用于发送ACL通知
        juliang_api_url: 巨量代理API地址，用于请求频繁时切换代理
    Returns:
        (是否成功, 是否需要重试, 是否应该停止, 详细信息字典)
    """
    retry_count = 0
    details = {
        "success": False,
        "pay_url": None,
        "order_info": None,
        "message": None,
        "raw_response": None
    }
    
    try:
        # 初始化巨量代理管理器
        from utils.proxy.juliang_proxy import get_juliang_manager
        juliang_manager = get_juliang_manager(juliang_api_url)

        # 调试输出：显示代理管理器状态
        console.print(f"[dim][调试] 巨量代理API URL: {juliang_api_url[:50] if juliang_api_url else '未配置'}...[/dim]")
        console.print(f"[dim][调试] 巨量代理管理器已配置: {juliang_manager.is_configured()}[/dim]")
        console.print(f"[dim][调试] 当前session代理: {session.proxies if session.proxies else '无'}[/dim]")

        # 如果配置了巨量代理，确保session使用代理
        if juliang_manager.is_configured():
            # 检查是否需要获取/更换代理
            need_new_proxy = False
            if not session.proxies:
                # session没有设置代理，需要获取
                need_new_proxy = True
                console.print("[yellow][巨量代理] session未设置代理，获取新代理...[/yellow]")
            elif juliang_manager.is_proxy_expiring():
                # 代理即将过期，需要更换
                need_new_proxy = True
                console.print("[yellow][巨量代理] 代理即将过期，更换新代理...[/yellow]")

            if need_new_proxy:
                new_proxy = juliang_manager.fetch_proxy()
                if new_proxy:
                    session.proxies = new_proxy
                    console.print(f"[green][巨量代理] 已设置代理: {new_proxy['http'][:40]}...[/green]")
                else:
                    console.print("[red][巨量代理] 获取代理失败[/red]")

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

        # 调试输出：显示当前使用的代理
        if debug_mode:
            if session.proxies:
                proxy_info = session.proxies.get('http', '无')
                console.print(f"[dim][调试] 使用代理: {proxy_info[:50]}...[/dim]")
            else:
                console.print(f"[dim][调试] 未使用代理[/dim]")

        response = session.post(BASE_URL_WEB+PAY_TICKET_URL, json=request_data, timeout=10)

        # 检查是否IP被风控
        try:
            result = response.json()
            details["raw_response"] = result
        except:
            result = {}

        # 调试模式：始终打印响应状态和内容摘要
        if debug_mode:
            console.print(f"[dim][调试] HTTP状态码: {response.status_code}[/dim]")
            console.print(f"[dim][调试] 响应摘要: {str(result)[:200]}...[/dim]")

        # 检查是否IP被风控(ACL)
        if check_ip_blocked(response, result):
            console.print("\n[bold red]⚠️ 警告：IP已被风控(ACL)！[/bold red]")

            # 配置了巨量代理时，立即切换代理而不是等待
            if juliang_manager.is_configured():
                console.print("[yellow][ACL] 检测到ACL，立即切换代理...[/yellow]")
                new_proxy = juliang_manager.rotate_proxy()
                if new_proxy:
                    session.proxies = new_proxy
                    console.print(f"[green][巨量代理] ACL后已切换到新代理: {new_proxy['http'][:40]}...[/green]")
                    console.print(f"[green][巨量代理] 新代理有效期: {juliang_manager.proxy_remain_seconds}秒[/green]")
                else:
                    console.print("[red][巨量代理] 获取新代理失败[/red]")

                # 发送ACL通知
                if notifier and hasattr(notifier, 'enabled') and notifier.enabled:
                    try:
                        notifier.notify_acl_blocked(wait_minutes=0)  # 不等待，直接切换
                    except Exception:
                        pass

                return False, True, False, details  # 重试，使用新代理
            else:
                # 没有配置巨量代理，执行原等待逻辑
                console.print("[yellow]未配置巨量代理，执行等待...[/yellow]")
                wait_if_ip_blocked(response, result, debug_mode, notifier)
                return False, True, False, details  # 需要重试

        response.raise_for_status()

        # 处理响应提示
        message = result.get("message", "") if isinstance(result, dict) else str(result)
        details["message"] = message
        
        # 检查是否限购/已购买
        if "限购" in message or "已购买" in message or "重复" in message:
            if debug_mode:
                console.print(f"[yellow][调试][限购提示] {message}[/yellow]")
            return False, False, True, details
        
        elif "拥挤" in message:
            retry_count += 1
            if debug_mode:
                console.print(f"[yellow][调试][通道拥挤] 抢票通道拥挤，建议启用猛攻模式快速重试[/yellow]")
            # 不等待，直接返回让上层启用猛攻模式
            return False, True, False, details
        elif "超时" in message:
            if debug_mode:
                console.print(f"[red][调试][下单报错] 请求超时，可能是网络不好，协议异常或者本地时间偏差[/red]")
            return False, True, False, details
        elif "余票" in message:
            if debug_mode:
                console.print(f"[yellow][调试][下单报错] 可用库存不足[/yellow]")
            return False, True, False, details
        elif "开票时间未到" in message or "未开始" in message:
            if debug_mode:
                console.print(f"[yellow][调试][下单报错] 开票时间未到，等待后重试...[/yellow]")
            # 等待1秒后重试，避免频繁请求
            import time
            time.sleep(1)
            return False, True, False, details
        elif "频繁" in message:
            if debug_mode:
                console.print(f"[yellow][调试][请求频繁] 请求过于频繁，尝试切换代理...[/yellow]")
            console.print(f"[yellow][请求频繁] 检测到请求过于频繁，准备切换代理...[/yellow]")
            
            # 尝试切换巨量代理 - 请求频繁时立即强制更换，不等待
            if juliang_manager.is_configured():
                console.print(f"[yellow][巨量代理] 正在获取新代理...[/yellow]")
                # 使用 rotate_proxy 强制立即更换，而不是 mark_proxy_failed
                new_proxy = juliang_manager.rotate_proxy()
                if new_proxy:
                    session.proxies = new_proxy
                    console.print(f"[green][巨量代理] 已切换到新代理: {new_proxy['http'][:40]}...[/green]")
                    console.print(f"[green][巨量代理] 新代理有效期: {juliang_manager.proxy_remain_seconds}秒[/green]")
                    console.print(f"[green][巨量代理] 已切换代理，立即继续抢票，无需等待！[/green]")
                else:
                    console.print(f"[red][巨量代理] 获取新代理失败，等待3秒后重试...[/red]")
                    import time
                    time.sleep(3)
            else:
                # 没有配置巨量代理，等待5秒后重试
                console.print(f"[yellow]未配置巨量代理，等待5秒后重试...[/yellow]")
                import time
                time.sleep(5)
            
            return False, True, False, details
        elif result.get("isSuccess") == True:
            if debug_mode:
                console.print(f"[green][调试][下单成功] 抢票成功！[/green]")
                # 使用 Syntax 高亮显示 JSON
                result_json = json.dumps(result, ensure_ascii=False, indent=2)
                syntax = Syntax(result_json, "json", theme="monokai", line_numbers=False)
                console.print(Panel(syntax, title="响应内容", border_style="green"))
            
            details["success"] = True
            
            # 获取 orderInfo 并转换为支付链接
            try:
                order_info = result.get("result", {}).get("orderInfo", "")
                details["order_info"] = order_info
                if order_info:
                    from utils.payment.alipay_convert import AiliPay
                    alipay = AiliPay()
                    pay_url = alipay.convert_alipay_to_h5(order_info)
                    details["pay_url"] = pay_url
                    console.clear()
                    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
                    console.print(f"[bold blue][支付链接] {pay_url}[/bold blue]")
                    console.print(f"[bold yellow][提示] 请复制链接到浏览器打开支付，或打开手机 ALLCPP APP 支付[/bold yellow]")
                    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")
            except Exception as e:
                if debug_mode:
                    console.print(f"[red][调试][支付链接转换失败] {e}[/red]")
            
            return True, False, False, details
        else:
            if debug_mode:
                console.print(f"[red][调试][下单失败] 抢票失败！[/red]")
                result_json = json.dumps(result, ensure_ascii=False, indent=2)
                syntax = Syntax(result_json, "json", theme="monokai", line_numbers=False)
                console.print(Panel(syntax, title="响应内容", border_style="red"))
            return False, False, False, details
    except Exception as e:
        details["message"] = str(e)
        if debug_mode:
            console.print(f"[red][调试][下单失败] 提交订单失败: {e}[/red]")
        return False, True, False, details
