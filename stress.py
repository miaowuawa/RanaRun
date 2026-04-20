#!/usr/bin/env python3
"""
压力测试脚本 - 测试下单延迟阈值
功能：逐渐降低延迟进行下单测试，检测ACL触发点
"""

import json
import time
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, IntPrompt, FloatPrompt
from rich import box

from utils.env2sess import env_to_request_session
from utils.ticket.purchase import submit_ticket_order, check_ip_blocked

console = Console()


def load_env_files():
    """加载环境文件列表"""
    env_files = []
    try:
        for file in os.listdir("."):
            if file.startswith("environment_") and file.endswith(".json"):
                env_files.append(file)
    except Exception as e:
        console.print(f"[red]读取环境文件失败: {e}[/red]")
    return env_files


def select_env_file():
    """选择环境文件"""
    env_files = load_env_files()
    
    if not env_files:
        console.print("[red]没有找到环境文件，请先创建环境[/red]")
        return None
    
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("文件名", style="green")
    
    for idx, file in enumerate(env_files, 1):
        table.add_row(str(idx), file)
    
    console.print(table)
    
    choice = Prompt.ask("请选择环境文件序号", choices=[str(i) for i in range(1, len(env_files) + 1)])
    return env_files[int(choice) - 1]


def check_acl_triggered(response, result):
    """检查是否触发ACL控制"""
    if response is None:
        return False
    
    # 使用已有的check_ip_blocked函数
    if check_ip_blocked(response, result):
        return True
    
    # 额外检查ACL关键词
    if isinstance(result, dict):
        message = str(result.get("message", "")).lower()
        if "acl" in message or "风控" in message or "限制" in message:
            return True
    
    return False


def stress_test(env_file, ticket_id, purchaser_id, start_delay_ms, min_delay_ms, 
                delay_step_ms, orders_per_batch, rest_interval_sec, max_orders):
    """
    压力测试主函数
    
    Args:
        env_file: 环境文件路径
        ticket_id: 票种ID
        purchaser_id: 购买人ID
        start_delay_ms: 初始延迟（毫秒）
        min_delay_ms: 最小延迟（毫秒）
        delay_step_ms: 每次降低延迟的步长（毫秒）
        orders_per_batch: 每批次下单次数
        rest_interval_sec: 批次间休息间隔（秒）
        max_orders: 最大下单次数
    """
    # 加载环境
    with open(env_file, "r", encoding="utf-8") as f:
        env = json.load(f)
    
    session = env_to_request_session(env)
    
    console.print(Panel(
        f"[bold cyan]压力测试配置[/bold cyan]\n"
        f"环境文件: {env_file}\n"
        f"票种ID: {ticket_id}\n"
        f"购买人ID: {purchaser_id}\n"
        f"初始延迟: {start_delay_ms}ms\n"
        f"最小延迟: {min_delay_ms}ms\n"
        f"延迟步长: {delay_step_ms}ms\n"
        f"每批次下单: {orders_per_batch}次\n"
        f"批次间隔: {rest_interval_sec}秒\n"
        f"最大下单: {max_orders}次",
        border_style="cyan"
    ))
    
    if not Prompt.ask("\n确认开始测试?", choices=["y", "n"], default="y") == "y":
        console.print("[yellow]已取消测试[/yellow]")
        return
    
    current_delay_ms = start_delay_ms
    total_orders = 0
    success_count = 0
    acl_triggered = False
    acl_delay_ms = None
    
    # 测试结果记录
    results = []
    
    console.print("\n[bold green]开始压力测试...[/bold green]\n")
    
    try:
        while current_delay_ms >= min_delay_ms and total_orders < max_orders and not acl_triggered:
            console.print(f"\n[bold cyan]当前延迟: {current_delay_ms}ms[/bold cyan]")
            console.print("-" * 50)
            
            batch_success = 0
            batch_fail = 0
            
            for i in range(orders_per_batch):
                if total_orders >= max_orders:
                    break
                
                total_orders += 1
                
                # 执行下单
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[progress.description]第 {i+1}/{orders_per_batch} 次下单 (延迟 {current_delay_ms}ms)..."),
                    console=console,
                    transient=True
                ) as progress:
                    progress.add_task("ordering")
                    
                    # 延迟
                    time.sleep(current_delay_ms / 1000)
                    
                    # 下单
                    success, need_retry, should_stop = submit_ticket_order(
                        session, ticket_id, purchaser_id, debug_mode=True, count=1
                    )
                
                if success:
                    batch_success += 1
                    success_count += 1
                    console.print(f"  [green]✓ 下单成功 ({total_orders}/{max_orders})[/green]")
                else:
                    batch_fail += 1
                    console.print(f"  [red]✗ 下单失败 ({total_orders}/{max_orders})[/red]")
                
                # 检查是否需要停止（限购等情况）
                if should_stop:
                    console.print(f"\n[yellow]检测到限购或重复购买，停止测试[/yellow]")
                    acl_triggered = True
                    acl_delay_ms = current_delay_ms
                    break
                
                # 短暂间隔避免瞬间爆发
                time.sleep(0.1)
            
            # 记录本批次结果
            results.append({
                "delay_ms": current_delay_ms,
                "success": batch_success,
                "fail": batch_fail,
                "acl_triggered": acl_triggered
            })
            
            # 显示本批次统计
            console.print(f"\n[dim]本批次统计: 成功 {batch_success}, 失败 {batch_fail}[/dim]")
            
            # 降低延迟进入下一批次
            if not acl_triggered and current_delay_ms > min_delay_ms:
                current_delay_ms = max(min_delay_ms, current_delay_ms - delay_step_ms)
                
                # 批次间休息
                if current_delay_ms >= min_delay_ms and total_orders < max_orders:
                    console.print(f"\n[yellow]休息 {rest_interval_sec} 秒后继续...[/yellow]")
                    time.sleep(rest_interval_sec)
                    
                    # 刷新session
                    session = env_to_request_session(env)
    
    except KeyboardInterrupt:
        console.print("\n\n[yellow]用户中断测试[/yellow]")
    
    # 显示最终报告
    show_stress_report(results, acl_triggered, acl_delay_ms, total_orders, success_count)


