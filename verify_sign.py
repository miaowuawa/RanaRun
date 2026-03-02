import hashlib

def generate_signature(timestamp: int, nonce: str, ticket_type_id: str) -> str:
    # 使用用户提供的算法
    raw = f"cpp2C0T2y5u0m7a2d9l{timestamp}{nonce}{ticket_type_id}mKSEDLushKSIJSISHMNFEDNSUYQEAVJSfwp"
    signature = hashlib.md5(raw[::-1].upper().encode('utf-8')).hexdigest()
    return signature

# 测试数据
timestamp = 1772470696945
nonce = "ZLQVH"
ticket_type_id = "5518"
expected_sign = "0b16ddb2154c8660299a2eb7f291f5a1"

# 计算sign
calculated_sign = generate_signature(timestamp, nonce, ticket_type_id)

# 验证结果
print(f"时间戳: {timestamp}")
print(f"随机字符串: {nonce}")
print(f"票档ID: {ticket_type_id}")
print(f"预期sign: {expected_sign}")
print(f"计算sign: {calculated_sign}")
print(f"结果: {'正确' if calculated_sign == expected_sign else '错误'}")
