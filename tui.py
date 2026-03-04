from rich.console import Console
from rich.prompt import Prompt
from tui_utils.menus import (
    show_main_menu,
    show_env_management_menu,
    show_order_test_menu,
    show_ticket_query_menu
)
from tui_utils.snipe_menu import show_snipe_menu, show_resale_config_menu
from tui_utils.menu_handlers import (
    handle_main_menu,
    handle_env_management,
    handle_order_test,
    handle_ticket_query,
    handle_snipe_menu
)
from tui_utils.resale_mode import resale_config_loop
from tui_utils.presale_mode import presale_config_loop


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
        # 回流模式配置
        self.resale_config = {
            "env_file": None,
            "event_id": None,
            "ticket_info": None,
            "purchaser_ids": None,
            "ticket_count": 1,
            "resale_mode": "split",  # split=拆分回流, merge=合并回流
            "refresh_delay": 150,  # 刷新延迟(ms)
            "order_delay": 150     # 下单延迟(ms)
        }
        # 预售模式配置
        self.presale_config = {
            "env_file": None,
            "event_id": None,
            "ticket_info": None,
            "purchaser_ids": None,
            "ticket_count": 1,
            "presale_mode": "merge",  # merge=合并抢票, split=分离抢票
            "presale_time": None,    # 开抢时间
            "presale_delay": 180,    # 抢票延迟(ms)
            "reflux_timeout": 5,     # 转入回流时间(分钟)
            "burst_delay": 90,       # 爆发模式延迟(ms)
            "time_offset": 0         # 时间偏移(秒)
        }
        
    def run(self):
        while self.running:
            if self.current_menu == "main":
                show_main_menu(self.console, self.debug_mode)
                choice = Prompt.ask("\n请选择功能", choices=["0", "1", "2", "3", "4", "5"], default="0")
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
            elif self.current_menu == "snipe":
                show_snipe_menu(self.console)
                choice = Prompt.ask("\n请选择模式", choices=["0", "1", "2"], default="0")
                handle_snipe_menu(self, choice)
            elif self.current_menu == "resale_config":
                # 回流模式配置循环
                resale_config_loop(self)
            elif self.current_menu == "presale_config":
                # 预售模式配置循环
                presale_config_loop(self)
                
        self.console.print("\n[green]感谢使用，再见！[/green]")


def main():
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
