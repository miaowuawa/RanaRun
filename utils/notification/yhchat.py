"""
云湖消息通知模块
用于发送抢票状态通知到云湖APP
"""
import requests
import json
from typing import Optional
from urllib.parse import urljoin


class YHChatNotifier:
    """云湖消息通知器"""
    
    BASE_URL = "https://chat-go.jwzhd.com/open-apis/v1/bot/send"
    
    def __init__(self, token: str, recv_id: str, recv_type: str = "user"):
        """
        初始化通知器
        :param token: 云湖机器人Token
        :param recv_id: 接收者ID (用户ID或群ID)
        :param recv_type: 接收类型 (user/group)
        """
        self.token = token
        self.recv_id = recv_id
        self.recv_type = recv_type
        self.enabled = bool(token and recv_id)
    
    def _send_message(self, content_type: str, content: dict) -> bool:
        """
        发送消息
        :param content_type: 消息类型 (text/markdown/html)
        :param content: 消息内容对象
        :return: 是否发送成功
        """
        if not self.enabled:
            return False
        
        try:
            url = f"{self.BASE_URL}?token={self.token}"
            payload = {
                "recvId": self.recv_id,
                "recvType": self.recv_type,
                "contentType": content_type,
                "content": content
            }
            
            response = requests.post(
                url,
                headers={"Content-Type": "application/json; charset=utf-8"},
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                # 云湖API成功时code为1
                return result.get("code") == 1
            return False
        except Exception:
            # 通知失败不影响主流程
            return False
    
    def send_text(self, text: str, buttons: Optional[list] = None) -> bool:
        """
        发送文本消息
        :param text: 消息文本
        :param buttons: 可选的按钮列表
        :return: 是否发送成功
        """
        content = {"text": text}
        if buttons:
            content["buttons"] = buttons
        return self._send_message("text", content)
    
    def send_markdown(self, text: str, buttons: Optional[list] = None) -> bool:
        """
        发送Markdown消息
        :param text: Markdown文本
        :param buttons: 可选的按钮列表
        :return: 是否发送成功
        """
        content = {"text": text}
        if buttons:
            content["buttons"] = buttons
        return self._send_message("markdown", content)
    
    def notify_resale_hit(self, event_name: str, ticket_name: str, 
                          event_id: str, ticket_id: str) -> bool:
        """
        通知：回流票命中
        """
        text = f"🎯 **回流票命中提醒**\n\n" \
               f"活动：{event_name}\n" \
               f"票种：{ticket_name}\n" \
               f"时间：{self._get_current_time()}\n\n" \
               f"正在尝试下单..."
        
        buttons = [[{
            "text": "查看活动",
            "actionType": 1,
            "url": f"https://www.allcpp.cn/event/{event_id}"
        }]]
        
        return self.send_markdown(text, buttons)
    
    def notify_purchase_success(self, event_name: str, ticket_name: str,
                                pay_url: Optional[str] = None, 
                                order_info: Optional[str] = None) -> bool:
        """
        通知：抢票成功
        """
        text = f"🎉 **抢票成功！**\n\n" \
               f"活动：{event_name}\n" \
               f"票种：{ticket_name}\n" \
               f"时间：{self._get_current_time()}"
        
        if order_info:
            text += f"\n订单：{order_info[:50]}..."
        
        buttons = []
        if pay_url:
            buttons.append([{
                "text": "立即支付",
                "actionType": 1,
                "url": pay_url
            }])
        
        return self.send_markdown(text, buttons if buttons else None)
    
    def notify_acl_blocked(self, ip: Optional[str] = None, 
                          wait_minutes: int = 10) -> bool:
        """
        通知：IP被ACL风控
        """
        text = f"⚠️ **IP被风控提醒**\n\n" \
               f"您的IP已被ACL风控\n"
        
        if ip:
            text += f"IP地址：{ip}\n"
        
        text += f"等待时间：{wait_minutes}分钟\n" \
                f"开始时间：{self._get_current_time()}\n\n" \
                f"系统将在{wait_minutes}分钟后自动恢复抢票"
        
        return self.send_markdown(text)
    
    def notify_error(self, error_msg: str) -> bool:
        """
        通知：错误信息
        """
        text = f"❌ **抢票异常**\n\n" \
               f"时间：{self._get_current_time()}\n" \
               f"错误：{error_msg}"
        
        return self.send_markdown(text)
    
    @staticmethod
    def _get_current_time() -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_notifier_from_config(config: dict) -> YHChatNotifier:
    """
    从配置创建通知器
    :param config: 配置字典，包含 yhchat_token, yhchat_user_id 等
    :return: 通知器实例
    """
    token = config.get("yhchat_token", "")
    recv_id = config.get("yhchat_user_id", "")
    recv_type = config.get("yhchat_recv_type", "user")
    
    return YHChatNotifier(token, recv_id, recv_type)
