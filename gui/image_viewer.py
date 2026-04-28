#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片查看器 —— 非模态，可同时打开多个，全内存加载
"""

import logging

from PyQt5.QtCore import Qt, QUrl, QPointF, QPoint, QRectF
from PyQt5.QtGui import (QPixmap, QIcon, QColor, QPainter, QPalette,
                         QWheelEvent, QKeySequence, QCursor)
from PyQt5.QtNetwork import (QNetworkAccessManager, QNetworkRequest, QNetworkReply,
                             QNetworkProxy)
from PyQt5.QtWidgets import (QMainWindow, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSizePolicy,
                             QStatusBar, QShortcut, QScrollArea, QFrame,
                             QToolButton, QSlider, QApplication)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
class _ImageCanvas(QWidget):
    """
    可缩放 + 可拖拽的图片画布。
    不依赖 QLabel.setScaledContents，直接用 QPainter 绘制，更流畅。
    """

    MIN_ZOOM = 0.05
    MAX_ZOOM = 16.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._offset = QPointF(0, 0)
        self._drag_start: QPoint | None = None
        self._drag_offset_start = QPointF(0, 0)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 200)

    # ------------------------------------------------------------ public API

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._fit_to_window()
        self.update()

    def set_zoom(self, factor: float) -> None:
        self._zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
        self._clamp_offset()
        self.update()

    def zoom_factor(self) -> float:
        return self._zoom

    def fit_to_window(self) -> None:
        self._fit_to_window()
        self.update()

    def actual_size(self) -> None:
        self._zoom = 1.0
        self._center_image()
        self.update()

    # ------------------------------------------------------------ painting

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#1a1a2e"))

        if self._pixmap is None or self._pixmap.isNull():
            painter.setPen(QColor("#4a4a6a"))
            painter.drawText(self.rect(), Qt.AlignCenter, "正在加载…")
            return

        w = self._pixmap.width() * self._zoom
        h = self._pixmap.height() * self._zoom
        x = self._offset.x()
        y = self._offset.y()
        painter.drawPixmap(QRectF(x, y, w, h), self._pixmap,
                           QRectF(0, 0, self._pixmap.width(), self._pixmap.height()))

    # ------------------------------------------------------------ interaction

    def wheelEvent(self, event: QWheelEvent):
        if self._pixmap is None:
            return
        delta = event.angleDelta().y()
        factor = 1.12 if delta > 0 else 1 / 1.12

        # 以鼠标位置为中心缩放
        mouse = QPointF(event.pos())
        rel = mouse - self._offset          # 鼠标在图片坐标系中的位置
        self._zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom * factor))
        self._offset = mouse - rel * (self._zoom / (self._zoom / factor))
        self._clamp_offset()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()
            self._drag_offset_start = QPointF(self._offset)
            self.setCursor(QCursor(Qt.ClosedHandCursor))

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            delta = QPointF(event.pos() - self._drag_start)
            self._offset = self._drag_offset_start + delta
            self._clamp_offset()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = None
            self.setCursor(QCursor(Qt.ArrowCursor))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap and not self._pixmap.isNull():
            self._fit_to_window()

    def mouseDoubleClickEvent(self, _event):
        if self._zoom > 1.05:
            self._fit_to_window()
        else:
            self.actual_size()
        self.update()

    # ------------------------------------------------------------ helpers

    def _fit_to_window(self):
        if self._pixmap is None or self._pixmap.isNull():
            return
        ww, wh = self.width(), self.height()
        pw, ph = self._pixmap.width(), self._pixmap.height()
        if pw == 0 or ph == 0:
            return
        self._zoom = min(ww / pw, wh / ph) * 0.96
        self._center_image()

    def _center_image(self):
        if self._pixmap is None:
            return
        w = self._pixmap.width() * self._zoom
        h = self._pixmap.height() * self._zoom
        self._offset = QPointF((self.width() - w) / 2, (self.height() - h) / 2)

    def _clamp_offset(self):
        """防止图片完全拖出可视区域。"""
        if self._pixmap is None:
            return
        iw = self._pixmap.width() * self._zoom
        ih = self._pixmap.height() * self._zoom
        margin = 60
        x = self._offset.x()
        y = self._offset.y()
        x = min(x, self.width() - margin)
        x = max(x, margin - iw)
        y = min(y, self.height() - margin)
        y = max(y, margin - ih)
        self._offset = QPointF(x, y)


# ──────────────────────────────────────────────────────────────────────────────
class ImageViewer(QMainWindow):
    """
    非模态图片查看器。
    - 调用 show() 而非 exec_()，可同时打开多个实例。
    - 全内存加载，不写磁盘。
    - 支持鼠标滚轮缩放、拖拽平移、键盘导航。
    """

    _STYLE = """
    QMainWindow { background: #1a1a2e; }
    QWidget#toolbar {
        background: #16213e;
        border-bottom: 1px solid #0f3460;
    }
    QPushButton {
        background: #0f3460;
        color: #e0e0e0;
        border: 1px solid #1a4a7a;
        border-radius: 6px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 600;
    }
    QPushButton:hover { background: #1a5a8a; border-color: #4a9eff; }
    QPushButton:pressed { background: #0a2a50; }
    QPushButton:disabled { background: #0d1b33; color: #4a4a6a; }
    QLabel {
        color: #a0a8c0;
        font-size: 12px;
    }
    QStatusBar {
        background: #16213e;
        color: #6a7898;
        border-top: 1px solid #0f3460;
        font-size: 11px;
    }
    QSlider::groove:horizontal {
        height: 4px;
        background: #0f3460;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        width: 14px; height: 14px;
        margin: -5px 0;
        background: #4a9eff;
        border-radius: 7px;
    }
    QSlider::sub-page:horizontal {
        background: #4a9eff;
        border-radius: 2px;
    }
    """

    def __init__(self, all_files: list, start_index: int, file_preview, config: dict = None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.all_files = all_files
        self.current_index = start_index
        self.file_preview = file_preview
        self.config = config or {}

        self._nam = QNetworkAccessManager(self)
        self._setup_proxy()
        self._current_reply = None
        
        # 预加载缓存：存储前后图片的 pixmap
        self._preload_cache: dict[int, QPixmap] = {}
        self._preload_replies: dict[int, QNetworkReply] = {}

        self._build_ui()
        self._setup_shortcuts()
        self.setStyleSheet(self._STYLE)
        self._load_current()

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        self.setMinimumSize(900, 650)
        self.resize(1100, 750)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── toolbar ──────────────────────────────────────────────────────────
        toolbar = QWidget(objectName="toolbar")
        toolbar.setFixedHeight(52)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 0, 12, 0)
        tb.setSpacing(8)

        self.prev_btn = QPushButton("◀  上一张")
        self.prev_btn.setFixedWidth(90)
        self.prev_btn.clicked.connect(self.show_previous)

        self.next_btn = QPushButton("下一张  ▶")
        self.next_btn.setFixedWidth(90)
        self.next_btn.clicked.connect(self.show_next)

        sep1 = _vsep()

        zoom_lbl = QLabel("缩放")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(5, 800)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(140)
        self.zoom_slider.valueChanged.connect(self._on_slider_zoom)

        self.zoom_pct_lbl = QLabel("100 %")
        self.zoom_pct_lbl.setFixedWidth(46)
        self.zoom_pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        sep2 = _vsep()

        self.fit_btn = QPushButton("适应窗口")
        self.fit_btn.clicked.connect(self._fit_window)

        self.actual_btn = QPushButton("原始大小")
        self.actual_btn.clicked.connect(self._actual_size)

        self.copy_url_btn = QPushButton("复制链接")
        self.copy_url_btn.clicked.connect(self._copy_url)

        self.open_btn = QPushButton("↗ 浏览器打开")
        self.open_btn.clicked.connect(self._open_in_browser)

        tb.addWidget(self.prev_btn)
        tb.addWidget(self.next_btn)
        tb.addWidget(sep1)
        tb.addWidget(zoom_lbl)
        tb.addWidget(self.zoom_slider)
        tb.addWidget(self.zoom_pct_lbl)
        tb.addWidget(sep2)
        tb.addWidget(self.fit_btn)
        tb.addWidget(self.actual_btn)
        tb.addStretch()
        tb.addWidget(self.copy_url_btn)
        tb.addWidget(self.open_btn)

        root.addWidget(toolbar)

        # ── canvas ───────────────────────────────────────────────────────────
        self._canvas = _ImageCanvas()
        root.addWidget(self._canvas, 1)

        # ── status bar ───────────────────────────────────────────────────────
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("正在加载…")

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Left),   self, self.show_previous)
        QShortcut(QKeySequence(Qt.Key_Right),  self, self.show_next)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close)
        QShortcut(QKeySequence(Qt.Key_F),      self, self._fit_window)
        QShortcut(QKeySequence("1"),           self, self._actual_size)
    
    def _setup_proxy(self):
        """配置网络代理。"""
        proxy_cfg = self.config.get('proxy', {})
        if not proxy_cfg.get('enabled', False):
            # 禁用代理时，清除代理设置
            self._nam.setProxy(QNetworkProxy(QNetworkProxy.NoProxy))
            return
        
        proxy_type = proxy_cfg.get('type', 'http').lower()
        host = proxy_cfg.get('host', '127.0.0.1')
        port = proxy_cfg.get('port', 7890)
        username = proxy_cfg.get('username', '')
        password = proxy_cfg.get('password', '')
        
        # 设置代理类型
        if proxy_type == 'socks5':
            proxy = QNetworkProxy(QNetworkProxy.Socks5Proxy, host, port)
        else:  # http
            proxy = QNetworkProxy(QNetworkProxy.HttpProxy, host, port)
        
        # 设置认证
        if username:
            proxy.setUser(username)
        if password:
            proxy.setPassword(password)
        
        self._nam.setProxy(proxy)
        logger.info(f"图片查看器代理已启用: {proxy_type}://{host}:{port}")

    # ------------------------------------------------------------------ loading

    def _load_current(self):
        if not (0 <= self.current_index < len(self.all_files)):
            return

        fi = self.all_files[self.current_index]
        name = fi.get('name', '')
        url  = fi.get('url', '')

        self.setWindowTitle(f"图片查看器 — {name}")
        self._status.showMessage(f"正在加载  {name} …")
        self._canvas.set_pixmap(QPixmap())   # 清空旧图

        # 取消上一次请求
        if self._current_reply is not None:
            try:
                self._current_reply.abort()
                self._current_reply.deleteLater()
            except RuntimeError:
                pass
            self._current_reply = None

        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        reply = self._nam.get(req)
        self._current_reply = reply
        reply.finished.connect(lambda: self._on_image_loaded(reply, name))

        # 更新导航按钮状态
        self.prev_btn.setEnabled(self._has_prev())
        self.next_btn.setEnabled(self._has_next())

    def _on_image_loaded(self, reply: QNetworkReply, name: str):
        if reply.error() == QNetworkReply.OperationCanceledError:
            reply.deleteLater()
            return
        if reply.error() != QNetworkReply.NoError:
            self._status.showMessage(f"加载失败：{reply.errorString()}")
            reply.deleteLater()
            return

        data = bytes(reply.readAll())
        reply.deleteLater()
        self._current_reply = None

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            self._status.showMessage("无法解码图片数据")
            return

        self._canvas.set_pixmap(pixmap)
        self._sync_slider_to_canvas()

        idx = self.current_index + 1
        total = len(self.all_files)
        w, h = pixmap.width(), pixmap.height()
        size_kb = len(data) / 1024
        self._status.showMessage(
            f"{idx} / {total}   ·   {name}   ·   {w} × {h}  px   ·   {size_kb:.1f} KB"
        )
        
        # 预加载前后图片
        self._preload_adjacent()

    # ------------------------------------------------------------------ nav

    def show_previous(self):
        for i in range(self.current_index - 1, -1, -1):
            if self.file_preview.is_image(self.all_files[i]['name']):
                self.current_index = i
                self._load_current_with_cache()
                return

    def show_next(self):
        for i in range(self.current_index + 1, len(self.all_files)):
            if self.file_preview.is_image(self.all_files[i]['name']):
                self.current_index = i
                self._load_current_with_cache()
                return

    def _has_prev(self):
        return any(self.file_preview.is_image(self.all_files[i]['name'])
                   for i in range(self.current_index - 1, -1, -1))

    def _has_next(self):
        return any(self.file_preview.is_image(self.all_files[i]['name'])
                   for i in range(self.current_index + 1, len(self.all_files)))

    # ------------------------------------------------------------------ zoom

    def _on_slider_zoom(self, value: int):
        factor = value / 100.0
        self._canvas.set_zoom(factor)
        self.zoom_pct_lbl.setText(f"{value} %")

    def _sync_slider_to_canvas(self):
        pct = int(self._canvas.zoom_factor() * 100)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(pct)
        self.zoom_slider.blockSignals(False)
        self.zoom_pct_lbl.setText(f"{pct} %")

    def _fit_window(self):
        self._canvas.fit_to_window()
        self._sync_slider_to_canvas()

    def _actual_size(self):
        self._canvas.actual_size()
        self._sync_slider_to_canvas()

    # ------------------------------------------------------------------ actions

    def _copy_url(self):
        if 0 <= self.current_index < len(self.all_files):
            url = self.all_files[self.current_index].get('url', '')
            QApplication.clipboard().setText(url)
            self._status.showMessage("链接已复制到剪贴板")

    def _open_in_browser(self):
        if 0 <= self.current_index < len(self.all_files):
            from PyQt5.QtGui import QDesktopServices
            url = self.all_files[self.current_index].get('url', '')
            QDesktopServices.openUrl(QUrl(url))
    
    # ------------------------------------------------------------------ preload
    
    def _load_current_with_cache(self):
        """优先从预加载缓存加载，缓存未命中时走正常流程。"""
        if self.current_index in self._preload_cache:
            # 缓存命中，瞬间显示
            pixmap = self._preload_cache[self.current_index]
            fi = self.all_files[self.current_index]
            name = fi.get('name', '')
            
            self.setWindowTitle(f"图片查看器 — {name}")
            self._canvas.set_pixmap(pixmap)
            self._sync_slider_to_canvas()
            
            idx = self.current_index + 1
            total = len(self.all_files)
            w, h = pixmap.width(), pixmap.height()
            self._status.showMessage(
                f"{idx} / {total}   ·   {name}   ·   {w} × {h}  px   ·   [缓存]"
            )
            
            # 更新导航按钮
            self.prev_btn.setEnabled(self._has_prev())
            self.next_btn.setEnabled(self._has_next())
            
            # 预加载新的相邻图片
            self._preload_adjacent()
        else:
            # 缓存未命中，正常加载
            self._load_current()
    
    def _preload_adjacent(self):
        """预加载前后各 2 张图片到缓存。"""
        # 清理旧的预加载请求
        for idx, reply in list(self._preload_replies.items()):
            if abs(idx - self.current_index) > 2:
                try:
                    reply.abort()
                    reply.deleteLater()
                except RuntimeError:
                    pass
                del self._preload_replies[idx]
        
        # 清理远离当前位置的缓存
        for idx in list(self._preload_cache.keys()):
            if abs(idx - self.current_index) > 3:
                del self._preload_cache[idx]
        
        # 预加载前后各 2 张
        indices_to_preload = []
        
        # 向后找 2 张
        count = 0
        for i in range(self.current_index + 1, len(self.all_files)):
            if self.file_preview.is_image(self.all_files[i]['name']):
                indices_to_preload.append(i)
                count += 1
                if count >= 2:
                    break
        
        # 向前找 2 张
        count = 0
        for i in range(self.current_index - 1, -1, -1):
            if self.file_preview.is_image(self.all_files[i]['name']):
                indices_to_preload.append(i)
                count += 1
                if count >= 2:
                    break
        
        # 发起预加载请求
        for idx in indices_to_preload:
            if idx not in self._preload_cache and idx not in self._preload_replies:
                fi = self.all_files[idx]
                url = fi.get('url', '')
                req = QNetworkRequest(QUrl(url))
                req.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
                reply = self._nam.get(req)
                self._preload_replies[idx] = reply
                reply.finished.connect(lambda r=reply, i=idx: self._on_preload_finished(r, i))
    
    def _on_preload_finished(self, reply: QNetworkReply, index: int):
        """预加载完成回调。"""
        if index in self._preload_replies:
            del self._preload_replies[index]
        
        if reply.error() != QNetworkReply.NoError:
            reply.deleteLater()
            return
        
        data = bytes(reply.readAll())
        reply.deleteLater()
        
        if not data:
            return
        
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self._preload_cache[index] = pixmap
            logger.debug(f"预加载完成: index={index}, cache_size={len(self._preload_cache)}")


# ──────────────────────────────────────────────────────────────────────────────
def _vsep() -> QFrame:
    """垂直分隔线。"""
    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setStyleSheet("color: #0f3460;")
    sep.setFixedWidth(1)
    return sep
