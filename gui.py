import flet as ft
from utils.env2sess import generate_environment_file

class App:
    def __init__(self):
        self.logs = []
    
    def add_log(self, message):
        self.logs.append(message)
        if len(self.logs) > 50:  # 限制日志数量
            self.logs.pop(0)
        self.log_text.value = "\n".join(self.logs)
        self.log_text.update()
    
    def create_virtual_device(self, e):
        try:
            # 生成环境配置文件
            file_path = generate_environment_file("gui")
            self.add_log(f"虚拟设备创建成功: {file_path}")
        except Exception as ex:
            self.add_log(f"创建虚拟设备失败: {str(ex)}")
    
    def build(self, page: ft.Page):
        page.title = "RanaRun乐奈快跑 - ALLCPP购票 - 严禁商业化使用"
        page.window.width = 800
        page.window.height = 600
        
        # 创建选项卡
        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("虚拟设备生成", size=20, weight=ft.FontWeight.BOLD),
                                ft.Button(
                                    content=ft.Text("创建虚拟设备"),
                                    on_click=self.create_virtual_device
                                ),
                                ft.Text("点击上方按钮创建虚拟设备，生成environment_gui.json文件"),
                            ],
                            spacing=20,
                        ),
                        padding=20
                    )
                ),
            ],
            expand=1
        )
        
        # 创建日志区
        self.log_text = ft.Text(
            value="",
            size=12
        )
        
        log_area = ft.Container(
            content=ft.Column(
                [
                    ft.Text("日志"),
                    ft.Container(
                        content=ft.Column([self.log_text]),
                        border=ft.border.all(1, ft.colors.GREY_300),
                        padding=10
                    )
                ],
                spacing=10
            ),
            padding=20
        )
        
        # 构建页面布局
        page.add(
            ft.Column(
                [
                    tabs,
                    log_area
                ],
                expand=True
            )
        )
        
        # 初始化日志
        self.add_log("应用已启动")

def main(page: ft.Page):
    app = App()
    app.build(page)

if __name__ == "__main__":
    ft.app(target=main)
