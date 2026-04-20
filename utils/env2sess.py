# 把环境变量中的header，cookie转换为requests.Session
import requests
import json
import socket
from utils.vdevice.generate_env import init, generate_random_env
from utils.vdevice.latest import get_latest_ver


def env_to_request_session(env: dict) -> requests.Session:
    session = requests.Session()

    # 使用单数 header（与环境文件格式保持一致）
    header = env["header"].copy()
    if "Cookie" in header:
        del header["Cookie"]

    # 将userAgent转换为User-Agent
    if "userAgent" in header:
        header["User-Agent"] = header.pop("userAgent")

    # 先清空默认的 headers，然后再设置我们的 header
    session.headers.clear()
    session.headers.update(header)

    # 使用单数 cookie（与环境文件格式保持一致）
    if "cookie" in env and env["cookie"]:
        session.cookies.update(env["cookie"])

    # 处理代理设置
    if "proxy" in env and env["proxy"]:
        session.proxies = {
            "http": env["proxy"],
            "https": env["proxy"]
        }

    # 处理出口IP设置（云主机多IP绑定场景）
    if "exit_ip" in env and env["exit_ip"]:
        exit_ip = env["exit_ip"]
        try:
            # 创建一个自定义的HTTP适配器，绑定到指定的源IP地址
            from requests.adapters import HTTPAdapter
            from urllib3.poolmanager import PoolManager

            class SourceIPAdapter(HTTPAdapter):
                def __init__(self, source_ip, **kwargs):
                    self.source_ip = source_ip
                    super().__init__(**kwargs)

                def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
                    # 绑定到指定的源IP地址
                    pool_kwargs['source_address'] = (self.source_ip, 0)
                    self.poolmanager = PoolManager(
                        num_pools=connections,
                        maxsize=maxsize,
                        block=block,
                        **pool_kwargs
                    )

            # 为HTTP和HTTPS请求都使用自定义适配器
            session.mount('http://', SourceIPAdapter(exit_ip))
            session.mount('https://', SourceIPAdapter(exit_ip))
        except Exception as e:
            print(f"设置出口IP失败: {e}")

    # 先请求www.allcpp.cn获取基础cookie
    try:
        session.get("https://www.allcpp.cn/")
    except Exception as e:
        print(f"获取基础cookie失败: {e}")

    return session


def request_session_to_env(session: requests.Session) -> dict:
    env = {}

    # 复制 header 并移除 Cookie 字段，避免重复设置
    header = dict(session.headers)
    if "Cookie" in header:
        del header["Cookie"]
    env["header"] = header  # 修复：复数

    # 设置 cookie
    env["cookie"] = dict(session.cookies)  # 修复：复数

    # 保存代理设置
    if hasattr(session, "proxies") and session.proxies:
        # 假设所有协议使用相同的代理
        env["proxy"] = session.proxies.get("http", session.proxies.get("https"))

    return env


def generate_environment_file(custom_name: str, proxy: str = None, exit_ip: str = None) -> str:
    """
    生成最新版本app的environment_xxx.json文件
    :param custom_name: 用户自定义的名称，将作为文件名的一部分
    :param proxy: 代理设置，格式为"socks5://host:port"，默认不使用代理
    :param exit_ip: 出口IP地址，用于云主机多IP绑定场景
    :return: 生成的文件路径
    """
    # 初始化环境列表
    init()

    # 获取最新的app版本
    latest_ver = get_latest_ver()
    if not latest_ver:
        raise Exception("无法获取最新的app版本")

    # 生成随机环境
    env = generate_random_env(latest_ver)

    # 移除header中可能存在的Cookie字段，避免重复设置
    if "header" in env and "Cookie" in env["header"]:
        del env["header"]["Cookie"]

    # 添加空的cookie字段
    env["cookie"] = {}

    # 添加代理设置
    if proxy:
        env["proxy"] = proxy

    # 添加出口IP设置
    if exit_ip:
        env["exit_ip"] = exit_ip

    # 生成文件路径
    file_path = f"environment_{custom_name}.json"

    # 保存环境到文件
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(env, f, ensure_ascii=False, indent=2)

    return file_path