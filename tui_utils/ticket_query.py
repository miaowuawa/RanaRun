import json
import datetime
from rich.table import Table
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich import box


def select_city(app):
    from utils.location import get_provinces, get_cities_by_province
    
    provinces = get_provinces()
    
    app.console.print("\n[bold]选择省份:[/bold]")
    app.console.print("0. 全部城市")
    
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("省份", style="green")
    
    for idx, province in enumerate(provinces, 1):
        table.add_row(str(idx), province["name"])
    
    app.console.print(table)
    
    choice = Prompt.ask("请选择省份序号", choices=[str(i) for i in range(0, len(provinces) + 1)], default="0")
    
    if choice == "0":
        return ""
    
    selected_province = provinces[int(choice) - 1]
    cities = get_cities_by_province(selected_province["code"])
    
    if not cities:
        return ""
    
    app.console.print(f"\n[bold]选择 {selected_province['name']} 的城市:[/bold]")
    
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("城市", style="green")
    table.add_column("城市代码", style="yellow")
    
    for idx, city in enumerate(cities, 1):
        table.add_row(str(idx), city["name"], str(city["code"]))
    
    app.console.print(table)
    
    city_choice = Prompt.ask("请选择城市序号", choices=[str(i) for i in range(1, len(cities) + 1)])
    
    selected_city = cities[int(city_choice) - 1]
    app.console.print(f"[green]已选择: {selected_city['name']} (代码: {selected_city['code']})[/green]")
    
    return str(selected_city["code"])


def fetch_events_page(session, city, keyword, page_no, page_size=20):
    """获取指定页的活动列表"""
    import utils.urls as urls
    
    url = urls.BASE_URL_WEB + "allcpp/event/eventMainListV2.do"
    params = {
        "city": city if city else "",
        "isWannaGo": 0,
        "keyword": keyword if keyword else "",
        "pageNo": page_no,
        "pageSize": page_size,
        "sort": 1
    }
    
    response = session.get(url, params=params, timeout=10)
    result = response.json()
    
    if result and result.get("isSuccess"):
        return result.get("result", {}).get("list", []), result.get("result", {}).get("total", 0)
    return [], 0


def display_events_table(app, events, start_idx=1):
    """显示活动列表表格"""
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("活动ID", style="green")
    table.add_column("活动名称", style="yellow", width=40)
    table.add_column("城市", style="magenta")
    table.add_column("类型", style="blue")
    table.add_column("时间", style="cyan")
    
    for idx, event in enumerate(events, start_idx):
        event_id = event.get("id", "")
        name = event.get("name", "")
        
        # 获取城市信息 - 可能在不同字段中
        city_name = event.get("city", "")
        if not city_name:
            city_name = event.get("cityName", "")
        if not city_name:
            city_name = event.get("address", "")
        
        event_type = event.get("type", "")
        if not event_type:
            event_type = event.get("eventType", "")
        
        # 获取时间信息
        event_time = ""
        start_time = event.get("startTime", 0)
        if start_time:
            try:
                event_time = datetime.datetime.fromtimestamp(start_time / 1000).strftime("%m-%d")
            except:
                pass
        
        # 截断名称避免过长
        display_name = name[:37] + "..." if len(name) > 40 else name
        
        table.add_row(str(idx), str(event_id), display_name, city_name, event_type, event_time)
    
    app.console.print(table)


