from rich.console import Console
from rich.prompt import Prompt
from tui_utils.menus import (
    show_main_menu,
    show_env_management_menu,
    show_order_test_menu,
    show_ticket_query_menu
)
from tui_utils.menu_handlers import (
    handle_main_menu,
    handle_env_management,
    handle_order_test,
    handle_ticket_query
)


class TUIApp:
    def __init__(self):
        self.console = Console()
        self.running = True
        self.current_menu = "main"
        self.debug_mode = False
        self.order_config = {
            "env_file": None,
            "event_id": None,
            "ticket_info": None,
            "purchaser_ids": None,
            "ticket_count": 1,
            "base_delay": 0.5
        }
        
    def run(self):
        while self.running:
            if self.current_menu == "main":
                show_main_menu(self.console, self.debug_mode)
                choice = Prompt.ask("\n请选择功能", choices=["0", "1", "2", "3", "4"], default="0")
                handle_main_menu(self, choice)
            elif self.current_menu == "env_management":
                show_env_management_menu(self.console)
                choice = Prompt.ask("\n请选择功能", choices=["0", "1", "2", "3", "4"], default="0")
                handle_env_management(self, choice)
            elif self.current_menu == "order_test":
                show_order_test_menu(self.console)
                choice = Prompt.ask("\n请选择功能", choices=["0", "1", "2", "3", "4"], default="0")
                handle_order_test(self, choice)
            elif self.current_menu == "ticket_query":
                show_ticket_query_menu(self.console)
                choice = Prompt.ask("\n请选择功能", choices=["0", "1", "2", "3", "4"], default="0")
                handle_ticket_query(self, choice)
                
        self.console.print("\n[green]感谢使用，再见！[/green]")


def main():
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
