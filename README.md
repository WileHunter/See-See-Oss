# OSS 文件浏览器

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)

一个现代化的 OSS（对象存储服务）文件浏览器，支持阿里云 OSS、腾讯云 COS 等兼容 S3 协议的对象存储服务。

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用说明](#使用说明) • [配置文件](#配置文件) • [截图预览](#截图预览)



---

## ✨ 功能特性

### 🎨 现代化界面
- **商业级 UI 设计** - 精心设计的用户界面，流畅的交互体验
- **双视图模式** - 支持网格视图和列表视图自由切换
- **响应式布局** - 自适应窗口大小，完美支持各种分辨率

### 🚀 高性能
- **智能缩略图** - 内存缓存，最多缓存 800 张缩略图
- **并发加载** - 6 个并发请求，大幅提升加载速度
- **图片预加载** - 自动预加载前后图片，切换瞬间显示
- **防抖搜索** - 280ms 防抖，流畅的搜索体验

### 🖼️ 内置图片查看器
- **全功能查看器** - 支持缩放、拖拽、旋转
- **鼠标滚轮缩放** - 以鼠标位置为中心缩放
- **键盘快捷键** - 左右键切换、F 键适应窗口、ESC 关闭
- **多窗口支持** - 可同时打开多个图片查看器

### 📄 分页与导航
- **智能分页** - 支持 20/40/60/100 每页显示数量
- **页码跳转** - 直接输入页码快速跳转
- **动态加载** - 自动检测并加载超过 1000 个文件的存储桶
- **加载更多** - 一键加载下一批数据

### 🌐 网络功能
- **代理支持** - 支持 HTTP 和 SOCKS5 代理
- **热更新配置** - 代理配置实时生效，无需重启
- **GUI 配置** - 可视化代理配置界面

### 🔍 搜索与过滤
- **实时搜索** - 按文件名快速过滤
- **结果统计** - 实时显示搜索结果数量

---

## 📦 快速开始

### 环境要求

- Python 3.8+
- Windows / macOS / Linux

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/your-username/oss-file-browser.git
cd oss-file-browser
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **运行应用**
```bash
python main.py
```

---

## 📖 使用说明

### 基本使用

1. **连接存储桶**
   - 在顶部输入框输入存储桶 URL
   - 例如：`https://your-bucket.oss-cn-hangzhou.aliyuncs.com`
   - 点击「加载」按钮

2. **浏览文件**
   - 使用网格视图或列表视图浏览文件
   - 点击图片卡片查看详情
   - 双击图片打开内置查看器

3. **搜索文件**
   - 在搜索框输入文件名关键词
   - 实时过滤显示匹配结果

4. **分页导航**
   - 使用页码按钮切换页面
   - 或直接输入页码跳转
   - 点击「加载更多」获取更多数据

### 图片查看器

- **缩放**：鼠标滚轮或缩放滑块
- **拖拽**：按住左键拖动图片
- **切换**：左右方向键或点击按钮
- **适应窗口**：F 键或点击「适应窗口」按钮
- **原始大小**：1 键或点击「原始大小」按钮
- **关闭**：ESC 键或关闭窗口

### 代理配置

1. 点击顶部「⚙ 代理」按钮
2. 勾选「启用代理」
3. 选择代理类型（HTTP / SOCKS5）
4. 填写代理服务器地址和端口
5. 如需认证，填写用户名和密码
6. 点击「保存」立即生效

---

## ⚙️ 配置文件

配置文件位于 `config.yaml`，支持以下配置：

### 代理配置
```yaml
proxy:
  enabled: true          # 是否启用代理
  type: "http"          # 代理类型：http, socks5
  host: "127.0.0.1"     # 代理服务器地址
  port: 7890            # 代理端口
  username: ""          # 用户名（可选）
  password: ""          # 密码（可选）
```

### 界面配置
```yaml
ui:
  title: "OSS 文件浏览器"
  window_size: [1400, 900]
  theme: "light"
```

### 预览配置
```yaml
preview:
  cache_dir: "./cache"
  thumbnail_size: [200, 200]
  page_size: 20
```

---

## 🎯 支持的存储服务

- ✅ 阿里云 OSS
- ✅ 腾讯云 COS
- ✅ AWS S3
- ✅ MinIO
- ✅ 其他兼容 S3 协议的对象存储

**注意**：存储桶需要配置为公开读取权限，或提供公开访问的 URL。

---

## 🖼️ 截图预览

### 主界面 - 网格视图
![Grid View](screenshots/grid-view.png)

### 主界面 - 列表视图
![List View](screenshots/list-view.png)

### 图片查看器
![Image Viewer](screenshots/image-viewer.png)

---

## 🛠️ 技术栈

- **GUI 框架**：PyQt5
- **网络请求**：requests, QNetworkAccessManager
- **配置管理**：PyYAML
- **图片处理**：QPixmap (Qt 内置)

---

## 📝 项目结构

```
oss-file-browser/
├── gui/                      # GUI 模块
│   ├── main_window.py       # 主窗口
│   └── image_viewer.py      # 图片查看器
├── utils/                    # 工具模块
│   ├── oss_client.py        # OSS 客户端
│   ├── file_preview.py      # 文件预览
│   ├── thumbnail_manager.py # 缩略图管理
│   └── config_loader.py     # 配置加载
├── cache/                    # 缓存目录
├── config.yaml              # 配置文件
├── main.py                  # 主程序入口
├── requirements.txt         # 依赖列表
└── README.md               # 项目说明
```

---

## 📧 联系方式

如有问题或建议，欢迎：
- 提交 [Issue](https://github.com/your-username/oss-file-browser/issues)
- 发起 [Pull Request](https://github.com/your-username/oss-file-browser/pulls)

---

<div align="center">
**如果这个项目对你有帮助，请给个 ⭐️ Star 支持一下！**

