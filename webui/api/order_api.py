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

        if not env_file or not os.path.exists(env_file):
            return jsonify({"success": False, "error": "环境文件不存在"}), 400

        if not ticket_id:
            return jsonify({"success": False, "error": "缺少票种ID"}), 400

        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)

        from utils.env2sess import env_to_request_session
        from utils.ticket.purchase import submit_ticket_order_with_details

        session = env_to_request_session(env)

        # 处理购买者ID
        if order_mode == 'combined':
            # 合并模式：所有购买者一起下单
            result, retry, should_stop, details = submit_ticket_order_with_details(session, ticket_id, purchaser_ids, debug_mode, count)
            return jsonify({
                "success": True,
                "data": {
                    "result": result,
                    "retry": retry,
                    "should_stop": should_stop,
                    "mode": "combined",
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
                result, retry, should_stop, details = submit_ticket_order_with_details(session, ticket_id, purchaser_id, debug_mode, 1)
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
