import json
import time
import sys
import os
import subprocess
import random
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def submit_ticket_order(session, ticket_id: str, purchaser_ids: str, count: int, debug_mode: bool = False) -> tuple[bool, bool]:
    """
    提交购票订单
    Args:
        session: 请求会话
        ticket_id: 票种ID
        purchaser_ids: 购买者ID列表（逗号分隔）
        count: 购买数量
        debug_mode: 是否开启调试模式
    Returns:
        (是否成功, 是否需要重试)
    """
    try:
        from utils.ticket.purchase import submit_ticket_order as submit_order
        
        result, retry, should_stop = submit_order(session, ticket_id, purchaser_ids, debug_mode, count)
        
        # 调试模式下打印详细返回信息
        if debug_mode and not result:
            console.print(f"[dim][调试] 下单结果: 成功={result}, 重试={retry}, 停止={should_stop}[/dim]")
        
        return result, retry
    except Exception as e:
        if debug_mode:
            console.print(f"[red][下单失败] 提交订单失败: {e}[/red]")
        return False, True


def run_presale_mode(config_file):
    """运行预售模式抢票"""
    import random
    
    # 读取配置
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 加载环境
    with open(config["env_file"], "r", encoding="utf-8") as f:
        env = json.load(f)
    
    # 创建会话
    from utils.env2sess import env_to_request_session
    session = env_to_request_session(env)
    
    ticket_info = config["ticket_info"]
    ticket_id = str(ticket_info.get("id"))
    ticket_count = config.get("ticket_count", 1)
    presale_mode = config.get("presale_mode", "split")  # split=分离抢票, merge=合并抢票
    presale_delay = config.get("presale_delay", 150) / 1000  # 转换为秒
    burst_delay = config.get("burst_delay", 70) / 1000  # 转换为秒
    purchaser_ids = config.get("purchaser_ids", "")
    presale_time_str = config.get("presale_time", "")
    time_offset = config.get("time_offset", 0)
    reflux_timeout = config.get("reflux_timeout", 5)  # 转入回流时间（分钟）
    debug_mode = config.get("debug_mode", False)
    
    is_real_name = ticket_info.get("realnameAuth") or ticket_info.get("isRealName", False)
    
    # 解析购买人ID列表
    purchaser_id_list = []
    if purchaser_ids:
        purchaser_id_list = [pid.strip() for pid in purchaser_ids.split(",") if pid.strip()]
    
    console.clear()
    console.print(Panel(
        Text("RanaRun - 预售模式抢票中", style="bold cyan"),
        box.DOUBLE,
        padding=(1, 2)
    ))
    
    mode_text = "分离抢票（每单1张）" if presale_mode == "split" else "合并抢票（每单多张）"
    
    info_table = Table(box=box.SIMPLE, show_header=True)
    info_table.add_column("配置项", style="cyan")
    info_table.add_column("值", style="green")
    
    info_table.add_row("票种", ticket_info.get("ticketName") or ticket_info.get("name", ""))
    info_table.add_row("购买张数", str(ticket_count))
    info_table.add_row("抢票模式", mode_text)
    info_table.add_row("开抢时间", presale_time_str)
    info_table.add_row("抢票延迟", f"{presale_delay*1000:.0f}ms")
    info_table.add_row("爆发延迟", f"{burst_delay*1000:.0f}ms")
    info_table.add_row("时间偏移", f"{time_offset*1000:.2f}ms")
    info_table.add_row("转入回流", f"{reflux_timeout}分钟" if reflux_timeout > 0 else "不转入")
    
    console.print(info_table)
    console.print()
    
    # 解析开抢时间
    try:
        presale_time = datetime.strptime(presale_time_str, "%Y-%m-%d %H:%M:%S")
        presale_timestamp = presale_time.timestamp()
    except ValueError:
        console.print("[red]开抢时间格式错误[/red]")
        return
    
    # 计算实际开抢时间（考虑时间偏移）
    actual_presale_timestamp = presale_timestamp - time_offset
    actual_presale_time = datetime.fromtimestamp(actual_presale_timestamp)
    
    console.print(f"[cyan]本地开抢时间: {actual_presale_time.strftime('%Y-%m-%d %H:%M:%S')}[/cyan]")
    console.print()
    
    # 等待到开抢时间
    console.print("[yellow]等待开抢时间...[/yellow]")
    while True:
        current_time = time.time()
        remaining = actual_presale_timestamp - current_time
        
        if remaining <= 0:
            break
        
        if remaining > 60:
            console.print(f"[dim]距离开抢还有 {int(remaining/60)} 分钟[/dim]")
            time.sleep(min(30, remaining - 60))
        elif remaining > 10:
            console.print(f"[dim]距离开抢还有 {int(remaining)} 秒[/dim]")
            time.sleep(min(5, remaining - 10))
        elif remaining > 1:
            console.print(f"[yellow]距离开抢还有 {remaining:.1f} 秒[/yellow]")
            time.sleep(0.1)
        else:
            console.print(f"[red]距离开抢还有 {remaining:.3f} 秒[/red]")
            time.sleep(0.001)
    
    console.print("\n[bold red]开始抢票！！！[/bold red]")
    console.print()
    
    # 开始抢票
    start_time = time.time()
    success = False
    order_count = 0
    burst_mode_end_time = start_time + 2  # 爆发模式持续2秒
    
    # 计算需要抢的票数
    if presale_mode == "split":
        # 分离模式：每单1张，需要抢ticket_count次
        total_orders = ticket_count
    else:
        # 合并模式：一次下单ticket_count张
        total_orders = 1
    
    while order_count < total_orders:
        current_time = time.time()
        
        # 判断是否在爆发模式时间内
        in_burst_mode = current_time < burst_mode_end_time
        
        # 计算本次延迟
        if in_burst_mode:
            delay = get_random_delay_ms(burst_delay * 1000)
            mode_text = "[bold red]爆发模式[/bold red]"
        else:
            delay = get_random_delay_ms(presale_delay * 1000)
            mode_text = "[cyan]正常模式[/cyan]"
        
        console.print(f"[{mode_text}] 第{order_count+1}次下单，延迟: {delay*1000:.2f}ms")
        
        time.sleep(delay)
        
        # 提交订单
        if presale_mode == "split":
            # 分离模式：每次下单1张
            if purchaser_id_list:
                purchaser_id = purchaser_id_list[order_count % len(purchaser_id_list)]
            else:
                purchaser_id = ""

            result, retry = submit_ticket_order(session, ticket_id, purchaser_id, 1, debug_mode)
        else:
            # 合并模式：一次下单多张
            result, retry = submit_ticket_order(session, ticket_id, purchaser_ids, ticket_count, debug_mode)

        order_count += 1

        if result:
            success = True
            console.print("[bold green]抢票成功！[/bold green]")
            break
        else:
            if not retry:
                console.print("[yellow]无需重试，抢票失败[/yellow]")
                if debug_mode:
                    console.print("[dim][调试] 详细错误信息见上方输出[/dim]")
                break
            else:
                console.print("[yellow]抢票失败，继续重试...[/yellow]")
        
        # 检查是否超时，需要转入回流模式
        elapsed_time = (time.time() - start_time) / 60  # 转换为分钟
        if reflux_timeout > 0 and elapsed_time >= reflux_timeout and not success:
            console.print(f"\n[yellow]已超过{reflux_timeout}分钟未抢到，自动转入回流模式[/yellow]")
            start_reflux_mode(config_file)
            return
    
    if not success:
        console.print("[bold red]抢票失败[/bold red]")
    
    console.print("\n[yellow]按任意键退出...[/yellow]")
    input()


