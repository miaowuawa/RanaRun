"""
全局配置管理模块
用于存储和管理全局设置，如巨量代理API地址等
"""
import json
import os
from typing import Dict, Any, Optional

# 全局配置文件路径
GLOBAL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "global_config.json")

# 默认配置
DEFAULT_CONFIG = {
    "proxy": {
        "type": "none",  # none, juliang, shanchen
        "juliang": {
            "api_url": ""
        },
        "shanchen": {
            "api_key": "",
            "time_minutes": 1,
            "count": 3,
            "province": "",
            "city": ""
        }
    },
    "yhchat": {
        "token": "",
        "user_id": "",
        "enabled": False
    }
}


def _ensure_config_dir():
    """确保配置目录存在"""
    config_dir = os.path.dirname(GLOBAL_CONFIG_FILE)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)


def load_global_config() -> Dict[str, Any]:
    """
    加载全局配置
    返回: 配置字典
    """
    _ensure_config_dir()
    
    if not os.path.exists(GLOBAL_CONFIG_FILE):
        # 如果配置文件不存在，创建默认配置
        save_global_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(GLOBAL_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        # 合并默认配置，确保新字段存在
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        return merged_config
    except Exception as e:
        print(f"[全局配置] 加载配置失败: {e}，使用默认配置")
        return DEFAULT_CONFIG.copy()


def save_global_config(config: Dict[str, Any]) -> bool:
    """
    保存全局配置
    Args:
        config: 配置字典
    返回: 是否保存成功
    """
    _ensure_config_dir()
    
    try:
        with open(GLOBAL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[全局配置] 保存配置失败: {e}")
        return False


def get_proxy_config() -> Dict[str, Any]:
    """
    获取代理配置
    返回: 代理配置字典
    """
    config = load_global_config()
    return config.get("proxy", DEFAULT_CONFIG["proxy"])


def set_proxy_config(proxy_type: str = "none", juliang_api_url: str = "",
                     shanchen_api_key: str = "", shanchen_time: int = 1,
                     shanchen_count: int = 3, shanchen_province: str = "",
                     shanchen_city: str = "") -> bool:
    """
    设置代理配置
    Args:
        proxy_type: 代理类型 (none, juliang, shanchen)
        juliang_api_url: 巨量代理API地址
        shanchen_api_key: 闪臣代理API密钥
        shanchen_time: 闪臣代理时长(分钟)
        shanchen_count: 闪臣代理数量
        shanchen_province: 闪臣代理省份编号
        shanchen_city: 闪臣代理城市编号
    返回: 是否保存成功
    """
    config = load_global_config()
    config["proxy"] = {
        "type": proxy_type,
        "juliang": {
            "api_url": juliang_api_url
        },
        "shanchen": {
            "api_key": shanchen_api_key,
            "time_minutes": shanchen_time,
            "count": shanchen_count,
            "province": shanchen_province,
            "city": shanchen_city
        }
    }
    return save_global_config(config)


def get_juliang_config() -> Dict[str, Any]:
    """
    获取巨量代理配置 (兼容旧接口)
    返回: 巨量代理配置字典
    """
    proxy_config = get_proxy_config()
    return {
        "api_url": proxy_config.get("juliang", {}).get("api_url", ""),
        "enabled": proxy_config.get("type") == "juliang"
    }


def set_juliang_config(api_url: str = "", enabled: bool = False) -> bool:
    """
    设置巨量代理配置 (兼容旧接口)
    """
    proxy_config = get_proxy_config()
    proxy_type = "juliang" if enabled else proxy_config.get("type", "none")
    if proxy_type == "juliang" and not enabled:
        proxy_type = "none"
    return set_proxy_config(
        proxy_type=proxy_type,
        juliang_api_url=api_url,
        shanchen_api_key=proxy_config.get("shanchen", {}).get("api_key", ""),
        shanchen_time=proxy_config.get("shanchen", {}).get("time_minutes", 1),
        shanchen_count=proxy_config.get("shanchen", {}).get("count", 3),
        shanchen_province=proxy_config.get("shanchen", {}).get("province", ""),
        shanchen_city=proxy_config.get("shanchen", {}).get("city", "")
    )


def get_yhchat_config() -> Dict[str, Any]:
    """
    获取云湖配置
    返回: 云湖配置字典
    """
    config = load_global_config()
    return config.get("yhchat", DEFAULT_CONFIG["yhchat"])


def set_yhchat_config(token: str = "", user_id: str = "", enabled: bool = False) -> bool:
    """
    设置云湖配置
    Args:
        token: 机器人Token
        user_id: 接收用户ID
        enabled: 是否启用
    返回: 是否保存成功
    """
    config = load_global_config()
    config["yhchat"] = {
        "token": token,
        "user_id": user_id,
        "enabled": enabled
    }
    return save_global_config(config)


def get_juliang_api_url() -> str:
    """
    获取巨量代理API地址（如果启用）
    返回: API地址，如果未启用则返回空字符串
    """
    proxy_config = get_proxy_config()
    if proxy_config.get("type") == "juliang":
        return proxy_config.get("juliang", {}).get("api_url", "")
    return ""


def get_shanchen_config() -> Dict[str, Any]:
    """
    获取闪臣代理配置
    返回: 闪臣代理配置字典
    """
    proxy_config = get_proxy_config()
    return {
        "api_key": proxy_config.get("shanchen", {}).get("api_key", ""),
        "time_minutes": proxy_config.get("shanchen", {}).get("time_minutes", 1),
        "count": proxy_config.get("shanchen", {}).get("count", 3),
        "province": proxy_config.get("shanchen", {}).get("province", ""),
        "city": proxy_config.get("shanchen", {}).get("city", ""),
        "enabled": proxy_config.get("type") == "shanchen"
    }


def get_shanchen_api_key() -> str:
    """
    获取闪臣代理API密钥（如果启用）
    返回: API密钥，如果未启用则返回空字符串
    """
    proxy_config = get_proxy_config()
    if proxy_config.get("type") == "shanchen":
        return proxy_config.get("shanchen", {}).get("api_key", "")
    return ""


def get_current_proxy_config() -> Dict[str, Any]:
    """
    获取当前启用的代理配置
    返回: {"type": "none"/"juliang"/"shanchen", "config": {...}}
    """
    proxy_config = get_proxy_config()
    proxy_type = proxy_config.get("type", "none")
    
    if proxy_type == "juliang":
        return {
            "type": "juliang",
            "config": proxy_config.get("juliang", {}),
            "api_url": proxy_config.get("juliang", {}).get("api_url", "")
        }
    elif proxy_type == "shanchen":
        return {
            "type": "shanchen",
            "config": proxy_config.get("shanchen", {}),
            "api_key": proxy_config.get("shanchen", {}).get("api_key", ""),
            "time_minutes": proxy_config.get("shanchen", {}).get("time_minutes", 1),
            "count": proxy_config.get("shanchen", {}).get("count", 3),
            "province": proxy_config.get("shanchen", {}).get("province", ""),
            "city": proxy_config.get("shanchen", {}).get("city", "")
        }
    else:
        return {"type": "none", "config": {}}
