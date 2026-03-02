import flet as ft

def main(page: ft.Page):
    # 页面基础设置
    page.title = "Flet问候工具"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER  # 垂直居中
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER  # 水平居中

    # 创建输入框和显示文本
    name_input = ft.TextField(
        label="请输入你的名字", 
        width=300, 
        text_align=ft.TextAlign.LEFT
    )
    greeting_text = ft.Text(size=18)

    # 按钮点击事件
    def on_click(e):
        greeting_text.value = f"你好，{name_input.value}！2025年一起加油～"
        page.update()  # 刷新页面

    # 添加控件到页面
    page.add(
        name_input,
        ft.ElevatedButton("生成问候", on_click=on_click),
        greeting_text
    )

# 启动应用（桌面端），想转Web加view=ft.WEB_BROWSER
ft.app(target=main)


