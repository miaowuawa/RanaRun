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
presale_stop_event = threading.Event()
presale_thread = None


def select_env_for_presale(app):
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
    
    app.presale_config["env_file"] = env_files[int(choice) - 1]
    app.console.print(f"\n[green]已选择环境文件: {app.presale_config['env_file']}[/green]")
    
    Prompt.ask("按回车键继续", default="")


def select_ticket_for_presale(app):
    """选择票种"""
    from tui_utils.menus import show_header
    from tui_utils.env_management import get_env_files
    from datetime import datetime
    import time
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]选择票种[/cyan]\n")
    
    if not app.presale_config.get("env_file"):
        app.console.print("[yellow]请先选择环境文件[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    event_id = Prompt.ask("请输入活动ID")
    
    if not event_id:
        app.console.print("[yellow]已取消选择[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        with open(app.presale_config["env_file"], "r", encoding="utf-8") as f:
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
        app.presale_config["ticket_info"] = selected_ticket
        app.presale_config["event_id"] = event_id
        
        purchase_num = selected_ticket.get("purchaseNum", 0)
        app.presale_config["purchase_limit"] = purchase_num if purchase_num > 0 else None
        
        is_real_name = selected_ticket.get("realnameAuth") or selected_ticket.get("isRealName", False)
        
        # 获取开售时间
        sell_start_time = selected_ticket.get("sellStartTime", 0)
        if sell_start_time:
            # 转换毫秒时间戳为datetime
            sell_start_dt = datetime.fromtimestamp(sell_start_time / 1000)
            sell_start_str = sell_start_dt.strftime("%Y-%m-%d %H:%M:%S")
            app.presale_config["presale_time"] = sell_start_str
            
            app.console.print(f"\n[green]已选择票种: {selected_ticket.get('ticketName') or selected_ticket.get('name', '')}[/green]")
            app.console.print(f"[cyan]开售时间: {sell_start_str}[/cyan]")
            
            # 检查开售时间是否已过
            current_time = time.time()
            if sell_start_time / 1000 < current_time:
                app.console.print("\n[bold red]⚠️ 警告：该票种已开售！[/bold red]")
                app.console.print("[yellow]当前时间已超过开售时间，建议使用回流模式抢票。[/yellow]")
                app.console.print("[yellow]回流模式可以实时监控余票变化，有票立即下单。[/yellow]")
                
                use_reflux = Prompt.ask("\n是否切换到回流模式?", choices=["y", "n"], default="y")
                if use_reflux.lower() == "y":
                    app.current_menu = "resale_config"
                    # 将预售配置同步到回流配置
                    app.resale_config["env_file"] = app.presale_config["env_file"]
                    app.resale_config["event_id"] = app.presale_config["event_id"]
                    app.resale_config["ticket_info"] = app.presale_config["ticket_info"]
                    app.resale_config["purchase_limit"] = app.presale_config.get("purchase_limit")
                    app.console.print("[green]已切换到回流模式，请继续配置...[/green]")
                    Prompt.ask("按回车键继续", default="")
                    return
        else:
            app.console.print(f"\n[green]已选择票种: {selected_ticket.get('ticketName') or selected_ticket.get('name', '')}[/green]")
            app.console.print("[yellow]未获取到开售时间，请手动设置[/yellow]")
        
        if purchase_num > 0:
            app.console.print(f"[yellow]该票种限购 {purchase_num} 张[/yellow]")
        
        if is_real_name:
            app.console.print("[yellow]该票种需要实名认证，请设置购买人ID[/yellow]")
        else:
            app.console.print("[green]该票种无需实名认证[/green]")
        
    except Exception as ex:
        app.console.print(f"[red]获取票种信息失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def set_purchaser_for_presale(app):
    """设置购买人ID"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置购买人ID[/cyan]\n")
    
    if not app.presale_config.get("ticket_info"):
        app.console.print("[yellow]请先选择票种[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    ticket_info = app.presale_config.get("ticket_info", {})
    is_real_name = ticket_info.get("realnameAuth") or ticket_info.get("isRealName", False)
    
    if not is_real_name:
        app.console.print("[yellow]该票种无需实名认证[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        with open(app.presale_config["env_file"], "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_purchaser_list
        
        app.console.print("[cyan]正在获取购买人列表...[/cyan]")
        session = env_to_request_session(env)
        purchaser_list = get_purchaser_list(session, 0.5)
        
        if not purchaser_list:
            app.console.print("[red]获取购买人列表失败[/red]")
            Prompt.ask("按回车键继续", default="")
            return
        
        app.console.print(f"\n[cyan]共找到 {len(purchaser_list)} 个购买人[/cyan]\n")
        
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
        
        choice = Prompt.ask("\n请选择购买人序号（可多选，用逗号分隔）", default="1")
        
        purchaser_ids = []
        for idx_str in choice.split(","):
            idx = int(idx_str.strip())
            if 1 <= idx <= len(purchaser_list):
                purchaser_ids.append(str(purchaser_list[idx - 1]["id"]))
        
        app.presale_config["purchaser_ids"] = ",".join(purchaser_ids)
        app.console.print(f"\n[green]已选择购买人ID: {app.presale_config['purchaser_ids']}[/green]")
        
    except Exception as ex:
        app.console.print(f"[red]设置购买人失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def set_ticket_count_for_presale(app):
    """设置购买张数"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置购买张数[/cyan]\n")
    
    if not app.presale_config.get("ticket_info"):
        app.console.print("[yellow]请先选择票种[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    purchase_limit = app.presale_config.get("purchase_limit")
    
    if purchase_limit:
        app.console.print(f"[yellow]该票种限购 {purchase_limit} 张[/yellow]\n")
    
    count = Prompt.ask("请输入购买张数", default=str(app.presale_config.get("ticket_count", 1)))
    
    try:
        count = int(count)
        if count <= 0:
            count = 1
            app.console.print("[yellow]购买张数必须大于0，已重置为1[/yellow]")
        elif purchase_limit and count > purchase_limit:
            app.console.print(f"\n[bold red]错误: 购买张数 {count} 超出限购数量 {purchase_limit} 张！[/bold red]")
            app.console.print(f"[yellow]已自动设置为限购数量: {purchase_limit}[/yellow]")
            count = purchase_limit
        app.presale_config["ticket_count"] = count
        app.console.print(f"\n[green]已设置购买张数: {count}[/green]")
    except ValueError:
        app.presale_config["ticket_count"] = 1
        app.console.print("[yellow]输入无效，已重置为1[/yellow]")
    
    Prompt.ask("按回车键继续", default="")


def set_presale_time(app):
    """设置开抢时间"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置开抢时间[/cyan]\n")
    
    app.console.print("[yellow]请输入开抢时间，格式：YYYY-MM-DD HH:MM:SS[/yellow]")
    app.console.print("[yellow]例如：2026-03-05 10:00:00[/yellow]\n")
    
    time_str = Prompt.ask("开抢时间", default="")
    
    if not time_str:
        app.console.print("[yellow]已取消设置[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        presale_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        app.presale_config["presale_time"] = presale_time.strftime("%Y-%m-%d %H:%M:%S")
        app.console.print(f"\n[green]已设置开抢时间: {app.presale_config['presale_time']}[/green]")
    except ValueError:
        app.console.print("[red]时间格式错误，请使用 YYYY-MM-DD HH:MM:SS 格式[/red]")
    
    Prompt.ask("按回车键继续", default="")


def set_presale_delay(app):
    """设置抢票延迟"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置抢票延迟[/cyan]\n")
    
    app.console.print("[yellow]请设置抢票延迟（毫秒）[/yellow]")
    app.console.print("[yellow]建议值：100-300ms[/yellow]\n")
    
    delay = Prompt.ask("抢票延迟(ms)", default=str(app.presale_config.get("presale_delay", 150)))
    
    try:
        delay = int(delay)
        if delay < 0:
            delay = 0
            app.console.print("[yellow]延迟不能为负数，已重置为0[/yellow]")
        app.presale_config["presale_delay"] = delay
        app.console.print(f"\n[green]已设置抢票延迟: {delay}ms[/green]")
    except ValueError:
        app.presale_config["presale_delay"] = 150
        app.console.print("[yellow]输入无效，已重置为150ms[/yellow]")
    
    Prompt.ask("按回车键继续", default="")


def set_presale_mode(app):
    """设置预售模式（合并/分离）"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置预售模式[/cyan]\n")
    
    current_mode = app.presale_config.get("presale_mode", "split")
    
    app.console.print("[bold]预售模式说明:[/bold]\n")
    app.console.print("[green]1. 分离抢票[/green]")
    app.console.print("   - 每次下单只购买1张票")
    app.console.print("   - 适合需要抢多张票的情况")
    app.console.print("   - 每张票单独下单，提高成功率")
    app.console.print("")
    app.console.print("[green]2. 合并抢票[/green]")
    app.console.print("   - 每次下单购买多张票（购买张数）")
    app.console.print("   - 适合需要一次性购买多张票的情况")
    app.console.print("   - 一次下单多张，减少请求次数")
    app.console.print("")
    
    app.console.print(f"[dim]当前模式: {'分离抢票' if current_mode == 'split' else '合并抢票'}[/dim]\n")
    
    choice = Prompt.ask("请选择预售模式", choices=["1", "2"], default="1" if current_mode == "split" else "2")
    
    if choice == "1":
        app.presale_config["presale_mode"] = "split"
        app.console.print("\n[green]已设置为分离抢票模式[/green]")
    else:
        app.presale_config["presale_mode"] = "merge"
        app.console.print("\n[green]已设置为合并抢票模式[/green]")
    
    Prompt.ask("按回车键继续", default="")


def set_reflux_timeout(app):
    """设置转入回流时间"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置转入回流时间[/cyan]\n")
    
    app.console.print("[yellow]如果超过此时间（分钟）未抢到票，自动开启回流模式[/yellow]")
    app.console.print("[yellow]设置为0表示不自动转入回流模式[/yellow]\n")
    
    timeout = Prompt.ask("转入回流时间（分钟）", default=str(app.presale_config.get("reflux_timeout", 5)))
    
    try:
        timeout = int(timeout)
        if timeout < 0:
            timeout = 0
            app.console.print("[yellow]时间不能为负数，已重置为0[/yellow]")
        app.presale_config["reflux_timeout"] = timeout
        app.console.print(f"\n[green]已设置转入回流时间: {timeout}分钟[/green]")
    except ValueError:
        app.presale_config["reflux_timeout"] = 5
        app.console.print("[yellow]输入无效，已重置为5分钟[/yellow]")
    
    Prompt.ask("按回车键继续", default="")


def set_burst_mode(app):
    """设置爆发模式延迟"""
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]设置爆发模式[/cyan]\n")
    
    app.console.print("[bold]爆发模式说明:[/bold]")
    app.console.print("[yellow]在开抢的1-2秒内以极低延迟抢票[/yellow]")
    app.console.print("[yellow]建议值：60-80ms[/yellow]")
    app.console.print("[yellow]注意：极低延迟可能触发风控[/yellow]\n")
    
    burst_delay = Prompt.ask("爆发模式延迟(ms)", default=str(app.presale_config.get("burst_delay", 70)))
    
    try:
        burst_delay = int(burst_delay)
        if burst_delay < 0:
            burst_delay = 0
            app.console.print("[yellow]延迟不能为负数，已重置为0[/yellow]")
        app.presale_config["burst_delay"] = burst_delay
        app.console.print(f"\n[green]已设置爆发模式延迟: {burst_delay}ms[/green]")
    except ValueError:
        app.presale_config["burst_delay"] = 70
        app.console.print("[yellow]输入无效，已重置为70ms[/yellow]")
    
    Prompt.ask("按回车键继续", default="")


