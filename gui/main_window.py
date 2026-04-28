#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口 —— 重构版
商业化 UI / 内存缩略图 / 防抖搜索 / 无阻塞并发
"""

import os
import logging

from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QSize, QTimer,
                          QPropertyAnimation, QEasingCurve)
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette, QCursor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QListWidget, QListWidgetItem,
    QProgressBar, QStatusBar, QFrame, QSplitter, QScrollArea,
    QMessageBox, QComboBox, QSizePolicy, QToolButton, QTextBrowser,
    QMenu, QAction, QCheckBox, QSpacerItem, QDialog, QDialogButtonBox,
    QGroupBox, QFormLayout,
)

from utils.oss_client import OSSClient
from utils.file_preview import FilePreview
from utils.thumbnail_manager import ThumbnailManager
from utils.config_loader import ConfigLoader
from gui.image_viewer import ImageViewer

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# 全局样式表
# ──────────────────────────────────────────────────────────────────────────────
_APP_STYLE = """
/* ── 基础 ─────────────────────────────────────── */
* { font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif; }

QMainWindow, QWidget { background: #F2F4F7; }
QWidget#surface { background: #FFFFFF; border-radius: 10px; }

/* ── 顶栏 ─────────────────────────────────────── */
QWidget#topbar {
    background: #FFFFFF;
    border-bottom: 1px solid #E4E7ED;
}

/* ── 输入框 ───────────────────────────────────── */
QLineEdit {
    height: 38px;
    padding: 0 12px;
    border: 1.5px solid #DCDFE6;
    border-radius: 8px;
    background: #F5F7FA;
    color: #303133;
    font-size: 13px;
    selection-background-color: #409EFF;
}
QLineEdit:focus {
    border-color: #409EFF;
    background: #FFFFFF;
}
QLineEdit:hover { border-color: #C0C4CC; }

/* ── 搜索框 ───────────────────────────────────── */
QLineEdit#searchBox {
    height: 34px;
    padding-left: 34px;
    border-radius: 17px;
    background: #F0F2F5;
    border: 1.5px solid transparent;
}
QLineEdit#searchBox:focus {
    border-color: #409EFF;
    background: white;
}

/* ── 主按钮 ───────────────────────────────────── */
QPushButton#primary {
    height: 38px;
    padding: 0 20px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                                stop:0 #409EFF, stop:1 #2980D9);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                                stop:0 #53AAFF, stop:1 #3590EA);
}
QPushButton#primary:pressed {
    background: #2471C9;
}
QPushButton#primary:disabled { background: #C0D8F0; color: #96B8D8; }

/* ── 幽灵按钮 ─────────────────────────────────── */
QPushButton#ghost {
    height: 34px;
    padding: 0 14px;
    background: transparent;
    color: #606266;
    border: 1.5px solid #DCDFE6;
    border-radius: 7px;
    font-size: 12px;
}
QPushButton#ghost:hover { border-color: #409EFF; color: #409EFF; background: #ECF5FF; }
QPushButton#ghost:pressed { background: #D9ECFF; }

/* ── 视图切换按钮 ─────────────────────────────── */
QPushButton#viewToggle {
    width: 36px; height: 36px;
    border: 1.5px solid #DCDFE6;
    border-radius: 7px;
    background: white;
    font-size: 16px;
    padding: 0;
}
QPushButton#viewToggle:hover { border-color: #409EFF; background: #ECF5FF; }
QPushButton#viewToggle[active="true"] {
    border-color: #409EFF;
    background: #ECF5FF;
    color: #409EFF;
}

/* ── 分页按钮 ─────────────────────────────────── */
QPushButton#pageBtn {
    min-width: 32px; height: 32px;
    padding: 0 10px;
    border: 1.5px solid #DCDFE6;
    border-radius: 6px;
    background: white;
    font-size: 13px;
    color: #606266;
}
QPushButton#pageBtn:hover { border-color: #409EFF; color: #409EFF; }
QPushButton#pageBtn:disabled { color: #C0C4CC; border-color: #E4E7ED; }
QPushButton#pageBtn[active="true"] {
    background: #409EFF;
    border-color: #409EFF;
    color: white;
    font-weight: 600;
}
QLineEdit#gotoInput {
    height: 32px;
    padding: 0 8px;
    border: 1.5px solid #DCDFE6;
    border-radius: 6px;
    background: white;
    color: #303133;
    font-size: 13px;
    text-align: center;
}
QLineEdit#gotoInput:focus {
    border-color: #409EFF;
}

