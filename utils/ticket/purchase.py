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
        print(f"[调试][下单]此次延迟：{actual_delay}秒")
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
            print(f"[调试][服务器卡顿]请求阻塞，重试中（第{retry_count}次）")
            return False, True
        if "超时" in message:
            print(f"[调试][下单报错]请求超时，可能是网络不好，协议异常或者本地时间偏差")
            return False, False
        elif "余票" in message:
            print(f"[调试][下单报错]可用库存不足")
            return False, True
        elif result.get("errorCode") == 0:
            print(f"[调试][下单成功]抢票成功！响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return True, False
        else:
            print(f"[调试][下单失败]抢票失败！响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return False, False
    except Exception as e:
        print(f"[调试][下单失败]提交订单失败: {e}")
        return False, True