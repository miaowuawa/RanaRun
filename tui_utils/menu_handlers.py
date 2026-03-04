from rich.prompt import Prompt


def handle_main_menu(app, choice: str):
    if choice == "1":
        app.current_menu = "env_management"
    elif choice == "2":
        app.current_menu = "order_test"
    elif choice == "3":
        app.current_menu = "ticket_query"
    elif choice == "4":
        app.current_menu = "snipe"
    elif choice == "5":
        app.debug_mode = not app.debug_mode
        app.console.print(f"\n[green]调试模式已{'开启' if app.debug_mode else '关闭'}[/green]")
        Prompt.ask("按回车键继续", default="")
    elif choice == "0":
        app.running = False
    else:
        app.console.print("[red]无效的选项，请重新选择[/red]")


def handle_env_management(app, choice: str):
    from tui_utils.env_management import (
        create_virtual_device,
        list_env_files,
        edit_env_file,
        delete_env_file
    )
    
    if choice == "1":
        create_virtual_device(app)
    elif choice == "2":
        list_env_files(app)
    elif choice == "3":
        edit_env_file(app)
    elif choice == "4":
        delete_env_file(app)
    elif choice == "0":
        app.current_menu = "main"
    else:
        app.console.print("[red]无效的选项，请重新选择[/red]")


def handle_order_test(app, choice: str):
    from tui_utils.order_test import (
        select_env_for_order,
        select_event,
        select_ticket_type,
        execute_order
    )
    
    if choice == "1":
        select_env_for_order(app)
    elif choice == "2":
        select_event(app)
    elif choice == "3":
        select_ticket_type(app)
    elif choice == "4":
        execute_order(app)
    elif choice == "0":
        app.current_menu = "main"
    else:
        app.console.print("[red]无效的选项，请重新选择[/red]")


def handle_ticket_query(app, choice: str):
    from tui_utils.ticket_query import (
        search_events,
        query_by_id,
        view_ticket_info,
        view_purchaser_list
    )
    
    if choice == "1":
        search_events(app)
    elif choice == "2":
        query_by_id(app)
    elif choice == "3":
        view_ticket_info(app)
    elif choice == "4":
        view_purchaser_list(app)
    elif choice == "0":
        app.current_menu = "main"
    else:
        app.console.print("[red]无效的选项，请重新选择[/red]")


def handle_snipe_menu(app, choice: str):
    """处理抢票菜单选择"""
    if choice == "1":
        # 预售模式
        app.current_menu = "presale_config"
    elif choice == "2":
        # 回流模式
        app.current_menu = "resale_config"
    elif choice == "0":
        app.current_menu = "main"
    else:
        app.console.print("[red]无效的选项，请重新选择[/red]")
