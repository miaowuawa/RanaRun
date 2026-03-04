import os
import sys
import json
import time
import subprocess
import random

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.live import Live
from rich.layout import Layout
from rich.syntax import Syntax

from utils.env2sess import env_to_request_session
from utils.ticket.purchase import submit_ticket_order
from utils.ticket.check import get_ticket_type_list

console = Console()


def get_random_delay_ms(base_delay_ms: int) -> float:
    """
    生成随机延迟（基准延迟 ± 10-50ms）
    Args:
        base_delay_ms: 基准延迟（毫秒）
    Returns:
        随机延迟（秒）
    """
    random_offset = random.uniform(-0.05, 0.05)
    ms_delay = random.uniform(0.01, 0.05)
    actual_delay = (base_delay_ms / 1000) + random_offset + ms_delay
    return max(0.01, actual_delay)


def log_message(logs, message):
    """添加日志消息，合并重复消息"""
    timestamp = time.strftime("%H:%M:%S")
    new_log = f"[{timestamp}] {message}"
    
    if logs:
        last_log = logs[-1]
        if "无票，继续尝试刷新" in last_log:
            import re
            match = re.search(r'无票，继续尝试刷新.*?(\d+)次\)$', last_log)
            if match:
                count = int(match.group(1)) + 1
                logs[-1] = re.sub(r'\(\d+次\)$', f'({count}次)', last_log)
                return
            elif "无票，继续尝试刷新……" in last_log and "次" not in last_log:
                logs[-1] = last_log.replace("无票，继续尝试刷新……", "无票，继续尝试刷新…… (2次)")
                return
    
    logs.append(new_log)
    if len(logs) > 50:
        logs.pop(0)


def create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_name):
    """创建状态显示表格"""
    layout = Layout()
    
    # 状态信息
    status_text = Text()
    status_text.append(f"票种: {ticket_name}\n", style="bold cyan")
    status_text.append(f"检测次数: {check_count}\n", style="green")
    status_text.append(f"下单尝试: {order_attempts}\n", style="yellow")
    status_text.append(f"成功: {success_count}/{ticket_count}\n", style="bold green" if success_count >= ticket_count else "green")
    status_text.append(f"当前余票: {current_stock}", style="cyan" if current_stock > 0 else "red")
    
    # 日志区域
    log_text = Text("\n".join(logs[-20:]))  # 显示最近20条日志
    
    layout.split_column(
        Layout(Panel(status_text, title="抢票状态", border_style="cyan"), size=8),
        Layout(Panel(log_text, title="日志", border_style="dim"))
    )
    
    return layout


