#!/usr/bin/env python3
"""
云湖机器人票务监控脚本
监控活动票种变更，通过云湖机器人发送通知
"""

import json
import time
import sys
import os
import requests
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

from utils.env2sess import env_to_request_session
from utils.ticket.check import get_ticket_type_list

console = Console()

# 云湖API配置
YHCHAT_API_URL = "https://chat-go.jwzhd.com/open-apis/v1/bot/send"
MIN_SEND_INTERVAL = 5  # 最小发送间隔5秒


@dataclass
class TicketStatus:
    """票种状态"""
    ticket_id: str
    name: str
    remainder_num: int
    status: str  # 有票/缺票/停售
    price: float
    is_real_name: bool
    
    def to_dict(self):
        return asdict(self)


class YHChatBot:
    """云湖机器人客户端"""
    
    def __init__(self, token: str, group_id: str):
        self.token = token
        self.group_id = group_id
        self.last_send_time = 0
    
    def _check_rate_limit(self) -> float:
        """检查速率限制，返回需要等待的时间"""
        elapsed = time.time() - self.last_send_time
        if elapsed < MIN_SEND_INTERVAL:
            return MIN_SEND_INTERVAL - elapsed
        return 0
    
    def send_message(self, content: str, content_type: str = "text") -> bool:
        """
        发送消息到云湖群
        
        Args:
            content: 消息内容
            content_type: 消息类型 (text/markdown/html)
        
        Returns:
            是否发送成功
        """
        # 速率限制检查
        wait_time = self._check_rate_limit()
        if wait_time > 0:
            console.print(f"[yellow]速率限制: 等待 {wait_time:.1f} 秒...[/yellow]")
            time.sleep(wait_time)
        
        url = f"{YHCHAT_API_URL}?token={self.token}"
        
        payload = {
            "recvId": self.group_id,
            "recvType": "group",
            "contentType": content_type,
            "content": {
                "text": content
            }
        }
        
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()

            # 云湖API返回code为1表示成功（根据实际API文档）
            is_success = (
                response.status_code == 200 and
                (result.get("code") == 1 or result.get("success") == True)
            )

            if is_success:
                self.last_send_time = time.time()
                return True
            else:
                console.print(f"[red]发送消息失败: {result.get('msg', result.get('message', '未知错误'))}[/red]")
                console.print(f"[dim]响应: {result}[/dim]")
                return False
        except Exception as e:
            console.print(f"[red]发送消息异常: {e}[/red]")
            return False
    
    def send_markdown(self, title: str, content: str) -> bool:
        """发送Markdown格式消息"""
        markdown_text = f"**{title}**\n\n{content}"
        return self.send_message(markdown_text, "markdown")


