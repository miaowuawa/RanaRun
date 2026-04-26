# 全局配置模块
from .global_config import (
    load_global_config,
    save_global_config,
    get_proxy_config,
    set_proxy_config,
    get_juliang_config,
    set_juliang_config,
    get_shanchen_config,
    get_shanchen_api_key,
    get_yhchat_config,
    set_yhchat_config,
    get_juliang_api_url,
    get_current_proxy_config
)

__all__ = [
    'load_global_config',
    'save_global_config',
    'get_proxy_config',
    'set_proxy_config',
    'get_juliang_config',
    'set_juliang_config',
    'get_shanchen_config',
    'get_shanchen_api_key',
    'get_yhchat_config',
    'set_yhchat_config',
    'get_juliang_api_url',
    'get_current_proxy_config'
]
