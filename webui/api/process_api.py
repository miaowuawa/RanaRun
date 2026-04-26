"""
抢票进程管理API
"""
import os
import json
from flask import Blueprint, jsonify, request
from webui.process_manager import process_manager

process_bp = Blueprint('process', __name__)


@process_bp.route('/list', methods=['GET'])
def list_processes():
    """获取所有进程列表"""
    try:
        processes = process_manager.get_all_processes()
        return jsonify({
            "success": True,
            "data": [p.to_dict() for p in processes]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/test_notification', methods=['POST'])
def test_notification():
    """测试云湖通知"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        user_id = data.get('user_id', '')

        if not token or not user_id:
            return jsonify({"success": False, "error": "请填写Token和用户ID"}), 400

        # 创建通知器并发送测试消息
        from utils.notification.yhchat import YHChatNotifier
        notifier = YHChatNotifier(token, user_id, 'user')

        success = notifier.send_markdown(
            "🧪 **云湖通知测试**\n\n"
            "这是一条测试消息！\n\n"
            "如果您收到此消息，说明云湖通知配置正确。\n\n"
            "时间：" + __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            buttons=[[{
                "text": "查看帮助",
                "actionType": 1,
                "url": "https://www.yhchat.com/document/400-410"
            }]]
        )

        if success:
            return jsonify({"success": True, "message": "测试消息已发送"})
        else:
            return jsonify({"success": False, "error": "发送失败，请检查Token和用户ID"}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/create', methods=['POST'])
def create_process():
    """创建新进程"""
    try:
        data = request.get_json()
        name = data.get('name', '未命名进程')
        mode = data.get('mode')  # 'presale' 或 'resale'
        config = data.get('config', {})

        if not mode or mode not in ['presale', 'resale']:
            return jsonify({"success": False, "error": "无效的模式"}), 400

        # 验证必要配置
        if not config.get('env_file'):
            return jsonify({"success": False, "error": "缺少环境文件"}), 400

        if not config.get('ticket_id'):
            return jsonify({"success": False, "error": "缺少票种ID"}), 400

        # 创建进程
        process_id = process_manager.create_process(name, mode, config)

        return jsonify({
            "success": True,
            "data": {"process_id": process_id}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/start', methods=['POST'])
def start_process():
    """启动进程"""
    try:
        data = request.get_json()
        process_id = data.get('process_id')

        if not process_id:
            return jsonify({"success": False, "error": "缺少进程ID"}), 400

        success = process_manager.start_process(process_id)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "启动进程失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/stop', methods=['POST'])
def stop_process():
    """停止进程"""
    try:
        data = request.get_json()
        process_id = data.get('process_id')

        if not process_id:
            return jsonify({"success": False, "error": "缺少进程ID"}), 400

        success = process_manager.stop_process(process_id)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "停止进程失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/detail', methods=['GET'])
def get_process_detail():
    """获取进程详情"""
    try:
        process_id = request.args.get('process_id')

        if not process_id:
            return jsonify({"success": False, "error": "缺少进程ID"}), 400

        process_info = process_manager.get_process(process_id)

        if not process_info:
            return jsonify({"success": False, "error": "进程不存在"}), 404

        # 读取日志
        log_file = f"logs/{process_info.mode}_{process_id}.log"
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = f.readlines()[-100:]  # 最后100行
            except Exception:
                pass

        return jsonify({
            "success": True,
            "data": {
                "process": process_info.to_dict(),
                "logs": logs
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/logs', methods=['GET'])
def get_process_logs():
    """获取进程日志"""
    try:
        process_id = request.args.get('process_id')
        lines = request.args.get('lines', 100, type=int)

        if not process_id:
            return jsonify({"success": False, "error": "缺少进程ID"}), 400

        process_info = process_manager.get_process(process_id)

        if not process_info:
            return jsonify({"success": False, "error": "进程不存在"}), 404

        # 读取日志 - 使用绝对路径
        webui_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file = os.path.join(webui_dir, "logs", f"{process_info.mode}_{process_id}.log")
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = f.readlines()[-lines:]
            except Exception as e:
                logger.error(f"读取日志文件失败: {e}")
        else:
            logger.warning(f"日志文件不存在: {log_file}")

        return jsonify({
            "success": True,
            "data": {"logs": logs}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/cleanup', methods=['POST'])
def cleanup_processes():
    """清理已停止的进程"""
    try:
        process_manager.cleanup_stopped()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/time_offset', methods=['GET'])
def calculate_time_offset():
    """计算时间偏移量"""
    try:
        from utils.time_sync import calculate_time_offset as calc_offset

        offset = calc_offset()

        if offset is None:
            return jsonify({"success": False, "error": "计算时间偏移失败"}), 500

        return jsonify({
            "success": True,
            "data": {
                "offset": offset,
                "offset_ms": offset * 1000
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/event_tickets', methods=['GET'])
def get_event_tickets():
    """通过活动ID获取票种列表"""
    try:
        event_id = request.args.get('event_id')
        env_file = request.args.get('env_file')

        if not event_id:
            return jsonify({"success": False, "error": "缺少活动ID"}), 400

        if not env_file or not os.path.exists(env_file):
            return jsonify({"success": False, "error": "环境文件不存在"}), 400

        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)

        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_ticket_type_list

        session = env_to_request_session(env)
        ticket_data = get_ticket_type_list(session, event_id, 0.5)

        if not ticket_data:
            return jsonify({"success": False, "error": "获取票种信息失败"}), 500

        # 解析票种列表
        ticket_list = []
        if "result" in ticket_data and ticket_data.get("isSuccess"):
            ticket_list = ticket_data.get("result", {}).get("ticketTypeList", [])
        else:
            ticket_list = ticket_data.get("ticketTypeList", [])

        # 格式化票种信息
        formatted_tickets = []
        for ticket in ticket_list:
            formatted_tickets.append({
                "id": ticket.get("id"),
                "name": ticket.get("ticketName") or ticket.get("name", ""),
                "square": ticket.get("square", ""),
                "price": ticket.get("ticketPrice") or ticket.get("price", 0),
                "remainder": ticket.get("remainderNum", 0),
                "purchase_limit": ticket.get("purchaseNum", 0),
                "is_real_name": ticket.get("realnameAuth") or ticket.get("isRealName", False),
                "sell_start_time": ticket.get("sellStartTime", 0),
                "sell_end_time": ticket.get("sellEndTime", 0),
                "description": ticket.get("ticketDescription", "")
            })

        return jsonify({
            "success": True,
            "data": {
                "tickets": formatted_tickets,
                "count": len(formatted_tickets)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/purchasers', methods=['GET'])
def get_purchasers():
    """获取购买人列表"""
    try:
        env_file = request.args.get('env_file')

        if not env_file or not os.path.exists(env_file):
            return jsonify({"success": False, "error": "环境文件不存在"}), 400

        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)

        from utils.env2sess import env_to_request_session
        from utils.ticket.check import get_purchaser_list

        session = env_to_request_session(env)
        purchasers = get_purchaser_list(session)

        if purchasers is None:
            return jsonify({"success": False, "error": "获取购买人列表失败，请检查是否已登录"}), 400

        # 格式化购买人信息（与TUI保持一致）
        formatted_purchasers = []
        for p in purchasers:
            formatted_purchasers.append({
                "id": p.get("id"),
                "realname": p.get("realname", ""),
                "idcard": p.get("idcard", ""),
                "mobile": p.get("mobile", ""),
                "isSelf": p.get("isSelf", False)
            })

        return jsonify({
            "success": True,
            "data": {
                "purchasers": formatted_purchasers,
                "count": len(formatted_purchasers)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/test_juliang_proxy', methods=['POST'])
def test_juliang_proxy():
    """测试巨量代理"""
    try:
        data = request.get_json()
        api_url = data.get('api_url', '')

        if not api_url:
            return jsonify({"success": False, "error": "请填写巨量代理API地址"}), 400

        # 测试获取代理
        from utils.proxy.juliang_proxy import JuliangProxyManager
        manager = JuliangProxyManager(api_url)
        proxy = manager.fetch_proxy()

        if proxy:
            return jsonify({
                "success": True,
                "data": {
                    "proxy": proxy['http'][:50] + "..." if len(proxy['http']) > 50 else proxy['http']
                }
            })
        else:
            return jsonify({"success": False, "error": "获取代理失败，请检查API地址是否正确"}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/global_config', methods=['GET'])
def get_global_config():
    """获取全局配置"""
    try:
        from utils.config import load_global_config
        config = load_global_config()
        return jsonify({"success": True, "data": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/global_config', methods=['POST'])
def save_global_config():
    """保存全局配置"""
    try:
        data = request.get_json()
        from utils.config import save_global_config as save_config
        success = save_config(data)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "保存配置失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/juliang_config', methods=['GET'])
def get_juliang_config_api():
    """获取巨量代理配置"""
    try:
        from utils.config import get_juliang_config, get_juliang_api_url
        config = get_juliang_config()
        return jsonify({
            "success": True,
            "data": {
                "api_url": config.get("api_url", ""),
                "enabled": config.get("enabled", False),
                "effective_api_url": get_juliang_api_url()  # 实际有效的API地址
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/juliang_config', methods=['POST'])
def save_juliang_config_api():
    """保存巨量代理配置"""
    try:
        data = request.get_json()
        api_url = data.get('api_url', '')
        enabled = data.get('enabled', False)

        from utils.config import set_juliang_config
        success = set_juliang_config(api_url, enabled)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "保存配置失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/proxy_config', methods=['GET'])
def get_proxy_config_api():
    """获取代理配置（支持巨量和闪臣）"""
    try:
        from utils.config import get_proxy_config, get_current_proxy_config
        config = get_proxy_config()
        current = get_current_proxy_config()
        return jsonify({
            "success": True,
            "data": {
                "type": config.get("type", "none"),
                "juliang": config.get("juliang", {}),
                "shanchen": config.get("shanchen", {}),
                "current": current
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/proxy_config', methods=['POST'])
def save_proxy_config_api():
    """保存代理配置（支持巨量和闪臣）"""
    try:
        data = request.get_json()
        proxy_type = data.get('proxy_type', 'none')
        juliang_api_url = data.get('juliang_api_url', '')
        shanchen_api_key = data.get('shanchen_api_key', '')
        shanchen_time = data.get('shanchen_time', 1)
        shanchen_count = data.get('shanchen_count', 3)
        shanchen_province = data.get('shanchen_province', '')
        shanchen_city = data.get('shanchen_city', '')

        from utils.config import set_proxy_config
        success = set_proxy_config(
            proxy_type=proxy_type,
            juliang_api_url=juliang_api_url,
            shanchen_api_key=shanchen_api_key,
            shanchen_time=shanchen_time,
            shanchen_count=shanchen_count,
            shanchen_province=shanchen_province,
            shanchen_city=shanchen_city
        )

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "保存配置失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/test_proxy', methods=['POST'])
def test_proxy():
    """测试代理（支持巨量和闪臣）"""
    try:
        data = request.get_json()
        proxy_type = data.get('proxy_type', '')
        config = data.get('config', {})

        if proxy_type == 'juliang':
            api_url = config.get('api_url', '')
            if not api_url:
                return jsonify({"success": False, "error": "请填写巨量代理API地址"}), 400

            from utils.proxy.juliang_proxy import JuliangProxyManager
            manager = JuliangProxyManager(api_url)
            proxy = manager.fetch_proxy()

        elif proxy_type == 'shanchen':
            api_key = config.get('api_key', '')
            time_minutes = config.get('time_minutes', 1)
            count = config.get('count', 1)
            province = config.get('province', '')
            city = config.get('city', '')

            if not api_key:
                return jsonify({"success": False, "error": "请填写闪臣代理API密钥"}), 400

            from utils.proxy.shanchen_proxy import ShanchenProxyManager
            manager = ShanchenProxyManager(api_key, time_minutes, count, province, city)
            proxy = manager.fetch_proxy()
        else:
            return jsonify({"success": False, "error": "未知的代理类型"}), 400

        if proxy:
            return jsonify({
                "success": True,
                "data": {
                    "proxy": proxy['http'][:50] + "..." if len(proxy['http']) > 50 else proxy['http']
                }
            })
        else:
            return jsonify({"success": False, "error": "获取代理失败，请检查配置是否正确"}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/yhchat_config', methods=['GET'])
def get_yhchat_config_api():
    """获取云湖配置"""
    try:
        from utils.config import get_yhchat_config
        config = get_yhchat_config()
        return jsonify({
            "success": True,
            "data": config
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@process_bp.route('/yhchat_config', methods=['POST'])
def save_yhchat_config_api():
    """保存云湖配置"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        user_id = data.get('user_id', '')
        enabled = data.get('enabled', False)

        from utils.config import set_yhchat_config
        success = set_yhchat_config(token, user_id, enabled)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "保存配置失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