class TicketMonitor:
    """票务监控器"""
    
    def __init__(self, env_file: str, event_id: str, bot: YHChatBot, check_interval: int = 30):
        self.env_file = env_file
        self.event_id = event_id
        self.bot = bot
        self.check_interval = check_interval
        self.previous_status: Dict[str, TicketStatus] = {}
        self.running = False
        self.check_count = 0
        self.notification_count = 0
        
        # 加载环境
        with open(env_file, "r", encoding="utf-8") as f:
            self.env = json.load(f)
    
    def _get_ticket_status(self, ticket: dict) -> TicketStatus:
        """从票种数据提取状态"""
        remainder = ticket.get("remainderNum", 0)
        
        # 通过时间戳判断是否在销售时间内
        sell_start_time = ticket.get("sellStartTime", 0)  # 毫秒时间戳
        sell_end_time = ticket.get("sellEndTime", 0)  # 毫秒时间戳
        current_time_ms = int(time.time() * 1000)
        
        # 判断是否在销售时间内
        is_on_sale = True
        if sell_start_time > 0 and current_time_ms < sell_start_time:
            is_on_sale = False  # 未开售
        if sell_end_time > 0 and current_time_ms > sell_end_time:
            is_on_sale = False  # 已停售
        
        if not is_on_sale:
            status = "停售"
        elif remainder > 0:
            status = "有票"
        else:
            status = "缺票"
        
        return TicketStatus(
            ticket_id=str(ticket.get("id", "")),
            name=ticket.get("ticketName") or ticket.get("name", "未知"),
            remainder_num=remainder,
            status=status,
            price=ticket.get("price", 0.0),
            is_real_name=ticket.get("realnameAuth") or ticket.get("isRealName", False)
        )
    
    def _format_notification(self, changes: List[dict]) -> str:
        """格式化变更通知"""
        lines = []
        lines.append(f"📅 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"🎫 活动ID: {self.event_id}")
        lines.append(f"🔍 检测次数: {self.check_count}")
        lines.append("")
        
        for change in changes:
            ticket = change["ticket"]
            old_status = change["old_status"]
            new_status = change["new_status"]
            
            lines.append(f"---")
            lines.append(f"📌 票种: {ticket.name}")
            lines.append(f"💰 价格: ¥{ticket.price}")
            lines.append(f"📝 实名: {'是' if ticket.is_real_name else '否'}")
            lines.append(f"⏮️ 变更前: {old_status.status} (余票: {old_status.remainder_num})")
            lines.append(f"⏭️ 变更后: {new_status.status} (余票: {ticket.remainder_num})")
            
            # 高亮重要变更
            if old_status.status == "缺票" and new_status.status == "有票":
                lines.append(f"🎉 **有票了！快快快抢！**")
            elif old_status.status == "有票" and new_status.status == "缺票":
                lines.append(f"😔 **票被抢光啦！呜呜呜～**")
            elif new_status.status == "停售":
                lines.append(f"🚫 **卖票时间结束啦！**")
        
        return "\n".join(lines)
    
    def _check_changes(self, current_tickets: List[TicketStatus]) -> List[dict]:
        """检查票种变更"""
        changes = []
        current_dict = {t.ticket_id: t for t in current_tickets}
        
        # 检查现有票种变更
        for ticket in current_tickets:
            ticket_id = ticket.ticket_id
            
            if ticket_id in self.previous_status:
                prev = self.previous_status[ticket_id]
                
                # 状态变更
                if prev.status != ticket.status:
                    changes.append({
                        "ticket": ticket,
                        "old_status": prev,
                        "new_status": ticket
                    })
                # 库存显著变化（增加或减少超过5张）
                elif abs(prev.remainder_num - ticket.remainder_num) >= 5:
                    changes.append({
                        "ticket": ticket,
                        "old_status": prev,
                        "new_status": ticket
                    })
            else:
                # 新增票种
                changes.append({
                    "ticket": ticket,
                    "old_status": TicketStatus(ticket_id, ticket.name, 0, "未上架", ticket.price, ticket.is_real_name),
                    "new_status": ticket
                })
        
        # 检查下架的票种
        for ticket_id, prev in self.previous_status.items():
            if ticket_id not in current_dict:
                changes.append({
                    "ticket": prev,
                    "old_status": prev,
                    "new_status": TicketStatus(ticket_id, prev.name, 0, "已下架", prev.price, prev.is_real_name)
                })
        
        return changes
    
    def _fetch_tickets(self) -> Optional[List[TicketStatus]]:
        """获取当前票种列表"""
        try:
            session = env_to_request_session(self.env)
            ticket_data = get_ticket_type_list(session, self.event_id, 0.5)
            
            if not ticket_data or "ticketTypeList" not in ticket_data:
                return None
            
            ticket_list = ticket_data.get("ticketTypeList", [])
            return [self._get_ticket_status(t) for t in ticket_list]
        except Exception as e:
            console.print(f"[red]获取票种信息失败: {e}[/red]")
            return None
    
    def _create_status_layout(self, tickets: List[TicketStatus], changes: List[dict]) -> Layout:
        """创建状态显示布局"""
        layout = Layout()
        
        # 状态信息
        status_text = Text()
        status_text.append(f"活动ID: {self.event_id}\n", style="bold cyan")
        status_text.append(f"检测次数: {self.check_count}\n", style="green")
        status_text.append(f"通知次数: {self.notification_count}\n", style="yellow")
        status_text.append(f"监控票种: {len(tickets)}个\n", style="cyan")
        status_text.append(f"上次检测: {datetime.now().strftime('%H:%M:%S')}", style="dim")
        
        # 票种列表
        ticket_table = Table(box=box.SIMPLE, show_header=True)
        ticket_table.add_column("票种", style="cyan", max_width=30)
        ticket_table.add_column("状态", style="green", width=8)
        ticket_table.add_column("余票", style="yellow", width=6)
        ticket_table.add_column("价格", style="green", width=8)
        
        for t in tickets[:10]:  # 只显示前10个
            status_color = "green" if t.status == "有票" else ("red" if t.status == "停售" else "yellow")
            ticket_table.add_row(
                t.name[:28],
                f"[{status_color}]{t.status}[/{status_color}]",
                str(t.remainder_num),
                f"¥{t.price}"
            )
        
        if len(tickets) > 10:
            ticket_table.add_row("...", "", "", f"还有 {len(tickets)-10} 个票种")
        
        # 最近变更
        change_text = Text()
        if changes:
            change_text.append("最近变更:\n", style="bold yellow")
            for c in changes[-5:]:
                t = c["ticket"]
                old = c["old_status"]
                new = c["new_status"]
                change_text.append(f"  {t.name}: {old.status} -> {new.status}\n", style="dim")
        else:
            change_text.append("暂无变更", style="dim")
        
        layout.split_column(
            Layout(Panel(status_text, title="监控状态", border_style="cyan"), size=6),
            Layout(Panel(ticket_table, title="票种列表", border_style="green")),
            Layout(Panel(change_text, title="最近变更", border_style="yellow"), size=8)
        )
        
        return layout
    
    def start(self):
        """启动监控"""
        self.running = True
        
        # 发送启动通知
        start_msg = f"🚀 **监控开始**\n\n📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🎫 活动ID: {self.event_id}\n⏱️ 检测间隔: {self.check_interval}秒"
        if self.bot.send_markdown("票务监控启动", start_msg):
            console.print("[green]启动通知已发送[/green]")
        
        console.print(Panel(
            f"[bold green]监控已启动[/bold green]\n"
            f"活动ID: {self.event_id}\n"
            f"检测间隔: {self.check_interval}秒\n"
            f"按 Ctrl+C 停止监控",
            border_style="green"
        ))
        
        try:
            with Live(console=console, refresh_per_second=1, screen=False) as live:
                while self.running:
                    self.check_count += 1
                    
                    # 获取当前票种状态
                    current_tickets = self._fetch_tickets()
                    
                    if current_tickets is None:
                        console.print(f"[red]第 {self.check_count} 次检测失败，将在下次重试[/red]")
                        time.sleep(self.check_interval)
                        continue
                    
                    # 首次检测，只记录状态
                    if not self.previous_status:
                        self.previous_status = {t.ticket_id: t for t in current_tickets}
                        console.print(f"[cyan]第 {self.check_count} 次检测: 已记录 {len(current_tickets)} 个票种初始状态[/cyan]")
                    else:
                        # 检查变更
                        changes = self._check_changes(current_tickets)
                        
                        if changes:
                            self.notification_count += 1
                            console.print(f"[yellow]检测到 {len(changes)} 个变更，发送通知...[/yellow]")
                            
                            # 发送通知
                            notification = self._format_notification(changes)
                            if self.bot.send_markdown("🎫 票务变更通知", notification):
                                console.print(f"[green]通知已发送 ({self.notification_count})[/green]")
                        else:
                            console.print(f"[dim]第 {self.check_count} 次检测: 无变更[/dim]")
                        
                        # 更新状态
                        self.previous_status = {t.ticket_id: t for t in current_tickets}
                    
                    # 更新显示
                    changes = []  # 清空用于显示的变更
                    layout = self._create_status_layout(current_tickets, [])
                    live.update(layout)
                    
                    # 等待下次检测
                    time.sleep(self.check_interval)
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]监控已停止[/yellow]")
            
            # 发送停止通知
            stop_msg = f"🛑 **监控停止**\n\n📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🔍 总检测次数: {self.check_count}\n📢 总通知次数: {self.notification_count}"
            self.bot.send_markdown("票务监控停止", stop_msg)


