#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSS 客户端封装
"""

import requests
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 禁用第三方库的 DEBUG 日志
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)


class OSSClient:
    """OSS 客户端（支持公开访问的存储桶）"""
    
    def __init__(self, bucket_url, debug=True, proxy_config=None):
        """
        初始化 OSS 客户端
        
        Args:
            bucket_url: 存储桶 URL
            debug: 是否启用调试模式
            proxy_config: 代理配置字典
        """
        self.bucket_url = bucket_url.rstrip('/')
        self.files = []
        self.debug = debug
        self.last_response = None  # 保存最后一次响应用于调试
        self.proxies = self._setup_proxy(proxy_config) if proxy_config else None
        
        # 分页相关
        self.is_truncated = False
        self.next_continuation_token = None
        self.total_loaded = 0
    
    def _setup_proxy(self, proxy_config):
        """
        配置代理
        
        Args:
            proxy_config: 代理配置字典
            
        Returns:
            dict: requests 库使用的代理配置
        """
        if not proxy_config.get('enabled', False):
            return None
        
        proxy_type = proxy_config.get('type', 'http').lower()
        host = proxy_config.get('host', '127.0.0.1')
        port = proxy_config.get('port', 7890)
        username = proxy_config.get('username', '')
        password = proxy_config.get('password', '')
        
        # 构建代理 URL
        if username and password:
            auth = f"{username}:{password}@"
        else:
            auth = ""
        
        if proxy_type == 'socks5':
            proxy_url = f"socks5://{auth}{host}:{port}"
        else:  # http
            proxy_url = f"http://{auth}{host}:{port}"
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url,
        }
        
        logger.info(f"OSS 客户端代理已启用: {proxy_type}://{host}:{port}")
        return proxies
    
    def list_files(self, prefix='', max_keys=1000, continuation_token=None):
        """
        列出存储桶中的文件（支持分页）
        
        Args:
            prefix: 文件前缀
            max_keys: 最大返回数量（最大 1000）
            continuation_token: 分页令牌，用于获取下一页
            
        Returns:
            list: 文件列表
        """
        try:
            # 构建请求参数
            params = {
                'list-type': '2',  # 使用 ListObjectsV2 API
                'prefix': prefix,
                'max-keys': min(max_keys, 1000),  # 限制最大值为 1000
            }
            
            # 如果有分页令牌，添加到参数中
            if continuation_token:
                params['continuation-token'] = continuation_token
            
            logger.info(f"正在请求 URL: {self.bucket_url}")
            logger.info(f"请求参数: {params}")
            
            response = requests.get(
                self.bucket_url, 
                params=params, 
                timeout=10,
                proxies=self.proxies
            )
            self.last_response = response  # 保存响应
            
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应头: {dict(response.headers)}")
            logger.debug(f"响应内容长度: {len(response.text)} 字符")
            
            if self.debug:
                # 调试模式下打印响应内容前1000字符
                logger.debug(f"响应内容预览:\n{response.text[:1000]}")
            
            if response.status_code == 200:
                # 解析 XML 响应
                files, is_truncated, next_token = self._parse_xml_response_v2(response.text)
                
                # 更新分页状态
                self.is_truncated = is_truncated
                self.next_continuation_token = next_token
                self.total_loaded += len(files)
                
                logger.info(f"成功解析 {len(files)} 个文件")
                logger.info(f"是否还有更多数据: {is_truncated}")
                logger.info(f"累计已加载: {self.total_loaded} 个文件")
                
                # 如果不是分页请求，替换文件列表；否则追加
                if not continuation_token:
                    self.files = files
                else:
                    self.files.extend(files)
                
                return files
            else:
                logger.error(f"请求失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text[:500]}")
                return []
        except Exception as e:
            logger.exception(f"列出文件失败: {e}")
            return []
    
    def load_next_page(self):
        """
        加载下一页数据
        
        Returns:
            list: 新加载的文件列表，如果没有更多数据则返回空列表
        """
        if not self.is_truncated or not self.next_continuation_token:
            logger.info("没有更多数据可加载")
            return []
        
        logger.info(f"加载下一页，token: {self.next_continuation_token[:20]}...")
        return self.list_files(continuation_token=self.next_continuation_token)
    
    def has_more_data(self):
        """
        检查是否还有更多数据
        
        Returns:
            bool: 是否还有更多数据
        """
        return self.is_truncated and self.next_continuation_token is not None
    
    def _parse_xml_response_v2(self, xml_text):
        """
        解析 ListObjectsV2 XML 响应
        
        Args:
            xml_text: XML 文本
            
        Returns:
            tuple: (文件列表, 是否截断, 下一页令牌)
        """
        files = []
        is_truncated = False
        next_token = None
        
        try:
            logger.debug("开始解析 XML 响应（ListObjectsV2）")
            root = ET.fromstring(xml_text)
            logger.debug(f"XML 根节点: {root.tag}")
            
            # 尝试多种命名空间
            namespaces = [
                'http://s3.amazonaws.com/doc/2006-03-01/',  # AWS S3
                'http://doc.oss-cn-hangzhou.aliyuncs.com',  # 阿里云 OSS
                ''  # 无命名空间
            ]
            
            for ns in namespaces:
                # 查找 IsTruncated
                if ns:
                    truncated_elem = root.find(f'.//{{{ns}}}IsTruncated')
                    next_token_elem = root.find(f'.//{{{ns}}}NextContinuationToken')
                    contents = root.findall(f'.//{{{ns}}}Contents')
                else:
                    truncated_elem = root.find('.//IsTruncated')
                    next_token_elem = root.find('.//NextContinuationToken')
                    contents = root.findall('.//Contents')
                
                # 解析分页信息
                if truncated_elem is not None:
                    is_truncated = truncated_elem.text.lower() == 'true'
                    logger.debug(f"IsTruncated: {is_truncated}")
                
                if next_token_elem is not None and next_token_elem.text:
                    next_token = next_token_elem.text
                    logger.debug(f"NextContinuationToken: {next_token[:50]}...")
                
                logger.debug(f"使用命名空间 '{ns}' 找到 {len(contents)} 个 Contents 节点")
                
                if contents:
                    for content in contents:
                        if ns:
                            key = content.find(f'{{{ns}}}Key')
                            size = content.find(f'{{{ns}}}Size')
                            last_modified = content.find(f'{{{ns}}}LastModified')
                        else:
                            key = content.find('Key')
                            size = content.find('Size')
                            last_modified = content.find('LastModified')
                        
                        if key is not None:
                            file_info = {
                                'name': key.text,
                                'url': f"{self.bucket_url}/{key.text}",
                                'size': int(size.text) if size is not None and size.text else 0,
                                'last_modified': last_modified.text if last_modified is not None else ''
                            }
                            files.append(file_info)
                            logger.debug(f"解析文件: {file_info['name']}")
                    break  # 找到数据后退出循环
            
            if not files:
                logger.warning("未能从 XML 中解析出任何文件")
                logger.debug(f"XML 内容:\n{xml_text[:2000]}")
                
        except ET.ParseError as e:
            logger.error(f"XML 解析错误: {e}")
            logger.debug(f"无法解析的内容:\n{xml_text[:1000]}")
        except Exception as e:
            logger.exception(f"解析 XML 失败: {e}")
        
        return files, is_truncated, next_token
        """
        解析 XML 响应
        
        Args:
            xml_text: XML 文本
            
        Returns:
            list: 文件列表
        """
        files = []
        try:
            logger.debug("开始解析 XML 响应")
            root = ET.fromstring(xml_text)
            logger.debug(f"XML 根节点: {root.tag}")
            
            # 尝试多种命名空间
            namespaces = [
                'http://s3.amazonaws.com/doc/2006-03-01/',  # AWS S3
                'http://doc.oss-cn-hangzhou.aliyuncs.com',  # 阿里云 OSS
                ''  # 无命名空间
            ]
            
            for ns in namespaces:
                if ns:
                    contents = root.findall(f'.//{{{ns}}}Contents')
                else:
                    contents = root.findall('.//Contents')
                
                logger.debug(f"使用命名空间 '{ns}' 找到 {len(contents)} 个 Contents 节点")
                
                if contents:
                    for content in contents:
                        if ns:
                            key = content.find(f'{{{ns}}}Key')
                            size = content.find(f'{{{ns}}}Size')
                            last_modified = content.find(f'{{{ns}}}LastModified')
                        else:
                            key = content.find('Key')
                            size = content.find('Size')
                            last_modified = content.find('LastModified')
                        
                        if key is not None:
                            file_info = {
                                'name': key.text,
                                'url': f"{self.bucket_url}/{key.text}",
                                'size': int(size.text) if size is not None and size.text else 0,
                                'last_modified': last_modified.text if last_modified is not None else ''
                            }
                            files.append(file_info)
                            logger.debug(f"解析文件: {file_info['name']}")
                    break  # 找到数据后退出循环
            
            if not files:
                logger.warning("未能从 XML 中解析出任何文件")
                logger.debug(f"XML 内容:\n{xml_text[:2000]}")
                
        except ET.ParseError as e:
            logger.error(f"XML 解析错误: {e}")
            logger.debug(f"无法解析的内容:\n{xml_text[:1000]}")
        except Exception as e:
            logger.exception(f"解析 XML 失败: {e}")
        
        return files
    
    def get_debug_info(self):
        """
        获取调试信息
        
        Returns:
            dict: 调试信息
        """
        if not self.last_response:
            return {"error": "没有可用的响应数据"}
        
        return {
            "url": self.last_response.url,
            "status_code": self.last_response.status_code,
            "headers": dict(self.last_response.headers),
            "content_preview": self.last_response.text[:2000],
            "content_length": len(self.last_response.text)
        }
    
    def get_file_url(self, file_name):
        """
        获取文件 URL
        
        Args:
            file_name: 文件名
            
        Returns:
            str: 文件 URL
        """
        return f"{self.bucket_url}/{file_name}"

    def _parse_xml_response(self, xml_text):
        """
        解析旧版 ListObjects XML 响应（兼容性保留）
        
        Args:
            xml_text: XML 文本
            
        Returns:
            list: 文件列表
        """
        files, _, _ = self._parse_xml_response_v2(xml_text)
        return files
