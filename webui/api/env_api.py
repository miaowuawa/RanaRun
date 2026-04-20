"""
环境管理API
"""
import os
import json
import re
from flask import Blueprint, jsonify, request

env_bp = Blueprint('env', __name__)


def get_env_files():
    """获取所有环境文件"""
    env_files = []
    try:
        for file in os.listdir("."):
            if file.startswith("environment_") and file.endswith(".json"):
                env_files.append(file)
    except Exception as e:
        print(f"读取文件列表失败: {e}")
    return sorted(env_files)


@env_bp.route('/list', methods=['GET'])
def list_env():
    """获取环境文件列表"""
    try:
        files = get_env_files()
        env_list = []

        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    env = json.load(f)

                # 提取基本信息
                name = file.replace("environment_", "").replace(".json", "")
                proxy = env.get("proxy", "")
                exit_ip = env.get("exit_ip", "")

                # 获取header信息
                header = env.get("header", {})
                device_info = {
                    "equipmentType": header.get("equipmentType", ""),
                    "appVersion": header.get("appVersion", ""),
                }

                # 获取cookie数量
                cookie = env.get("cookie", {})
                cookie_count = len(cookie) if isinstance(cookie, dict) else 0

                env_list.append({
                    "file": file,
                    "name": name,
                    "proxy": proxy,
                    "exit_ip": exit_ip,
                    "device_info": device_info,
                    "cookie_count": cookie_count,
                    "has_login": cookie_count > 0
                })
            except Exception as e:
                env_list.append({
                    "file": file,
                    "name": file.replace("environment_", "").replace(".json", ""),
                    "error": str(e)
                })

        return jsonify({
            "success": True,
            "data": env_list
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/detail', methods=['GET'])
def get_env_detail():
    """获取环境详情"""
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({"success": False, "error": "缺少文件名参数"}), 400

    try:
        file_path = os.path.join(".", file_name)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        with open(file_path, "r", encoding="utf-8") as f:
            env = json.load(f)

        return jsonify({
            "success": True,
            "data": env
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/create', methods=['POST'])
def create_env():
    """创建新环境"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        proxy = data.get('proxy', '').strip()
        exit_ip = data.get('exit_ip', '').strip()

        if not name:
            return jsonify({"success": False, "error": "环境名称不能为空"}), 400

        # 验证名称格式
        if not re.match(r'^[a-zA-Z0-9_\-]+$', name):
            return jsonify({"success": False, "error": "名称只能包含字母、数字、下划线和横线"}), 400

        # 检查是否已存在
        file_name = f"environment_{name}.json"
        if os.path.exists(file_name):
            return jsonify({"success": False, "error": "该环境名称已存在"}), 400

        # 验证IP格式
        if exit_ip:
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, exit_ip):
                return jsonify({"success": False, "error": "IP格式不正确"}), 400

        # 创建环境
        from utils.env2sess import generate_environment_file
        proxy_setting = proxy if proxy else None
        exit_ip_setting = exit_ip if exit_ip else None

        file_path = generate_environment_file(name, proxy_setting, exit_ip_setting)

        return jsonify({
            "success": True,
            "data": {"file": file_path, "name": name}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/update', methods=['POST'])
def update_env():
    """更新环境配置"""
    try:
        data = request.get_json()
        file_name = data.get('file')
        config = data.get('config', {})

        if not file_name:
            return jsonify({"success": False, "error": "缺少文件名"}), 400

        file_path = os.path.join(".", file_name)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        # 读取现有配置
        with open(file_path, "r", encoding="utf-8") as f:
            env = json.load(f)

        # 更新配置
        if "proxy" in config:
            if config["proxy"]:
                env["proxy"] = config["proxy"]
            elif "proxy" in env:
                del env["proxy"]

        if "exit_ip" in config:
            if config["exit_ip"]:
                # 验证IP格式
                ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
                if not re.match(ip_pattern, config["exit_ip"]):
                    return jsonify({"success": False, "error": "IP格式不正确"}), 400
                env["exit_ip"] = config["exit_ip"]
            elif "exit_ip" in env:
                del env["exit_ip"]

        if "header" in config:
            env["header"].update(config["header"])

        # 保存
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(env, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/delete', methods=['POST'])
def delete_env():
    """删除环境"""
    try:
        data = request.get_json()
        file_name = data.get('file')

        if not file_name:
            return jsonify({"success": False, "error": "缺少文件名"}), 400

        file_path = os.path.join(".", file_name)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        os.remove(file_path)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/test_exit_ip', methods=['POST'])
def test_exit_ip():
    """测试出口IP"""
    try:
        data = request.get_json()
        file_name = data.get('file')

        if not file_name:
            return jsonify({"success": False, "error": "缺少文件名"}), 400

        file_path = os.path.join(".", file_name)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        with open(file_path, "r", encoding="utf-8") as f:
            env = json.load(f)

        exit_ip = env.get("exit_ip", "")
        if not exit_ip:
            return jsonify({"success": False, "error": "该环境未设置出口IP"}), 400

        # 创建会话并测试
        from utils.env2sess import env_to_request_session
        session = env_to_request_session(env)

        # 测试请求
        response = session.get("https://httpbin.org/ip", timeout=10)
        result = response.json()
        actual_ip = result.get("origin", "未知")

        success = exit_ip in actual_ip

        return jsonify({
            "success": True,
            "data": {
                "configured_ip": exit_ip,
                "actual_ip": actual_ip,
                "test_passed": success
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/refresh_cookie', methods=['POST'])
def refresh_cookie():
    """刷新Cookie"""
    try:
        data = request.get_json()
        file_name = data.get('file')

        if not file_name:
            return jsonify({"success": False, "error": "缺少文件名"}), 400

        file_path = os.path.join(".", file_name)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        with open(file_path, "r", encoding="utf-8") as f:
            env = json.load(f)

        from utils.env2sess import env_to_request_session
        session = env_to_request_session(env)

        if session.cookies:
            try:
                env["cookie"] = dict(session.cookies)
            except Exception:
                cookie_dict = {}
                for cookie in session.cookies:
                    cookie_dict[cookie.name] = cookie.value
                env["cookie"] = cookie_dict

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(env, f, ensure_ascii=False, indent=2)

            return jsonify({
                "success": True,
                "data": {"cookie_count": len(env["cookie"])}
            })
        else:
            return jsonify({"success": False, "error": "未获取到新的Cookie"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/send_sms', methods=['POST'])
def send_sms():
    """发送登录验证码"""
    try:
        data = request.get_json()
        file_name = data.get('file')
        country = data.get('country', '86')
        phone = data.get('phone', '').strip()

        if not file_name:
            return jsonify({"success": False, "error": "缺少文件名"}), 400

        if not phone:
            return jsonify({"success": False, "error": "请输入手机号"}), 400

        file_path = os.path.join(".", file_name)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        with open(file_path, "r", encoding="utf-8") as f:
            env = json.load(f)

        # 检查用户是否存在
        from utils.user.check import check_if_user_exists
        exists = check_if_user_exists(env, country, phone)

        if not exists:
            return jsonify({"success": False, "error": "用户不存在，请先去ALLCPP注册账号"}), 400

        # 发送验证码
        from utils.user.login import get_login_code
        success, message = get_login_code(env, country, phone)

        if success:
            return jsonify({"success": True, "message": "验证码已发送"})
        else:
            return jsonify({"success": False, "error": message}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/login', methods=['POST'])
def login_account():
    """登录账号"""
    try:
        data = request.get_json()
        file_name = data.get('file')
        country = data.get('country', '86')
        phone = data.get('phone', '').strip()
        code = data.get('code', '').strip()

        if not file_name:
            return jsonify({"success": False, "error": "缺少文件名"}), 400

        if not phone or not code:
            return jsonify({"success": False, "error": "请输入手机号和验证码"}), 400

        file_path = os.path.join(".", file_name)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        with open(file_path, "r", encoding="utf-8") as f:
            env = json.load(f)

        # 执行登录
        from utils.user.login import user_login_sms
        session, success, message = user_login_sms(env, country, phone, code)

        if success:
            # 保存cookie
            if session.cookies:
                try:
                    env["cookie"] = dict(session.cookies)
                except Exception:
                    cookie_dict = {}
                    for cookie in session.cookies:
                        cookie_dict[cookie.name] = cookie.value
                    env["cookie"] = cookie_dict

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(env, f, ensure_ascii=False, indent=2)

            return jsonify({
                "success": True,
                "message": "登录成功",
                "data": {"cookie_count": len(env.get("cookie", {}))}
            })
        else:
            return jsonify({"success": False, "error": message}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@env_bp.route('/update_header', methods=['POST'])
def update_header():
    """更新Header配置"""
    try:
        data = request.get_json()
        file_name = data.get('file')
        header_updates = data.get('header', {})

        if not file_name:
            return jsonify({"success": False, "error": "缺少文件名"}), 400

        file_path = os.path.join(".", file_name)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        with open(file_path, "r", encoding="utf-8") as f:
            env = json.load(f)

        # 更新header
        if "header" not in env:
            env["header"] = {}

        env["header"].update(header_updates)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(env, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True, "message": "Header已更新"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