def start_reflux_mode(config_file):
    """启动回流模式"""
    console.print("\n[cyan]正在启动回流模式...[/cyan]")
    
    # 读取配置
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 转换为回流模式配置
    resale_config = {
        "env_file": config["env_file"],
        "event_id": config.get("event_id", ""),
        "ticket_info": config["ticket_info"],
        "purchaser_ids": config.get("purchaser_ids", ""),
        "ticket_count": config["ticket_count"],
        "resale_mode": config.get("presale_mode", "split"),
        "refresh_delay": config.get("presale_delay", 150),
        "order_delay": config.get("presale_delay", 150),
        "debug_mode": config.get("debug_mode", False)
    }
    
    # 保存回流模式配置
    resale_config_file = os.path.join(os.path.dirname(config_file), "resale_config.json")
    try:
        with open(resale_config_file, "w", encoding="utf-8") as f:
            json.dump(resale_config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        console.print(f"[red]保存回流配置失败: {e}[/red]")
        return
    
    # 启动回流模式窗口
    script_path = os.path.join(os.path.dirname(__file__), "resale_worker.py")
    
    try:
        if sys.platform == "win32":
            subprocess.Popen([sys.executable, script_path, resale_config_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif sys.platform == "darwin":
            # macOS - 使用 Terminal.app 打开新窗口
            # 创建临时脚本文件
            temp_script = f"/tmp/resale_worker_{int(time.time())}.sh"
            with open(temp_script, "w") as f:
                f.write(f"#!/bin/bash\n")
                f.write(f"cd '{os.path.dirname(os.path.dirname(__file__))}'\n")
                f.write(f"'{sys.executable}' '{script_path}' '{resale_config_file}'\n")
                f.write(f"rm -f '{temp_script}'\n")
            os.chmod(temp_script, 0o755)
            subprocess.Popen(["open", "-a", "Terminal", temp_script])
        else:
            subprocess.Popen([sys.executable, script_path, resale_config_file])

        console.print("[green]回流模式窗口已启动！[/green]")
    except Exception as e:
        console.print(f"[red]启动回流模式失败: {e}[/red]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]请指定配置文件路径[/red]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    if not os.path.exists(config_file):
        console.print(f"[red]配置文件不存在: {config_file}[/red]")
        sys.exit(1)
    
    try:
        run_presale_mode(config_file)
    except KeyboardInterrupt:
        console.print("\n[yellow]程序已被用户中断[/yellow]")
    except Exception as e:
        console.print(f"[red]程序运行出错: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        console.print("\n[yellow]请按任意键继续...[/yellow]")
        input()