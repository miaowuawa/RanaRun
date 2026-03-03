import os
import sys
import json
import time
import subprocess

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

from utils.session import env_to_request_session
from utils.ticket.purchase import submit_ticket_order
from utils.urls import CHECK_TICKET_URL, BASE_URL_WEB

console = Console()


def log_message(logs, message):
    """添加日志消息"""
    timestamp = time.strftime("%H:%M:%S")
    logs.append(f"[{timestamp}] {message}")
    # 只保留最近50条日志
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
    
    try:
        while True:
            check_count += 1
            
            # 检测余票
            try:
                check_url = f"{BASE_URL_WEB}{CHECK_TICKET_URL}{ticket_id}"
                response = session.get(check_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get("isSuccess"):
                    result = data.get("result", {})
                    current_stock = result.get("stock", 0)
                    
                    # 更新显示
                    if check_count % 10 == 0:  # 每10次检测显示一次状态
                        log_message(logs, f"检测中... 余票: {current_stock}")
                    
                    # 有余票则尝试下单
                    if current_stock > 0:
                        log_message(logs, f"[green]检测到余票: {current_stock}张[/green]")
                        
                        # 应用下单延迟
                        if order_delay > 0:
                            time.sleep(order_delay)
                        
                        if resale_mode == "split":
                            # 拆分回流模式：一次只下1张
                            order_attempts += 1
                            log_message(logs, f"第{order_attempts}次下单尝试（拆分模式，1张）...")
                            
                            # 获取购买人ID
                            purchaser_id = ""
                            if is_real_name and purchaser_id_list:
                                if purchaser_index < len(purchaser_id_list):
                                    purchaser_id = purchaser_id_list[purchaser_index]
                                else:
                                    # 购买人用完了，使用第一个
                                    purchaser_id = purchaser_id_list[0]
                            
                            success, need_retry, should_stop = submit_ticket_order(
                                session,
                                ticket_id,
                                purchaser_id,
                                debug_mode
                            )
                            
                            if success:
                                success_count += 1
                                purchaser_index += 1  # 下一个购买人
                                log_message(logs, f"[green]下单成功! 当前成功: {success_count}张[/green]")
                                console.print(f"\n[bold green]✓ 下单成功! 当前成功: {success_count}张[/bold green]")
                                
                                # 如果已经达到目标张数，停止
                                if success_count >= ticket_count:
                                    console.print(f"\n[bold green]已达到目标张数 {ticket_count}，停止抢票[/bold green]")
                                    break
                            elif should_stop:
                                # 限购/已购买，停止抢票
                                console.print(f"\n[bold yellow]检测到限购/已购买，停止抢票[/bold yellow]")
                                console.print("[yellow]该账号可能已经购买过此票种，请检查订单[/yellow]")
                                break
                            else:
                                if need_retry:
                                    log_message(logs, "[yellow]下单失败，需要重试[/yellow]")
                                else:
                                    log_message(logs, "[red]下单失败，无需重试[/red]")
                        
                        else:
                            # 合并回流模式：一次下单多张
                            order_attempts += 1
                            # 计算本次下单数量（剩余需要的张数）
                            remaining = ticket_count - success_count
                            order_count = min(remaining, current_stock)
                            
                            log_message(logs, f"第{order_attempts}次下单尝试（合并模式，{order_count}张）...")
                            
                            # 获取购买人ID（合并模式需要多个购买人）
                            purchaser_id = ""
                            if is_real_name and purchaser_id_list:
                                # 取需要的购买人ID
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
                                console.print(f"\n[bold green]✓ 下单成功! 本次{order_count}张，当前成功: {success_count}张[/bold green]")
                                
                                # 如果已经达到目标张数，停止
                                if success_count >= ticket_count:
                                    console.print(f"\n[bold green]已达到目标张数 {ticket_count}，停止抢票[/bold green]")
                                    break
                            elif should_stop:
                                # 限购/已购买，停止抢票
                                console.print(f"\n[bold yellow]检测到限购/已购买，停止抢票[/bold yellow]")
                                console.print("[yellow]该账号可能已经购买过此票种，请检查订单[/yellow]")
                                break
                            else:
                                if need_retry:
                                    log_message(logs, "[yellow]下单失败，需要重试[/yellow]")
                                else:
                                    log_message(logs, "[red]下单失败，无需重试[/red]")
                
                # 等待刷新延迟
                time.sleep(refresh_delay)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log_message(logs, f"[red]检测出错: {e}[/red]")
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
        response.raise_for_status()
        result = response.json()

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
    if len(sys.argv) < 2:
        console.print("[red]错误: 未提供配置文件路径[/red]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        console.print(f"[red]错误: 配置文件不存在: {config_file}[/red]")
        sys.exit(1)
    
    run_resale_mode(config_file)
