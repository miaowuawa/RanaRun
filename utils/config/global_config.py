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
    "juliang": {
        "api_url": "",
        "enabled": False
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


def get_juliang_config() -> Dict[str, Any]:
    """
    获取巨量代理配置
    返回: 巨量代理配置字典
    """
    config = load_global_config()
    return config.get("juliang", DEFAULT_CONFIG["juliang"])


def set_juliang_config(api_url: str = "", enabled: bool = False) -> bool:
    """
    设置巨量代理配置
    Args:
        api_url: API地址
        enabled: 是否启用
    返回: 是否保存成功
    """
    config = load_global_config()
    config["juliang"] = {
        "api_url": api_url,
        "enabled": enabled
    }
    return save_global_config(config)


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
    juliang_config = get_juliang_config()
    if juliang_config.get("enabled", False):
        return juliang_config.get("api_url", "")
    return ""
