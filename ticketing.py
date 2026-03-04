import os
import json
import time
import random
import hashlib
import requests
from typing import Dict, List, Optional
from datetime import datetime
from utils.env2sess import env_to_request_session

# 全局配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 当前脚本所在目录
GET_TICKET_TYPE_URL = "https://www.allcpp.cn/allcpp/ticket/getTicketTypeList.do"
GET_PURCHASER_LIST_URL = "https://www.allcpp.cn/allcpp/user/purchaser/getList.do"
PAY_TICKET_URL = "https://www.allcpp.cn/api/ticket/pay/ali.do"
BASE_DELAY = 0.1  # 默认基准延迟（秒）


def load_json_configs() -> Dict[str, dict]:
    """
    加载目录下除envinfo.json外的所有JSON配置文件
    Returns:
        配置字典 {文件名: 配置内容}
    """
    configs = {}
    for filename in os.listdir(BASE_DIR):
        if filename.endswith(".json") and filename != "envinfo.json":
            file_path = os.path.join(BASE_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    configs[filename] = config
            except Exception as e:
                print(f"加载配置文件 {filename} 失败: {e}")
    return configs


def save_config(config_name: str, config_data: dict):
    """
    保存配置文件（主要用于更新cookie）
    """
    file_path = os.path.join(BASE_DIR, config_name)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        print(f"配置文件 {config_name} 已更新")
    except Exception as e:
        print(f"保存配置文件 {config_name} 失败: {e}")


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


def generate_signature_params(ticket_type_id: str) -> Dict[str, str]:
    """
    生成签名参数
    Args:
        ticket_id: 门票ID字符串
    Returns:
        包含nonce、timeStamp、sign的字典
    """

    # 随机字符串生成
    charset = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
    nonce = ''.join(random.choices(charset, k=5))

    timestamp = str(time.time() * 1000)  # 毫秒级时间戳
    sign = calc_sign(ts=timestamp,nonce=nonce,ticket_type_id=ticket_type_id)

    # 计算签名

    return {
        "nonce": nonce,
        "timeStamp": str(timestamp),
        "sign": sign
    }

SECRET = "cpp2C0T2y5u0m7a2d9l"

def calc_sign(ts: str, nonce: str, ticket_type_id: str) -> str:
    left = (ts + nonce.upper() + ticket_type_id)[::-1]
    right = SECRET.upper()[::-1]
    return hashlib.md5((left + right).encode("utf-8")).hexdigest()

def get_random_delay(base_delay: float) -> float:
    """
    根据基准延迟生成随机延迟（±0.2秒 + 10-50ms随机延迟），确保不小于0.1秒
    Args:
        base_delay: 基准延迟
    Returns:
        随机调整后的延迟值
    """
    # 生成-0.2到+0.2之间的随机数
    random_offset = random.uniform(-0.2, 0.2)
    # 生成10-50ms的随机延迟
    ms_delay = random.uniform(0.01, 0.05)
    actual_delay = base_delay + random_offset + ms_delay
    # 确保延迟不小于0.1秒
    actual_delay = max(0.1, actual_delay)
    return round(actual_delay, 3)


def get_ticket_type_list(session: requests.Session, event_main_id: str, base_delay: float) -> Optional[dict]:
    """
    获取票种列表（增加随机延迟和提示）
    Args:
        session: requests会话
        event_main_id: 项目ID
        base_delay: 基准延迟
    Returns:
        票种列表响应数据，失败返回None
    """
    # 生成并输出本次延迟
    actual_delay = get_random_delay(base_delay)
    print(f"[调试][获取票种列表]此次延迟：{actual_delay}秒")
    time.sleep(actual_delay)

    try:
        params = {"eventMainId": event_main_id}
        response = session.get(GET_TICKET_TYPE_URL, params=params, timeout=10)
        response.raise_for_status()

        # 检查是否有新cookie需要更新
        if session.cookies:
            new_cookies = []
            for key, value in session.cookies.items():
                new_cookies.append(f"{key}={value}")
            new_cookie_str = "; ".join(new_cookies)
        return response.json()
    except Exception as e:
        print(f"获取票种列表失败: {e}")
        return None


def get_purchaser_list(session: requests.Session, base_delay: float) -> Optional[List[dict]]:
    """
    获取购票人列表（增加随机延迟和提示）
    Args:
        base_delay: 基准延迟
    Returns:
        购票人列表，失败返回None
    """
    # 生成并输出本次延迟
    actual_delay = get_random_delay(base_delay)
    print(f"此次延迟：{actual_delay}秒")
    time.sleep(actual_delay)

    try:
        response = session.get(GET_PURCHASER_LIST_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data
        else:
            print("未获取到购票人信息")
            return None
    except Exception as e:
        print(f"获取购票人列表失败: {e}")
        return None


def check_ticket_status(ticket_info: dict) -> str:
    """
    检查票种状态
    Returns:
        - "ended": 已结束销售
        - "presale": 预售（未到开售时间）
        - "selling": 可售（正在销售）
    """
    now = int(time.time() * 1000)
    sell_start = ticket_info.get("sellStartTime", 0)
    sell_end = ticket_info.get("sellEndTime", 0)

    if now > sell_end:
        return "ended"
    elif now < sell_start:
        return "presale"
    else:
        return "selling"


def presale_mode(session: requests.Session, ticket_id: str, purchaser_id: str, base_delay: float):
    """
    预售模式：等待开售时间后抢票（适配随机延迟和响应提示）
    """
    ticket_info = None
    # 先获取最新的票种信息
    for config_name, config in load_json_configs().items():
        temp_session = create_session(config)
        ticket_data = get_ticket_type_list(temp_session, event_main_id, base_delay)
        if ticket_data and "ticketTypeList" in ticket_data:
            for t in ticket_data["ticketTypeList"]:
                if str(t["id"]) == ticket_id:
                    ticket_info = t
                    break
        if ticket_info:
            break

    if not ticket_info:
        print("未找到指定票种信息")
        return

    sell_start = ticket_info.get("sellStartTime", 0)
    sell_start_dt = datetime.fromtimestamp(sell_start / 1000)
    print(f"等待抢票开始，开售时间: {sell_start_dt.strftime('%Y-%m-%d %H:%M:%S')}")

    # 等待开售时间
    retry_count = 0
    while int(time.time() * 1000) < sell_start:
        actual_delay = get_random_delay(base_delay)
        print(f"此次延迟：{actual_delay}秒")
        time.sleep(actual_delay)
        remaining = (sell_start - int(time.time() * 1000)) / 1000
        if remaining % 10 == 0:  # 每10秒打印一次倒计时
            print(f"距离开售还有 {remaining:.0f} 秒")

    # 开始抢票
    print("开始抢票...")
    # 预售模式下失败持续重试
    while True:
        result, retry = submit_ticket_order(session, ticket_id, purchaser_id, base_delay)
        if result:  # 抢票成功则退出
            break
        if retry:  # 需要重试则继续
            retry_count += 1
            continue
        else:  # 无需重试则退出
            break


def check_ticket_stock(session: requests.Session, ticket_id: str, base_delay: float) -> bool:
    """
    检查票种库存（增加随机延迟和提示）
    Args:
        base_delay: 基准延迟
    Returns:
        True: 有库存，False: 无库存
    """
    try:
        # 生成并输出本次延迟
        actual_delay = get_random_delay(base_delay)
        print(f"此次延迟：{actual_delay}秒")
        time.sleep(actual_delay)

        # 重新获取票种信息检查库存
        ticket_data = get_ticket_type_list(session, event_main_id, base_delay)
        if ticket_data and "ticketTypeList" in ticket_data:
            for ticket in ticket_data["ticketTypeList"]:
                if str(ticket["id"]) == ticket_id:
                    # remainderNum > 0 表示有库存
                    return ticket.get("remainderNum", 0) > 0
        return False
    except Exception as e:
        print(f"检查库存失败: {e}")
        return False


def reflux_mode(session: requests.Session, ticket_id: str, purchaser_id: str, base_delay: float):
    """
    回流模式：循环扫描库存，有库存立即抢票（适配随机延迟和响应提示）
    """
    # 增加强制切换预售模式的交互
    print("\n⚠️  当前票种为可售状态，默认使用回流模式（扫描库存抢票）")
    print("======================================================================")
    print("⚠️  风险提示：强制对可售票种使用预售模式可能触发平台风控，导致账号封禁！")
    print("======================================================================")
    force_presale = input("是否强制使用预售模式？(y/N，默认N): ").strip().lower()

    if force_presale == "y":
        print("\n⚠️  你已选择强制使用预售模式，请注意账号安全！")
        confirm = input("请再次确认是否强制使用预售模式（输入YES确认）: ").strip()
        if confirm == "YES":
            presale_mode(session, ticket_id, purchaser_id, base_delay)
            return
        else:
            print("已取消强制切换，继续使用回流模式...")

    print("进入回流抢票模式，开始扫描库存...")
    retry_count = 0
    while True:
        if check_ticket_stock(session, ticket_id, base_delay - 0.2):
            print("检测到有库存，立即抢票！")
            result, retry = submit_ticket_order(session, ticket_id, purchaser_id, base_delay)
            if result:  # 抢票成功则退出
                break
            # 回流模式下无论是否重试都继续扫描库存
            retry_count += 1
        else:
            print("库存不够，再尝试一下")
        time.sleep(get_random_delay(base_delay))


def submit_ticket_order(session: requests.Session, ticket_id: str, purchaser_id: str, base_delay: float) -> tuple[bool, bool]:
    """
    提交购票订单（增加响应提示处理、随机延迟）
    Args:
        base_delay: 基准延迟
    Returns:
        (是否成功, 是否需要重试)
    """
    retry_count = 0
    try:
        # 生成并输出本次延迟
        actual_delay = get_random_delay(base_delay)
        print(f"此次延迟：{actual_delay}秒")
        time.sleep(actual_delay)

        # 生成签名参数
        sign_params = generate_signature_params(str(6198))

        # 构造请求数据
        request_data = {
            "timeStamp": sign_params["timeStamp"],
            "nonce": sign_params["nonce"],
            "sign": sign_params["sign"],
            "ticketTypeId": ticket_id,
            "count": 1,
            "purchaserIds": purchaser_id
        }

        # 注意接口要求的特殊格式：外层是一个key为JSON字符串，value为空字符串的字典
        payload = {json.dumps(request_data, ensure_ascii=False): ""}

        response = session.post(PAY_TICKET_URL, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        # 处理响应提示
        message = result.get("message", "") if isinstance(result, dict) else str(result)
        if "拥挤" in message:
            retry_count += 1
            print(f"[服务器卡顿]请求阻塞，重试中（第{retry_count}次）")
            return False, True
        if "超时" in message:
            print(f"[下单报错]请求超时，可能是协议异常")
            return False, False
        elif "余票" in message:
            print("可用库存不足")
            return False, True
        elif result.get("errorCode") == 0:
            print(f"抢票成功！响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return True, False
        else:
            print(f"抢票失败！响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return False, False
    except Exception as e:
        print(f"提交订单失败: {e}")
        return False, True


def main():
    global event_main_id
    # 1. 加载配置文件
    configs = load_json_configs()
    if not configs:
        print("未找到有效的配置文件（除envinfo.json外的JSON文件）")
        return

    # 2. 选择配置文件
    print("\n可用的配置文件：")
    for idx, name in enumerate(configs.keys(), 1):
        print(f"{idx}. {name}")
    config_choice = input("请选择要使用的配置文件序号: ")
    try:
        config_name = list(configs.keys())[int(config_choice) - 1]
        selected_config = configs[config_name]
    except (ValueError, IndexError):
        print("选择无效")
        return

    # 3. 创建session
    session = create_session(selected_config)

    # 4. 输入项目ID
    event_main_id = input("请输入项目ID: ").strip()
    if not event_main_id:
        print("项目ID不能为空")
        return

    # 5. 获取票种列表
    ticket_data = get_ticket_type_list(session, event_main_id, BASE_DELAY)
    if not ticket_data or "ticketTypeList" not in ticket_data:
        print("未获取到票种信息")
        return

    # 6. 展示票种信息
    print("\n可用的票种：")
    ticket_list = ticket_data["ticketTypeList"]
    for idx, ticket in enumerate(ticket_list, 1):
        status = check_ticket_status(ticket)
        status_text = {
            "ended": "已结束销售",
            "presale": "预售中",
            "selling": "可购买"
        }.get(status, "未知状态")
        print(f"{idx}. {ticket['ticketName']} - 价格: {ticket['ticketPrice']/100}元 - 状态: {status_text}")

    # 7. 选择票种
    while True:
        ticket_choice = input("\n请选择要抢的票种序号: ")
        try:
            selected_ticket = ticket_list[int(ticket_choice) - 1]
            ticket_status = check_ticket_status(selected_ticket)

            if ticket_status == "ended":
                print("此类型票已结束销售，请重新选择")
                continue
            break
        except (ValueError, IndexError):
            print("选择无效，请重新选择")

    # 8. 设置基准延迟（增加校验提示）
    print(f"\n⚠️  基准延迟设置提示：基准延迟减去0.2后不要小于0.1秒 ⚠️")
    while True:
        delay_input = input(f"请设置基准延迟（秒，默认{BASE_DELAY}）: ").strip()
        try:
            base_delay = float(delay_input) if delay_input else BASE_DELAY
            # 校验基准延迟
            if base_delay - 0.2 < 0.1:
                print(f"=======!!!!!!!警告!!!!!!!=======\n当前基准延迟{base_delay}秒，减去0.2后小于0.1秒，不建议这么设置！\n=======!!!!!!!警告!!!!!!!=======")
            break
        except ValueError:
            print("输入无效，请输入数字！")
            continue

    # 9. 检查是否需要实名，获取购票人ID
    if selected_ticket.get("realnameAuth"):
        print("\n此票种需要实名，正在获取购票人列表...")
        purchasers = get_purchaser_list(session, base_delay)
        if not purchasers:
            return

        print("\n可用的购票人：")
        for idx, p in enumerate(purchasers, 1):
            print(f"{idx}. 姓名: {p['realname']} - 身份证: {p['idcard']} - 手机号: {p['mobile']}")

        purchaser_choice = input("请选择购票人序号: ")
        try:
            selected_purchaser = purchasers[int(purchaser_choice) - 1]
            purchaser_id = str(selected_purchaser["id"])
        except (ValueError, IndexError):
            print("购票人选择无效")
            return
    else:
        purchaser_id = ""

    # 10. 根据票种状态选择抢票模式
    ticket_id = str(selected_ticket["id"])
    ticket_status = check_ticket_status(selected_ticket)

    if ticket_status == "presale":
        presale_mode(session, ticket_id, purchaser_id, base_delay)
    elif ticket_status == "selling":
        reflux_mode(session, ticket_id, purchaser_id, base_delay)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")