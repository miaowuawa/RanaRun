"""
WebUI Flask应用
"""
import os
import sys
import json
import logging
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webui.process_manager import process_manager
from webui.api.env_api import env_bp
from webui.api.ticket_api import ticket_bp
from webui.api.process_api import process_bp
from webui.api.order_api import order_bp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """创建Flask应用"""
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )

    # 启用CORS
    CORS(app)

    # 注册蓝图
    app.register_blueprint(env_bp, url_prefix='/api/env')
    app.register_blueprint(ticket_bp, url_prefix='/api/ticket')
    app.register_blueprint(process_bp, url_prefix='/api/process')
    app.register_blueprint(order_bp, url_prefix='/api/order')

    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')

    @app.route('/api/status')
    def status():
        """获取系统状态"""
        return jsonify({
            'status': 'ok',
            'version': '1.0.0',
            'process_count': len(process_manager.get_all_processes())
        })

    @app.route('/api/static/<path:filename>')
    def static_files(filename):
        """提供静态文件"""
        from flask import send_from_directory
        webui_dir = os.path.dirname(os.path.abspath(__file__))
        return send_from_directory(webui_dir, filename)

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return jsonify({'error': 'Internal server error'}), 500

    return app


def run_webui(host='0.0.0.0', port=5000, debug=False):
    """运行WebUI"""
    app = create_app()
    logger.info(f"Starting WebUI on {host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='RanaRun WebUI')
    parser.add_argument('--host', default='0.0.0.0', help='绑定IP地址')
    parser.add_argument('--port', type=int, default=5000, help='绑定端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')

    args = parser.parse_args()

    run_webui(host=args.host, port=args.port, debug=args.debug)