/* ── 列表模式文件项 ───────────────────────────── */
QListWidget {
    background: transparent;
    border: none;
    outline: none;
    padding: 4px;
}
QListWidget::item {
    height: 44px;
    border-radius: 7px;
    padding: 0 12px;
    color: #303133;
    font-size: 13px;
}
QListWidget::item:hover { background: #F0F4FF; }
QListWidget::item:selected {
    background: #E8F0FE;
    color: #1967D2;
}

/* ── 进度条 ───────────────────────────────────── */
QProgressBar {
    height: 3px;
    border: none;
    border-radius: 1px;
    background: #E4E7ED;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                                stop:0 #409EFF, stop:1 #36CFC9);
    border-radius: 1px;
}

/* ── 状态栏 ───────────────────────────────────── */
QStatusBar {
    background: #FAFBFC;
    border-top: 1px solid #E4E7ED;
    color: #909399;
    font-size: 12px;
    padding: 0 12px;
}

/* ── 下拉框 ───────────────────────────────────── */
QComboBox {
    height: 32px;
    padding: 0 8px;
    border: 1.5px solid #DCDFE6;
    border-radius: 6px;
    background: white;
    font-size: 12px;
    color: #606266;
}
QComboBox:hover { border-color: #C0C4CC; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    border: 1px solid #DCDFE6;
    border-radius: 6px;
    background: white;
    selection-background-color: #F0F4FF;
    selection-color: #409EFF;
}

/* ── 滚动条 ───────────────────────────────────── */
QScrollBar:vertical {
    width: 6px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #C8CACE;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #A0A4AB; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    height: 6px;
    background: transparent;
}
QScrollBar::handle:horizontal {
    background: #C8CACE;
    border-radius: 3px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


# ──────────────────────────────────────────────────────────────────────────────
# 缩略图卡片
# ──────────────────────────────────────────────────────────────────────────────
class ThumbnailCard(QFrame):
    """单个图片/文件卡片，支持 hover、选中高亮、点击信号。"""

    clicked = pyqtSignal(dict, int)        # (file_info, index_in_all_files)
    double_clicked = pyqtSignal(dict, int)

    _STYLE_NORMAL = """
        ThumbnailCard {
            background: white;
            border: 1.5px solid #E4E7ED;
            border-radius: 10px;
        }
    """
    _STYLE_HOVER = """
        ThumbnailCard {
            background: #F5F8FF;
            border: 1.5px solid #409EFF;
            border-radius: 10px;
        }
    """
    _STYLE_SELECTED = """
        ThumbnailCard {
            background: #E8F0FE;
            border: 2px solid #1967D2;
            border-radius: 10px;
        }
    """

    def __init__(self, file_info: dict, global_index: int, file_preview,
                 card_w: int = 190, card_h: int = 210, parent=None):
        super().__init__(parent)
        self.file_info = file_info
        self.global_index = global_index
        self.file_preview = file_preview
        self._selected = False

        self.setFixedSize(card_w, card_h)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(self._STYLE_NORMAL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 图片区
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedHeight(card_h - 52)
        self.img_label.setStyleSheet("color: #C0C4CC;")

        # 占位图标
        is_img = file_preview.is_image(file_info['name'])
        if is_img:
            self.img_label.setText("⏳")
            self.img_label.setStyleSheet("font-size: 28px; color: #DCDFE6;")
        else:
            self.img_label.setText(self._file_icon(file_info['name']))
            self.img_label.setStyleSheet("font-size: 32px;")

        # 文件名
        raw = os.path.basename(file_info['name'])
        display = raw if len(raw) <= 22 else raw[:19] + "…"
        name_lbl = QLabel(display)
        name_lbl.setToolTip(raw)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("font-size: 12px; color: #303133; font-weight: 500;")
        name_lbl.setWordWrap(False)

        # 大小
        size_lbl = QLabel(self._format_size(file_info.get('size', 0)))
        size_lbl.setAlignment(Qt.AlignCenter)
        size_lbl.setStyleSheet("font-size: 11px; color: #909399;")

        layout.addWidget(self.img_label, 1)
        layout.addWidget(name_lbl)
        layout.addWidget(size_lbl)

    # ---- public

    def set_thumbnail(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            self.img_label.width() - 4,
            self.img_label.height() - 4,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.img_label.setPixmap(scaled)
        self.img_label.setStyleSheet("")

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self.setStyleSheet(self._STYLE_SELECTED)
        else:
            self.setStyleSheet(self._STYLE_NORMAL)

    # ---- events

    def enterEvent(self, _e):
        if not self._selected:
            self.setStyleSheet(self._STYLE_HOVER)

    def leaveEvent(self, _e):
        if not self._selected:
            self.setStyleSheet(self._STYLE_NORMAL)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_info, self.global_index)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.file_info, self.global_index)

    # ---- helpers

    @staticmethod
    def _file_icon(name: str) -> str:
        ext = os.path.splitext(name)[1].lower()
        icons = {
            '.pdf': '📄', '.doc': '📝', '.docx': '📝',
            '.xls': '📊', '.xlsx': '📊', '.ppt': '📑', '.pptx': '📑',
            '.zip': '🗜️', '.rar': '🗜️', '.7z': '🗜️',
            '.mp4': '🎬', '.mov': '🎬', '.avi': '🎬',
            '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵',
            '.txt': '📃', '.md': '📃', '.json': '🔧', '.yaml': '🔧',
        }
        return icons.get(ext, '📁')

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / 1024 ** 2:.1f} MB"


# ──────────────────────────────────────────────────────────────────────────────
# 加载线程
# ──────────────────────────────────────────────────────────────────────────────
class LoadFilesThread(QThread):
    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, oss_client):
        super().__init__()
        self.oss_client = oss_client

    def run(self):
        try:
            self.finished.emit(self.oss_client.list_files())
        except Exception as exc:
            self.error.emit(str(exc))


