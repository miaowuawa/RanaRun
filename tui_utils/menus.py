from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


def show_header(console: Console):
    header = Panel(
        Text("RanaRun乐奈快跑 - ALLCPP购票 - 严禁商业化使用", style="bold cyan"),
        box.DOUBLE,
        padding=(1, 2)
    )
    console.print(header)


def show_main_menu(console: Console, debug_mode: bool):
    console.clear()
    show_header(console)
    
    table = Table(title="主菜单", box=box.ROUNDED, show_header=False)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("功能", style="green")
    table.add_row("1", "环境文件管理")
    table.add_row("2", "下单测试")
    table.add_row("3", "票务信息查询")
    table.add_row("4", f"调试模式: {'[green]开启[/green]' if debug_mode else '[red]关闭[/red]'}")
    table.add_row("0", "退出")
    
    console.print(table)


def show_env_management_menu(console: Console):
    console.clear()
    show_header(console)
    
    table = Table(title="环境文件管理", box=box.ROUNDED, show_header=False)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("功能", style="green")
    table.add_row("1", "创建虚拟环境")
    table.add_row("2", "查看环境文件列表")
    table.add_row("3", "编辑环境文件")
    table.add_row("4", "删除环境文件")
    table.add_row("0", "返回主菜单")
    
    console.print(table)


def show_order_test_menu(console: Console):
    console.clear()
    show_header(console)
    
    table = Table(title="下单测试", box=box.ROUNDED, show_header=False)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("功能", style="green")
    table.add_row("1", "选择环境文件")
    table.add_row("2", "选择活动")
    table.add_row("3", "选择票种")
    table.add_row("4", "执行下单")
    table.add_row("0", "返回主菜单")
    
    console.print(table)


def show_ticket_query_menu(console: Console):
    console.clear()
    show_header(console)
    
    table = Table(title="票务信息查询", box=box.ROUNDED, show_header=False)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("功能", style="green")
    table.add_row("1", "搜索活动")
    table.add_row("2", "根据ID查询")
    table.add_row("3", "查看票种信息")
    table.add_row("4", "查看购买人列表")
    table.add_row("0", "返回主菜单")
    
    console.print(table)
