import json
from rich.table import Table
from rich.prompt import Prompt
from rich import box


def select_env_for_order(app):
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
    
    app.order_config["env_file"] = env_files[int(choice) - 1]
    app.console.print(f"\n[green]已选择环境文件: {app.order_config['env_file']}[/green]")
    
    Prompt.ask("按回车键继续", default="")


def select_event(app):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]选择活动[/cyan]\n")
    
    event_id = Prompt.ask("请输入活动ID")
    
    if not event_id:
        app.console.print("[yellow]已取消选择[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    app.order_config["event_id"] = event_id
    app.order_config["ticket_info"] = None
    
    app.console.print(f"\n[green]已选择活动ID: {event_id}[/green]")
    
    Prompt.ask("按回车键继续", default="")


def select_ticket_type(app):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]选择票种[/cyan]\n")
    
    if not app.order_config["env_file"]:
        app.console.print("[yellow]请先选择环境文件[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    if not app.order_config["event_id"]:
        app.console.print("[yellow]请先选择活动[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        with open(app.order_config["env_file"], "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_ticket_type_list
        
        app.console.print("[cyan]正在获取票种信息...[/cyan]")
        session = env_to_request_session(env)
        
        ticket_data = get_ticket_type_list(session, app.order_config["event_id"], 0.5)
        
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
        table.add_column("实名", style="blue")
        
        for idx, ticket in enumerate(ticket_list, 1):
            name = ticket.get("ticketName") or ticket.get("name", "")
            price = ticket.get("ticketPrice") or ticket.get("price", 0)
            stock = ticket.get("remainderNum", 0)
            is_real_name = ticket.get("realnameAuth") or ticket.get("isRealName", False)
            
            table.add_row(
                str(idx),
                name,
                f"{price/100 if price else 0}元",
                str(stock),
                "是" if is_real_name else "否"
            )
        
        app.console.print(table)
        
        choice = Prompt.ask("\n请选择票种序号", choices=[str(i) for i in range(1, len(ticket_list) + 1)])
        
        selected_ticket = ticket_list[int(choice) - 1]
        app.order_config["ticket_info"] = selected_ticket
        
        is_real_name = selected_ticket.get("realnameAuth") or selected_ticket.get("isRealName", False)
        
        app.console.print(f"\n[green]已选择票种: {selected_ticket.get('ticketName') or selected_ticket.get('name', '')}[/green]")
        
        if is_real_name:
            app.console.print("[yellow]该票种需要实名认证[/yellow]")
            purchaser_ids = Prompt.ask("请输入购买人ID（多个ID用逗号分隔）")
            app.order_config["purchaser_ids"] = purchaser_ids
        else:
            app.console.print("[green]该票种无需实名认证[/green]")
            app.order_config["purchaser_ids"] = None
        
        ticket_count = Prompt.ask("请输入购票数量", default="1")
        try:
            app.order_config["ticket_count"] = int(ticket_count)
            if app.order_config["ticket_count"] <= 0:
                app.console.print("[yellow]购票数量必须大于0，已重置为1[/yellow]")
                app.order_config["ticket_count"] = 1
        except ValueError:
            app.console.print("[yellow]输入无效，已重置为1[/yellow]")
            app.order_config["ticket_count"] = 1
        
        base_delay = Prompt.ask("请输入基准延迟（秒）", default="0.5")
        try:
            app.order_config["base_delay"] = float(base_delay)
            if app.order_config["base_delay"] < 0.1:
                app.console.print("[yellow]延迟不能小于0.1秒，已重置为0.5[/yellow]")
                app.order_config["base_delay"] = 0.5
        except ValueError:
            app.console.print("[yellow]输入无效，已重置为0.5[/yellow]")
            app.order_config["base_delay"] = 0.5
        
    except Exception as ex:
        app.console.print(f"[red]获取票种信息失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def execute_order(app):
    from tui_utils.menus import show_header
    from utils.ticket.purchase import submit_ticket_order
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]执行下单[/cyan]\n")
    
    if not app.order_config["env_file"]:
        app.console.print("[yellow]请先选择环境文件[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    if not app.order_config["event_id"]:
        app.console.print("[yellow]请先选择活动[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    if not app.order_config["ticket_info"]:
        app.console.print("[yellow]请先选择票种[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        with open(app.order_config["env_file"], "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        
        ticket_info = app.order_config["ticket_info"]
        ticket_id = str(ticket_info.get("id"))
        is_real_name = ticket_info.get("realnameAuth") or ticket_info.get("isRealName", False)
        
        app.console.print("[bold]下单信息:[/bold]")
        app.console.print(f"环境文件: {app.order_config['env_file']}")
        app.console.print(f"活动ID: {app.order_config['event_id']}")
        app.console.print(f"票种名称: {ticket_info.get('ticketName') or ticket_info.get('name', '')}")
        app.console.print(f"票种ID: {ticket_id}")
        app.console.print(f"是否实名: {'是' if is_real_name else '否'}")
        if is_real_name:
            app.console.print(f"购买人ID: {app.order_config['purchaser_ids']}")
        app.console.print(f"基准延迟: {app.order_config['base_delay']}秒\n")
        
        if is_real_name and not app.order_config["purchaser_ids"]:
            app.console.print("[red]实名票种需要提供购买人ID[/red]")
            Prompt.ask("按回车键继续", default="")
            return
        
        confirm = Prompt.ask("确认下单?", choices=["y", "n"], default="n")
        if confirm.lower() != "y":
            app.console.print("[yellow]已取消下单[/yellow]")
            Prompt.ask("按回车键继续", default="")
            return
        
        app.console.print("\n[cyan]正在下单...[/cyan]")
        
        session = env_to_request_session(env)
        
        # 使用 utils.ticket.purchase 中的 submit_ticket_order
        purchaser_id = app.order_config["purchaser_ids"] if is_real_name else ""
        success, need_retry = submit_ticket_order(
            session, 
            ticket_id, 
            purchaser_id, 
            app.order_config["base_delay"]
        )
        
        # 根据结果显示状态
        if success:
            app.console.print("\n[green]下单成功！[/green]")
        elif need_retry:
            app.console.print("\n[yellow]下单需要重试[/yellow]")
        else:
            app.console.print("\n[red]下单失败[/red]")
        
        # 保存Cookie
        if session.cookies:
            try:
                env["cookie"] = dict(session.cookies)
            except Exception:
                cookie_dict = {}
                for cookie in session.cookies:
                    cookie_dict[cookie.name] = cookie.value
                env["cookie"] = cookie_dict
            
            with open(app.order_config["env_file"], "w", encoding="utf-8") as f:
                json.dump(env, f, ensure_ascii=False, indent=2)
            app.console.print("[cyan]Cookie已更新并保存[/cyan]")
            
    except Exception as ex:
        app.console.print(f"\n[red]下单失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")
