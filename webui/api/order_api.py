"""
下单测试API
"""
import os
import sys
import json
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

order_bp = Blueprint('order', __name__)


@order_bp.route('/test', methods=['POST'])
def test_order():
    """测试下单"""
    try:
        data = request.get_json()
        env_file = data.get('env_file')
        ticket_id = data.get('ticket_id')
        purchaser_ids = data.get('purchaser_ids', '')
        count = data.get('count', 1)
        debug_mode = data.get('debug_mode', False)
        order_mode = data.get('order_mode', 'separate')  # 'separate' 分离模式, 'combined' 合并模式
        use_juliang = data.get('use_juliang', False)  # 是否使用巨量代理

        if not env_file or not os.path.exists(env_file):
            return jsonify({"success": False, "error": "环境文件不存在"}), 400

        if not ticket_id:
            return jsonify({"success": False, "error": "缺少票种ID"}), 400

        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)

        from utils.env2sess import env_to_request_session
        from utils.ticket.purchase import submit_ticket_order_with_details

        session = env_to_request_session(env)

        # 如果启用巨量代理，获取代理URL
        juliang_api_url = ""
        if use_juliang:
            from utils.config import get_juliang_api_url
            juliang_api_url = get_juliang_api_url()
            if not juliang_api_url:
                return jsonify({"success": False, "error": "巨量代理未配置或已禁用，请先在进程管理页面配置"}), 400

        # 处理购买者ID
        if order_mode == 'combined':
            # 合并模式：所有购买者一起下单
            result, retry, should_stop, details = submit_ticket_order_with_details(session, ticket_id, purchaser_ids, debug_mode, count, None, juliang_api_url)
            return jsonify({
                "success": True,
                "data": {
                    "result": result,
                    "retry": retry,
                    "should_stop": should_stop,
                    "mode": "combined",
                    "use_juliang": use_juliang,
                    "pay_url": details.get("pay_url"),
                    "order_info": details.get("order_info"),
                    "message": details.get("message")
                }
            })
        else:
            # 分离模式：每个购买者单独下单
            purchaser_list = [p.strip() for p in purchaser_ids.split(',') if p.strip()]
            results = []

            for purchaser_id in purchaser_list:
                result, retry, should_stop, details = submit_ticket_order_with_details(session, ticket_id, purchaser_id, debug_mode, 1, None, juliang_api_url)
                results.append({
                    "purchaser_id": purchaser_id,
                    "result": result,
                    "retry": retry,
                    "should_stop": should_stop,
                    "pay_url": details.get("pay_url"),
                    "order_info": details.get("order_info"),
                    "message": details.get("message")
                })

                if should_stop:
                    break

            return jsonify({
                "success": True,
                "data": {
                    "results": results,
                    "mode": "separate",
                    "use_juliang": use_juliang,
                    "total": len(purchaser_list),
                    "success_count": sum(1 for r in results if r["result"])
                }
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@order_bp.route('/purchasers', methods=['POST'])
def get_purchasers():
    """获取购买人列表"""
    try:
        data = request.get_json()
        env_file = data.get('env_file')

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


@order_bp.route('/test_proxy_latency', methods=['POST'])
def test_proxy_latency():
    """测试代理IP访问cp.allcpp.cn的延迟"""
    try:
        data = request.get_json()
        use_juliang = data.get('use_juliang', False)

        import requests
        import time

        # 准备session
        session = requests.Session()

        # 如果使用巨量代理
        proxy_info = None
        if use_juliang:
            from utils.config import get_juliang_api_url
            from utils.proxy.juliang_proxy import get_juliang_manager

            api_url = get_juliang_api_url()
            if not api_url:
                return jsonify({"success": False, "error": "巨量代理未配置或已禁用"}), 400

            # 获取代理
            manager = get_juliang_manager(api_url)
            proxy = manager.fetch_proxy()
            if not proxy:
                return jsonify({"success": False, "error": "获取巨量代理失败"}), 400

            session.proxies = proxy
            proxy_info = proxy.get('http', '')

        # 测试访问cp.allcpp.cn
        url = "https://cp.allcpp.cn/"
        timeout = 10

        start_time = time.time()
        status_code = None
        error_msg = None

        try:
            response = session.get(url, timeout=timeout, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
            })
            elapsed_ms = int((time.time() - start_time) * 1000)
            status_code = response.status_code

            # 不管返回什么状态码都算成功，只要能连上
            return jsonify({
                "success": True,
                "data": {
                    "use_proxy": use_juliang,
                    "proxy": proxy_info[:50] + "..." if proxy_info and len(proxy_info) > 50 else proxy_info,
                    "url": url,
                    "latency_ms": elapsed_ms,
                    "status_code": status_code,
                    "message": f"连接成功，延迟 {elapsed_ms}ms (HTTP {status_code})"
                }
            })
        except requests.exceptions.Timeout:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return jsonify({
                "success": True,  # 超时也算有响应，只是慢
                "data": {
                    "use_proxy": use_juliang,
                    "proxy": proxy_info[:50] + "..." if proxy_info and len(proxy_info) > 50 else proxy_info,
                    "url": url,
                    "latency_ms": elapsed_ms,
                    "status_code": "TIMEOUT",
                    "message": f"请求超时 (>10秒)，耗时 {elapsed_ms}ms"
                }
            })
        except requests.exceptions.ProxyError as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return jsonify({
                "success": True,  # 代理错误也算有响应
                "data": {
                    "use_proxy": use_juliang,
                    "proxy": proxy_info[:50] + "..." if proxy_info and len(proxy_info) > 50 else proxy_info,
                    "url": url,
                    "latency_ms": elapsed_ms,
                    "status_code": "PROXY_ERROR",
                    "message": f"代理错误，耗时 {elapsed_ms}ms: {str(e)[:100]}"
                }
            })
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return jsonify({
                "success": True,  # 任何响应都算成功
                "data": {
                    "use_proxy": use_juliang,
                    "proxy": proxy_info[:50] + "..." if proxy_info and len(proxy_info) > 50 else proxy_info,
                    "url": url,
                    "latency_ms": elapsed_ms,
                    "status_code": "ERROR",
                    "message": f"请求异常，耗时 {elapsed_ms}ms: {str(e)[:100]}"
                }
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
