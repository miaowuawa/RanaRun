# 全局配置模块
from .global_config import (
    load_global_config,
    save_global_config,
    get_juliang_config,
    set_juliang_config,
    get_yhchat_config,
    set_yhchat_config,
    get_juliang_api_url
)

__all__ = [
    'load_global_config',
    'save_global_config',
    'get_juliang_config',
    'set_juliang_config',
    'get_yhchat_config',
    'set_yhchat_config',
    'get_juliang_api_url'
]
