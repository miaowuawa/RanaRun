def generate_ua(latest_ver: str, device_ver: str):
    ua = f'CPP/{latest_ver} (iPhone; iOS {device_ver};Scale/3.00)'
    return ua