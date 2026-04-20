#!/usr/bin/env python3
"""
RanaRun WebUI 服务器启动脚本
"""
import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webui.app import run_webui


def main():
    parser = argparse.ArgumentParser(
        description='RanaRun WebUI - ALLCPP购票助手Web界面',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python webui_server.py                    # 默认启动，绑定 0.0.0.0:5000
  python webui_server.py --host 127.0.0.1   # 只绑定本地地址
  python webui_server.py --port 8080        # 使用8080端口
  python webui_server.py --debug            # 调试模式
        """
    )

    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='绑定的IP地址 (默认: 0.0.0.0，表示所有接口)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='绑定的端口号 (默认: 5000)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式 (自动重载代码，显示详细错误)'
    )

    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    RanaRun WebUI 服务器                      ║
╠══════════════════════════════════════════════════════════════╣
║  访问地址: http://{args.host}:{args.port:<5}                    ║
║  调试模式: {'开启' if args.debug else '关闭':<10}                      ║
╚══════════════════════════════════════════════════════════════╝

按 Ctrl+C 停止服务器
""")

    try:
        run_webui(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        sys.exit(0)


if __name__ == '__main__':
    main()
