import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
import requests
import time
import random
import hashlib
from utils.env2sess import generate_environment_file, env_to_request_session
from utils.signer.gen import generate_signature

def create_session(config: dict) -> requests.Session:
    """
    根据配置创建requests session
    """
    # 检测配置格式，如果包含header字段，则使用env_to_request_session处理
    if "header" in config:
        return env_to_request_session(config)
    
    # 原有格式处理
    session = requests.Session()

    # 设置cookie
    if config.get("cookie"):
        cookies = {}
        if isinstance(config["cookie"], str):
            # 字符串格式的cookie
            for cookie in config["cookie"].split(";"):
                if "=" in cookie:
                    key, value = cookie.strip().split("=", 1)
                    cookies[key] = value
        elif isinstance(config["cookie"], dict):
            # 字典格式的cookie
            cookies = config["cookie"]
        session.cookies.update(cookies)

    # 设置headers
    if config.get("headers"):
        session.headers.update(config["headers"])

    # 设置代理
    if config.get("proxy") and config["proxy"].strip():
        proxies = {
            "http": config["proxy"],
            "https": config["proxy"]
        }
        session.proxies.update(proxies)

    return session

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("RanaRun乐奈快跑 - ALLCPP购票 - 严禁商业化使用")
        self.root.geometry("1000x800")
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建选项卡
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 环境管理选项卡
        self.env_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.env_tab, text="环境管理")
        
        # 环境管理选项卡内容
        # 创建顶部框架（列表头和按钮）
        self.top_frame = ttk.Frame(self.env_tab)
        self.top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 列表标题
        ttk.Label(self.top_frame, text="环境文件列表", font=("SimHei", 12, "bold")).pack(side=tk.LEFT)
        
        # 创建虚拟环境按钮
        self.create_btn = ttk.Button(self.top_frame, text="创建虚拟环境", command=self.create_virtual_device)
        self.create_btn.pack(side=tk.RIGHT)
        
        # 创建列表框架
        self.list_frame = ttk.Frame(self.env_tab)
        self.list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建列表
        self.tree = ttk.Treeview(self.list_frame, columns=("name"), show="headings")
        self.tree.heading("name", text="环境文件名")
        self.tree.column("name", width=700)
        
        # 绑定点击事件
        self.tree.bind("<<TreeviewSelect>>", self.show_env_info)
        
        # 绑定右键菜单
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # 创建信息展示区
        self.info_frame = ttk.LabelFrame(self.env_tab, text="环境信息", padding="10")
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 票务信息查询选项卡
        self.ticket_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.ticket_tab, text="票务信息查询")
        
        # 票务信息查询选项卡内容
        self.ticket_frame = ttk.Frame(self.ticket_tab, padding="10")
        self.ticket_frame.pack(fill=tk.BOTH, expand=True)
        
        # 购买人管理选项卡
        self.purchaser_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.purchaser_tab, text="购买人管理")
        
        # 购买人管理选项卡内容
        self.purchaser_frame = ttk.Frame(self.purchaser_tab, padding="10")
        self.purchaser_frame.pack(fill=tk.BOTH, expand=True)
        
        # 环境文件选择
        ttk.Label(self.purchaser_frame, text="环境文件:", font=("SimHei", 10, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.purchaser_env_var = tk.StringVar()
        self.purchaser_env_combobox = ttk.Combobox(self.purchaser_frame, textvariable=self.purchaser_env_var, width=50)
        self.purchaser_env_combobox.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 获取购买人列表按钮
        self.get_purchasers_btn = ttk.Button(self.purchaser_frame, text="获取购买人列表", command=self.get_purchaser_list)
        self.get_purchasers_btn.grid(row=0, column=2, padx=10, pady=10, sticky=tk.W)
        
        # 购买人列表
        ttk.Label(self.purchaser_frame, text="购买人列表:", font=("SimHei", 10, "bold")).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.purchaser_list_frame = ttk.Frame(self.purchaser_frame)
        self.purchaser_list_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)
        
        # 创建购买人列表
        self.purchaser_tree = ttk.Treeview(self.purchaser_list_frame, columns= ("id", "name", "idCard", "mobile"), show="headings")
        self.purchaser_tree.heading("id", text="购买人ID")
        self.purchaser_tree.heading("name", text="姓名")
        self.purchaser_tree.heading("idCard", text="身份证号")
        self.purchaser_tree.heading("mobile", text="手机号")
        self.purchaser_tree.column("id", width=100)
        self.purchaser_tree.column("name", width=100)
        self.purchaser_tree.column("idCard", width=200)
        self.purchaser_tree.column("mobile", width=150)
        
        # 添加滚动条
        purchaser_scrollbar = ttk.Scrollbar(self.purchaser_list_frame, orient=tk.VERTICAL, command=self.purchaser_tree.yview)
        self.purchaser_tree.configure(yscroll=purchaser_scrollbar.set)
        purchaser_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.purchaser_tree.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重
        self.purchaser_frame.columnconfigure(1, weight=1)
        self.purchaser_frame.rowconfigure(2, weight=1)
        
        # 下单测试选项卡
        self.purchase_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.purchase_tab, text="下单测试")
        
        # 下单测试选项卡内容
        self.purchase_frame = ttk.Frame(self.purchase_tab, padding="10")
        self.purchase_frame.pack(fill=tk.BOTH, expand=True)
        
        # 环境文件选择
        ttk.Label(self.purchase_frame, text="环境文件:", font=("SimHei", 10, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.purchase_env_var = tk.StringVar()
        self.purchase_env_combobox = ttk.Combobox(self.purchase_frame, textvariable=self.purchase_env_var, width=50)
        self.purchase_env_combobox.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 活动ID输入
        ttk.Label(self.purchase_frame, text="活动ID:", font=('SimHei', 10, 'bold')).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.event_id_var = tk.StringVar(value="6198")  # 默认活动ID
        self.event_id_entry = ttk.Entry(self.purchase_frame, textvariable=self.event_id_var, width=20)
        self.event_id_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 获取票档列表按钮
        self.get_ticket_list_btn = ttk.Button(self.purchase_frame, text="获取票档列表", command=self.get_ticket_list)
        self.get_ticket_list_btn.grid(row=1, column=2, padx=10, pady=10, sticky=tk.W)
        
        # 票档列表
        ttk.Label(self.purchase_frame, text="票档列表:", font=('SimHei', 10, 'bold')).grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        self.ticket_list_frame = ttk.Frame(self.purchase_frame, height=200)  # 设置最小高度
        self.ticket_list_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)
        self.ticket_list_frame.grid_propagate(False)  # 防止框架大小被内容撑开
        
        # 创建票档列表
        self.ticket_tree = ttk.Treeview(self.ticket_list_frame, columns= ("id", "name", "price", "stock", "realname"), show="headings")
        self.ticket_tree.heading("id", text="票档ID")
        self.ticket_tree.heading("name", text="票档名称")
        self.ticket_tree.heading("price", text="价格")
        self.ticket_tree.heading("stock", text="余票")
        self.ticket_tree.heading("realname", text="是否实名")
        self.ticket_tree.column("id", width=100)
        self.ticket_tree.column("name", width=200)
        self.ticket_tree.column("price", width=80)
        self.ticket_tree.column("stock", width=80)
        self.ticket_tree.column("realname", width=100)
        
        # 添加滚动条
        ticket_scrollbar = ttk.Scrollbar(self.ticket_list_frame, orient=tk.VERTICAL, command=self.ticket_tree.yview)
        self.ticket_tree.configure(yscroll=ticket_scrollbar.set)
        ticket_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ticket_tree.pack(fill=tk.BOTH, expand=True)
        
        # 绑定票档选择事件
        self.ticket_tree.bind("<<TreeviewSelect>>", self.on_ticket_select)
        
        # 票张数输入
        ttk.Label(self.purchase_frame, text="票张数:", font=('SimHei', 10, 'bold')).grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        self.ticket_count_var = tk.StringVar(value="1")  # 默认1张
        self.ticket_count_entry = ttk.Entry(self.purchase_frame, textvariable=self.ticket_count_var, width=10)
        self.ticket_count_entry.grid(row=4, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 购票人ID输入（默认禁用，根据票信息启用）
        ttk.Label(self.purchase_frame, text="购买人ID:", font=('SimHei', 10, 'bold')).grid(row=5, column=0, padx=10, pady=10, sticky=tk.W)
        self.purchaser_id_var = tk.StringVar(value="")  # 默认空
        self.purchaser_id_entry = ttk.Entry(self.purchase_frame, textvariable=self.purchaser_id_var, width=50, state=tk.DISABLED)
        self.purchaser_id_entry.grid(row=5, column=1, padx=10, pady=10, sticky=tk.W)
        ttk.Label(self.purchase_frame, text="多个购买人ID用逗号隔开", font=('SimHei', 8)).grid(row=6, column=1, padx=10, pady=5, sticky=tk.W)
        
        # 基准延迟输入
        ttk.Label(self.purchase_frame, text="基准延迟(秒):", font=('SimHei', 10, 'bold')).grid(row=7, column=0, padx=10, pady=10, sticky=tk.W)
        self.delay_var = tk.StringVar(value="0.5")  # 默认值
        self.delay_entry = ttk.Entry(self.purchase_frame, textvariable=self.delay_var, width=10)
        self.delay_entry.grid(row=7, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 测试按钮
        self.test_purchase_btn = ttk.Button(self.purchase_frame, text="测试下单", command=self.test_purchase)
        self.test_purchase_btn.grid(row=7, column=2, padx=10, pady=10, sticky=tk.W)
        
        # 结果显示区域
        ttk.Label(self.purchase_frame, text="测试结果:", font=('SimHei', 10, 'bold')).grid(row=8, column=0, padx=10, pady=10, sticky=tk.W)
        self.purchase_result_frame = ttk.LabelFrame(self.purchase_frame, text="测试结果", padding="10")
        self.purchase_result_frame.grid(row=9, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)
        
        self.purchase_result_text = tk.Text(self.purchase_result_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.purchase_result_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重
        self.purchase_frame.columnconfigure(1, weight=1)
        self.purchase_frame.rowconfigure(3, weight=1)
        self.purchase_frame.rowconfigure(9, weight=1)
        
        # 存储当前票信息和票档列表
        self.current_ticket_info = None
        self.ticket_list = []
        
        # 环境文件选择
        ttk.Label(self.ticket_frame, text="环境文件:", font=("SimHei", 10, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.env_file_var = tk.StringVar()
        self.env_file_combobox = ttk.Combobox(self.ticket_frame, textvariable=self.env_file_var, width=50)
        self.env_file_combobox.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 城市代码输入
        ttk.Label(self.ticket_frame, text="城市代码:", font=("SimHei", 10, "bold")).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.city_code_var = tk.StringVar(value="310100")  # 默认上海
        self.city_code_entry = ttk.Entry(self.ticket_frame, textvariable=self.city_code_var, width=20)
        self.city_code_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 关键词输入
        ttk.Label(self.ticket_frame, text="关键词:", font=("SimHei", 10, "bold")).grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        self.keyword_var = tk.StringVar(value="comicup")
        self.keyword_entry = ttk.Entry(self.ticket_frame, textvariable=self.keyword_var, width=50)
        self.keyword_entry.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 搜索按钮
        self.search_btn = ttk.Button(self.ticket_frame, text="搜索", command=self.search_events)
        self.search_btn.grid(row=2, column=2, padx=10, pady=10, sticky=tk.W)
        
        # 活动ID输入
        ttk.Label(self.ticket_frame, text="活动ID:", font=("SimHei", 10, "bold")).grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        self.event_id_var = tk.StringVar(value="6198")  # 默认值
        self.event_id_entry = ttk.Entry(self.ticket_frame, textvariable=self.event_id_var, width=20)
        self.event_id_entry.grid(row=3, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 根据ID获取票信息按钮
        self.get_ticket_by_id_btn = ttk.Button(self.ticket_frame, text="根据ID获取票信息", command=self.get_ticket_by_id)
        self.get_ticket_by_id_btn.grid(row=3, column=2, padx=10, pady=10, sticky=tk.W)
        
        # 搜索结果列表
        ttk.Label(self.ticket_frame, text="搜索结果:", font=("SimHei", 10, "bold")).grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        self.event_list_frame = ttk.Frame(self.ticket_frame)
        self.event_list_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)
        
        # 创建结果列表
        self.event_tree = ttk.Treeview(self.event_list_frame, columns=("name", "type", "city", "time"), show="headings")
        self.event_tree.heading("name", text="活动名称")
        self.event_tree.heading("type", text="类型")
        self.event_tree.heading("city", text="城市")
        self.event_tree.heading("time", text="时间")
        self.event_tree.column("name", width=300)
        self.event_tree.column("type", width=100)
        self.event_tree.column("city", width=100)
        self.event_tree.column("time", width=200)
        
        # 绑定点击事件
        self.event_tree.bind("<<TreeviewSelect>>", self.show_ticket_info)
        
        # 添加滚动条
        event_scrollbar = ttk.Scrollbar(self.event_list_frame, orient=tk.VERTICAL, command=self.event_tree.yview)
        self.event_tree.configure(yscroll=event_scrollbar.set)
        event_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.event_tree.pack(fill=tk.BOTH, expand=True)
        
        # 票务信息展示
        ttk.Label(self.ticket_frame, text="票务信息:", font=("SimHei", 10, "bold")).grid(row=6, column=0, padx=10, pady=10, sticky=tk.W)
        self.ticket_info_frame = ttk.LabelFrame(self.ticket_frame, text="活动详情", padding="10")
        self.ticket_info_frame.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)
        
        # 创建分页控件
        self.ticket_notebook = ttk.Notebook(self.ticket_info_frame)
        self.ticket_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重
        self.ticket_frame.columnconfigure(1, weight=1)
        self.ticket_frame.rowconfigure(5, weight=1)
        self.ticket_frame.rowconfigure(7, weight=2)
        
        # 创建信息展示和编辑区域
        self.info_notebook = ttk.Notebook(self.info_frame)
        self.info_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 原始JSON标签页
        self.json_tab = ttk.Frame(self.info_notebook)
        self.info_notebook.add(self.json_tab, text="原始JSON")
        
        self.info_text = tk.Text(self.json_tab, wrap=tk.WORD, state=tk.DISABLED)
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # 可视化编辑标签页
        self.edit_tab = ttk.Frame(self.info_notebook)
        self.info_notebook.add(self.edit_tab, text="可视化编辑")
        
        # 创建编辑表单
        self.edit_frame = ttk.Frame(self.edit_tab, padding="10")
        self.edit_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条
        self.edit_scrollbar = ttk.Scrollbar(self.edit_frame)
        self.edit_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建编辑画布
        self.edit_canvas = tk.Canvas(self.edit_frame, yscrollcommand=self.edit_scrollbar.set)
        self.edit_canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        self.edit_scrollbar.config(command=self.edit_canvas.yview)
        
        # 创建编辑内容框架
        self.edit_content = ttk.Frame(self.edit_canvas)
        self.edit_canvas.create_window((0, 0), window=self.edit_content, anchor=tk.NW)
        
        # 存储当前编辑的环境文件和配置
        self.current_env_file = None
        self.current_env = None
        self.original_env = None
        
        # 创建右键菜单
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="删除", command=self.delete_env)
        self.context_menu.add_command(label="刷新cookie", command=self.refresh_cookie)
        self.context_menu.add_command(label="登录", command=self.login)
        
        # 加载环境文件列表
        self.load_env_files()
    
    def load_env_files(self):
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 列出所有environment_开头的json文件
        env_files = []
        for file in os.listdir("."):
            if file.startswith("environment_") and file.endswith(".json"):
                self.tree.insert("", tk.END, values=(file,))
                env_files.append(file)
        
        # 更新票务查询选项卡中的环境文件下拉列表
        self.env_file_combobox['values'] = env_files
        if env_files:
            self.env_file_var.set(env_files[0])
        
        # 更新购买人管理选项卡中的环境文件下拉列表
        self.purchaser_env_combobox['values'] = env_files
        if env_files:
            self.purchaser_env_var.set(env_files[0])
        
        # 更新下单测试选项卡中的环境文件下拉列表
        self.purchase_env_combobox['values'] = env_files
        if env_files:
            self.purchase_env_var.set(env_files[0])
    
    def create_virtual_device(self):
        # 创建一个输入对话框让用户输入文件名
        dialog = tk.Toplevel(self.root)
        dialog.title("创建虚拟设备")
        dialog.geometry("300x150")
        
        # 添加标签和输入框
        ttk.Label(dialog, text="请输入环境名称:", padding=(10, 10)).pack(fill=tk.X)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).pack(padx=10, pady=10)
        
        # 确认按钮
        def confirm():
            name = name_var.get().strip()
            if not name:
                messagebox.showinfo("提示", "请输入环境名称")
                return
            
            # 生成环境配置文件
            try:
                file_path = generate_environment_file(name)
                messagebox.showinfo("成功", f"虚拟设备创建成功: {file_path}")
                # 重新加载列表
                self.load_env_files()
                # 关闭对话框
                dialog.destroy()
            except Exception as ex:
                messagebox.showerror("错误", f"创建虚拟设备失败: {str(ex)}")
        
        # 取消按钮
        def cancel():
            dialog.destroy()
        
        # 添加按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="确认", command=confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=cancel).pack(side=tk.LEFT, padx=10)
        
        # 聚焦输入框
        dialog.wait_window()
    
    def show_env_info(self, event):
        # 显示选中的环境文件信息
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        file_name = self.tree.item(selected_item[0], "values")[0]
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                env = json.load(f)
            
            # 存储当前环境文件和配置
            self.current_env_file = file_name
            self.current_env = env.copy()
            self.original_env = env.copy()
            
            # 清空信息区
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            
            # 格式化显示环境信息
            info = json.dumps(env, ensure_ascii=False, indent=2)
            self.info_text.insert(tk.END, info)
            self.info_text.config(state=tk.DISABLED)
            
            # 生成可视化编辑表单
            self.generate_edit_form(env)
            
        except Exception as ex:
            messagebox.showerror("错误", f"读取环境文件失败: {str(ex)}")
    
    def generate_edit_form(self, env):
        # 清空编辑内容
        for widget in self.edit_content.winfo_children():
            widget.destroy()
        
        # 创建表单标题
        ttk.Label(self.edit_content, text="环境配置编辑", font=("SimHei", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        # 存储输入控件
        self.input_widgets = {}
        
        # 显示header配置
        ttk.Label(self.edit_content, text="Header配置", font=("SimHei", 10, "bold")).grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        if "header" in env:
            header = env["header"]
            row = 2
            for key, value in header.items():
                ttk.Label(self.edit_content, text=f"{self.get_chinese_name(key)}:", width=20, anchor=tk.E).grid(row=row, column=0, pady=5, padx=10, sticky=tk.W)
                entry = ttk.Entry(self.edit_content, width=50)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, pady=5, padx=10, sticky=tk.W)
                self.input_widgets[f"header.{key}"] = entry
                row += 1
        
        # 显示proxy配置
        ttk.Label(self.edit_content, text="代理配置", font=("SimHei", 10, "bold")).grid(row=row, column=0, columnspan=2, pady=10, sticky=tk.W)
        row += 1
        
        # 代理类型选择
        ttk.Label(self.edit_content, text="代理类型:", width=20, anchor=tk.E).grid(row=row, column=0, pady=5, padx=10, sticky=tk.W)
        proxy_type_var = tk.StringVar()
        proxy_type_combobox = ttk.Combobox(self.edit_content, textvariable=proxy_type_var, values=["https", "socks5"], width=10)
        proxy_type_combobox.grid(row=row, column=1, pady=5, padx=10, sticky=tk.W)
        self.input_widgets["proxy_type"] = proxy_type_combobox
        row += 1
        
        # 代理地址输入
        proxy_value = env.get("proxy", "")
        # 提取代理类型和地址
        proxy_type = "https"
        proxy_address = ""
        if proxy_value:
            if proxy_value.startswith("socks5://"):
                proxy_type = "socks5"
                proxy_address = proxy_value[9:]
            elif proxy_value.startswith("https://"):
                proxy_type = "https"
                proxy_address = proxy_value[8:]
            else:
                proxy_address = proxy_value
        
        proxy_type_var.set(proxy_type)
        
        ttk.Label(self.edit_content, text="代理地址:", width=20, anchor=tk.E).grid(row=row, column=0, pady=5, padx=10, sticky=tk.W)
        proxy_entry = ttk.Entry(self.edit_content, width=40)
        proxy_entry.insert(0, proxy_address)
        proxy_entry.grid(row=row, column=1, pady=5, padx=10, sticky=tk.W)
        self.input_widgets["proxy_address"] = proxy_entry
        
        # 保存按钮
        row += 2
        save_btn = ttk.Button(self.edit_content, text="保存修改", command=self.save_env_changes)
        save_btn.grid(row=row, column=0, columnspan=2, pady=10)
        
        # 调整画布大小
        self.edit_content.update_idletasks()
        self.edit_canvas.config(scrollregion=self.edit_canvas.bbox("all"))
    
    def get_chinese_name(self, key):
        # 为配置项提供中文名称
        chinese_names = {
            "mobileSource": "移动设备来源",
            "equipmentType": "设备类型",
            "deviceVersion": "设备版本",
            "deviceSpec": "设备规格",
            "appHeader": "应用头部",
            "appVersion": "应用版本",
            "userAgent": "用户代理",
            "Cookie": "Cookie",
            "Accept-Language": "接受语言",
            "Accept-Encoding": "接受编码",
            "Accept": "接受类型",
            "Connection": "连接状态"
        }
        return chinese_names.get(key, key)
    
    def save_env_changes(self):
        # 保存环境配置更改
        if not self.current_env_file or not self.current_env:
            messagebox.showinfo("提示", "请先选择一个环境文件")
            return
        
        # 检查是否修改了除代理外的配置
        has_non_proxy_changes = False
        
        # 处理代理配置
        proxy_type = self.input_widgets.get("proxy_type", None)
        proxy_address = self.input_widgets.get("proxy_address", None)
        if proxy_type and proxy_address:
            proxy_type_value = proxy_type.get().strip()
            proxy_address_value = proxy_address.get().strip()
            if proxy_address_value:
                full_proxy = f"{proxy_type_value}://{proxy_address_value}"
            else:
                full_proxy = ""
            
            if full_proxy != self.original_env.get("proxy", ""):
                self.current_env["proxy"] = full_proxy
        
        # 处理其他配置
        for key, widget in self.input_widgets.items():
            if key not in ["proxy_type", "proxy_address"]:
                value = widget.get().strip()
                header_key = key.split(".")[1]
                if value != str(self.original_env.get("header", {}).get(header_key, "")):
                    has_non_proxy_changes = True
                    if "header" not in self.current_env:
                        self.current_env["header"] = {}
                    self.current_env["header"][header_key] = value
        
        # 如果修改了除代理外的配置，显示风控提示
        if has_non_proxy_changes:
            if not messagebox.askyesno(
                "风控提示", 
                "修改此配置可能造成意料之外的风控，除非您已做好充足准备，请勿修改。\n\n确定要保存修改吗？"
            ):
                # 用户取消修改
                return
        
        # 保存修改
        try:
            with open(self.current_env_file, "w", encoding="utf-8") as f:
                json.dump(self.current_env, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"环境配置保存成功")
            
            # 重新加载环境信息
            self.show_env_info(None)
        except Exception as ex:
            messagebox.showerror("错误", f"保存环境配置失败: {str(ex)}")
    
    def show_context_menu(self, event):
        # 显示右键菜单
        selected_item = self.tree.identify_row(event.y)
        if selected_item:
            self.tree.selection_set(selected_item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def delete_env(self):
        # 删除选中的环境文件
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showinfo("提示", "请先选择一个环境文件")
            return
        
        file_name = self.tree.item(selected_item[0], "values")[0]
        if messagebox.askyesno("确认", f"确定要删除 {file_name} 吗？"):
            try:
                os.remove(file_name)
                messagebox.showinfo("成功", f"环境文件 {file_name} 删除成功")
                # 重新加载列表
                self.load_env_files()
                # 清空信息区
                self.info_text.config(state=tk.NORMAL)
                self.info_text.delete(1.0, tk.END)
                self.info_text.config(state=tk.DISABLED)
            except Exception as ex:
                messagebox.showerror("错误", f"删除环境文件失败: {str(ex)}")
    
    def refresh_cookie(self):
        # 刷新cookie
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showinfo("提示", "请先选择一个环境文件")
            return
        
        file_name = self.tree.item(selected_item[0], "values")[0]
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                env = json.load(f)
        except Exception as ex:
            messagebox.showerror("错误", f"读取环境文件失败: {str(ex)}")
            return
        
        try:
            # 导入必要的模块
            
            # 创建session
            session = create_session(env)
            
            # 请求www.allcpp.cn
            url1 = "https://www.allcpp.cn/"
            print(f"[调试][刷新cookie]请求URL: {url1}")
            print(f"[调试][刷新cookie]请求Headers: {dict(session.headers)}")
            print(f"[调试][刷新cookie]请求Cookies: {dict(session.cookies)}")
            response1 = session.get(url1)
            print(f"[调试][刷新cookie]响应状态码: {response1.status_code}")
            print(f"[调试][刷新cookie]响应Headers: {dict(response1.headers)}")
            
            # 请求user.allcpp.cn
            url2 = "https://user.allcpp.cn/"
            print(f"[调试][刷新cookie]请求URL: {url2}")
            print(f"[调试][刷新cookie]请求Headers: {dict(session.headers)}")
            print(f"[调试][刷新cookie]请求Cookies: {dict(session.cookies)}")
            response2 = session.get(url2)
            print(f"[调试][刷新cookie]响应状态码: {response2.status_code}")
            print(f"[调试][刷新cookie]响应Headers: {dict(response2.headers)}")
            
            # 更新cookie，处理可能的CookieConflictError
            try:
                env["cookie"] = dict(session.cookies)
            except Exception:
                # 如果出现cookie冲突，只保留最新的cookie
                cookie_dict = {}
                for cookie in session.cookies:
                    cookie_dict[cookie.name] = cookie.value
                env["cookie"] = cookie_dict
            
            # 保存cookie到环境文件
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(env, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", "cookie刷新成功")
        except Exception as ex:
            messagebox.showerror("错误", f"刷新cookie失败: {str(ex)}")
    
    def search_events(self):
        # 搜索活动
        city_code = self.city_code_var.get().strip()
        keyword = self.keyword_var.get().strip()
        
        if not city_code:
            messagebox.showinfo("提示", "请输入城市代码")
            return
        
        if not keyword:
            messagebox.showinfo("提示", "请输入关键词")
            return
        
        try:
            # 导入必要的模块
            import requests
            import utils.urls as urls
            
            # 构建URL
            url = urls.BASE_URL_WEB + urls.EVENT_LIST_URL.format(city=city_code, keyword=keyword)
            
            # 使用电脑header
            header = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # 打印请求信息
            print(f"[调试][搜索活动]请求URL: {url}")
            print(f"[调试][搜索活动]请求Headers: {header}")
            
            resp = requests.get(url, headers=header)
            
            # 打印响应信息
            print(f"[调试][搜索活动]响应状态码: {resp.status_code}")
            print(f"[调试][搜索活动]响应Headers: {dict(resp.headers)}")
            print(f"[调试][搜索活动]响应内容: {resp.text}")
            
            if resp.status_code == 200:
                # 解析响应
                data = resp.json()
                if data.get("isSuccess"):
                    events = data.get("result", {}).get("list", [])
                    
                    # 清空列表
                    for item in self.event_tree.get_children():
                        self.event_tree.delete(item)
                    
                    # 添加活动到列表
                    for event in events:
                        event_id = event.get("id")
                        name = event.get("name")
                        event_type = event.get("type")
                        city_name = event.get("cityName")
                        enter_time = event.get("enterTime")
                        
                        # 转换时间戳为可读格式
                        import datetime
                        time_str = ""
                        if enter_time:
                            try:
                                time_str = datetime.datetime.fromtimestamp(enter_time / 1000).strftime("%Y-%m-%d %H:%M")
                            except:
                                time_str = str(enter_time)
                        
                        self.event_tree.insert("", tk.END, values=(name, event_type, city_name, time_str), tags=(event_id,))
                else:
                    messagebox.showinfo("提示", "搜索失败: " + data.get("message", "未知错误"))
            else:
                messagebox.showinfo("提示", f"搜索失败: 状态码 {resp.status_code}")
        except Exception as ex:
            messagebox.showerror("错误", f"搜索失败: {str(ex)}")
    
    def show_ticket_info(self, event):
        # 显示票务信息
        selected_item = self.event_tree.selection()
        if not selected_item:
            return
        
        # 获取活动ID
        item = selected_item[0]
        event_id = self.event_tree.item(item, "tags")[0]
        
        self.get_ticket_info_by_id(event_id)
    
    def get_ticket_by_id(self):
        # 根据ID获取票信息
        event_id = self.event_id_var.get().strip()
        if not event_id:
            messagebox.showinfo("提示", "请输入活动ID")
            return
        
        self.get_ticket_info_by_id(event_id)
    
    def get_ticket_info_by_id(self, event_id):
        # 通用的获取票务信息方法
        env_file = self.env_file_var.get()
        if not env_file:
            messagebox.showinfo("提示", "请选择一个环境文件")
            return
        
        try:
            # 读取环境配置
            with open(env_file, "r", encoding="utf-8") as f:
                env = json.load(f)
            
            # 导入必要的模块
            from utils.ticket.check import get_ticket_type_list, get_purchaser_list
            
            # 创建session
            session = create_session(env)
            
            # 使用get_ticket_type_list函数获取票务信息
            ticket_data = get_ticket_type_list(session, event_id, 0.5)
            
            # 更新cookie到环境文件
            if session.cookies:
                try:
                    env["cookie"] = dict(session.cookies)
                except Exception:
                    # 如果出现cookie冲突，只保留最新的cookie
                    cookie_dict = {}
                    for cookie in session.cookies:
                        cookie_dict[cookie.name] = cookie.value
                    env["cookie"] = cookie_dict
                # 保存更新后的cookie到文件
                with open(env_file, "w", encoding="utf-8") as f:
                    json.dump(env, f, ensure_ascii=False, indent=2)
            
            # 清空票务信息（移除所有标签页）
            for tab in self.ticket_notebook.tabs():
                self.ticket_notebook.forget(tab)
            
            if ticket_data:
                # 检查返回数据结构是否符合预期
                if "result" in ticket_data and ticket_data.get("isSuccess"):
                    # 标准格式：{"isSuccess": true, "result": {"ticketTypeList": [...]}}
                    ticket_list = ticket_data.get("result", {}).get("ticketTypeList", [])
                else:
                    # 适配示例返回格式：直接包含ticketTypeList字段
                    ticket_list = ticket_data.get("ticketTypeList", [])
                
                if ticket_list:
                    # 为每个票档创建一个标签页
                    for i, ticket in enumerate(ticket_list):
                        ticket_id = ticket.get("id")
                        name = ticket.get("ticketName") or ticket.get("name")  # 适配不同字段名
                        price = ticket.get("ticketPrice") or ticket.get("price")  # 适配不同字段名
                        stock = ticket.get("remainderNum")  # 使用remainderNum字段
                        is_real_name = ticket.get("realnameAuth") or ticket.get("isRealName")  # 适配不同字段名
                        sale_start_time = ticket.get("sellStartTime")  # 使用sellStartTime字段
                        
                        # 转换时间戳为可读格式
                        import datetime
                        sale_time_str = ""
                        if sale_start_time:
                            try:
                                sale_time_str = datetime.datetime.fromtimestamp(sale_start_time / 1000).strftime("%Y-%m-%d %H:%M")
                            except:
                                sale_time_str = str(sale_start_time)
                        
                        # 创建标签页内容
                        tab_frame = ttk.Frame(self.ticket_notebook)
                        tab_text = tk.Text(tab_frame, wrap=tk.WORD, state=tk.DISABLED)
                        tab_text.pack(fill=tk.BOTH, expand=True)
                        
                        # 插入票务信息
                        tab_text.config(state=tk.NORMAL)
                        tab_text.insert(tk.END, f"活动ID: {event_id}\n\n")
                        tab_text.insert(tk.END, f"票档ID: {ticket_id}\n")
                        tab_text.insert(tk.END, f"票档名称: {name}\n")
                        tab_text.insert(tk.END, f"价格: {price/100 if price else 0}元\n")  # 适配价格单位
                        tab_text.insert(tk.END, f"余票: {stock}\n")
                        tab_text.insert(tk.END, f"是否实名: {'是' if is_real_name else '否'}\n")
                        tab_text.insert(tk.END, f"开售时间: {sale_time_str}\n")
                        
                        # 如果有票档描述，也显示出来
                        ticket_description = ticket.get("ticketDescription")
                        if ticket_description:
                            tab_text.insert(tk.END, f"票档描述: {ticket_description}\n")
                        
                        tab_text.config(state=tk.DISABLED)
                        
                        # 添加标签页
                        self.ticket_notebook.add(tab_frame, text=f"票档 {i+1}: {name}")
                else:
                    # 无票务信息时显示提示
                    tab_frame = ttk.Frame(self.ticket_notebook)
                    tab_text = tk.Text(tab_frame, wrap=tk.WORD, state=tk.DISABLED)
                    tab_text.pack(fill=tk.BOTH, expand=True)
                    tab_text.config(state=tk.NORMAL)
                    tab_text.insert(tk.END, f"活动ID: {event_id}\n\n")
                    tab_text.insert(tk.END, "暂无票务信息\n")
                    tab_text.config(state=tk.DISABLED)
                    self.ticket_notebook.add(tab_frame, text="无票档")
            else:
                # 显示具体的错误信息
                error_message = "未知错误"
                if ticket_data:
                    error_message = ticket_data.get('message', '未知错误')
                tab_frame = ttk.Frame(self.ticket_notebook)
                tab_text = tk.Text(tab_frame, wrap=tk.WORD, state=tk.DISABLED)
                tab_text.pack(fill=tk.BOTH, expand=True)
                tab_text.config(state=tk.NORMAL)
                tab_text.insert(tk.END, f"获取票务信息失败: {error_message}\n")
                tab_text.config(state=tk.DISABLED)
                self.ticket_notebook.add(tab_frame, text="错误")
        except Exception as ex:
            # 显示具体的异常信息
            messagebox.showerror("错误", f"获取票务信息失败: {str(ex)}")
    
    def login(self):
        # 登录功能
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showinfo("提示", "请先选择一个环境文件")
            return
        
        file_name = self.tree.item(selected_item[0], "values")[0]
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                env = json.load(f)
        except Exception as ex:
            messagebox.showerror("错误", f"读取环境文件失败: {str(ex)}")
            return
        
        # 创建登录对话框
        login_dialog = tk.Toplevel(self.root)
        login_dialog.title("登录")
        login_dialog.geometry("400x300")
        
        # 添加区号和手机号输入
        ttk.Label(login_dialog, text="区号:", padding=(10, 10)).grid(row=0, column=0, sticky=tk.E)
        country_var = tk.StringVar(value="86")
        ttk.Entry(login_dialog, textvariable=country_var, width=10).grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        ttk.Label(login_dialog, text="手机号:", padding=(10, 10)).grid(row=1, column=0, sticky=tk.E)
        phone_var = tk.StringVar()
        ttk.Entry(login_dialog, textvariable=phone_var, width=30).grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 登录方式选择
        login_method_var = tk.StringVar(value="sms")
        ttk.Radiobutton(login_dialog, text="验证码登录", variable=login_method_var, value="sms").grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W)
        ttk.Radiobutton(login_dialog, text="密码登录", variable=login_method_var, value="password").grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W)
        
        # 验证码/密码输入
        ttk.Label(login_dialog, text="验证码/密码:", padding=(10, 10)).grid(row=4, column=0, sticky=tk.E)
        code_var = tk.StringVar()
        code_entry = ttk.Entry(login_dialog, textvariable=code_var, width=30)
        code_entry.grid(row=4, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 获取验证码按钮
        get_code_btn = ttk.Button(login_dialog, text="获取验证码")
        get_code_btn.grid(row=5, column=1, padx=10, pady=5, sticky=tk.W)
        
        # 登录按钮
        login_btn = ttk.Button(login_dialog, text="登录")
        login_btn.grid(row=6, column=0, columnspan=2, pady=10)
        
        # 导入必要的模块
        from utils.user.check import check_if_user_exists
        from utils.user.login import get_login_code, user_login_sms
        import requests
        from utils.env2sess import env_to_request_session
        import utils.urls as urls
        
        # 检查用户存在性
        def check_user():
            country = country_var.get().strip()
            phone = phone_var.get().strip()
            if not country or not phone:
                messagebox.showinfo("提示", "请输入区号和手机号")
                return False
            
            try:
                exists = check_if_user_exists(env, country, phone)
                if not exists:
                    messagebox.showinfo("提示", "用户不存在，请先去ALLCPP注册账号再试")
                    return False
                return True
            except Exception as ex:
                messagebox.showerror("错误", f"检查用户失败: {str(ex)}")
                return False
        
        # 获取验证码
        def get_code():
            if not check_user():
                return
            
            country = country_var.get().strip()
            phone = phone_var.get().strip()
            
            try:
                success, message = get_login_code(env, country, phone, "")
                if success:
                    messagebox.showinfo("成功", message)
                else:
                    messagebox.showerror("错误", f"获取验证码失败: {message}")
            except Exception as ex:
                messagebox.showerror("错误", f"获取验证码失败: {str(ex)}")
        
        # 登录
        def do_login():
            if not check_user():
                return
            
            country = country_var.get().strip()
            phone = phone_var.get().strip()
            code = code_var.get().strip()
            
            if not code:
                messagebox.showinfo("提示", "请输入验证码")
                return
            
            try:
                # 使用create_session创建session
                session = create_session(env)
                
                # 直接使用session登录，以便获取cookie
                header = env["header"]
                url = urls.USERBASE_URL_WEB + urls.USER_SMSLOGIN_URL
                data = {"phone": phone, "country": country, "phoneCode": code}
                
                # 打印请求信息
                print(f"[调试][登录]请求URL: {url}")
                print(f"[调试][登录]请求Headers: {header}")
                print(f"[调试][登录]请求Cookies: {dict(session.cookies)}")
                print(f"[调试][登录]请求数据: {data}")
                
                resp = session.post(url, headers=header, data=data)
                
                # 打印响应信息
                print(f"[调试][登录]响应状态码: {resp.status_code}")
                print(f"[调试][登录]响应Headers: {dict(resp.headers)}")
                print(f"[调试][登录]响应内容: {resp.text}")
                
                if resp.status_code == 200:
                    # 登录成功，获取cookie，处理可能的CookieConflictError
                    try:
                        env["cookie"] = dict(session.cookies)
                    except Exception:
                        # 如果出现cookie冲突，只保留最新的cookie
                        cookie_dict = {}
                        for cookie in session.cookies:
                            cookie_dict[cookie.name] = cookie.value
                        env["cookie"] = cookie_dict
                    
                    # 保存cookie到环境文件
                    with open(file_name, "w", encoding="utf-8") as f:
                        json.dump(env, f, ensure_ascii=False, indent=2)
                    
                    messagebox.showinfo("成功", "登录成功，cookie已保存")
                    login_dialog.destroy()
                else:
                    # 登录失败，显示服务端返回信息
                    try:
                        response_text = resp.text
                    except:
                        response_text = str(resp.content)
                    messagebox.showerror("错误", f"登录失败: {response_text}")
            except Exception as ex:
                messagebox.showerror("错误", f"登录失败: {str(ex)}")
        
        # 绑定按钮事件
        get_code_btn.config(command=get_code)
        login_btn.config(command=do_login)
        
        # 聚焦输入框
        phone_entry = login_dialog.winfo_children()[3]
        phone_entry.focus_set()
        
        login_dialog.wait_window()
    
    def generate_signature_params(self, ticket_type_id: str) -> dict:
        """
        生成签名参数
        Args:
            ticket_type_id: 票档ID字符串
        Returns:
            包含nonce、timeStamp、sign的字典
        """
        # 随机字符串生成 - 只使用大写字母
        charset = "ABCDEFGHJKMNPQRSTWXYZ"
        nonce = ''.join(random.choices(charset, k=5))
        
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳
        
        # 输出sign计算过程
        print(f"[调试][签名计算]时间戳: {timestamp}")
        print(f"[调试][签名计算]随机字符串: {nonce}")
        print(f"[调试][签名计算]票档ID: {ticket_type_id}")
        
        sign = generate_signature(timestamp, nonce, ticket_type_id)
        
        print(f"[调试][签名计算]签名结果: {sign}")
        
        return {
            "nonce": nonce,
            "timeStamp": str(timestamp),
            "sign": sign
        }
    
    def get_random_delay(self, base_delay: float) -> float:
        """
        根据基准延迟生成随机延迟（±0.2秒），确保不小于0.1秒
        Args:
            base_delay: 基准延迟
        Returns:
            随机调整后的延迟值
        """
        # 生成-0.2到+0.2之间的随机数
        random_offset = random.uniform(-0.2, 0.2)
        actual_delay = base_delay + random_offset
        # 确保延迟不小于0.1秒
        actual_delay = max(0.1, actual_delay)
        return round(actual_delay, 3)
    
    def get_purchaser_list(self):
        """
        获取购买人列表
        """
        env_file = self.purchaser_env_var.get()
        if not env_file:
            messagebox.showinfo("提示", "请选择一个环境文件")
            return
        
        try:
            # 读取环境配置
            with open(env_file, "r", encoding="utf-8") as f:
                env = json.load(f)
            
            # 创建session
            session = create_session(env)
            
            # 导入get_purchaser_list函数
            from utils.ticket.check import get_purchaser_list
            
            # 获取购买人列表
            purchasers = get_purchaser_list(session, 0.5)
            
            # 更新cookie到环境文件
            if session.cookies:
                try:
                    env["cookie"] = dict(session.cookies)
                except Exception:
                    # 如果出现cookie冲突，只保留最新的cookie
                    cookie_dict = {}
                    for cookie in session.cookies:
                        cookie_dict[cookie.name] = cookie.value
                    env["cookie"] = cookie_dict
                # 保存更新后的cookie到文件
                with open(env_file, "w", encoding="utf-8") as f:
                    json.dump(env, f, ensure_ascii=False, indent=2)
            
            # 清空购买人列表
            for item in self.purchaser_tree.get_children():
                self.purchaser_tree.delete(item)
            
            # 添加购买人到列表
            if purchasers:
                for purchaser in purchasers:
                    purchaser_id = purchaser.get("id")
                    name = purchaser.get("realname")  # 使用realname字段
                    id_card = purchaser.get("idcard")  # 使用idcard字段
                    mobile = purchaser.get("mobile")  # 添加手机号
                    self.purchaser_tree.insert("", tk.END, values=(purchaser_id, name, id_card, mobile))
            else:
                messagebox.showinfo("提示", "未获取到购买人信息")
            
        except Exception as ex:
            messagebox.showerror("错误", f"获取购买人列表失败: {str(ex)}")
    
    def get_ticket_list(self):
        """
        获取票档列表
        """
        env_file = self.purchase_env_var.get()
        if not env_file:
            messagebox.showinfo("提示", "请选择一个环境文件")
            return
        
        event_id = self.event_id_var.get().strip()
        if not event_id:
            messagebox.showinfo("提示", "请输入活动ID")
            return
        
        try:
            # 读取环境配置
            with open(env_file, "r", encoding="utf-8") as f:
                env = json.load(f)
            
            # 创建session
            session = create_session(env)
            
            # 导入必要的模块
            import utils.urls as urls
            
            # 构建URL和参数 - 使用eventMainId参数
            url = urls.BASE_URL_WEB + urls.GET_TICKET_TYPE_URL
            params = {"eventMainId": event_id}
            
            # 打印调试信息
            print(f"[调试][获取票档列表]请求URL: {url}")
            print(f"[调试][获取票档列表]请求参数: {params}")
            print(f"[调试][获取票档列表]请求Headers: {dict(session.headers)}")
            try:
                print(f"[调试][获取票档列表]请求Cookies: {dict(session.cookies)}")
            except Exception:
                # 处理可能的CookieConflictError
                cookie_dict = {}
                for cookie in session.cookies:
                    cookie_dict[cookie.name] = cookie.value
                print(f"[调试][获取票档列表]请求Cookies: {cookie_dict}")
            
            # 发送请求
            response = session.get(url, params=params, timeout=10)
            
            # 打印响应调试信息
            print(f"[调试][获取票档列表]响应状态码: {response.status_code}")
            print(f"[调试][获取票档列表]响应Headers: {dict(response.headers)}")
            print(f"[调试][获取票档列表]响应内容: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            print(f"[调试][获取票档列表]响应JSON: {result}")
            
            # 更新cookie到环境文件
            if session.cookies:
                try:
                    env["cookie"] = dict(session.cookies)
                except Exception:
                    # 如果出现cookie冲突，只保留最新的cookie
                    cookie_dict = {}
                    for cookie in session.cookies:
                        cookie_dict[cookie.name] = cookie.value
                    env["cookie"] = cookie_dict
                # 保存更新后的cookie到文件
                with open(env_file, "w", encoding="utf-8") as f:
                    json.dump(env, f, ensure_ascii=False, indent=2)
            
            # 处理响应
            # 检查响应是否包含ticketTypeList字段
            if "ticketTypeList" in result:
                self.ticket_list = result.get("ticketTypeList", [])
                
                # 清空票档列表
                for item in self.ticket_tree.get_children():
                    self.ticket_tree.delete(item)
                
                # 添加票档到列表
                if self.ticket_list:
                    for ticket in self.ticket_list:
                        ticket_id = ticket.get("id")
                        name = ticket.get("ticketName") or ticket.get("name")
                        price = ticket.get("ticketPrice") or ticket.get("price")
                        stock = ticket.get("remainderNum")
                        is_real_name = ticket.get("realnameAuth") or ticket.get("isRealName")
                        realname_text = "是" if is_real_name else "否"
                        self.ticket_tree.insert("", tk.END, values=(ticket_id, name, f"{price/100 if price else 0}元", stock, realname_text), tags=(ticket_id,))
                else:
                    messagebox.showinfo("提示", "未获取到票档信息")
            else:
                messagebox.showinfo("提示", f"获取票档列表失败: {result.get('message', '未知错误')}")
            
        except Exception as ex:
            messagebox.showerror("错误", f"获取票档列表失败: {str(ex)}")
    
    def on_ticket_select(self, event):
        """
        票档选择事件处理
        """
        selected_item = self.ticket_tree.selection()
        if not selected_item:
            return
        
        # 获取选中的票档ID
        item = selected_item[0]
        ticket_id = self.ticket_tree.item(item, "tags")[0]
        
        # 找到对应的票档信息
        for ticket in self.ticket_list:
            if str(ticket.get("id")) == ticket_id:
                self.current_ticket_info = ticket
                
                # 根据是否实名决定是否启用购买人ID输入
                is_real_name = ticket.get("realnameAuth") or ticket.get("isRealName")
                if is_real_name:
                    self.purchaser_id_entry.config(state=tk.NORMAL)
                else:
                    self.purchaser_id_entry.config(state=tk.DISABLED)
                    self.purchaser_id_var.set("")
                break
    
    def test_purchase(self):
        """
        测试下单功能
        """
        env_file = self.purchase_env_var.get()
        if not env_file:
            messagebox.showinfo("提示", "请选择一个环境文件")
            return
        
        # 检查是否已选择票档
        if not self.current_ticket_info:
            messagebox.showinfo("提示", "请先选择一个票档")
            return
        
        # 获取票档ID
        ticket_id = str(self.current_ticket_info.get("id"))
        
        # 获取票张数
        try:
            count = int(self.ticket_count_var.get().strip())
            if count <= 0:
                messagebox.showinfo("提示", "票张数必须大于0")
                return
        except ValueError:
            messagebox.showinfo("提示", "请输入有效的票张数")
            return
        
        # 根据是否实名决定是否需要购买人ID
        is_real_name = self.current_ticket_info.get('realnameAuth') or self.current_ticket_info.get('isRealName')
        purchaser_id = self.purchaser_id_var.get().strip()
        
        # 检查购买人ID数量是否与票张数一致
        if is_real_name:
            if not purchaser_id:
                messagebox.showinfo("提示", "请输入购买人ID")
                return
            purchaser_ids = [id.strip() for id in purchaser_id.split(",") if id.strip()]
            if len(purchaser_ids) != count:
                messagebox.showinfo("提示", f"购买人ID数量必须与票张数一致（需要{count}个购买人ID）")
                return
            # 重新组合购买人ID字符串
            purchaser_id = ",".join(purchaser_ids)
        
        try:
            base_delay = float(self.delay_var.get().strip())
        except ValueError:
            messagebox.showinfo("提示", "请输入有效的基准延迟")
            return
        
        try:
            # 读取环境配置
            with open(env_file, "r", encoding="utf-8") as f:
                env = json.load(f)
            
            # 创建session
            session = create_session(env)
            
            # 生成签名参数（发送请求前生成，避免时间戳过期）
            sign_params = self.generate_signature_params(ticket_id)
            # 输出sign计算过程
            print(f"[调试][下单]签名参数: {sign_params}")
            
            result_text = ""
            
            # 构造请求数据
            request_data = {
                "timeStamp": sign_params["timeStamp"],
                "nonce": sign_params["nonce"],
                "sign": sign_params["sign"],
                "ticketTypeId": ticket_id,
                "count": count
            }
            
            # 如果需要购买人ID，添加到请求数据
            if is_real_name and purchaser_id:
                request_data["purchaserIds"] = purchaser_id
            
            # 构造与用户提供格式一致的请求体
            # 使用普通的JSON对象格式
            payload = request_data
            
            # 输出请求数据和请求体
            print(f"[调试][下单]请求数据: {request_data}")
            print(f"[调试][下单]请求体: {payload}")
            result_text += f"[调试][下单]请求数据: {json.dumps(request_data, ensure_ascii=False)}\n"
            result_text += f"[调试][下单]请求体: {json.dumps(payload, ensure_ascii=False)}\n"
            
            # 发送请求
            PAY_TICKET_URL = "https://www.allcpp.cn/api/ticket/pay/ali.do"
            response = session.post(PAY_TICKET_URL, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            # 处理响应
            message = result.get("message", "") if isinstance(result, dict) else str(result)
            result_text += f"[调试][下单]响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}\n"
            
            if "拥挤" in message:
                result_text += "[调试][服务器卡顿]请求阻塞，需要重试\n"
            elif "超时" in message:
                result_text += "[调试][下单报错]请求超时，可能是网络不好，协议异常或者本地时间偏差\n"
            elif "余票" in message:
                result_text += "[调试][下单报错]可用库存不足\n"
            elif result.get("isSuccess") == True:
                result_text += "[调试][下单成功]抢票成功！\n"
            else:
                result_text += "[调试][下单失败]抢票失败！\n"
            
            # 更新cookie到环境文件
            if session.cookies:
                try:
                    env["cookie"] = dict(session.cookies)
                except Exception:
                    # 如果出现cookie冲突，只保留最新的cookie
                    cookie_dict = {}
                    for cookie in session.cookies:
                        cookie_dict[cookie.name] = cookie.value
                    env["cookie"] = cookie_dict
                # 保存更新后的cookie到文件
                with open(env_file, "w", encoding="utf-8") as f:
                    json.dump(env, f, ensure_ascii=False, indent=2)
                result_text += "[调试][下单]cookie已更新并保存\n"
            
            # 显示结果
            self.purchase_result_text.config(state=tk.NORMAL)
            self.purchase_result_text.delete(1.0, tk.END)
            self.purchase_result_text.insert(tk.END, result_text)
            self.purchase_result_text.config(state=tk.DISABLED)
            
        except Exception as ex:
            error_text = f"[调试][下单失败]提交订单失败: {str(ex)}\n"
            self.purchase_result_text.config(state=tk.NORMAL)
            self.purchase_result_text.delete(1.0, tk.END)
            self.purchase_result_text.insert(tk.END, error_text)
            self.purchase_result_text.config(state=tk.DISABLED)
            messagebox.showerror("错误", f"测试下单失败: {str(ex)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
