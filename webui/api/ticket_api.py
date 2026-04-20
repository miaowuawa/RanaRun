"""
票务查询API
"""
import os
import sys
import json
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ticket_bp = Blueprint('ticket', __name__)


# 城市列表
CITIES = [
    {"code": "", "name": "全部城市"},
    {"code": "110100", "name": "北京"},
    {"code": "310100", "name": "上海"},
    {"code": "440100", "name": "广州"},
    {"code": "440300", "name": "深圳"},
    {"code": "330100", "name": "杭州"},
    {"code": "320100", "name": "南京"},
    {"code": "420100", "name": "武汉"},
    {"code": "510100", "name": "成都"},
    {"code": "500000", "name": "重庆"},
    {"code": "610100", "name": "西安"},
    {"code": "370100", "name": "济南"},
    {"code": "350100", "name": "福州"},
    {"code": "210100", "name": "沈阳"},
    {"code": "220100", "name": "长春"},
    {"code": "230100", "name": "哈尔滨"},
    {"code": "410100", "name": "郑州"},
    {"code": "430100", "name": "长沙"},
    {"code": "340100", "name": "合肥"},
    {"code": "320200", "name": "苏州"},
    {"code": "330200", "name": "宁波"},
    {"code": "350200", "name": "厦门"},
    {"code": "370200", "name": "青岛"},
    {"code": "440600", "name": "佛山"},
    {"code": "441900", "name": "东莞"},
    {"code": "450100", "name": "南宁"},
    {"code": "530100", "name": "昆明"},
    {"code": "520100", "name": "贵阳"},
    {"code": "360100", "name": "南昌"},
    {"code": "130100", "name": "石家庄"},
    {"code": "140100", "name": "太原"},
    {"code": "150100", "name": "呼和浩特"},
    {"code": "620100", "name": "兰州"},
    {"code": "630100", "name": "西宁"},
    {"code": "640100", "name": "银川"},
    {"code": "650100", "name": "乌鲁木齐"},
    {"code": "540100", "name": "拉萨"},
    {"code": "460100", "name": "海口"},
    {"code": "330300", "name": "温州"},
    {"code": "320400", "name": "常州"},
    {"code": "320500", "name": "南通"},
    {"code": "320600", "name": "徐州"},
    {"code": "320700", "name": "连云港"},
    {"code": "320800", "name": "淮安"},
    {"code": "320900", "name": "盐城"},
    {"code": "321000", "name": "扬州"},
    {"code": "321100", "name": "镇江"},
    {"code": "321200", "name": "泰州"},
    {"code": "321300", "name": "宿迁"},
    {"code": "330400", "name": "嘉兴"},
    {"code": "330500", "name": "湖州"},
    {"code": "330600", "name": "绍兴"},
    {"code": "330700", "name": "金华"},
    {"code": "330800", "name": "衢州"},
    {"code": "330900", "name": "舟山"},
    {"code": "331000", "name": "台州"},
    {"code": "331100", "name": "丽水"}
]


@ticket_bp.route('/cities', methods=['GET'])
def get_cities():
    """获取城市列表"""
    return jsonify({
        "success": True,
        "data": CITIES
    })


@ticket_bp.route('/search', methods=['GET'])
def search_events():
    """搜索活动"""
    try:
        keyword = request.args.get('keyword', '')
        city = request.args.get('city', '')
        env_file = request.args.get('env_file', '')
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 20, type=int)

        if not keyword:
            return jsonify({"success": False, "error": "缺少关键词"}), 400

        # 如果提供了环境文件，使用环境的session
        if env_file and os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                env = json.load(f)
            from utils.env2sess import env_to_request_session
            session = env_to_request_session(env)
            results = search_event_with_session(session, keyword, city, page, size)
        else:
            # 没有环境文件时使用默认方式
            from utils.event.search import search_event_allcpp
            results = search_event_allcpp(keyword, city, page, size)

        return jsonify({
            "success": True,
            "data": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def search_event_with_session(session, keyword: str, city: str = "", page: int = 1, size: int = 20) -> list:
    """使用session搜索ALLCPP活动"""
    try:
        from utils.urls import BASE_URL_WEB
        url = f"{BASE_URL_WEB}allcpp/event/eventMainListV2.do"
        params = {
            "city": city if city else "",
            "isWannaGo": 0,
            "keyword": keyword if keyword else "",
            "pageNo": page,
            "pageSize": size,
            "sort": 1
        }

        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()

        result = response.json()

        if result.get("isSuccess"):
            # API返回的是 list 字段，不是 eventMainList
            event_list = result.get("result", {}).get("list", [])
            return event_list
        else:
            return []
    except Exception as e:
        print(f"搜索活动失败: {e}")
        return []


@ticket_bp.route('/event_detail', methods=['GET'])
def get_event_detail():
    """获取活动详情"""
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
                "event": ticket_data.get("ticketMain", {}),
                "tickets": formatted_tickets
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@ticket_bp.route('/purchasers', methods=['GET'])
def get_purchasers():
    """获取购买人列表"""
    try:
        env_file = request.args.get('env_file')

        if not env_file or not os.path.exists(env_file):
            return jsonify({"success": False, "error": "环境文件不存在"}), 400

        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)

        from utils.env2sess import env_to_request_session
        from utils.user.purchaser import get_purchaser_list

        session = env_to_request_session(env)
        purchasers = get_purchaser_list(session)

        return jsonify({
            "success": True,
            "data": purchasers
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
