import hashlib

# 安卓端已经用不了这个sign了，目前苹果保留了这个签名方式，之所以能拿到，是因为cpp的苹果app没壳~欸嘿
def generate_signature(timestamp: int, nonce: str, ticket_type_id: str) -> str:
    # Step 1: 格式化
    ts_str = str(timestamp)
    tid_str = str(ticket_type_id)

    # Step 2: 拼接（两个硬编码密钥夹住参数）
    raw = f"cpp2C0T2y5u0m7a2d9l{ts_str}{nonce}{tid_str}mKSEDLushKSIJSISHMNFEDNSUYQEAVJSfwp"

    # Step 3: 逆序
    reversed_str = raw[::-1]

    # Step 4: 转大写
    uppercased = reversed_str.upper()

    # Step 5+6: MD5 → 小写hex
    signature = hashlib.md5(uppercased.encode('utf-8')).hexdigest()

    return signature