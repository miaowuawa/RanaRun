"""
预售模式抢票工作进程
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

        # 计算需要抢的票数
        if presale_mode == "split":
            # 分离模式：每单1张，需要抢ticket_count次
            total_orders = ticket_count
        else:
            # 合并模式：一次下单ticket_count张
            total_orders = 1

        # 抢票循环
        order_count = 0
        success = False
        start_time = time.time() + time_offset  # 考虑时间偏移
        burst_mode_end_time = start_time + 2  # 爆发模式持续2秒

        log(f"开始抢票... 前2秒使用爆发模式({burst_delay_ms}ms)，之后使用正常模式({delay_ms}ms)")
        log(f"实际开抢时间(考虑偏移): {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

        while order_count < total_orders and not success:
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
                    purchaser_id = purchaser_id_list[order_count % len(purchaser_id_list)]
                    result, retry, should_stop, details = submit_ticket_order_with_details(session, ticket_id, purchaser_id, debug_mode, 1)
                else:
                    result, retry, should_stop, details = submit_ticket_order_with_details(session, ticket_id, purchaser_ids, debug_mode, ticket_count)

                order_count += 1

                if result:
                    success = True
                    pay_url = details.get("pay_url") if details else None
                    order_info = details.get("order_info") if details else None
                    log(f"抢票成功！共尝试 {order_count} 次")
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
                    break
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

        if not success:
            log(f"抢票结束，未成功。共尝试 {order_count} 次")

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
