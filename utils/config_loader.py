#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件加载器
"""

import os
import yaml


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def load_config(config_path='config.yaml'):
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            dict: 配置字典
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    @staticmethod
    def save_config(config, config_path='config.yaml'):
        """
        保存配置文件
        
        Args:
            config: 配置字典
            config_path: 配置文件路径
        """
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
