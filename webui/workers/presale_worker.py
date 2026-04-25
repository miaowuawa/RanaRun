"""
预售模式抢票工作进程
"""
import json
import time
import random
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.env2sess import env_to_request_session
from utils.ticket.purchase import submit_ticket_order_with_details
from utils.notification.yhchat import create_notifier_from_config


def get_random_delay_ms(base_delay_ms: int) -> float:
    """
    生成随机延迟（基准延迟 ± 10-50ms）
    Args:
        base_delay_ms: 基准延迟（毫秒）
    Returns:
        随机延迟（秒）
    """
    random_offset = random.uniform(-0.05, 0.05)
    ms_delay = random.uniform(0.01, 0.05)
    actual_delay = (base_delay_ms / 1000) + random_offset + ms_delay
    return max(0.01, actual_delay)


def get_ticket_info(session, ticket_id, log_func):
    """
    获取票种详细信息，包括开售时间
    """
    try:
        from utils.ticket.check import get_ticket_info as _get_ticket_info
        ticket_data = _get_ticket_info(session, ticket_id, 0.5)
        if ticket_data and isinstance(ticket_data, dict):
            # 尝试从result中获取
            if ticket_data.get("isSuccess") and "result" in ticket_data:
                return ticket_data["result"]
            # 或者直接返回
            return ticket_data
        return None
    except Exception as e:
        log_func(f"获取票种信息失败: {e}")
        return None


def wait_for_sale_start(sell_start_time_ms, time_offset, log_func, log_file):
    """
    等待到开售时间
    Args:
        sell_start_time_ms: 开售时间（毫秒时间戳）
        time_offset: 时间偏移（秒）
        log_func: 日志函数
        log_file: 日志文件路径，用于写入状态标记
    Returns:
        实际开售时间（秒时间戳，考虑偏移）
    """
    if not sell_start_time_ms:
        log_func("未获取到开售时间，立即开始抢票")
        return time.time() + time_offset

    # 转换为秒
    sell_start_time = sell_start_time_ms / 1000

    # 考虑时间偏移后的开售时间
    adjusted_sell_start = sell_start_time + time_offset

    current_time = time.time()

    # 格式化时间显示
    sell_start_str = datetime.fromtimestamp(sell_start_time).strftime("%Y-%m-%d %H:%M:%S")
    adjusted_str = datetime.fromtimestamp(adjusted_sell_start).strftime("%Y-%m-%d %H:%M:%S")

    log_func(f"票种开售时间: {sell_start_str}")
    log_func(f"考虑时间偏移后: {adjusted_str}")

    # 如果还没到开售时间，等待
    wait_seconds = adjusted_sell_start - current_time

    if wait_seconds > 0:
        log_func(f"[状态] 等待中 - 离开售还有 {wait_seconds:.1f} 秒")

        # 分段等待，避免长时间阻塞
        while wait_seconds > 0:
            if wait_seconds > 60:
                sleep_time = 60
            elif wait_seconds > 10:
                sleep_time = 10
            else:
                sleep_time = min(1, wait_seconds)

            time.sleep(sleep_time)
            current_time = time.time()
            wait_seconds = adjusted_sell_start - current_time

            # 每10秒输出一次日志和状态标记
            if wait_seconds > 0 and int(wait_seconds) % 10 == 0:
                log_func(f"[状态] 等待中 - 还剩 {wait_seconds:.1f} 秒")

        log_func("[状态] 等待结束 - 开售时间到！开始抢票")
    else:
        log_func(f"开售时间已过 {abs(wait_seconds):.1f} 秒，立即开始抢票")

    return adjusted_sell_start