def run_resale_mode(config_file):
    """运行回流模式抢票"""
    # 读取配置
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 加载环境
    with open(config["env_file"], "r", encoding="utf-8") as f:
        env = json.load(f)
    
    # 创建会话
    session = env_to_request_session(env)
    
    ticket_info = config["ticket_info"]
    ticket_id = str(ticket_info.get("id"))
    event_id = config.get("event_id", "")
    ticket_count = config.get("ticket_count", 1)
    resale_mode = config.get("resale_mode", "split")  # split=拆分回流, merge=合并回流
    refresh_delay = config.get("refresh_delay", 150) / 1000  # 转换为秒
    order_delay = config.get("order_delay", 150) / 1000  # 转换为秒
    purchaser_ids = config.get("purchaser_ids", "")
    debug_mode = config.get("debug_mode", False)  # 调试模式
    
    is_real_name = ticket_info.get("realnameAuth") or ticket_info.get("isRealName", False)
    
    # 解析购买人ID列表
    purchaser_id_list = []
    if purchaser_ids:
        purchaser_id_list = [pid.strip() for pid in purchaser_ids.split(",") if pid.strip()]
    
    console.clear()
    console.print(Panel(
        Text("RanaRun - 回流模式抢票中", style="bold cyan"),
        box.DOUBLE,
        padding=(1, 2)
    ))
    
    mode_text = "拆分回流（每单1张）" if resale_mode == "split" else "合并回流（每单多张）"
    console.print(f"\n[green]票种:[/green] {ticket_info.get('ticketName') or ticket_info.get('name', '')}")
    console.print(f"[green]目标张数:[/green] {ticket_count}")
    console.print(f"[green]回流模式:[/green] {mode_text}")
    console.print(f"[green]刷新延迟:[/green] {refresh_delay * 1000:.0f}ms")
    console.print(f"[green]下单延迟:[/green] {order_delay * 1000:.0f}ms")
    console.print(f"[green]调试模式:[/green] {'开启' if debug_mode else '关闭'}")
    console.print("\n[cyan]按 Ctrl+C 停止抢票[/cyan]\n")
    
    logs = []
    check_count = 0
    order_attempts = 0
    success_count = 0
    purchaser_index = 0  # 当前使用的购买人索引（拆分模式用）
    current_stock = 0
    
    # 创建初始状态表格
    layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
    
    try:
        with Live(layout, console=console, refresh_per_second=4, screen=False) as live:
            while True:
                check_count += 1
                
                # 检测余票 - 使用check.py中的函数
                try:
                    ticket_data = get_ticket_type_list(session, event_id, refresh_delay)
                    
                    if ticket_data and "ticketTypeList" in ticket_data:
                        ticket_list = ticket_data.get("ticketTypeList", [])
                        
                        # 查找目标票种的库存
                        current_stock = 0
                        for ticket in ticket_list:
                            if str(ticket.get("id")) == ticket_id:
                                current_stock = ticket.get("remainderNum", 0)
                                break
                        
                        # 有余票则尝试下单
                        if current_stock > 0:
                            log_message(logs, f"[green]检测到余票: {current_stock}张[/green]")
                            layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                            live.update(layout)
                            
                            # 应用下单延迟（带随机偏移）
                            if order_delay > 0:
                                actual_delay = get_random_delay_ms(int(order_delay * 1000))
                                time.sleep(actual_delay)
                            
                            if resale_mode == "split":
                                # 拆分回流模式：一次只下1张
                                order_attempts += 1
                                log_message(logs, f"第{order_attempts}次下单尝试（拆分模式，1张）...")
                                layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                live.update(layout)
                                
                                # 获取购买人ID
                                purchaser_id = ""
                                if is_real_name and purchaser_id_list:
                                    if purchaser_index < len(purchaser_id_list):
                                        purchaser_id = purchaser_id_list[purchaser_index]
                                    else:
                                        purchaser_id = purchaser_id_list[0]
                                
                                success, need_retry, should_stop = submit_ticket_order(
                                    session,
                                    ticket_id,
                                    purchaser_id,
                                    debug_mode
                                )
                                
                                if success:
                                    success_count += 1
                                    purchaser_index += 1
                                    log_message(logs, f"[green]下单成功! 当前成功: {success_count}张[/green]")
                                    layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                    live.update(layout)
                                    
                                    if success_count >= ticket_count:
                                        log_message(logs, f"[green]已达到目标张数 {ticket_count}，停止抢票[/green]")
                                        layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                        live.update(layout)
                                        break
                                elif should_stop:
                                    log_message(logs, "[yellow]检测到限购/已购买，停止抢票[/yellow]")
                                    layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                    live.update(layout)
                                    break
                                else:
                                    if need_retry:
                                        log_message(logs, "[yellow]下单失败，需要重试[/yellow]")
                                    else:
                                        log_message(logs, "[red]下单失败，无需重试[/red]")
                                    layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                    live.update(layout)
                            
                            else:
                                # 合并回流模式：一次下单多张
                                order_attempts += 1
                                remaining = ticket_count - success_count
                                order_count = min(remaining, current_stock)
                                
                                log_message(logs, f"第{order_attempts}次下单尝试（合并模式，{order_count}张）...")
                                layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                live.update(layout)
                                
                                purchaser_id = ""
                                if is_real_name and purchaser_id_list:
                                    needed_count = min(order_count, len(purchaser_id_list))
                                    purchaser_id = ",".join(purchaser_id_list[:needed_count])
                                
                                success, need_retry, should_stop = submit_ticket_order_merge(
                                    session,
                                    ticket_id,
                                    purchaser_id,
                                    order_count,
                                    debug_mode
                                )
                                
                                if success:
                                    success_count += order_count
                                    log_message(logs, f"[green]下单成功! 当前成功: {success_count}张[/green]")
                                    layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                    live.update(layout)
                                    
                                    if success_count >= ticket_count:
                                        log_message(logs, f"[green]已达到目标张数 {ticket_count}，停止抢票[/green]")
                                        layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                        live.update(layout)
                                        break
                                elif should_stop:
                                    log_message(logs, "[yellow]检测到限购/已购买，停止抢票[/yellow]")
                                    layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                    live.update(layout)
                                    break
                                else:
                                    if need_retry:
                                        log_message(logs, "[yellow]下单失败，需要重试[/yellow]")
                                    else:
                                        log_message(logs, "[red]下单失败，无需重试[/red]")
                                    layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                                    live.update(layout)
                        else:
                            # 无票，记录日志
                            log_message(logs, "无票，继续尝试刷新……")
                            layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                            live.update(layout)
                    else:
                        # 请求失败
                        log_message(logs, "[red]检测失败，正在重试...[/red]")
                        layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                        live.update(layout)
                    
                    # 等待刷新延迟（带随机偏移）
                    actual_refresh_delay = get_random_delay_ms(int(refresh_delay * 1000))
                    time.sleep(actual_refresh_delay)
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    log_message(logs, f"[red]检测出错: {e}[/red]")
                    layout = create_status_table(check_count, order_attempts, success_count, ticket_count, current_stock, logs, ticket_info.get('ticketName') or ticket_info.get('name', ''))
                    live.update(layout)
                    time.sleep(refresh_delay)
    
    except KeyboardInterrupt:
        console.print("\n\n[yellow]用户取消抢票[/yellow]")
    
    console.print(f"\n[bold]抢票结束[/bold]")
    console.print(f"检测次数: {check_count}")
    console.print(f"下单尝试: {order_attempts}")
    console.print(f"成功: {success_count}/{ticket_count}")
    
    if success_count > 0:
        console.print("\n[green]请前往 ALLCPP APP 或网站查看订单并完成支付[/green]")
    
    console.print("\n按回车键退出...")
    input()


