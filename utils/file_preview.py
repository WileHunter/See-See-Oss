#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件预览工具（精简版）
缩略图生成已迁移至 ThumbnailManager（纯内存），此模块仅保留判断类工具方法。
"""

import os


class FilePreview:

    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg'}

    def __init__(self, config: dict):
        self.config = config

    def is_image(self, file_name: str) -> bool:
        return os.path.splitext(file_name)[1].lower() in self.IMAGE_EXTS