class LoadMoreFilesThread(QThread):
    """加载更多文件的线程。"""
    finished = pyqtSignal(list, int)  # (new_files, target_page)
    error    = pyqtSignal(str)
    progress = pyqtSignal(int, int)   # (loaded, total_needed)

    def __init__(self, oss_client, target_page: int, page_size: int, current_count: int):
        super().__init__()
        self.oss_client = oss_client
        self.target_page = target_page
        self.page_size = page_size
        self.current_count = current_count

    def run(self):
        try:
            # 计算需要加载多少文件
            required_files = (self.target_page + 1) * self.page_size
            files_needed = required_files - self.current_count
            
            new_files = []
            while len(new_files) < files_needed and self.oss_client.has_more_data():
                batch = self.oss_client.load_next_page()
                if not batch:
                    break
                new_files.extend(batch)
                self.progress.emit(len(new_files), files_needed)
            
            self.finished.emit(new_files, self.target_page)
        except Exception as exc:
            self.error.emit(str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# 主窗口
# ──────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):

    PAGE_SIZES = [20, 40, 60, 100]

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.oss_client: OSSClient | None = None
        self.file_preview = FilePreview(config)
        self.thumb_mgr = ThumbnailManager(config, self)
        self.thumb_mgr.thumbnail_ready.connect(self._on_thumbnail_ready)

        self.all_files:    list = []
        self.filtered_files: list = []
        self._cards:       dict[str, ThumbnailCard] = {}   # file_key → card
        self._selected_card: ThumbnailCard | None = None
        self._open_viewers: list[ImageViewer] = []

        self.view_mode   = 'grid'   # 'grid' | 'list'
        self.page_size   = self.PAGE_SIZES[0]
        self.current_page = 0

        # 搜索防抖
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filter)

        self._build_ui()
        self.setStyleSheet(_APP_STYLE)

    # ═══════════════════════════════════════════════════════════════ UI build ══

    def _build_ui(self):
        cfg_ui = self.config.get('ui', {})
        title  = cfg_ui.get('title', 'OSS 文件浏览器')
        size   = cfg_ui.get('window_size', [1280, 820])
        self.setWindowTitle(title)
        self.setMinimumSize(960, 640)
        self.resize(size[0], size[1])
        
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'facvion.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        # 进度条（贴顶栏底部，高度 3px）
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        root.addWidget(self._build_subbar(), 0)
        root.addWidget(self._build_content_area(), 1)
        root.addWidget(self._build_pagination())

        self.statusBar().showMessage("就绪  ·  请输入存储桶 URL 后点击「加载」")

    # ── 顶栏 ──────────────────────────────────────────────────────────────────
    def _build_topbar(self) -> QWidget:
        bar = QWidget(objectName="topbar")
        bar.setFixedHeight(60)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(10)

        # Logo / 标题
        logo_lbl = QLabel("☁  OSS 预览")
        logo_lbl.setStyleSheet(
            "font-size: 17px; font-weight: 700; color: #303133; letter-spacing: -0.3px;"
        )
        logo_lbl.setFixedWidth(130)

        # URL 输入
        self.url_input = QLineEdit()
        self.url_input.setObjectName("urlInput")
        self.url_input.setPlaceholderText(
            "存储桶 URL，例如  https://bucket.oss-cn-hangzhou.aliyuncs.com"
        )
        self.url_input.returnPressed.connect(self._load_files)

        # 加载按钮
        self.load_btn = QPushButton("  加载  ")
        self.load_btn.setObjectName("primary")
        self.load_btn.setFixedWidth(86)
        self.load_btn.clicked.connect(self._load_files)

        # 代理设置按钮
        self.proxy_btn = QPushButton("⚙ 代理")
        self.proxy_btn.setObjectName("ghost")
        self.proxy_btn.setFixedWidth(70)
        self.proxy_btn.clicked.connect(self._show_proxy_dialog)

        h.addWidget(logo_lbl)
        h.addWidget(self.url_input, 1)
        h.addWidget(self.proxy_btn)
        h.addWidget(self.load_btn)

        return bar

    # ── 副栏（搜索 + 视图切换）────────────────────────────────────────────────
    def _build_subbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background: #FAFBFC; border-bottom: 1px solid #E4E7ED;")
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(10)

        # 搜索框（带图标感觉）
        search_wrap = QWidget()
        search_wrap.setFixedWidth(260)
        sw = QHBoxLayout(search_wrap)
        sw.setContentsMargins(0, 0, 0, 0)
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 13px; color: #909399;")
        self.search_box = QLineEdit(objectName="searchBox")
        self.search_box.setPlaceholderText("搜索文件名…")
        self.search_box.textChanged.connect(self._on_search_changed)
        sw.addWidget(search_icon)
        sw.addWidget(self.search_box)

        # 结果数
        self.count_lbl = QLabel("0 个文件")
        self.count_lbl.setStyleSheet("color: #909399; font-size: 12px;")

        h.addWidget(search_wrap)
        h.addWidget(self.count_lbl)
        h.addStretch()

        # 视图切换
        vt_lbl = QLabel("视图：")
        vt_lbl.setStyleSheet("font-size: 12px; color: #909399;")
        self.grid_btn = QPushButton("⊞", objectName="viewToggle")
        self.grid_btn.setToolTip("网格视图")
        self.grid_btn.setProperty("active", "true")
        self.grid_btn.clicked.connect(lambda: self._switch_view('grid'))

        self.list_btn = QPushButton("≡", objectName="viewToggle")
        self.list_btn.setToolTip("列表视图")
        self.list_btn.clicked.connect(lambda: self._switch_view('list'))

        h.addWidget(vt_lbl)
        h.addWidget(self.grid_btn)
        h.addWidget(self.list_btn)

        return bar

    # ── 内容区 ────────────────────────────────────────────────────────────────
    def _build_content_area(self) -> QWidget:
        wrap = QWidget()
        wrap.setStyleSheet("background: #F2F4F7;")
        v = QVBoxLayout(wrap)
        v.setContentsMargins(16, 12, 16, 8)
        v.setSpacing(0)

        # ── 列表视图 ──────────────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_list_item_double_clicked)
        self.list_widget.setStyleSheet("background: white; border-radius: 10px;")
        self.list_widget.setVisible(False)

        # ── 网格视图（scroll → flow grid）────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.grid_container)

        v.addWidget(self.list_widget, 1)
        v.addWidget(self.scroll_area, 1)

        return wrap

    # ── 分页栏 ────────────────────────────────────────────────────────────────
    def _build_pagination(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background: #FAFBFC; border-top: 1px solid #E4E7ED;")
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(6)

        self.prev_btn = QPushButton("‹", objectName="pageBtn")
        self.prev_btn.setFixedWidth(32)
        self.prev_btn.clicked.connect(self._prev_page)
        self.prev_btn.setEnabled(False)

        # 页码按钮容器
        self.page_btn_container = QWidget()
        self.page_btn_layout = QHBoxLayout(self.page_btn_container)
        self.page_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.page_btn_layout.setSpacing(4)

        self.next_btn = QPushButton("›", objectName="pageBtn")
        self.next_btn.setFixedWidth(32)
        self.next_btn.clicked.connect(self._next_page)
        self.next_btn.setEnabled(False)

        # 跳转到指定页
        goto_lbl = QLabel("跳转")
        goto_lbl.setStyleSheet("font-size: 12px; color: #909399;")
        self.goto_input = QLineEdit(objectName="gotoInput")
        self.goto_input.setPlaceholderText("页码")
        self.goto_input.setFixedWidth(60)
        self.goto_input.setAlignment(Qt.AlignCenter)
        self.goto_input.returnPressed.connect(self._goto_page_input)
        
        self.goto_btn = QPushButton("跳转", objectName="ghost")
        self.goto_btn.setFixedWidth(56)
        self.goto_btn.clicked.connect(self._goto_page_input)

        # 每页条数
        per_page_lbl = QLabel("每页")
        per_page_lbl.setStyleSheet("font-size: 12px; color: #909399;")
        self.page_size_combo = QComboBox()
        for s in self.PAGE_SIZES:
            self.page_size_combo.addItem(f"{s} 个", s)
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        self.page_size_combo.setFixedWidth(72)
        
        # 加载更多按钮
        self.load_more_btn = QPushButton("加载更多", objectName="ghost")
        self.load_more_btn.setFixedWidth(80)
        self.load_more_btn.clicked.connect(self._load_more_data)
        self.load_more_btn.setVisible(False)

        h.addWidget(self.prev_btn)
        h.addWidget(self.page_btn_container)
        h.addWidget(self.next_btn)
        h.addStretch()
        h.addWidget(self.load_more_btn)
        h.addSpacing(8)
        h.addWidget(goto_lbl)
        h.addWidget(self.goto_input)
        h.addWidget(self.goto_btn)
        h.addSpacing(12)
        h.addWidget(per_page_lbl)
        h.addWidget(self.page_size_combo)

        return bar

    # ═══════════════════════════════════════════════════════════ load files ═══

    def _load_files(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入存储桶 URL")
            return

        # 传递代理配置
        proxy_config = self.config.get('proxy', {})
        self.oss_client = OSSClient(url, proxy_config=proxy_config)
        self.load_btn.setEnabled(False)
        self.load_btn.setText("加载中…")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.statusBar().showMessage("正在连接存储桶…")

        self._load_thread = LoadFilesThread(self.oss_client)
        self._load_thread.finished.connect(self._on_files_loaded)
        self._load_thread.error.connect(self._on_load_error)
        self._load_thread.start()

    def _on_files_loaded(self, files: list):
        self.load_btn.setEnabled(True)
        self.load_btn.setText("  加载  ")
        self.progress.setVisible(False)

        self.all_files = files
        self.current_page = 0
        self._apply_filter()

        if not files:
            self.statusBar().showMessage("未找到文件，请确认 URL 及存储桶访问权限")
            QMessageBox.information(self, "提示",
                "未找到文件，请检查：\n\n"
                "① URL 是否正确\n"
                "② 存储桶是否公开（需要 ListBucket 权限）\n"
                "③ 网络连通性")
        else:
            # 显示加载状态
            has_more = self.oss_client.has_more_data() if self.oss_client else False
            more_info = f"（还有更多数据）" if has_more else ""
            self.statusBar().showMessage(f"已加载 {len(files)} 个文件 {more_info}")

    def _on_load_error(self, msg: str):
        self.load_btn.setEnabled(True)
        self.load_btn.setText("  加载  ")
        self.progress.setVisible(False)
        self.statusBar().showMessage(f"加载失败：{msg}")
        QMessageBox.critical(self, "加载失败", f"无法获取文件列表：\n{msg}")

    # ═══════════════════════════════════════════════════════ search / filter ══

    def _on_search_changed(self, _text: str):
        self._search_timer.start(280)   # 280 ms 防抖

    def _apply_filter(self):
        q = self.search_box.text().strip().lower()
        if q:
            self.filtered_files = [
                f for f in self.all_files
                if q in f['name'].lower()
            ]
        else:
            self.filtered_files = list(self.all_files)

        self.count_lbl.setText(f"{len(self.filtered_files)} 个文件")
        self.current_page = 0
        self._refresh_view()

    # ═══════════════════════════════════════════════════════════ view render ══

    def _refresh_view(self):
        if self.view_mode == 'grid':
            self._render_grid()
        else:
            self._render_list()
        self._refresh_pagination()

    def _switch_view(self, mode: str):
        if mode == self.view_mode:
            return
        self.view_mode = mode

        self.grid_btn.setProperty("active", "true" if mode == 'grid' else "false")
        self.list_btn.setProperty("active", "true" if mode == 'list' else "false")
        # 强制刷新 QSS（属性改变时需要）
        self.grid_btn.style().unpolish(self.grid_btn)
        self.grid_btn.style().polish(self.grid_btn)
        self.list_btn.style().unpolish(self.list_btn)
        self.list_btn.style().polish(self.list_btn)

        self.scroll_area.setVisible(mode == 'grid')
        self.list_widget.setVisible(mode == 'list')
        self.current_page = 0
        self._refresh_view()

    # ── 网格渲染 ──────────────────────────────────────────────────────────────
    def _render_grid(self):
        # 取消上一页所有进行中的缩略图请求
        self.thumb_mgr.cancel_all()

        # 清空旧 cards
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        self._selected_card = None

        page_files = self._page_files()
        if not page_files:
            placeholder = QLabel("暂无文件")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #C0C4CC; font-size: 15px; padding: 60px;")
            self.grid_layout.addWidget(placeholder, 0, 0, 1, 5)
            return

        # 计算每行列数（自适应）
        cols = max(3, (self.scroll_area.width() - 24) // (190 + 12))

        for idx, (fi, global_idx) in enumerate(page_files):
            card = ThumbnailCard(fi, global_idx, self.file_preview)
            card.clicked.connect(self._on_card_clicked)
            card.double_clicked.connect(self._on_card_double_clicked)

            row, col = divmod(idx, cols)
            self.grid_layout.addWidget(card, row, col)

            file_key = fi['name']
            self._cards[file_key] = card

            # 只对图片请求缩略图
            if self.file_preview.is_image(fi['name']):
                self.thumb_mgr.request(file_key, fi['url'])

        # 加右侧弹性填充，使最后一行左对齐
        self.grid_layout.setColumnStretch(cols, 1)

        # 更新进度条
        n_img = sum(1 for fi, _ in page_files if self.file_preview.is_image(fi['name']))
        if n_img > 0:
            self.progress.setVisible(True)
            self.progress.setRange(0, n_img)
            self.progress.setValue(0)

    def _on_thumbnail_ready(self, file_key: str, pixmap: QPixmap):
        card = self._cards.get(file_key)
        if card:
            card.set_thumbnail(pixmap)
        # 更新进度条
        done = self.progress.value() + 1
        self.progress.setValue(done)
        if done >= self.progress.maximum():
            self.progress.setVisible(False)

    # ── 列表渲染 ──────────────────────────────────────────────────────────────
    def _render_list(self):
        self.list_widget.clear()
        for fi, global_idx in self._page_files():
            name = fi['name']
            ext  = os.path.splitext(name)[1].lower()
            icon = ThumbnailCard._file_icon(name)
            size = ThumbnailCard._format_size(fi.get('size', 0))
            item = QListWidgetItem(f"  {icon}  {name}    ({size})")
            item.setData(Qt.UserRole, (fi, global_idx))
            self.list_widget.addItem(item)

    def _on_list_item_double_clicked(self, item: QListWidgetItem):
        fi, global_idx = item.data(Qt.UserRole)
        self._open_file(fi, global_idx)

    # ─────────────────────────────────────────────────────────────────────────
    def _on_card_clicked(self, fi: dict, global_idx: int):
        # 取消上一个选中
        if self._selected_card:
            self._selected_card.set_selected(False)
        card = self._cards.get(fi['name'])
        if card:
            card.set_selected(True)
            self._selected_card = card
        self.statusBar().showMessage(
            f"{fi['name']}   ·   {ThumbnailCard._format_size(fi.get('size', 0))}"
        )

    def _on_card_double_clicked(self, fi: dict, global_idx: int):
        self._open_file(fi, global_idx)

    def _open_file(self, fi: dict, global_idx: int):
        if self.file_preview.is_image(fi['name']):
            viewer = ImageViewer(self.all_files, global_idx, self.file_preview, self.config, parent=None)
            viewer.show()
            # 防止被 GC，追踪引用；destroyed 触发时 C++ 对象已析构，用 sip.isdeleted 过滤
            self._open_viewers.append(viewer)
            viewer.destroyed.connect(self._viewers_cleanup)
        else:
            self.statusBar().showMessage(f"不支持预览：{fi['name']}")

    def _viewers_cleanup(self):
        import sip
        # sip.isdeleted() 是判断 PyQt5 包装对象是否已被 C++ 侧释放的正确方式；
        # 直接调用任何方法（如 isHidden）都会 RuntimeError
        self._open_viewers = [v for v in self._open_viewers if not sip.isdeleted(v)]

    # ═══════════════════════════════════════════════════════════ pagination ═══

    def _page_files(self) -> list[tuple[dict, int]]:
        """返回当前页的 (file_info, global_index) 列表。"""
        start = self.current_page * self.page_size
        end   = start + self.page_size
        result = []
        for gi, fi in enumerate(self.all_files):
            if fi in self.filtered_files[start:end]:
                result.append((fi, gi))
        # 更高效的方式
        result = []
        for local_idx in range(start, min(end, len(self.filtered_files))):
            fi = self.filtered_files[local_idx]
            gi = self.all_files.index(fi) if fi in self.all_files else local_idx
            result.append((fi, gi))
        return result

    def _total_pages(self) -> int:
        return max(1, (len(self.filtered_files) + self.page_size - 1) // self.page_size)

    def _refresh_pagination(self):
        total = self._total_pages()
        # 清空旧页码按钮
        while self.page_btn_layout.count():
            item = self.page_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 生成页码（最多显示7个，两端+省略号）
        cur = self.current_page
        pages = self._visible_pages(cur, total)

        for p in pages:
            if p == '…':
                lbl = QLabel("…")
                lbl.setStyleSheet("color: #909399; padding: 0 4px;")
                self.page_btn_layout.addWidget(lbl)
            else:
                btn = QPushButton(str(p + 1), objectName="pageBtn")
                btn.setFixedWidth(36)
                if p == cur:
                    btn.setProperty("active", "true")
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)
                _p = p
                btn.clicked.connect(lambda _, pg=_p: self._goto_page(pg))
                self.page_btn_layout.addWidget(btn)

        self.prev_btn.setEnabled(cur > 0)
        self.next_btn.setEnabled(cur < total - 1)
        
        # 显示/隐藏"加载更多"按钮
        has_more = self.oss_client and self.oss_client.has_more_data()
        self.load_more_btn.setVisible(has_more)

    @staticmethod
    def _visible_pages(cur: int, total: int) -> list:
        """生成页码显示列表，含省略号。"""
        if total <= 7:
            return list(range(total))
        pages = []
        if cur <= 3:
            pages = list(range(5)) + ['…', total - 1]
        elif cur >= total - 4:
            pages = [0, '…'] + list(range(total - 5, total))
        else:
            pages = [0, '…', cur - 1, cur, cur + 1, '…', total - 1]
        return pages

    def _goto_page(self, page: int):
        if page == self.current_page:
            return
        
        # 检查是否需要加载更多数据
        required_files = (page + 1) * self.page_size
        if required_files > len(self.filtered_files) and self.oss_client and self.oss_client.has_more_data():
            # 需要加载更多数据
            self._load_more_for_page(page)
            return
        
        self.current_page = page
        self._refresh_view()
        self.scroll_area.verticalScrollBar().setValue(0)

    def _prev_page(self):
        if self.current_page > 0:
            self._goto_page(self.current_page - 1)

    def _next_page(self):
        if self.current_page < self._total_pages() - 1:
            self._goto_page(self.current_page + 1)

    def _on_page_size_changed(self, idx: int):
        self.page_size = self.page_size_combo.itemData(idx)
        self.current_page = 0
        self._refresh_view()

    def _goto_page_input(self):
        """处理页码跳转输入。"""
        text = self.goto_input.text().strip()
        if not text:
            return
        
        try:
            page_num = int(text)
            total = self._total_pages()
            
            if page_num < 1:
                QMessageBox.warning(self, "提示", "页码必须大于 0")
                return
            
            # 检查是否超出当前已加载的范围
            required_files = page_num * self.page_size
            if required_files > len(self.filtered_files):
                if self.oss_client and self.oss_client.has_more_data():
                    # 有更多数据可加载
                    reply = QMessageBox.question(
                        self, "提示",
                        f"页码 {page_num} 超出当前已加载范围（共 {total} 页）。\n\n"
                        f"是否从存储桶加载更多数据？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        self._load_more_for_page(page_num - 1)
                    return
                else:
                    QMessageBox.warning(
                        self, "提示",
                        f"页码超出范围，当前最大页码为 {total}"
                    )
                    return
            
            # 页码从 1 开始，索引从 0 开始
            self._goto_page(page_num - 1)
            self.goto_input.clear()
            
        except ValueError:
            QMessageBox.warning(self, "提示", "请输入有效的页码数字")
    
    def _load_more_for_page(self, target_page: int):
        """加载更多数据以到达目标页。"""
        if not self.oss_client or not self.oss_client.has_more_data():
            return
        
        self.load_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.statusBar().showMessage("正在加载更多数据...")
        
        self._load_more_thread = LoadMoreFilesThread(self.oss_client, target_page, self.page_size, len(self.all_files))
        self._load_more_thread.finished.connect(self._on_more_files_loaded)
        self._load_more_thread.error.connect(self._on_load_error)
        self._load_more_thread.progress.connect(self._on_load_more_progress)
        self._load_more_thread.start()
    
    def _on_more_files_loaded(self, new_files: list, target_page: int):
        """更多文件加载完成。"""
        self.load_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if new_files:
            # 追加新文件
            self.all_files.extend(new_files)
            self._apply_filter()
            
            # 跳转到目标页
            if target_page < self._total_pages():
                self.current_page = target_page
                self._refresh_view()
            
            has_more = self.oss_client.has_more_data() if self.oss_client else False
            more_info = f"（还有更多数据）" if has_more else ""
            self.statusBar().showMessage(f"已加载 {len(self.all_files)} 个文件 {more_info}")
        else:
            self.statusBar().showMessage("没有更多数据")
    
    def _on_load_more_progress(self, loaded: int, total_needed: int):
        """加载进度更新。"""
        self.statusBar().showMessage(f"正在加载更多数据... ({loaded}/{total_needed})")
    
    def _load_more_data(self):
        """手动加载更多数据。"""
        if not self.oss_client or not self.oss_client.has_more_data():
            return
        
        # 加载下一批数据
        self._load_more_for_page(self.current_page)

    # ═══════════════════════════════════════════════════════════ proxy config ══

    def _show_proxy_dialog(self):
        """显示代理配置对话框。"""
        dialog = ProxyConfigDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            # 获取新配置
            new_proxy_config = dialog.get_config()
            self.config['proxy'] = new_proxy_config
            
            # 保存到配置文件
            try:
                ConfigLoader.save_config(self.config)
                self.statusBar().showMessage("代理配置已保存并应用", 3000)
                
                # 热更新：重新配置缩略图管理器的代理
                self.thumb_mgr._setup_proxy(self.config)
                
                # 如果已经加载了 OSS 客户端，重新创建以应用新代理
                if self.oss_client:
                    url = self.url_input.text().strip()
                    if url:
                        proxy_config = self.config.get('proxy', {})
                        self.oss_client = OSSClient(url, proxy_config=proxy_config)
                
                logger.info("代理配置已热更新")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存配置失败：{e}")

    # ── 窗口大小改变时重新排列网格列数 ───────────────────────────────────────
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.view_mode == 'grid' and self.filtered_files:
            self._render_grid()


# ──────────────────────────────────────────────────────────────────────────────
# 代理配置对话框
# ──────────────────────────────────────────────────────────────────────────────
class ProxyConfigDialog(QDialog):
    """代理配置对话框。"""

    _STYLE = """
    QDialog {
        background: #F2F4F7;
    }
    QGroupBox {
        font-weight: 600;
        font-size: 13px;
        color: #303133;
        border: 1.5px solid #DCDFE6;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 12px;
        background: white;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        background: white;
    }
    QLabel {
        color: #606266;
        font-size: 12px;
    }
    QLineEdit, QComboBox {
        height: 32px;
        padding: 0 10px;
        border: 1.5px solid #DCDFE6;
        border-radius: 6px;
        background: white;
        color: #303133;
        font-size: 12px;
    }
    QLineEdit:focus, QComboBox:focus {
        border-color: #409EFF;
    }
    QCheckBox {
        color: #303133;
        font-size: 13px;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1.5px solid #DCDFE6;
        border-radius: 3px;
        background: white;
    }
    QCheckBox::indicator:checked {
        background: #409EFF;
        border-color: #409EFF;
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
    }
    QPushButton {
        height: 34px;
        padding: 0 18px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
    }
    QPushButton#primary {
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #409EFF, stop:1 #2980D9);
        color: white;
        border: none;
    }
    QPushButton#primary:hover {
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #53AAFF, stop:1 #3590EA);
    }
    QPushButton {
        background: white;
        color: #606266;
        border: 1.5px solid #DCDFE6;
    }
    QPushButton:hover {
        border-color: #409EFF;
        color: #409EFF;
    }
    """

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.proxy_config = config.get('proxy', {})
        
        self.setWindowTitle("代理配置")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setStyleSheet(self._STYLE)
        
        self._build_ui()
        self._load_config()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 启用代理
        self.enabled_cb = QCheckBox("启用代理")
        self.enabled_cb.toggled.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_cb)

        # 代理设置组
        group = QGroupBox("代理设置")
        form = QFormLayout(group)
        form.setContentsMargins(16, 20, 16, 16)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # 代理类型
        self.type_combo = QComboBox()
        self.type_combo.addItem("HTTP", "http")
        self.type_combo.addItem("SOCKS5", "socks5")
        form.addRow("代理类型：", self.type_combo)

        # 主机
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("例如：127.0.0.1")
        form.addRow("主机地址：", self.host_input)

        # 端口
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("例如：7890")
        form.addRow("端口：", self.port_input)

        # 用户名（可选）
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("可选，如需认证请填写")
        form.addRow("用户名：", self.username_input)

        # 密码（可选）
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("可选，如需认证请填写")
        form.addRow("密码：", self.password_input)

        layout.addWidget(group)
        self.proxy_group = group

        # 提示信息
        tip = QLabel(
            "💡 提示：修改代理配置后会立即生效，无需重启应用。\n"
            "   常见代理端口：Clash (7890)、V2Ray (1080)、Shadowsocks (1080)"
        )
        tip.setStyleSheet("color: #909399; font-size: 11px; padding: 8px; background: #F5F7FA; border-radius: 6px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        layout.addStretch()

        # 按钮
        btn_box = QDialogButtonBox()
        
        save_btn = QPushButton("保存", objectName="primary")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_box.addButton(save_btn, QDialogButtonBox.AcceptRole)
        btn_box.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        
        layout.addWidget(btn_box)

    def _load_config(self):
        """加载当前配置。"""
        self.enabled_cb.setChecked(self.proxy_config.get('enabled', False))
        
        proxy_type = self.proxy_config.get('type', 'http')
        idx = self.type_combo.findData(proxy_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        
        self.host_input.setText(self.proxy_config.get('host', '127.0.0.1'))
        self.port_input.setText(str(self.proxy_config.get('port', 7890)))
        self.username_input.setText(self.proxy_config.get('username', ''))
        self.password_input.setText(self.proxy_config.get('password', ''))
        
        self._on_enabled_changed(self.enabled_cb.isChecked())

    def _on_enabled_changed(self, enabled: bool):
        """启用状态改变。"""
        self.proxy_group.setEnabled(enabled)

    def get_config(self) -> dict:
        """获取配置。"""
        return {
            'enabled': self.enabled_cb.isChecked(),
            'type': self.type_combo.currentData(),
            'host': self.host_input.text().strip() or '127.0.0.1',
            'port': int(self.port_input.text().strip() or '7890'),
            'username': self.username_input.text().strip(),
            'password': self.password_input.text().strip(),
        }