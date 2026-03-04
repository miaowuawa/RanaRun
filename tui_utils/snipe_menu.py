from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


def show_snipe_menu(console: Console):
    """显示抢票菜单"""
    console.clear()
    header = Panel(
        Text("RanaRun乐奈快跑 - 抢票模式", style="bold cyan"),
        box.DOUBLE,
        padding=(1, 2)
    )
    console.print(header)
    
    table = Table(title="抢票模式选择", box=box.ROUNDED, show_header=False)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("模式", style="green")
    table.add_column("说明", style="yellow")
    table.add_row("1", "预售模式", "在指定时间自动开始抢票")
    table.add_row("2", "回流模式", "实时监控余票，有票立即下单")
    table.add_row("0", "返回主菜单", "")
    
    console.print(table)


def show_presale_config_menu(console: Console, config: dict):
    """显示预售模式配置菜单"""
    console.clear()
    header = Panel(
        Text("RanaRun乐奈快跑 - 预售模式配置", style="bold cyan"),
        box.DOUBLE,
        padding=(1, 2)
    )
    console.print(header)
    
    # 显示当前配置
    config_table = Table(title="当前配置", box=box.SIMPLE, show_header=True)
    config_table.add_column("配置项", style="cyan")
    config_table.add_column("当前值", style="green")
    
    env_file = config.get("env_file", "未设置")
    ticket_info = config.get("ticket_info", {})
    ticket_name = ticket_info.get("ticketName") or ticket_info.get("name", "未设置") if ticket_info else "未设置"
    purchaser_ids = config.get("purchaser_ids", "未设置") or "未设置"
    ticket_count = config.get("ticket_count", 1)
    presale_time = config.get("presale_time", "未设置")
    presale_delay = config.get("presale_delay", 150)
    presale_mode = config.get("presale_mode", "split")
    presale_mode_text = "分离抢票（每单1张）" if presale_mode == "split" else "合并抢票（每单多张）"
    reflux_timeout = config.get("reflux_timeout", 5)
    burst_delay = config.get("burst_delay", 70)
    time_offset = config.get("time_offset", 0)
    
    config_table.add_row("环境文件", str(env_file))
    config_table.add_row("票种", str(ticket_name))
    config_table.add_row("购买人ID", str(purchaser_ids))
    config_table.add_row("购买张数", str(ticket_count))
    config_table.add_row("开抢时间", str(presale_time))
    config_table.add_row("抢票延迟(ms)", str(presale_delay))
    config_table.add_row("预售模式", presale_mode_text)
    config_table.add_row("转入回流(分钟)", str(reflux_timeout))
    config_table.add_row("爆发延迟(ms)", str(burst_delay))
    config_table.add_row("时间偏移(ms)", f"{time_offset*1000:.2f}" if time_offset else "未计算")
    
    console.print(config_table)
    console.print()
    
    table = Table(title="配置选项", box=box.ROUNDED, show_header=False)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("功能", style="green")
    table.add_row("1", "选择环境文件")
    table.add_row("2", "选择票种")
    table.add_row("3", "设置购买人ID")
    table.add_row("4", "设置购买张数")
    table.add_row("5", "设置开抢时间")
    table.add_row("6", "设置抢票延迟(ms)")
    table.add_row("7", "设置预售模式")
    table.add_row("8", "设置转入回流时间")
    table.add_row("9", "设置爆发模式延迟(ms)")
    table.add_row("10", "[bold green]开始抢票[/bold green]")
    table.add_row("0", "返回")
    
    console.print(table)


def show_resale_config_menu(console: Console, config: dict):
    """显示回流模式配置菜单"""
    console.clear()
    header = Panel(
        Text("RanaRun乐奈快跑 - 回流模式配置", style="bold cyan"),
        box.DOUBLE,
        padding=(1, 2)
    )
    console.print(header)
    
    # 显示当前配置
    config_table = Table(title="当前配置", box=box.SIMPLE, show_header=True)
    config_table.add_column("配置项", style="cyan")
    config_table.add_column("当前值", style="green")
    
    env_file = config.get("env_file", "未设置")
    ticket_info = config.get("ticket_info", {})
    ticket_name = ticket_info.get("ticketName") or ticket_info.get("name", "未设置") if ticket_info else "未设置"
    purchaser_ids = config.get("purchaser_ids", "未设置") or "未设置"
    ticket_count = config.get("ticket_count", 1)
    refresh_delay = config.get("refresh_delay", 150)
    order_delay = config.get("order_delay", 150)
    resale_mode = config.get("resale_mode", "split")
    resale_mode_text = "拆分回流（每单1张）" if resale_mode == "split" else "合并回流（每单多张）"
    
    config_table.add_row("环境文件", str(env_file))
    config_table.add_row("票种", str(ticket_name))
    config_table.add_row("购买人ID", str(purchaser_ids))
    config_table.add_row("购买张数", str(ticket_count))
    config_table.add_row("回流模式", resale_mode_text)
    config_table.add_row("刷新延迟(ms)", str(refresh_delay))
    config_table.add_row("下单延迟(ms)", str(order_delay))
    
    console.print(config_table)
    console.print()
    
    table = Table(title="配置选项", box=box.ROUNDED, show_header=False)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("功能", style="green")
    table.add_row("1", "选择环境文件")
    table.add_row("2", "选择票种")
    table.add_row("3", "设置购买人ID")
    table.add_row("4", "设置购买张数")
    table.add_row("5", "设置回流模式")
    table.add_row("6", "设置刷新延迟(ms)")
    table.add_row("7", "设置下单延迟(ms)")
    table.add_row("8", "[bold green]开始抢票[/bold green]")
    table.add_row("0", "返回")
    
    console.print(table)