def show_stress_report(results, acl_triggered, acl_delay_ms, total_orders, success_count):
    """显示压力测试报告"""
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]压力测试报告[/bold cyan]")
    console.print("=" * 60)
    
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("延迟(ms)", style="cyan")
    table.add_column("成功", style="green")
    table.add_column("失败", style="red")
    table.add_column("状态", style="yellow")
    
    for r in results:
        status = "[red]ACL触发[/red]" if r["acl_triggered"] else "[green]正常[/green]"
        table.add_row(
            str(r["delay_ms"]),
            str(r["success"]),
            str(r["fail"]),
            status
        )
    
    console.print(table)
    
    console.print(f"\n[bold]总下单次数:[/bold] {total_orders}")
    console.print(f"[bold]成功次数:[/bold] {success_count}")
    console.print(f"[bold]成功率:[/bold] {(success_count/total_orders*100):.1f}%" if total_orders > 0 else "N/A")
    
    if acl_triggered and acl_delay_ms:
        console.print(f"\n[bold red]⚠️ ACL控制触发点: {acl_delay_ms}ms[/bold red]")
        console.print(f"[yellow]建议: 使用高于 {acl_delay_ms}ms 的延迟进行抢票[/yellow]")
    else:
        console.print(f"\n[green]✓ 测试完成，未触发ACL控制[/green]")
    
    console.print("=" * 60)


def main():
    """主函数"""
    console.print(Panel(
        "[bold cyan]RanaRun 压力测试工具[/bold cyan]\n"
        "测试下单延迟阈值，检测ACL触发点",
        box.DOUBLE,
        padding=(1, 2)
    ))
    
    # 选择环境文件
    console.print("\n[bold]步骤1: 选择环境文件[/bold]")
    env_file = select_env_file()
    if not env_file:
        return
    
    # 输入票种ID
    console.print("\n[bold]步骤2: 输入购票信息[/bold]")
    ticket_id = Prompt.ask("票种ID")
    if not ticket_id:
        console.print("[red]票种ID不能为空[/red]")
        return
    
    purchaser_id = Prompt.ask("购买人ID")
    if not purchaser_id:
        console.print("[red]购买人ID不能为空[/red]")
        return
    
    # 配置测试参数
    console.print("\n[bold]步骤3: 配置测试参数[/bold]")
    
    start_delay_ms = IntPrompt.ask("初始延迟(ms)", default=500)
    min_delay_ms = IntPrompt.ask("最小延迟(ms)", default=50)
    delay_step_ms = IntPrompt.ask("延迟降低步长(ms)", default=50)
    orders_per_batch = IntPrompt.ask("每批次下单次数", default=3)
    rest_interval_sec = IntPrompt.ask("批次间休息间隔(秒)", default=5)
    max_orders = IntPrompt.ask("最大总下单次数", default=30)
    
    # 确认配置
    console.print("\n[bold yellow]请确认测试配置:[/bold yellow]")
    console.print(f"  将从 {start_delay_ms}ms 开始，每次降低 {delay_step_ms}ms")
    console.print(f"  直到 {min_delay_ms}ms 或触发ACL")
    console.print(f"  每批次 {orders_per_batch} 次下单，休息 {rest_interval_sec} 秒")
    console.print(f"  最大下单 {max_orders} 次")
    
    if not Prompt.ask("\n开始测试?", choices=["y", "n"], default="y") == "y":
        console.print("[yellow]已取消[/yellow]")
        return
    
    # 开始测试
    stress_test(
        env_file=env_file,
        ticket_id=ticket_id,
        purchaser_id=purchaser_id,
        start_delay_ms=start_delay_ms,
        min_delay_ms=min_delay_ms,
        delay_step_ms=delay_step_ms,
        orders_per_batch=orders_per_batch,
        rest_interval_sec=rest_interval_sec,
        max_orders=max_orders
    )


if __name__ == "__main__":
    main()
