import os
import json
from rich.table import Table
from rich.prompt import Prompt
from rich import box
from utils.env2sess import generate_environment_file


def get_env_files(app):
    env_files = []
    try:
        for file in os.listdir("."):
            if file.startswith("environment_") and file.endswith(".json"):
                env_files.append(file)
    except Exception as e:
        app.console.print(f"[red]读取文件列表失败: {str(e)}[/red]")
    return env_files


def create_virtual_device(app):
    from tui_utils.menus import show_header

    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]创建虚拟环境[/cyan]")

    name = Prompt.ask("请输入环境名称")
    if not name:
        app.console.print("[yellow]已取消创建[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return

    proxy = Prompt.ask("请输入代理地址(可选，格式如socks5://127.0.0.1:1080)", default="")
    exit_ip = Prompt.ask("请输入出口IP(可选，适用于云主机多IP绑定场景)", default="")

    try:
        proxy_setting = proxy if proxy.strip() else None
        exit_ip_setting = exit_ip if exit_ip.strip() else None
        file_path = generate_environment_file(name, proxy_setting, exit_ip_setting)
        app.console.print(f"[green]虚拟设备创建成功: {file_path}[/green]")
        if exit_ip_setting:
            app.console.print(f"[cyan]已设置出口IP: {exit_ip_setting}[/cyan]")
    except Exception as ex:
        app.console.print(f"[red]创建虚拟设备失败: {str(ex)}[/red]")

    Prompt.ask("按回车键继续", default="")


def list_env_files(app):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]环境文件列表[/cyan]\n")
    
    env_files = get_env_files(app)
    
    if not env_files:
        app.console.print("[yellow]暂无环境文件[/yellow]")
    else:
        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("序号", style="cyan", width=5)
        table.add_column("文件名", style="green")
        
        for idx, file in enumerate(env_files, 1):
            table.add_row(str(idx), file)
        
        app.console.print(table)
    
    Prompt.ask("按回车键继续", default="")


def edit_env_file(app):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]编辑环境文件[/cyan]\n")
    
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
    
    choice = Prompt.ask("\n请选择要编辑的环境文件序号", choices=[str(i) for i in range(1, len(env_files) + 1)])
    
    file_name = env_files[int(choice) - 1]
    
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            env = json.load(f)
        
        while True:
            app.console.clear()
            show_header(app.console)
            app.console.print(f"\n[cyan]环境文件: {file_name}[/cyan]\n")
            
            app.console.print("[bold]编辑选项:[/bold]")
            app.console.print("1. 查看环境详情")
            app.console.print("2. 修改Header配置")
            app.console.print("3. 修改代理配置")
            app.console.print("4. 修改出口IP配置")
            app.console.print("5. 测试出口IP")
            app.console.print("6. 刷新Cookie")
            app.console.print("7. 登录账号")
            app.console.print("0. 返回")

            edit_choice = Prompt.ask("请选择", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="0")

            if edit_choice == "0":
                break
            elif edit_choice == "1":
                show_env_details(app, env, file_name)
                Prompt.ask("按回车键继续", default="")
            elif edit_choice == "2":
                edit_header_config(app, env, file_name)
            elif edit_choice == "3":
                edit_proxy(app, env, file_name)
            elif edit_choice == "4":
                edit_exit_ip(app, env, file_name)
            elif edit_choice == "5":
                test_exit_ip(app, env, file_name)
            elif edit_choice == "6":
                refresh_cookie(app, env, file_name)
            elif edit_choice == "7":
                login(app, env, file_name)
                
    except Exception as ex:
        app.console.print(f"[red]读取环境文件失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def show_env_details(app, env, file_name):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print(f"\n[cyan]环境文件: {file_name}[/cyan]\n")
    
    if "header" in env:
        table = Table(title="Header配置", box=box.SIMPLE)
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="green")
        
        chinese_names = {
            "mobileSource": "移动设备来源",
            "equipmentType": "设备类型",
            "deviceVersion": "设备版本",
            "deviceSpec": "设备规格",
            "appHeader": "应用头部",
            "appVersion": "应用版本",
            "userAgent": "用户代理",
            "User-Agent": "用户代理",
            "Accept-Language": "接受语言",
            "Accept-Encoding": "接受编码",
            "Accept": "接受类型",
            "Connection": "连接状态"
        }
        
        for key, value in env["header"].items():
            display_name = chinese_names.get(key, key)
            display_value = str(value)
            if len(display_value) > 50:
                display_value = display_value[:47] + "..."
            table.add_row(display_name, display_value)
        
        app.console.print(table)
    
    if "proxy" in env and env["proxy"]:
        app.console.print(f"\n[bold]代理配置:[/bold] {env['proxy']}")

    if "exit_ip" in env and env["exit_ip"]:
        app.console.print(f"[bold]出口IP:[/bold] {env['exit_ip']}")
    else:
        app.console.print("[bold]出口IP:[/bold] 未设置")

    if "cookie" in env and env["cookie"]:
        cookie_count = len(env["cookie"]) if isinstance(env["cookie"], dict) else 1
        app.console.print(f"[bold]Cookie:[/bold] 已设置 ({cookie_count} 项)")
    else:
        app.console.print("[bold]Cookie:[/bold] 未设置")


