# 直播流检测工具

## 功能特性
- 多进程404检测
- 多进程速度检测
- 画面变化检测
- 智能分组输出
- 进度可视化
- **白名单支持**：绕过画面检测，最低等级为useful

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法
```bash
python url-check_v-txt10.py
```

## 文件说明

### 资源文件
- `resources.m3u` - 本地M3U格式资源
- `resources.txt` - 本地TXT格式资源
- `white.txt` - 白名单文件

### 白名单功能
- **绕过画面检测**：白名单条目直接标记为有效
- **最低等级保证**：白名单条目最低为useful等级
- **匹配方式**：支持名称和URL匹配

#### white.txt格式示例
```
# 白名单文件示例
# 支持URL和名称匹配，每行一个
# 以#开头的行为注释

# 按名称匹配
CCTV-1
湖南卫视

# 按URL匹配
http://example.com/cctv1.m3u8

# 按IP地址匹配
http://8.218.84.3:8885/
```

## 输出文件
- `live+excellent+{daytime}.txt` - 超高清流
- `live+wonderful+{daytime}.txt` - 高清流  
- `live+good+{daytime}.txt` - 标清流
- `live+useful+{daytime}.txt` - 可用流

## 核心文件
- `url-check_v-txt10.py` - 主程序
- `video_check_worker.py` - 画面检测工作进程