def submit_ticket_order_merge(session, ticket_id: str, purchaser_id: str, count: int, debug_mode: bool = False) -> tuple[bool, bool, bool]:
    """提交购票订单（合并模式，一次多张）"""
    from utils.ticket.purchase import generate_signature_params
    from utils.urls import PAY_TICKET_URL, BASE_URL_WEB
    
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

        response = session.post(BASE_URL_WEB + PAY_TICKET_URL, json=request_data, timeout=10)
        
        # 检查是否IP被风控
        try:
            result = response.json()
        except:
            result = {}
        
        from utils.ticket.check import wait_if_ip_blocked
        if wait_if_ip_blocked(response, result):
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
            if debug_mode:
                console.print(f"[yellow][调试][服务器卡顿] 请求阻塞，重试中[/yellow]")
            return False, True, False
        if "超时" in message:
            if debug_mode:
                console.print(f"[red][调试][下单报错] 请求超时[/red]")
            return False, False, False
        elif "余票" in message:
            if debug_mode:
                console.print(f"[yellow][调试][下单报错] 可用库存不足[/yellow]")
            return False, True, False
        elif result.get("isSuccess") == True:
            if debug_mode:
                console.print(f"[green][调试][下单成功] 抢票成功！[/green]")
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


if __name__ == "__main__":
    try:
        if len(sys.argv) < 2:
            console.print("[red]错误: 未提供配置文件路径[/red]")
            sys.exit(1)
        
        config_file = sys.argv[1]
        if not os.path.exists(config_file):
            console.print(f"[red]错误: 配置文件不存在: {config_file}[/red]")
            sys.exit(1)
        
        run_resale_mode(config_file)
    except KeyboardInterrupt:
        console.print("\n[yellow]程序已被用户中断[/yellow]")
    except Exception as e:
        console.print(f"[red]程序运行出错: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        console.print("\n[yellow]请按任意键继续...[/yellow]")
        input()
