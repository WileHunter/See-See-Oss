#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缩略图管理器 —— 基于 Qt 原生 QNetworkAccessManager
全内存缓存，无磁盘写入，可中断，零额外线程
"""

from collections import OrderedDict
import logging

from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.QtNetwork import (QNetworkAccessManager, QNetworkRequest, QNetworkReply,
                             QNetworkProxy)
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)


class ThumbnailManager(QObject):
    """
    纯内存、事件驱动的缩略图管理器。

    使用 QNetworkAccessManager 的异步模型：所有请求在 Qt 事件循环中完成，
    无需额外线程，天然线程安全，且支持一键取消全部请求。

    LRU 缓存默认最多保留 800 张缩略图，超出时淘汰最旧的。
    并发请求数提升到 6 个，加快缩略图加载速度。
    """

    thumbnail_ready = pyqtSignal(str, QPixmap)   # (file_key, pixmap)

    MAX_CACHE = 800  # 增加缓存容量
    THUMB_W = 180
    THUMB_H = 180
    MAX_CONCURRENT = 6  # 最大并发请求数

    def __init__(self, config: dict = None, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        # 设置最大并发连接数
        self._nam.setNetworkAccessible(QNetworkAccessManager.Accessible)
        
        # 配置代理
        if config:
            self._setup_proxy(config)
        
        self._cache: OrderedDict[str, QPixmap] = OrderedDict()
        # url_str → (QNetworkReply, file_key)
        self._inflight: dict[str, tuple] = {}
        # 待处理队列
        self._pending: list[tuple[str, str]] = []  # [(file_key, url), ...]

    # ------------------------------------------------------------------ public

    def request(self, file_key: str, url: str) -> None:
        """请求一张缩略图。命中缓存时同步 emit，否则异步 fetch。"""
        if file_key in self._cache:
            self._cache.move_to_end(file_key)
            self.thumbnail_ready.emit(file_key, self._cache[file_key])
            return

        if url in self._inflight:
            return   # 已在途，等结果即可

        # 如果当前并发数已满，加入待处理队列
        if len(self._inflight) >= self.MAX_CONCURRENT:
            if (file_key, url) not in self._pending:
                self._pending.append((file_key, url))
            return

        self._start_request(file_key, url)
    
    def _start_request(self, file_key: str, url: str) -> None:
        """启动一个缩略图请求。"""
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        req.setRawHeader(b"User-Agent", b"OSSBrowser/2.0")
        # 设置优先级为高，加快图片加载
        req.setPriority(QNetworkRequest.HighPriority)
        reply = self._nam.get(req)
        self._inflight[url] = (reply, file_key)
        reply.finished.connect(lambda: self._on_finished(reply, url, file_key))

    def cancel_all(self) -> None:
        """中止所有进行中的请求（切页、切模式时调用）。"""
        for reply, _ in list(self._inflight.values()):
            try:
                reply.abort()
                reply.deleteLater()
            except RuntimeError:
                pass
        self._inflight.clear()
        self._pending.clear()

    def invalidate(self, file_key: str) -> None:
        """从缓存中删除某个 key。"""
        self._cache.pop(file_key, None)

    def clear(self) -> None:
        self.cancel_all()
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    @property
    def inflight_count(self) -> int:
        return len(self._inflight)

    # ----------------------------------------------------------------- private

    def _on_finished(self, reply: QNetworkReply, url: str, file_key: str) -> None:
        self._inflight.pop(url, None)

        if reply.error() != QNetworkReply.NoError:
            # abort() 产生的错误静默处理
            if reply.error() != QNetworkReply.OperationCanceledError:
                logger.debug("thumbnail fetch error [%s]: %s", file_key, reply.errorString())
            reply.deleteLater()
            self._process_pending()
            return

        data = bytes(reply.readAll())
        reply.deleteLater()

        if not data:
            self._process_pending()
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            logger.debug("cannot decode image [%s]", file_key)
            self._process_pending()
            return

        pixmap = pixmap.scaled(
            self.THUMB_W, self.THUMB_H,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        # LRU 插入
        self._cache[file_key] = pixmap
        self._cache.move_to_end(file_key)
        if len(self._cache) > self.MAX_CACHE:
            self._cache.popitem(last=False)

        self.thumbnail_ready.emit(file_key, pixmap)
        
        # 处理待处理队列
        self._process_pending()
    
    def _process_pending(self) -> None:
        """处理待处理队列中的请求。"""
        while self._pending and len(self._inflight) < self.MAX_CONCURRENT:
            file_key, url = self._pending.pop(0)
            # 再次检查缓存和进行中状态
            if file_key not in self._cache and url not in self._inflight:
                self._start_request(file_key, url)

    def _setup_proxy(self, config: dict) -> None:
        """配置网络代理。"""
        proxy_cfg = config.get('proxy', {})
        if not proxy_cfg.get('enabled', False):
            # 禁用代理时，清除代理设置
            self._nam.setProxy(QNetworkProxy(QNetworkProxy.NoProxy))
            logger.info("代理已禁用")
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
        logger.info(f"代理已启用: {proxy_type}://{host}:{port}")
