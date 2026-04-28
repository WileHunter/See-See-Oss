#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSS 文件浏览器主程序
"""

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from gui.main_window import MainWindow
from utils.config_loader import ConfigLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger('urllib3').setLevel(logging.WARNING)


def main():
    # 加载配置（找不到文件时使用内置默认值，不再抛异常）
    try:
        config = ConfigLoader.load_config()
    except FileNotFoundError:
        config = _default_config()

    app = QApplication(sys.argv)
    app.setApplicationName(config.get('ui', {}).get('title', 'OSS 文件浏览器'))
    
    # 设置应用程序图标
    icon_path = os.path.join(os.path.dirname(__file__), 'facvion.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # ⚠️  不在这里设置全局样式表：
    # MainWindow 内部已通过 setStyleSheet(_APP_STYLE) 管理自己的样式，
    # 若此处调用 qt_material 或 app.setStyleSheet() 会整体覆盖它。

    window = MainWindow(config)
    
    # 为主窗口也设置图标
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    
    window.show()
    sys.exit(app.exec_())


def _default_config() -> dict:
    """内置默认配置，config.yaml 缺失时使用。"""
    return {
        'ui': {
            'title': 'OSS 文件浏览器',
            'window_size': [1280, 820],
        },
        'preview': {
            'cache_dir': './cache',
            'thumbnail_size': [200, 200],
            'page_size': 20,
        },
        'proxy': {
            'enabled': False,
            'type': 'http',
            'host': '127.0.0.1',
            'port': 7890,
            'username': '',
            'password': '',
        },
    }


if __name__ == '__main__':
    main()