def edit_header_config(app, env, file_name):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print(f"\n[cyan]编辑Header配置 - {file_name}[/cyan]\n")
    
    if "header" not in env:
        app.console.print("[yellow]该环境文件没有header配置[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return
    
    chinese_names = {
        "mobileSource": "移动设备来源",
        "equipmentType": "设备类型",
        "deviceVersion": "设备版本",
        "deviceSpec": "设备规格",
        "appHeader": "应用头部",
        "appVersion": "应用版本",
        "userAgent": "用户代理",
        "User-Agent": "用户代理",
        "Accept-Language": "接受语言",
        "Accept-Encoding": "接受编码",
        "Accept": "接受类型",
        "Connection": "连接状态"
    }
    
    header = env["header"]
    
    while True:
        app.console.clear()
        show_header(app.console)
        app.console.print(f"\n[cyan]编辑Header配置 - {file_name}[/cyan]\n")
        
        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("序号", style="cyan", width=5)
        table.add_column("配置项", style="green")
        table.add_column("当前值", style="yellow")
        
        for idx, (key, value) in enumerate(header.items(), 1):
            display_name = chinese_names.get(key, key)
            display_value = str(value)
            if len(display_value) > 40:
                display_value = display_value[:37] + "..."
            table.add_row(str(idx), display_name, display_value)
        
        app.console.print(table)
        app.console.print("0. 返回")
        
        choice = Prompt.ask("\n请选择要修改的配置项序号", choices=[str(i) for i in range(0, len(header) + 1)])
        
        if choice == "0":
            break
        
        key = list(header.keys())[int(choice) - 1]
        display_name = chinese_names.get(key, key)
        current_value = str(header[key])
        
        app.console.print(f"\n[cyan]修改 {display_name} ({key})[/cyan]")
        app.console.print(f"当前值: {current_value}")
        
        new_value = Prompt.ask("请输入新值 (直接回车保持不变)", default=current_value)
        
        if new_value != current_value:
            header[key] = new_value
            app.console.print(f"[green]已更新 {display_name}[/green]")
            
            try:
                with open(file_name, "w", encoding="utf-8") as f:
                    json.dump(env, f, ensure_ascii=False, indent=2)
                app.console.print("[green]配置已保存[/green]")
            except Exception as ex:
                app.console.print(f"[red]保存失败: {str(ex)}[/red]")
        else:
            app.console.print("[yellow]未修改[/yellow]")
        
        Prompt.ask("按回车键继续", default="")


def edit_proxy(app, env, file_name):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print(f"\n[cyan]修改代理配置 - {file_name}[/cyan]\n")
    
    current_proxy = env.get("proxy", "")
    app.console.print(f"当前代理: {current_proxy if current_proxy else '未设置'}\n")
    
    proxy_type = "https"
    proxy_address = ""
    
    if current_proxy:
        if current_proxy.startswith("socks5://"):
            proxy_type = "socks5"
            proxy_address = current_proxy[9:]
        elif current_proxy.startswith("https://"):
            proxy_type = "https"
            proxy_address = current_proxy[8:]
        else:
            proxy_address = current_proxy
    
    app.console.print(f"当前代理类型: {proxy_type}")
    app.console.print(f"当前代理地址: {proxy_address}\n")
    
    proxy_type = Prompt.ask("代理类型", choices=["https", "socks5"], default=proxy_type)
    proxy_address = Prompt.ask("代理地址 (直接回车清除代理)", default=proxy_address)
    
    if proxy_address.strip():
        new_proxy = f"{proxy_type}://{proxy_address}"
        env["proxy"] = new_proxy
        app.console.print(f"\n[green]代理已设置为: {new_proxy}[/green]")
    else:
        if "proxy" in env:
            del env["proxy"]
        app.console.print("\n[green]代理已清除[/green]")
    
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(env, f, ensure_ascii=False, indent=2)
        app.console.print("[green]配置已保存[/green]")
    except Exception as ex:
        app.console.print(f"[red]保存失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def refresh_cookie(app, env, file_name):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print(f"\n[cyan]刷新Cookie - {file_name}[/cyan]\n")
    
    try:
        from utils.env2sess import env_to_request_session
        
        app.console.print("[cyan]正在获取新Cookie...[/cyan]")
        session = env_to_request_session(env)
        
        if session.cookies:
            try:
                env["cookie"] = dict(session.cookies)
            except Exception:
                cookie_dict = {}
                for cookie in session.cookies:
                    cookie_dict[cookie.name] = cookie.value
                env["cookie"] = cookie_dict
            
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(env, f, ensure_ascii=False, indent=2)
            
            app.console.print(f"\n[green]Cookie已刷新，共 {len(env['cookie'])} 项[/green]")
            
            table = Table(box=box.SIMPLE, show_header=True)
            table.add_column("Cookie名称", style="cyan")
            table.add_column("值预览", style="yellow")
            
            for key, value in list(env["cookie"].items())[:10]:
                display_value = str(value)
                if len(display_value) > 30:
                    display_value = display_value[:27] + "..."
                table.add_row(key, display_value)
            
            if len(env["cookie"]) > 10:
                table.add_row(f"... 还有 {len(env['cookie']) - 10} 项", "")
            
            app.console.print(table)
        else:
            app.console.print("[yellow]未获取到新的Cookie[/yellow]")
            
    except Exception as ex:
        app.console.print(f"[red]刷新Cookie失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def login(app, env, file_name):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print(f"\n[cyan]登录账号 - {file_name}[/cyan]\n")
    
    try:
        from utils.user.check import check_if_user_exists
        from utils.user.login import get_login_code
        import utils.urls as urls
        from utils.env2sess import env_to_request_session
        
        country = Prompt.ask("区号", default="86")
        phone = Prompt.ask("手机号")
        
        if not country or not phone:
            app.console.print("[yellow]请输入完整的区号和手机号[/yellow]")
            Prompt.ask("按回车键继续", default="")
            return
        
        app.console.print("\n[cyan]检查用户是否存在...[/cyan]")
        exists = check_if_user_exists(env, country, phone)
        
        if not exists:
            app.console.print("[red]用户不存在，请先去ALLCPP注册账号再试[/red]")
            Prompt.ask("按回车键继续", default="")
            return
        
        app.console.print("[green]用户存在[/green]\n")
        
        get_code = Prompt.ask("是否获取验证码", choices=["y", "n"], default="y")
        
        if get_code.lower() == "y":
            try:
                success, message = get_login_code(env, country, phone)
                
                if success:
                    app.console.print("[green]验证码已发送[/green]")
                else:
                    app.console.print(f"[red]获取验证码失败: {message}[/red]")
                    Prompt.ask("按回车键继续", default="")
                    return
            except Exception as ex:
                app.console.print(f"[red]获取验证码失败: {str(ex)}[/red]")
                Prompt.ask("按回车键继续", default="")
                return
            
            verify_code = Prompt.ask("请输入验证码")
            
            if not verify_code:
                app.console.print("[yellow]验证码不能为空[/yellow]")
                Prompt.ask("按回车键继续", default="")
                return
            
            app.console.print("\n[cyan]正在登录...[/cyan]")
            
            try:
                from utils.user.login import user_login_sms
                
                session, success, message = user_login_sms(env, country, phone, verify_code)
                
                if success:
                    app.console.print("[green]登录成功！[/green]")
                    
                    if session.cookies:
                        try:
                            env["cookie"] = dict(session.cookies)
                        except Exception:
                            cookie_dict = {}
                            for cookie in session.cookies:
                                cookie_dict[cookie.name] = cookie.value
                            env["cookie"] = cookie_dict
                        
                        with open(file_name, "w", encoding="utf-8") as f:
                            json.dump(env, f, ensure_ascii=False, indent=2)
                        app.console.print("[cyan]Cookie已保存[/cyan]")
                else:
                    app.console.print(f"[red]登录失败: {message}[/red]")
                    
            except Exception as ex:
                app.console.print(f"[red]登录失败: {str(ex)}[/red]")
        else:
            app.console.print("[yellow]已取消登录[/yellow]")
            
    except Exception as ex:
        app.console.print(f"[red]登录失败: {str(ex)}[/red]")
    
    Prompt.ask("按回车键继续", default="")


def delete_env_file(app):
    from tui_utils.menus import show_header
    
    app.console.clear()
    show_header(app.console)
    app.console.print("\n[cyan]删除环境文件[/cyan]\n")
    
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
    
    choice = Prompt.ask("\n请选择要删除的环境文件序号", choices=[str(i) for i in range(1, len(env_files) + 1)])
    
    file_name = env_files[int(choice) - 1]
    
    confirm = Prompt.ask(f"确认删除 {file_name}?", choices=["y", "n"], default="n")
    
    if confirm.lower() == "y":
        try:
            os.remove(file_name)
            app.console.print(f"[green]已删除: {file_name}[/green]")
        except Exception as ex:
            app.console.print(f"[red]删除失败: {str(ex)}[/red]")
    else:
        app.console.print("[yellow]已取消删除[/yellow]")

    Prompt.ask("按回车键继续", default="")


def edit_exit_ip(app, env, file_name):
    from tui_utils.menus import show_header

    app.console.clear()
    show_header(app.console)
    app.console.print(f"\n[cyan]修改出口IP配置 - {file_name}[/cyan]\n")

    current_exit_ip = env.get("exit_ip", "")
    app.console.print(f"当前出口IP: {current_exit_ip if current_exit_ip else '未设置'}\n")
    app.console.print("[dim]说明: 出口IP用于云主机多IP绑定场景，请求将使用指定的源IP地址[/dim]\n")

    new_exit_ip = Prompt.ask("请输入新的出口IP (直接回车清除)", default=current_exit_ip)

    if new_exit_ip.strip():
        # 简单验证IP格式
        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, new_exit_ip.strip()):
            env["exit_ip"] = new_exit_ip.strip()
            app.console.print(f"\n[green]出口IP已设置为: {new_exit_ip.strip()}[/green]")
        else:
            app.console.print("[red]IP格式不正确，应为xxx.xxx.xxx.xxx格式[/red]")
            Prompt.ask("按回车键继续", default="")
            return
    else:
        if "exit_ip" in env:
            del env["exit_ip"]
        app.console.print("\n[yellow]出口IP已清除[/yellow]")

    try:
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(env, f, ensure_ascii=False, indent=2)
        app.console.print("[green]配置已保存[/green]")
    except Exception as ex:
        app.console.print(f"[red]保存失败: {str(ex)}[/red]")

    Prompt.ask("按回车键继续", default="")


def test_exit_ip(app, env, file_name):
    from tui_utils.menus import show_header

    app.console.clear()
    show_header(app.console)
    app.console.print(f"\n[cyan]测试出口IP - {file_name}[/cyan]\n")

    exit_ip = env.get("exit_ip", "")
    if not exit_ip:
        app.console.print("[yellow]该环境未设置出口IP[/yellow]")
        Prompt.ask("按回车键继续", default="")
        return

    app.console.print(f"[bold]配置的出口IP:[/bold] {exit_ip}\n")

    try:
        from utils.env2sess import env_to_request_session

        app.console.print("[cyan]正在测试出口IP...[/cyan]")
        app.console.print("[dim]正在请求 httpbin.org/ip 获取当前出口IP...[/dim]\n")

        session = env_to_request_session(env)

        # 测试请求，获取当前出口IP
        response = session.get("https://httpbin.org/ip", timeout=10)
        result = response.json()

        actual_ip = result.get("origin", "未知")
        app.console.print(f"[bold]实际出口IP:[/bold] {actual_ip}")

        if exit_ip in actual_ip:
            app.console.print("\n[green]✓ 出口IP配置正确！请求已成功使用指定的源IP地址[/green]")
        else:
            app.console.print("\n[yellow]⚠ 警告: 实际出口IP与配置的出口IP不一致[/yellow]")
            app.console.print("[dim]可能原因:[/dim]")
            app.console.print("  - 该IP未绑定到当前主机")
            app.console.print("  - 代理设置覆盖了出口IP")
            app.console.print("  - 网络配置问题")

    except Exception as ex:
        app.console.print(f"[red]测试失败: {str(ex)}[/red]")
        app.console.print("[dim]可能原因: 网络连接问题或IP配置错误[/dim]")

    Prompt.ask("\n按回车键继续", default="")
