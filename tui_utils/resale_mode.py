import json
import time
import threading
import subprocess
import sys
import os
from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt


# 全局变量用于控制抢票线程
resale_stop_event = threading.Event()
resale_thread = None


def select_env_for_resale(app):
    """选择环境文件"""
    from tui_utils.menus import show_header
    from tui_utils.env_management import get_env_files
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]选择环境文件[/cyan]\n")
    
    env_files = get_env_files(app)
    
    if not env_files:
        app.console.print("[yellow]暂无环境文件[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("文件名", style="green")
    
    for idx, file in enumerate(env_files, 1):
        table.add_row(str(idx), file)
    
    app.console.print(table)
    
    choice = Prompt.ask("\n请选择环境文件序号", choices=[str(i) for i in range(1, len(env_files) + 1)])
    
    app.resale_config["env_file"] = env_files[int(choice) - 1]
    app.console.print(f"\n[green]已选择环境文件: {app.resale_config['env_file']}[/green]")
    
    Prompt.ask("按回车键继续", default="")


def select_ticket_for_resale(app):
    """选择票种"""
    from tui_utils.menus import show_header
    from tui_utils.env_management import get_env_files
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]选择票种[/cyan]\n")
    
    if not app.resale_config.get("env_file"):
        app.console.print("[yellow]请先选择环境文件[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    event_id = Prompt.ask("请输入活动ID")
    
    if not event_id:
        app.console.print("[yellow]已取消选择[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        with open(app.resale_config["env_file"], "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_ticket_type_list
        
        app.console.print("[cyan]正在获取票种信息...[/cyan]")
        session = env_to_request_session(env)
        
        ticket_data = get_ticket_type_list(session, event_id, 0.5)
        
        if not ticket_data:
            app.console.print("[red]获取票种信息失败[/red]")
            Prompt.ask("按回车键继续", default="")
            return
        
        ticket_list = None
        if "result" in ticket_data and ticket_data.get("isSuccess"):
            ticket_list = ticket_data.get("result", {}).get("ticketTypeList", [])
        else:
            ticket_list = ticket_data.get("ticketTypeList", [])
        
        if not ticket_list:
            app.console.print("[yellow]暂无票种信息[/yellow]")
            Prompt.ask("按回车键继续", default="")
            return
        
        app.console.print(f"\n[cyan]共找到 {len(ticket_list)} 个票种[/cyan]\n")
        
        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("序号", style="cyan", width=5)
        table.add_column("票种名称", style="green")
        table.add_column("价格", style="yellow")
        table.add_column("余票", style="magenta")
        table.add_column("限购", style="red")
        table.add_column("实名", style="blue")
        
        for idx, ticket in enumerate(ticket_list, 1):
            name = ticket.get("ticketName") or ticket.get("name", "")
            price = ticket.get("ticketPrice") or ticket.get("price", 0)
            stock = ticket.get("remainderNum", 0)
            purchase_num = ticket.get("purchaseNum", 0)
            is_real_name = ticket.get("realnameAuth") or ticket.get("isRealName", False)
            
            table.add_row(
                str(idx),
                name,
                f"{price/100 if price else 0}元",
                str(stock),
                str(purchase_num) if purchase_num > 0 else "-",
                "是" if is_real_name else "否"
            )
        
        app.console.print(table)
        
        choice = Prompt.ask("\n请选择票种序号", choices=[str(i) for i in range(1, len(ticket_list) + 1)])
        
        selected_ticket = ticket_list[int(choice) - 1]
        app.resale_config["ticket_info"] = selected_ticket
        app.resale_config["event_id"] = event_id
        
        # 保存限购数量
        purchase_num = selected_ticket.get("purchaseNum", 0)
        app.resale_config["purchase_limit"] = purchase_num if purchase_num > 0 else None
        
        is_real_name = selected_ticket.get("realnameAuth") or selected_ticket.get("isRealName", False)
        
        app.console.print(f"\n[green]已选择票种: {selected_ticket.get('ticketName') or selected_ticket.get('name', '')}[/green]")
        
        if purchase_num > 0:
            app.console.print(f"[yellow]该票种限购 {purchase_num} 张[/yellow]")
        
        if is_real_name:
            app.console.print("[yellow]该票种需要实名认证，请设置购买人ID[/yellow]")
        else:
            app.console.print("[green]该票种无需实名认证[/green]")
        
    except Exception as ex:
        app.console.print(f"[red]获取票种信息失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def set_purchaser_for_resale(app):
    """设置购买人ID - 从API获取购买人列表供用户选择"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置购买人ID[/cyan]\n")
    
    # 检查是否已选择票种
    if not app.resale_config.get("ticket_info"):
        app.console.print("[yellow]请先选择票种[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    # 检查票种是否需要实名认证
    ticket_info = app.resale_config.get("ticket_info", {})
    is_real_name = ticket_info.get("realnameAuth") or ticket_info.get("isRealName", False)
    
    if not is_real_name:
        app.console.print("[green]该票种无需实名认证，不需要设置购买人[/green]")
        app.resale_config["purchaser_ids"] = ""
        Prompt.ask("按回车键继续", default="")
        return
    
    # 检查是否已选择环境文件
    if not app.resale_config.get("env_file"):
        app.console.print("[yellow]请先选择环境文件[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        with open(app.resale_config["env_file"], "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_purchaser_list
        
        app.console.print("[cyan]正在获取购买人列表...[/cyan]")
        session = env_to_request_session(env)
        
        purchaser_list = get_purchaser_list(session, 0.5)
        
        if not purchaser_list:
            app.console.print("[yellow]暂无购买人信息，请先在ALLCPP添加购买人[/yellow]")
            Prompt.ask("按回车键继续", default="")
            return
        
        app.console.print(f"\n[cyan]共找到 {len(purchaser_list)} 个购买人[/cyan]\n")
        
        # 显示购买人列表
        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("序号", style="cyan", width=5)
        table.add_column("购买人ID", style="green")
        table.add_column("姓名", style="yellow")
        table.add_column("身份证号", style="magenta")
        table.add_column("手机号", style="blue")
        
        for idx, purchaser in enumerate(purchaser_list, 1):
            purchaser_id = purchaser.get("id", "")
            name = purchaser.get("realname", "")
            id_card = purchaser.get("idcard", "")
            mobile = purchaser.get("mobile", "")
            
            table.add_row(str(idx), str(purchaser_id), name, id_card, mobile)
        
        app.console.print(table)
        
        # 显示当前购买张数
        ticket_count = app.resale_config.get("ticket_count", 1)
        app.console.print(f"\n[dim]当前购买张数: {ticket_count}[/dim]")
        
        # 让用户选择购买人
        app.console.print("\n[bold]选择方式:[/bold]")
        app.console.print("1. 选择单个购买人")
        app.console.print("2. 选择多个购买人")
        app.console.print("0. 返回")
        
        choice = Prompt.ask("请选择", choices=["0", "1", "2"], default="1")
        
        if choice == "0":
            return
        elif choice == "1":
            # 选择单个购买人
            purchaser_choice = Prompt.ask(
                "请选择购买人序号",
                choices=[str(i) for i in range(1, len(purchaser_list) + 1)]
            )
            selected = purchaser_list[int(purchaser_choice) - 1]
            app.resale_config["purchaser_ids"] = str(selected.get("id", ""))
            app.console.print(f"\n[green]已选择购买人: {selected.get('realname', '')} (ID: {selected.get('id', '')})[/green]")
            
            # 检查购买人数量与张数
            if ticket_count > 1:
                app.console.print(f"[yellow]警告: 当前购买张数为 {ticket_count}，但只选择了1个购买人[/yellow]")
                app.console.print("[yellow]建议: 选择与购买张数相同数量的购买人[/yellow]")
            
        elif choice == "2":
            # 选择多个购买人
            app.console.print("\n[dim]请输入序号，多个用逗号分隔（如: 1,2,3）[/dim]")
            choices_input = Prompt.ask("请选择购买人序号")
            
            selected_ids = []
            selected_names = []
            for idx_str in choices_input.split(","):
                idx_str = idx_str.strip()
                if idx_str.isdigit():
                    idx = int(idx_str)
                    if 1 <= idx <= len(purchaser_list):
                        purchaser = purchaser_list[idx - 1]
                        selected_ids.append(str(purchaser.get("id", "")))
                        selected_names.append(purchaser.get("realname", ""))
            
            if selected_ids:
                purchaser_count = len(selected_ids)
                app.resale_config["purchaser_ids"] = ",".join(selected_ids)
                app.console.print(f"\n[green]已选择购买人: {', '.join(selected_names)}[/green]")
                app.console.print(f"[green]ID: {app.resale_config['purchaser_ids']}[/green]")
                
                # 检查购买人数量与张数
                if purchaser_count > ticket_count:
                    app.console.print(f"\n[bold red]警告: 选择了 {purchaser_count} 个购买人，但购买张数只有 {ticket_count} 张！[/bold red]")
                    app.console.print("[yellow]多余的购买人将不会被使用[/yellow]")
                elif purchaser_count < ticket_count:
                    app.console.print(f"\n[yellow]提示: 选择了 {purchaser_count} 个购买人，购买张数为 {ticket_count} 张[/yellow]")
                    if purchaser_count < ticket_count:
                        app.console.print("[yellow]警告: 购买人数量少于购买张数，可能导致下单失败[/yellow]")
                else:
                    app.console.print(f"\n[green]购买人数量 ({purchaser_count}) 与购买张数 ({ticket_count}) 匹配[/green]")
            else:
                app.console.print("[yellow]未选择有效的购买人[/yellow]")
        
    except Exception as ex:
        app.console.print(f"[red]获取购买人列表失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def set_ticket_count_for_resale(app):
    """设置购买张数"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置购买张数[/cyan]\n")
    
    # 检查是否已选择票种
    if not app.resale_config.get("ticket_info"):
        app.console.print("[yellow]请先选择票种[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    # 获取限购数量
    purchase_limit = app.resale_config.get("purchase_limit")
    
    if purchase_limit:
        app.console.print(f"[yellow]该票种限购 {purchase_limit} 张[/yellow]\n")
    
    count = Prompt.ask("请输入购买张数", default=str(app.resale_config.get("ticket_count", 1)))
    
    try:
        count = int(count)
        if count <= 0:
            count = 1
            app.console.print("[yellow]购买张数必须大于0，已重置为1[/yellow]")
        elif purchase_limit and count > purchase_limit:
            # 超出限购数量
            app.console.print(f"\n[bold red]错误: 购买张数 {count} 超出限购数量 {purchase_limit} 张！[/bold red]")
            app.console.print(f"[yellow]已自动设置为限购数量: {purchase_limit}[/yellow]")
            count = purchase_limit
        app.resale_config["ticket_count"] = count
        app.console.print(f"\n[green]已设置购买张数: {count}[/green]")
    except ValueError:
        app.resale_config["ticket_count"] = 1
        app.console.print("[yellow]输入无效，已重置为1[/yellow]")
    
    Prompt.ask("按回车键继续", default="")


def set_refresh_delay(app):
    """设置刷新延迟"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置刷新延迟[/cyan]\n")
    app.console.print("[dim]刷新延迟是指检测余票的时间间隔，默认150ms[/dim]\n")
    
    delay = Prompt.ask("请输入刷新延迟(ms)", default=str(app.resale_config.get("refresh_delay", 150)))
    
    try:
        delay = int(delay)
        if delay < 50:
            delay = 50
            app.console.print("[yellow]刷新延迟不能小于50ms，已重置为50ms[/yellow]")
        app.resale_config["refresh_delay"] = delay
        app.console.print(f"\n[green]已设置刷新延迟: {delay}ms[/green]")
    except ValueError:
        app.resale_config["refresh_delay"] = 150
        app.console.print("[yellow]输入无效，已重置为150ms[/yellow]")
    
    Prompt.ask("按回车键继续", default="")


def set_order_delay(app):
    """设置下单延迟"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置下单延迟[/cyan]\n")
    app.console.print("[dim]下单延迟是指检测到余票后到实际下单的延迟，默认150ms[/dim]\n")
    
    delay = Prompt.ask("请输入下单延迟(ms)", default=str(app.resale_config.get("order_delay", 150)))
    
    try:
        delay = int(delay)
        if delay < 0:
            delay = 0
            app.console.print("[yellow]下单延迟不能小于0ms，已重置为0ms[/yellow]")
        app.resale_config["order_delay"] = delay
        app.console.print(f"\n[green]已设置下单延迟: {delay}ms[/green]")
    except ValueError:
        app.resale_config["order_delay"] = 150
        app.console.print("[yellow]输入无效，已重置为150ms[/yellow]")
    
    Prompt.ask("按回车键继续", default="")


def set_resale_mode(app):
    """设置回流模式"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置回流模式[/cyan]\n")
    
    current_mode = app.resale_config.get("resale_mode", "split")
    
    app.console.print("[bold]回流模式说明:[/bold]\n")
    app.console.print("[green]1. 拆分回流[/green]")
    app.console.print("   - 每次下单只购买1张票")
    app.console.print("   - 适合需要抢多张票的情况")
    app.console.print("   - 每张票单独下单，提高成功率")
    app.console.print("")
    app.console.print("[green]2. 合并回流[/green]")
    app.console.print("   - 每次下单购买多张票（购买张数）")
    app.console.print("   - 适合需要一次性购买多张票的情况")
    app.console.print("   - 一次下单多张，减少请求次数")
    app.console.print("")
    
    app.console.print(f"[dim]当前模式: {'拆分回流' if current_mode == 'split' else '合并回流'}[/dim]\n")
    
    choice = Prompt.ask("请选择回流模式", choices=["1", "2"], default="1" if current_mode == "split" else "2")
    
    if choice == "1":
        app.resale_config["resale_mode"] = "split"
        app.console.print("\n[green]已设置为拆分回流模式[/green]")
    else:
        app.resale_config["resale_mode"] = "merge"
        app.console.print("\n[green]已设置为合并回流模式[/green]")
    
    Prompt.ask("按回车键继续", default="")


def validate_resale_config(config: dict) -> tuple[bool, str]:
    """验证回流模式配置是否完整"""
    if not config.get("env_file"):
        return False, "未选择环境文件"
    if not config.get("ticket_info"):
        return False, "未选择票种"
    
    ticket_info = config.get("ticket_info", {})
    is_real_name = ticket_info.get("realnameAuth") or ticket_info.get("isRealName", False)
    
    if is_real_name and not config.get("purchaser_ids"):
        return False, "实名票种需要设置购买人ID"
    
    return True, ""


def start_resale_mode(app):
    """启动回流模式抢票"""
    from tui_utils.menus import show_header
    from tui_utils.snipe_menu import show_resale_config_menu
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]启动回流模式[/cyan]\n")
    
    # 验证配置
    is_valid, error_msg = validate_resale_config(app.resale_config)
    if not is_valid:
        app.console.print(f"[red]配置不完整: {error_msg}[/red]")
        Prompt.ask("按回车键继续", default="")
        return
    
    # 显示配置确认
    app.console.print("[bold]当前配置:[/bold]")
    config_table = Table(box=box.SIMPLE)
    config_table.add_column("配置项", style="cyan")
    config_table.add_column("值", style="green")
    
    config_table.add_row("环境文件", app.resale_config["env_file"])
    config_table.add_row("票种", app.resale_config["ticket_info"].get("ticketName") or app.resale_config["ticket_info"].get("name", ""))
    config_table.add_row("购买张数", str(app.resale_config["ticket_count"]))
    config_table.add_row("刷新延迟", f"{app.resale_config['refresh_delay']}ms")
    config_table.add_row("下单延迟", f"{app.resale_config['order_delay']}ms")
    
    app.console.print(config_table)
    app.console.print()
    
    confirm = Prompt.ask("确认启动抢票?", choices=["y", "n"], default="n")
    if confirm.lower() != "y":
        app.console.print("[yellow]已取消启动[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    # 启动抢票子进程
    app.console.print("\n[green]正在启动抢票进程...[/green]")
    
    # 保存配置到临时文件（添加 debug_mode）
    config_file = ".resale_config.json"
    config_to_save = app.resale_config.copy()
    config_to_save["debug_mode"] = app.debug_mode
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, ensure_ascii=False, indent=2)
    
    # 在新窗口中启动抢票脚本
    script_path = os.path.join(os.path.dirname(__file__), "resale_worker.py")
    
    try:
        # 使用 subprocess 启动新窗口
        if sys.platform == "win32":
            # Windows
            subprocess.Popen(
                ["start", "cmd", "/k", sys.executable, script_path, config_file],
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Linux/Mac
            subprocess.Popen(
                [sys.executable, script_path, config_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        app.console.print("[green]抢票进程已启动，请查看新窗口[/green]")
        app.console.print("[dim]提示: 关闭新窗口即可停止抢票[/dim]")
        
    except Exception as ex:
        app.console.print(f"[red]启动失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def handle_resale_config(app, choice: str):
    """处理回流模式配置菜单选择"""
    if choice == "1":
        select_env_for_resale(app)
    elif choice == "2":
        select_ticket_for_resale(app)
    elif choice == "3":
        set_purchaser_for_resale(app)
    elif choice == "4":
        set_ticket_count_for_resale(app)
    elif choice == "5":
        set_resale_mode(app)
    elif choice == "6":
        set_refresh_delay(app)
    elif choice == "7":
        set_order_delay(app)
    elif choice == "8":
        start_resale_mode(app)
    elif choice == "0":
        app.current_menu = "snipe"
    else:
        app.console.print("[red]无效的选项[/red]")


def resale_config_loop(app):
    """回流模式配置循环"""
    from tui_utils.snipe_menu import show_resale_config_menu
    from rich.prompt import Prompt
    
    while app.current_menu == "resale_config":
        show_resale_config_menu(app.console, app.resale_config)
        choice = Prompt.ask(
            "\n请选择功能",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"],
            default="0"
        )
        handle_resale_config(app, choice)
