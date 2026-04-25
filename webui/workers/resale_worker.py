"""
回流模式抢票工作进程
"""
import json
import time
import random
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.env2sess import env_to_request_session
from utils.ticket.purchase import submit_ticket_order_with_details
from utils.ticket.check import get_ticket_type_list
from utils.notification.yhchat import create_notifier_from_config


def resale_worker(config: dict, process_id: str):
    """
    回流模式抢票工作进程
    """
    # 日志文件路径 - 使用绝对路径
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(script_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"resale_{process_id}.log")

    def log(message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")

    # 初始化云湖通知器
    notifier = create_notifier_from_config(config)
    if notifier.enabled:
        log("云湖通知已启用")

    try:
        log(f"回流模式进程 {process_id} 启动")
        log(f"配置: {json.dumps(config, ensure_ascii=False)}")

        # 加载环境
        env_file = config.get("env_file")
        if not env_file or not os.path.exists(env_file):
            log(f"错误: 环境文件不存在 {env_file}")
            return

        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)

        # 创建会话
        session = env_to_request_session(env)
        log("会话创建成功")

        # 获取配置
        event_id = config.get("event_id")
        ticket_id = config.get("ticket_id")
        purchaser_ids = config.get("purchaser_ids", "")
        ticket_count = config.get("ticket_count", 1)
        refresh_delay = config.get("refresh_delay", 1.0)
        stop_on_success = config.get("stop_on_success", True)
        debug_mode = config.get("debug_mode", False)

        if not event_id or not ticket_id:
            log("错误: 未设置活动ID或票种ID")
            return

        log(f"活动ID: {event_id}")
        log(f"票种ID: {ticket_id}")
        log(f"刷新延迟: {refresh_delay}秒")

        # 解析购买者ID
        purchaser_id_list = [pid.strip() for pid in purchaser_ids.split(",") if pid.strip()]

        # 检测循环
        check_count = 0
        success = False
        current_stock = 0

        log("开始检测余票...")

        while not success:
            try:
                check_count += 1

                # 获取票种信息
                ticket_data = get_ticket_type_list(session, event_id, refresh_delay)

                if ticket_data and "ticketTypeList" in ticket_data:
                    ticket_list = ticket_data.get("ticketTypeList", [])

                    # 查找目标票种
                    target_ticket = None
                    for ticket in ticket_list:
                        if str(ticket.get("id")) == str(ticket_id):
                            target_ticket = ticket
                            break

                    if target_ticket:
                        remainder = target_ticket.get("remainderNum", 0)
                        current_stock = remainder

                        if remainder > 0:
                            log(f"发现余票: {remainder} 张！")

                            # 发送回流票命中通知
                            try:
                                if notifier.enabled:
                                    event_name = target_ticket.get("eventName", "未知活动")
                                    ticket_name = target_ticket.get("ticketName", "未知票种")
                                    notifier.notify_resale_hit(event_name, ticket_name, event_id, ticket_id)
                            except Exception:
                                pass  # 通知失败不影响抢票

                            # 尝试下单
                            if purchaser_id_list:
                                purchaser_id = purchaser_id_list[0]
                            else:
                                purchaser_id = purchaser_ids

                            result, retry, should_stop, details = submit_ticket_order_with_details(
                                session, ticket_id, purchaser_id, debug_mode, ticket_count, notifier
                            )

                            if result:
                                success = True
                                pay_url = details.get("pay_url") if details else None
                                order_info = details.get("order_info") if details else None
                                log(f"抢票成功！共检测 {check_count} 次")
                                if order_info:
                                    log(f"订单信息: {order_info}")
                                if pay_url:
                                    log(f"支付链接: {pay_url}")
                                else:
                                    # 如果没有支付链接，尝试生成
                                    try:
                                        from utils.payment.alipay_convert import AiliPay
                                        alipay = AiliPay()
                                        pay_url = alipay.convert_alipay_to_h5(order_info)
                                        if pay_url:
                                            log(f"支付链接: {pay_url}")
                                    except Exception as e:
                                        log(f"支付链接生成失败: {e}")

                                # 发送抢票成功通知
                                try:
                                    if notifier.enabled:
                                        event_name = target_ticket.get("eventName", "未知活动")
                                        ticket_name = target_ticket.get("ticketName", "未知票种")
                                        notifier.notify_purchase_success(event_name, ticket_name, pay_url, order_info)
                                except Exception:
                                    pass  # 通知失败不影响抢票

                                if stop_on_success:
                                    break
                            else:
                                log("下单失败，继续检测...")
                        else:
                            if check_count % 10 == 0:
                                log(f"第 {check_count} 次检测，暂无余票")
                    else:
                        log("未找到目标票种")

                # 随机延迟
                actual_delay = refresh_delay + random.uniform(-0.1, 0.1)
                actual_delay = max(0.1, actual_delay)
                time.sleep(actual_delay)

            except Exception as e:
                log(f"检测异常: {e}")
                time.sleep(refresh_delay)

        if not success:
            log(f"抢票结束，未成功。共检测 {check_count} 次")

    except Exception as e:
        log(f"进程异常: {e}")
        import traceback
        log(traceback.format_exc())


if __name__ == "__main__":
    # 测试
    test_config = {
        "env_file": "environment_test.json",
        "event_id": "1234",
        "ticket_id": "5678",
        "purchaser_ids": "123,456",
        "ticket_count": 1,
        "refresh_delay": 1.0,
        "debug_mode": True
    }
    resale_worker(test_config, "test")
