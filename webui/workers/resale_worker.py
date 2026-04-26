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
        # 回流模式配置
        resale_mode = config.get("resale_mode", "merge")  # 合并/分离模式
        order_delay = config.get("order_delay", 100)  # 下单延迟(毫秒)
        max_order_attempts = config.get("max_order_attempts", 10)  # 有票时最大下单次数
        # 猛攻模式配置
        aggressive_mode = config.get("aggressive_mode", False)
        aggressive_delay_ms = config.get("aggressive_delay", 50)  # 猛攻延迟(毫秒)
        aggressive_count = config.get("aggressive_count", 20)  # 猛攻次数
        
        # 代理池配置（优先使用传入的配置，如果没有则使用全局配置）
        proxy_type = config.get("proxy_type", "none")
        proxy_config = config.get("proxy_config", {})

        if proxy_type == "none":
            # 从全局配置获取
            try:
                from utils.config import get_current_proxy_config
                current_proxy = get_current_proxy_config()
                proxy_type = current_proxy.get("type", "none")
                proxy_config = current_proxy.get("config", {})
                if proxy_type != "none":
                    log(f"[代理] 使用全局配置: 类型={proxy_type}")
            except Exception as e:
                log(f"获取全局代理配置失败: {e}")

        # 初始化代理池
        proxy_pool = None
        if proxy_type != "none":
            try:
                from utils.proxy.proxy_pool import get_proxy_pool
                proxy_pool = get_proxy_pool(process_id, proxy_type, proxy_config)
                if proxy_pool:
                    log(f"[代理池] 已启动，类型={proxy_type}，缓存区目标大小: 3个代理")
                    # 等待代理池预热
                    time.sleep(2)
                    status = proxy_pool.get_status()
                    log(f"[代理池] 当前缓存状态: {status['valid_count']}/{status['target_size']} 个有效代理")
                else:
                    log(f"[代理] 代理已禁用或未配置")
            except Exception as e:
                log(f"[代理池] 启动失败: {e}")

        # 兼容旧版本：获取巨量代理API URL用于下单函数
        juliang_api_url = ""
        if proxy_type == "juliang":
            juliang_api_url = proxy_config.get("api_url", "")

        if not event_id or not ticket_id:
            log("错误: 未设置活动ID或票种ID")
            return

        log(f"活动ID: {event_id}")
        log(f"票种ID: {ticket_id}")
        log(f"刷新延迟: {refresh_delay}秒")
        log(f"下单延迟: {order_delay}ms")
        log(f"抢票模式: {'分离模式' if resale_mode == 'split' else '合并模式'}")
        log(f"最大下单次数: {max_order_attempts}次")
        if aggressive_mode:
            log(f"猛攻模式: 启用 (延迟{aggressive_delay_ms}ms, 次数{aggressive_count})")
        if proxy_pool:
            log(f"[代理池] 已启用，优先从缓存获取代理")

        # 解析购买者ID
        purchaser_id_list = [pid.strip() for pid in purchaser_ids.split(",") if pid.strip()]

        # 检测循环
        check_count = 0
        success_count = 0  # 成功订单数（分离模式下可能有多单）
        success = False
        current_stock = 0
        aggressive_remaining = 0  # 剩余猛攻次数
        in_aggressive_mode = False  # 是否在猛攻模式中
        order_attempt_count = 0  # 当前有票时的下单尝试次数
        in_order_mode = False  # 是否在有票下单模式中

        # 分离模式：需要抢ticket_count单；合并模式：只需成功1单
        target_success = ticket_count if resale_mode == "split" else 1

        log(f"目标：成功抢购 {target_success} 单")
        log("开始检测余票...")

        while success_count < target_success:
            try:
                check_count += 1

                # 如果在猛攻模式中，跳过余票检测直接下单
                # 检查是否需要从代理池获取新代理
                if proxy_pool and (check_count % 5 == 0 or not session.proxies):  # 每5次请求或没有代理时
                    try:
                        cached_proxy = proxy_pool.get_proxy()
                        if cached_proxy:
                            session.proxies = cached_proxy
                            log(f"[代理池] 切换到缓存代理: {cached_proxy['http'][:40]}...")
                    except Exception as e:
                        log(f"[代理池] 获取代理失败: {e}")

                if in_aggressive_mode:
                    # 猛攻模式：高速重试下单
                    aggressive_remaining -= 1
                    mode_text = f"猛攻模式(剩余{aggressive_remaining}次)"
                    log(f"[{mode_text}] 第{check_count}次尝试下单...")

                    # 分离模式：使用不同的购买者
                    if resale_mode == "split" and purchaser_id_list:
                        purchaser_id = purchaser_id_list[success_count % len(purchaser_id_list)]
                    elif purchaser_id_list:
                        purchaser_id = purchaser_id_list[0]
                    else:
                        purchaser_id = purchaser_ids

                    result, retry, should_stop, details = submit_ticket_order_with_details(
                        session, ticket_id, purchaser_id, debug_mode, 1 if resale_mode == "split" else ticket_count, notifier, juliang_api_url
                    )

                    # 猛攻模式下：只有请求频繁/ACL等情况才切换代理，通道拥挤不换代理
                    if proxy_pool and not result and details:
                        message = details.get("message", "")
                        if any(kw in message for kw in ["频繁", "acl", "custom", "proxy", "连接"]):
                            try:
                                new_proxy = proxy_pool.get_proxy()
                                if new_proxy:
                                    session.proxies = new_proxy
                                    log(f"[代理池-猛攻] 检测到'{message[:20]}...'，快速切换到新代理: {new_proxy['http'][:40]}...")
                            except Exception as e:
                                log(f"[代理池-猛攻] 切换代理失败: {e}")

                    # 检查猛攻模式是否结束
                    message = details.get("message", "") if details else ""

                    # 检查是否应该停止（限购等情况）
                    if should_stop:
                        log(f"[猛攻模式] 检测到限购或不可重试错误: {message}")
                        log("[猛攻模式] 停止抢票")
                        in_aggressive_mode = False
                        aggressive_remaining = 0
                        break  # 跳出主循环

                    if result:
                        # 下单成功
                        success_count += 1
                        pay_url = details.get("pay_url") if details else None
                        order_info = details.get("order_info") if details else None
                        log(f"[猛攻模式] 第 {success_count}/{target_success} 单抢票成功！共检测 {check_count} 次")
                        in_aggressive_mode = False
                        aggressive_remaining = 0
                        order_attempt_count = 0  # 重置下单计数
                        in_order_mode = False
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
                                notifier.notify_purchase_success("回流抢票", f"票种ID: {ticket_id}", pay_url, order_info)
                        except Exception:
                            pass  # 通知失败不影响抢票

                        # 如果已达到目标，退出循环
                        if success_count >= target_success:
                            break

                        # 分离模式下，抢下一单前稍微延迟
                        if resale_mode == "split":
                            log("等待1秒后抢下一单...")
                            time.sleep(1)
                        elif stop_on_success:
                            break
                    elif "余票" in message:
                        # 余票不足，退出猛攻模式
                        log(f"[猛攻模式] 余票不足: {message}")
                        in_aggressive_mode = False
                        aggressive_remaining = 0
                        log("[猛攻模式] 退出猛攻模式，恢复正常检测")
                    elif aggressive_remaining <= 0:
                        # 猛攻次数用完
                        log("[猛攻模式] 高速重试次数用完，恢复正常检测")
                        in_aggressive_mode = False

                    # 猛攻模式延迟
                    if in_aggressive_mode:
                        time.sleep(aggressive_delay_ms / 1000 + random.uniform(-0.01, 0.01))
                    continue  # 跳过后续正常检测

                # 正常模式：获取票种信息
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
                            # 进入有票下单模式
                            if not in_order_mode:
                                in_order_mode = True
                                order_attempt_count = 0
                                log(f"发现余票: {remainder} 张！开始下单模式（最大{max_order_attempts}次）")

                                # 发送回流票命中通知
                                try:
                                    if notifier.enabled:
                                        event_name = target_ticket.get("eventName", "未知活动")
                                        ticket_name = target_ticket.get("ticketName", "未知票种")
                                        notifier.notify_resale_hit(event_name, ticket_name, event_id, ticket_id)
                                except Exception:
                                    pass  # 通知失败不影响抢票

                            # 检查是否超过最大尝试次数
                            if order_attempt_count >= max_order_attempts:
                                log(f"[下单模式] 已达到最大尝试次数({max_order_attempts}次)，返回余票检测")
                                in_order_mode = False
                                order_attempt_count = 0
                                continue

                            # 下单延迟
                            actual_delay = order_delay / 1000 + random.uniform(-0.01, 0.01)
                            actual_delay = max(0.01, actual_delay)
                            log(f"[下单模式] 第{order_attempt_count + 1}/{max_order_attempts}次尝试，延迟{actual_delay*1000:.0f}ms")
                            time.sleep(actual_delay)

                            order_attempt_count += 1

                            # 分离模式：使用不同的购买者
                            if resale_mode == "split" and purchaser_id_list:
                                purchaser_id = purchaser_id_list[success_count % len(purchaser_id_list)]
                            elif purchaser_id_list:
                                purchaser_id = purchaser_id_list[0]
                            else:
                                purchaser_id = purchaser_ids

                            result, retry, should_stop, details = submit_ticket_order_with_details(
                                session, ticket_id, purchaser_id, debug_mode, 1 if resale_mode == "split" else ticket_count, notifier, juliang_api_url
                            )

                            # 检查是否需要切换代理（请求频繁或失败）
                            if proxy_pool and details:
                                message = details.get("message", "")
                                # 请求频繁、ACL、连接失败等情况都切换代理
                                if any(kw in message for kw in ["频繁", "acl", "custom", "proxy", "连接"]):
                                    try:
                                        log(f"[代理池] 检测到'{message[:20]}...'，切换到新代理")
                                        new_proxy = proxy_pool.get_proxy()
                                        if new_proxy:
                                            session.proxies = new_proxy
                                            log(f"[代理池] 已切换到新代理: {new_proxy['http'][:40]}...")
                                    except Exception as e:
                                        log(f"[代理池] 切换代理失败: {e}")

                            # 检查是否需要进入猛攻模式（仅对通道拥挤触发）
                            message = details.get("message", "") if details else ""
                            
                            # 检查是否应该停止（限购等情况）
                            if should_stop:
                                log(f"[下单模式] 检测到限购或不可重试错误: {message}")
                                log("[下单模式] 停止抢票")
                                break  # 跳出主循环
                            
                            if aggressive_mode and not result and "拥挤" in message:
                                in_aggressive_mode = True
                                aggressive_remaining = aggressive_count
                                in_order_mode = False  # 退出下单模式，进入猛攻模式
                                order_attempt_count = 0
                                log(f"[猛攻模式] 检测到通道拥挤，启动猛攻模式！高速重试{aggressive_count}次")
                                continue  # 跳过正常延迟，直接进入猛攻模式

                            if result:
                                # 下单成功
                                success_count += 1
                                pay_url = details.get("pay_url") if details else None
                                order_info = details.get("order_info") if details else None
                                log(f"[下单模式] 第 {success_count}/{target_success} 单抢票成功！共检测 {check_count} 次，下单{order_attempt_count}次")
                                order_attempt_count = 0
                                in_order_mode = False
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

                                # 如果已达到目标，退出循环
                                if success_count >= target_success:
                                    break

                                # 分离模式下，抢下一单前稍微延迟
                                if resale_mode == "split":
                                    log("等待1秒后抢下一单...")
                                    time.sleep(1)
                                elif stop_on_success:
                                    break
                            elif "余票" in message:
                                # 余票不足，退出下单模式
                                log(f"[下单模式] 余票不足: {message}")
                                log("[下单模式] 退出下单模式，返回余票检测")
                                in_order_mode = False
                                order_attempt_count = 0
                            # 否则继续下单模式，直到达到最大次数
                        else:
                            # 余票为0，退出下单模式
                            if in_order_mode:
                                log("[下单模式] 余票已售罄，退出下单模式")
                                in_order_mode = False
                                order_attempt_count = 0
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

        if success_count == 0:
            log(f"抢票结束，未成功。共检测 {check_count} 次")
        elif success_count < target_success:
            log(f"抢票结束，部分成功。成功 {success_count}/{target_success} 单，共检测 {check_count} 次")
        else:
            log(f"抢票成功！共成功 {success_count} 单，共检测 {check_count} 次")

    except Exception as e:
        log(f"进程异常: {e}")
        import traceback
        log(traceback.format_exc())
    finally:
        # 停止代理池
        try:
            if proxy_pool:
                from utils.proxy.proxy_pool import stop_proxy_pool
                stop_proxy_pool(process_id)
                log("[代理池] 已停止")
        except:
            pass


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
