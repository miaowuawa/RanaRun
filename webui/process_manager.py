"""
抢票进程管理器
用于管理多个抢票进程的生命周期
"""
import multiprocessing
import time
import json
import os
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ProcessInfo:
    """进程信息"""
    id: str
    name: str
    mode: str  # 'presale' 或 'resale'
    status: str  # 'running', 'stopped', 'error'
    pid: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    message: str = ""
    config: Dict = None

    def to_dict(self):
        return asdict(self)


class SnipeProcessManager:
    """抢票进程管理器"""

    def __init__(self):
        self.processes: Dict[str, ProcessInfo] = {}
        self._process_objects: Dict[str, multiprocessing.Process] = {}
        self._lock = multiprocessing.Lock()

    def create_process(self, name: str, mode: str, config: Dict) -> str:
        """创建新的抢票进程"""
        import uuid
        process_id = str(uuid.uuid4())[:8]

        process_info = ProcessInfo(
            id=process_id,
            name=name,
            mode=mode,
            status='starting',
            start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            config=config
        )

        with self._lock:
            self.processes[process_id] = process_info

        return process_id

    def start_process(self, process_id: str) -> bool:
        """启动抢票进程"""
        if process_id not in self.processes:
            return False

        process_info = self.processes[process_id]

        try:
            if process_info.mode == 'presale':
                from webui.workers.presale_worker import presale_worker
                target = presale_worker
            else:
                from webui.workers.resale_worker import resale_worker
                target = resale_worker

            # 创建进程
            p = multiprocessing.Process(
                target=target,
                args=(process_info.config, process_info.id),
                daemon=False  # 非守护进程，允许子进程在主进程退出后继续运行
            )
            p.start()

            with self._lock:
                self._process_objects[process_id] = p
                process_info.pid = p.pid
                process_info.status = 'running'

            return True
        except Exception as e:
            process_info.status = 'error'
            process_info.message = str(e)
            return False

    def stop_process(self, process_id: str) -> bool:
        """停止抢票进程"""
        if process_id not in self.processes:
            return False

        process_info = self.processes[process_id]

        try:
            if process_id in self._process_objects:
                p = self._process_objects[process_id]
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=5)
                    if p.is_alive():
                        p.kill()

                del self._process_objects[process_id]

            process_info.status = 'stopped'
            process_info.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
        except Exception as e:
            process_info.message = str(e)
            return False

    def get_process(self, process_id: str) -> Optional[ProcessInfo]:
        """获取进程信息"""
        return self.processes.get(process_id)

    def get_all_processes(self) -> List[ProcessInfo]:
        """获取所有进程信息"""
        import os

        # 获取webui目录路径
        webui_dir = os.path.dirname(os.path.abspath(__file__))

        # 更新运行中进程的状态
        for process_id, process_info in self.processes.items():
            if process_info.status == 'running' and process_id in self._process_objects:
                p = self._process_objects[process_id]
                if not p.is_alive():
                    # 检查日志文件判断是否成功 - 使用绝对路径
                    log_file = os.path.join(webui_dir, "logs", f"{process_info.mode}_{process_id}.log")

                    log_content = None
                    if os.path.exists(log_file):
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_content = f.read()
                        except:
                            pass

                    if log_content:
                        # 检查成功关键字 - 必须包含"抢票成功"或"下单成功"
                        # 注意：不能仅用"成功"，因为"抢票失败"也包含这两个字
                        if '抢票成功' in log_content or '下单成功' in log_content:
                            process_info.status = 'success'
                            process_info.message = '抢票成功'
                        else:
                            process_info.status = 'stopped'
                    else:
                        process_info.status = 'stopped'

                    process_info.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # 进程仍在运行，检查是否在等待中
                    log_file = os.path.join(webui_dir, "logs", f"{process_info.mode}_{process_id}.log")
                    if os.path.exists(log_file):
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_content = f.read()
                                # 检查是否有等待中状态
                                if '[状态] 等待中' in log_content:
                                    # 提取剩余时间
                                    import re
                                    match = re.search(r'还剩 ([\d.]+) 秒', log_content)
                                    if match:
                                        process_info.message = f'等待开售中，还剩 {match.group(1)} 秒'
                                    else:
                                        process_info.message = '等待开售中'
                                elif '[状态] 等待结束' in log_content:
                                    process_info.message = '正在抢票中'
                        except:
                            pass

        return list(self.processes.values())

    def cleanup_stopped(self):
        """清理已停止的进程"""
        to_remove = []
        for process_id, process_info in self.processes.items():
            if process_info.status in ['stopped', 'error']:
                to_remove.append(process_id)

        for process_id in to_remove:
            if process_id in self._process_objects:
                del self._process_objects[process_id]
            del self.processes[process_id]


# 全局进程管理器实例
process_manager = SnipeProcessManager()