def search_events(app):
    from tui_utils.menus import show_header
    from tui_utils.env_management import get_env_files
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]搜索活动[/cyan]\n")
    
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
    env_file = env_files[int(choice) - 1]
    
    city = select_city(app)
    keyword = Prompt.ask("请输入关键词 (留空搜索全部)", default="")
    
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        
        app.console.print("\n[cyan]正在搜索活动...[/cyan]")
        session = env_to_request_session(env)
        
        # 获取第一页
        page_size = 50  # 每页显示50条
        all_events = []
        page_no = 1
        
        while True:
            events, total = fetch_events_page(session, city, keyword, page_no, page_size)
            
            if not events:
                break
            
            all_events.extend(events)
            
            # 如果已经获取了所有活动，或者已经获取了超过100条，停止获取
            if len(all_events) >= total or len(all_events) >= 100:
                break
            
            page_no += 1
        
        if app.debug_mode:
            app.console.print(f"\n[bold cyan]共获取 {len(all_events)} 条活动数据[/bold cyan]")
        
        if all_events:
            app.console.print(f"\n[cyan]共找到 {len(all_events)} 个活动{' (已显示全部)' if len(all_events) >= total else ''}[/cyan]\n")
            
            # 分页显示
            page_size_display = 20  # 每页显示20条
            current_page = 0
            
            while True:
                start_idx = current_page * page_size_display
                end_idx = min(start_idx + page_size_display, len(all_events))
                page_events = all_events[start_idx:end_idx]
                
                if not page_events:
                    break
                
                app.console.clear()
                show_header(app.console)
                app.console.print(f"\n[cyan]搜索活动 - 第 {current_page + 1}/{(len(all_events) + page_size_display - 1) // page_size_display} 页 (共 {len(all_events)} 个)[/cyan]\n")
                
                display_events_table(app, page_events, start_idx + 1)
                
                # 显示导航选项
                app.console.print("\n[dim]操作: [n]下一页 [p]上一页 [q]退出[/dim]")
                
                if current_page == 0 and end_idx >= len(all_events):
                    # 只有一页
                    action = Prompt.ask("请选择", choices=["q"], default="q")
                elif current_page == 0:
                    # 第一页
                    action = Prompt.ask("请选择", choices=["n", "q"], default="n")
                elif end_idx >= len(all_events):
                    # 最后一页
                    action = Prompt.ask("请选择", choices=["p", "q"], default="p")
                else:
                    # 中间页
                    action = Prompt.ask("请选择", choices=["n", "p", "q"], default="n")
                
                if action == "n" and end_idx < len(all_events):
                    current_page += 1
                elif action == "p" and current_page > 0:
                    current_page -= 1
                elif action == "q":
                    break
        else:
            app.console.print("[yellow]未找到活动[/yellow]")
            Prompt.ask("按回车键继续", default="")
            
    except Exception as ex:
        app.console.print(f"[red]搜索活动失败: {str(ex)}[/red]")
        Prompt.ask("按回车键继续", default="")