def validate_presale_config(config: dict) -> tuple[bool, str]:
    """验证预售模式配置是否完整"""
    if not config.get("env_file"):
        return False, "未选择环境文件"
    if not config.get("ticket_info"):
        return False, "未选择票种"
    if not config.get("presale_time"):
        return False, "未设置开抢时间"
    
    ticket_info = config.get("ticket_info", {})
    is_real_name = ticket_info.get("realnameAuth") or ticket_info.get("isRealName", False)
    
    if is_real_name and not config.get("purchaser_ids"):
        return False, "实名票种需要设置购买人ID"
    
    return True, ""


def start_presale_mode(app):
    """启动预售模式抢票"""
    from tui_utils.menus import show_header
    from utils.time_sync import calculate_time_offset
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]启动预售模式[/cyan]\n")
    
    # 验证配置
    is_valid, error_msg = validate_presale_config(app.presale_config)
    if not is_valid:
        app.console.print(f"[red]配置不完整: {error_msg}[/red]")
        Prompt.ask("按回车键继续", default="")
        return
    
    # 计算时间偏移
    app.console.print("[cyan]正在计算时间偏移量...[/cyan]")
    time_offset = calculate_time_offset()
    
    if time_offset is None:
        app.console.print("[red]时间偏移计算失败，请检查网络连接[/red]")
        Prompt.ask("按回车键继续", default="")
        return
    
    app.presale_config["time_offset"] = time_offset
    
    # 显示配置确认
    app.console.print("\n[bold]当前配置:[/bold]")
    config_table = Table(box=box.SIMPLE)
    config_table.add_column("配置项", style="cyan")
    config_table.add_column("值", style="green")
    
    config_table.add_row("环境文件", app.presale_config["env_file"])
    config_table.add_row("票种", app.presale_config["ticket_info"].get("ticketName") or app.presale_config["ticket_info"].get("name", ""))
    config_table.add_row("购买人ID", app.presale_config.get("purchaser_ids", "无需实名"))
    config_table.add_row("购买张数", str(app.presale_config["ticket_count"]))
    config_table.add_row("开抢时间", app.presale_config["presale_time"])
    config_table.add_row("抢票延迟", f"{app.presale_config['presale_delay']}ms")
    config_table.add_row("预售模式", "分离抢票" if app.presale_config.get("presale_mode") == "split" else "合并抢票")
    config_table.add_row("转入回流时间", f"{app.presale_config['reflux_timeout']}分钟")
    config_table.add_row("爆发模式延迟", f"{app.presale_config['burst_delay']}ms")
    config_table.add_row("时间偏移", f"{time_offset*1000:.2f}ms")
    
    app.console.print(config_table)
    app.console.print()
    
    confirm = Prompt.ask("确认启动抢票?", choices=["y", "n"], default="n")
    if confirm.lower() != "y":
        app.console.print("[yellow]已取消启动[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    # 保存配置文件
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presale_config.json")
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(app.presale_config, f, ensure_ascii=False, indent=2)
        app.console.print(f"[green]配置已保存到: {config_file}[/green]")
    except Exception as e:
        app.console.print(f"[red]保存配置失败: {e}[/red]")
        Prompt.ask("按回车键继续", default="")
        return
    
    # 启动抢票窗口
    app.console.print("\n[cyan]正在启动抢票窗口...[/cyan]")
    
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tui_utils", "presale_worker.py")
    
    try:
        if sys.platform == "win32":
            subprocess.Popen([sys.executable, script_path, config_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen([sys.executable, script_path, config_file])
        
        app.console.print("[green]抢票窗口已启动！[/green]")
        app.console.print("[yellow]请在新窗口中查看抢票进度[/yellow]")
    except Exception as e:
        app.console.print(f"[red]启动抢票窗口失败: {e}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def handle_presale_config(app, choice: str):
    """处理预售模式配置菜单选择"""
    if choice == "1":
        select_env_for_presale(app)
    elif choice == "2":
        select_ticket_for_presale(app)
    elif choice == "3":
        set_purchaser_for_presale(app)
    elif choice == "4":
        set_ticket_count_for_presale(app)
    elif choice == "5":
        set_presale_time(app)
    elif choice == "6":
        set_presale_delay(app)
    elif choice == "7":
        set_presale_mode(app)
    elif choice == "8":
        set_reflux_timeout(app)
    elif choice == "9":
        set_burst_mode(app)
    elif choice == "10":
        start_presale_mode(app)
    elif choice == "0":
        app.current_menu = "snipe"
    else:
        app.console.print("[red]无效的选项[/red]")


def presale_config_loop(app):
    """预售模式配置循环"""
    from tui_utils.snipe_menu import show_presale_config_menu
    from rich.prompt import Prompt
    
    while app.current_menu == "presale_config":
        show_presale_config_menu(app.console, app.presale_config)
        choice = Prompt.ask(
            "\n请选择功能",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            default="0"
        )
        handle_presale_config(app, choice)