def presale_worker(config: dict, process_id: str):
    """
    预售模式抢票工作进程
    """
    # 日志文件路径 - 使用绝对路径
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(script_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"presale_{process_id}.log")

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
        log(f"预售模式进程 {process_id} 启动")
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
        ticket_id = config.get("ticket_id")
        purchaser_ids = config.get("purchaser_ids", "")
        ticket_count = config.get("count", 1)  # 前端使用count
        delay_ms = config.get("delay", 150)  # 普通模式延迟(毫秒)
        burst_delay_ms = config.get("burst_delay", 70)  # 爆发模式延迟(毫秒)
        time_offset = config.get("time_offset", 0)  # 时间偏移(秒)
        debug_mode = config.get("debug_mode", False)
        presale_mode = config.get("presale_mode", "merge")

        if not ticket_id:
            log("错误: 未设置票种ID")
            return

        log(f"票种ID: {ticket_id}")
        log(f"购买数量: {ticket_count}")
        log(f"抢票延迟: {delay_ms}ms")
        log(f"爆发延迟: {burst_delay_ms}ms")
        log(f"时间偏移: {time_offset*1000:.2f}ms")

        # 解析购买者ID
        purchaser_id_list = [pid.strip() for pid in purchaser_ids.split(",") if pid.strip()]

        # 获取票种信息，提取开售时间
        log("正在获取票种信息...")
        ticket_info = get_ticket_info(session, ticket_id, log)
        sell_start_time_ms = None
        if ticket_info:
            sell_start_time_ms = ticket_info.get("sellStartTime")
            ticket_name = ticket_info.get("ticketName") or ticket_info.get("name", "")
            log(f"票种名称: {ticket_name}")

        # 等待到开售时间
        start_time = wait_for_sale_start(sell_start_time_ms, time_offset, log, log_file)
        burst_mode_end_time = start_time + 2  # 爆发模式持续2秒

        log(f"开始抢票... 前2秒使用爆发模式({burst_delay_ms}ms)，之后使用正常模式({delay_ms}ms)")
        log(f"实际开抢时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

        # 初始化抢票循环变量
        order_count = 0
        success_count = 0  # 成功订单数（分离模式下可能有多单）
        max_orders = 1000  # 最大尝试次数，防止无限循环

        # 分离模式：需要抢ticket_count单；合并模式：只需成功1单
        target_success = ticket_count if presale_mode == "split" else 1

        log(f"目标：成功抢购 {target_success} 单")

        while order_count < max_orders and success_count < target_success:
            try:
                current_time = time.time()

                # 判断是否在爆发模式时间内（开抢后2秒内）
                in_burst_mode = current_time < burst_mode_end_time

                # 计算本次延迟
                if in_burst_mode:
                    delay = get_random_delay_ms(burst_delay_ms)
                    mode_text = "爆发模式"
                else:
                    delay = get_random_delay_ms(delay_ms)
                    mode_text = "正常模式"

                log(f"[{mode_text}] 第{order_count+1}次下单，延迟: {delay*1000:.2f}ms")

                time.sleep(delay)

                # 提交订单
                if presale_mode == "split" and purchaser_id_list:
                    purchaser_id = purchaser_id_list[success_count % len(purchaser_id_list)]
                    result, retry, should_stop, details = submit_ticket_order_with_details(session, ticket_id, purchaser_id, debug_mode, 1, notifier)
                else:
                    result, retry, should_stop, details = submit_ticket_order_with_details(session, ticket_id, purchaser_ids, debug_mode, ticket_count, notifier)

                order_count += 1

                if result:
                    success_count += 1
                    pay_url = details.get("pay_url") if details else None
                    order_info = details.get("order_info") if details else None
                    log(f"第 {success_count}/{target_success} 单抢票成功！共尝试 {order_count} 次")
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
                            notifier.notify_purchase_success("预售抢票", f"票种ID: {ticket_id}", pay_url, order_info)
                    except Exception:
                        pass  # 通知失败不影响抢票

                    # 如果已达到目标，退出循环
                    if success_count >= target_success:
                        break

                    # 分离模式下，抢下一单前稍微延迟
                    if presale_mode == "split":
                        log("等待1秒后抢下一单...")
                        time.sleep(1)
                else:
                    if not retry:
                        log(f"无需重试，抢票失败 (尝试 {order_count} 次)")
                        if details and details.get("message"):
                            log(f"失败原因: {details['message']}")
                        break

                    if order_count % 10 == 0:
                        log(f"已尝试 {order_count} 次...")

            except Exception as e:
                log(f"下单异常: {e}")
                time.sleep(1)

        if success_count == 0:
            log(f"抢票结束，未成功。共尝试 {order_count} 次")
        elif success_count < target_success:
            log(f"抢票结束，部分成功。成功 {success_count}/{target_success} 单，共尝试 {order_count} 次")
        else:
            log(f"抢票成功！共成功 {success_count} 单，尝试 {order_count} 次")

    except Exception as e:
        log(f"进程异常: {e}")
        import traceback
        log(traceback.format_exc())


if __name__ == "__main__":
    # 测试
    test_config = {
        "env_file": "environment_test.json",
        "ticket_id": "1234",
        "purchaser_ids": "123,456",
        "count": 1,
        "delay": 150,
        "burst_delay": 70,
        "debug_mode": True
    }
    presale_worker(test_config, "test")