def query_by_id(app):
    from tui_utils.menus import show_header
    from tui_utils.env_management import get_env_files
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]根据ID查询[/cyan]\n")
    
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
    env_file = env_files[int(choice) - 1]
    
    event_id = Prompt.ask("请输入活动ID")
    
    if not event_id:
        app.console.print("[yellow]已取消查询[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_ticket_type_list
        
        app.console.print("\n[cyan]正在获取票种信息...[/cyan]")
        session = env_to_request_session(env)
        
        ticket_data = get_ticket_type_list(session, event_id, 0.5)
        
        if not ticket_data:
            app.console.print("[red]获取失败[/red]")
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
        table.add_column("票种ID", style="green")
        table.add_column("票种名称", style="yellow")
        table.add_column("价格", style="magenta")
        table.add_column("余票", style="blue")
        table.add_column("实名", style="white")
        
        for idx, ticket in enumerate(ticket_list, 1):
            ticket_id = ticket.get("id", "")
            name = ticket.get("ticketName") or ticket.get("name", "")
            price = ticket.get("ticketPrice") or ticket.get("price", 0)
            stock = ticket.get("remainderNum", 0)
            is_real_name = ticket.get("realnameAuth") or ticket.get("isRealName", False)
            
            table.add_row(
                str(idx),
                str(ticket_id),
                name,
                f"{price/100 if price else 0}元",
                str(stock),
                "是" if is_real_name else "否"
            )
        
        app.console.print(table)
        
    except Exception as ex:
        app.console.print(f"[red]查询失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def view_ticket_info(app):
    from tui_utils.menus import show_header
    from tui_utils.env_management import get_env_files
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]查看票种信息[/cyan]\n")
    
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
    env_file = env_files[int(choice) - 1]
    
    event_id = Prompt.ask("请输入活动ID")
    
    if not event_id:
        app.console.print("[yellow]已取消查询[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_ticket_type_list
        
        app.console.print("\n[cyan]正在获取票种信息...[/cyan]")
        session = env_to_request_session(env)
        
        ticket_data = get_ticket_type_list(session, event_id, 0.5)
        
        if not ticket_data:
            app.console.print("[red]获取失败[/red]")
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
        
        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("序号", style="cyan", width=5)
        table.add_column("票种名称", style="green")
        
        for idx, ticket in enumerate(ticket_list, 1):
            name = ticket.get("ticketName") or ticket.get("name", "")
            table.add_row(str(idx), name)
        
        app.console.print(table)
        
        choice = Prompt.ask("\n请选择票种序号查看详情", choices=[str(i) for i in range(1, len(ticket_list) + 1)])
        
        ticket = ticket_list[int(choice) - 1]
        
        app.console.clear()
        show_header(app.console)
        app.console.print(f"\n[cyan]票种详情[/cyan]\n")
        
        if app.debug_mode:
            app.console.print("\n[bold cyan]完整票种信息:[/bold cyan]")
            json_syntax = Syntax(json.dumps(ticket, ensure_ascii=False, indent=2), "json", theme="monokai", line_numbers=False)
            app.console.print(json_syntax)
            app.console.print()
        
        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("属性", style="cyan")
        table.add_column("值", style="green")
        
        ticket_id = ticket.get("id", "")
        name = ticket.get("ticketName") or ticket.get("name", "")
        price = ticket.get("ticketPrice") or ticket.get("price", 0)
        stock = ticket.get("remainderNum", 0)
        is_real_name = ticket.get("realnameAuth") or ticket.get("isRealName", False)
        sell_start = ticket.get("sellStartTime", 0)
        sell_end = ticket.get("sellEndTime", 0)
        description = ticket.get("ticketDescription", "")
        
        table.add_row("票种ID", str(ticket_id))
        table.add_row("票种名称", name)
        table.add_row("价格", f"{price/100 if price else 0}元")
        table.add_row("余票", str(stock))
        table.add_row("是否实名", "是" if is_real_name else "否")
        
        if sell_start:
            sell_start_time = datetime.datetime.fromtimestamp(sell_start / 1000).strftime("%Y-%m-%d %H:%M:%S")
            table.add_row("开售时间", sell_start_time)
        
        if sell_end:
            sell_end_time = datetime.datetime.fromtimestamp(sell_end / 1000).strftime("%Y-%m-%d %H:%M:%S")
            table.add_row("结束时间", sell_end_time)
        
        if description:
            table.add_row("描述", description)
        
        app.console.print(table)
        
    except Exception as ex:
        app.console.print(f"[red]获取失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def view_purchaser_list(app):
    from tui_utils.menus import show_header
    from tui_utils.env_management import get_env_files
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]查看购买人列表[/cyan]\n")
    
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
    env_file = env_files[int(choice) - 1]
    
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)
        
        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_purchaser_list
        
        app.console.print("\n[cyan]正在获取购买人列表...[/cyan]")
        session = env_to_request_session(env)
        
        purchaser_list = get_purchaser_list(session, 0.5)
        
        # 只有在调试模式开启时才显示原始数据
        if app.debug_mode:
            app.console.print("\n[bold cyan]完整购买人列表 (调试模式):[/bold cyan]")
            json_syntax = Syntax(json.dumps(purchaser_list, ensure_ascii=False, indent=2), "json", theme="monokai", line_numbers=False)
            app.console.print(json_syntax)
            app.console.print()
        
        if not purchaser_list:
            app.console.print("[yellow]暂无购买人信息[/yellow]")
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
        
    except Exception as ex:
        app.console.print(f"[red]获取失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")