def main():
    """主函数"""
    console.print(Panel(
        "[bold cyan]云湖机器人票务监控[/bold cyan]\n"
        "监控活动票种变更，自动发送通知到云湖群",
        box.DOUBLE,
        padding=(1, 2)
    ))
    
    # 输入配置
    console.print("\n[bold]步骤1: 云湖机器人配置[/bold]")
    bot_token = Prompt.ask("机器人Token", password=True)
    if not bot_token:
        console.print("[red]Token不能为空[/red]")
        return
    
    group_id = Prompt.ask("群ID")
    if not group_id:
        console.print("[red]群ID不能为空[/red]")
        return
    
    console.print("\n[bold]步骤2: 选择环境文件[/bold]")
    env_files = []
    try:
        for file in os.listdir("."):
            if file.startswith("environment_") and file.endswith(".json"):
                env_files.append(file)
    except Exception as e:
        console.print(f"[red]读取环境文件失败: {e}[/red]")
        return
    
    if not env_files:
        console.print("[red]没有找到环境文件[/red]")
        return
    
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("序号", style="cyan", width=5)
    table.add_column("文件名", style="green")
    for idx, file in enumerate(env_files, 1):
        table.add_row(str(idx), file)
    console.print(table)
    
    choice = Prompt.ask("请选择环境文件", choices=[str(i) for i in range(1, len(env_files) + 1)])
    env_file = env_files[int(choice) - 1]
    
    console.print("\n[bold]步骤3: 监控配置[/bold]")
    event_id = Prompt.ask("活动ID")
    if not event_id:
        console.print("[red]活动ID不能为空[/red]")
        return
    
    check_interval = IntPrompt.ask("检测间隔(秒)", default=30)
    if check_interval < 10:
        console.print("[yellow]警告: 检测间隔过短可能触发风控[/yellow]")
    
    # 确认配置
    console.print("\n[bold yellow]配置确认:[/bold yellow]")
    console.print(f"  群ID: {group_id}")
    console.print(f"  环境文件: {env_file}")
    console.print(f"  活动ID: {event_id}")
    console.print(f"  检测间隔: {check_interval}秒")
    
    if not Prompt.ask("\n开始监控?", choices=["y", "n"], default="y") == "y":
        console.print("[yellow]已取消[/yellow]")
        return
    
    # 创建机器人和监控器
    bot = YHChatBot(bot_token, group_id)
    monitor = TicketMonitor(env_file, event_id, bot, check_interval)
    
    # 启动监控
    monitor.start()


if __name__ == "__main__":
    main()
