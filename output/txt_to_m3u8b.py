# -*- coding: utf-8 -*-
"""
简化版TXT转M3U8工具，解决逗号问题
"""

import os
import sys

def txt_to_m3u8_simple(txt_file_path, m3u8_file_path):
    """简化版转换函数，支持CSV和TXT格式"""
    try:
        # 尝试多种编码方式
        content = None
        for encoding in ['utf-8', 'gbk', 'latin-1']:
            try:
                with open(txt_file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            print(f"[ERROR] 无法读取文件: {os.path.basename(txt_file_path)}")
            return False
            
        lines = content.splitlines()
        
        with open(m3u8_file_path, 'w', encoding='utf-8') as m3u8_file:
            m3u8_file.write("#EXTM3U\n")
            current_group = "默认分组"
            
            # 检查是否为CSV格式
            is_csv = txt_file_path.endswith('.csv')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 处理CSV格式
                if is_csv:
                    # 跳过CSV头部
                    if line.startswith('名称,URL,分类'):
                        continue
                    
                    # 解析CSV行：名称,URL,分类,速度
                    parts = line.split(',')
                    if len(parts) >= 3:
                        tvg_name = parts[0].strip()
                        url = parts[1].strip()
                        current_group = parts[2].strip()
                        
                        # 写入M3U8格式
                        m3u8_file.write(f"#EXTINF:-1 tvg-name=\"{tvg_name}\" group-title=\"{current_group}\",{tvg_name}\n")
                        m3u8_file.write(f"{url}\n")
                else:
                    # 处理TXT格式
                    # 处理分组行
                    if line.endswith(",#group#"):
                        current_group = line.replace(",#group#", "")
                        continue
                    
                    # 跳过纯分组行
                    if line == "#group#" or line == ",#group#":
                        continue
                    
                    # 处理频道行
                    if "," in line and "http" in line:
                        comma_pos = line.find(",")
                        tvg_name = line[:comma_pos].strip()
                        url = line[comma_pos+1:].strip()
                    else:
                        # 处理纯链接格式
                        tvg_name = os.path.basename(line).split('.')[0] if line else "Unknown"
                        url = line
                    
                    # 写入M3U8格式
                    m3u8_file.write(f"#EXTINF:-1 tvg-name=\"{tvg_name}\" group-title=\"{current_group}\",{tvg_name}\n")
                    m3u8_file.write(f"{url}\n")
        
        print(f"[SUCCESS] 转换完成: {os.path.basename(m3u8_file_path)}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 转换失败: {str(e)}")
        return False

def convert_all_txt_in_directory(directory_path="."):
    """转换目录内所有txt文件为m3u文件"""
    try:
        txt_files = []
        for file in os.listdir(directory_path):
            if file.endswith('.txt') and not file.startswith('.'):
                txt_files.append(file)
        
        if not txt_files:
            print("[INFO] 当前目录没有找到txt文件")
            return
        
        print(f"[INFO] 找到 {len(txt_files)} 个txt文件")
        
        success_count = 0
        for txt_file in txt_files:
            txt_path = os.path.join(directory_path, txt_file)
            m3u_file = os.path.splitext(txt_file)[0] + '.m3u'
            m3u_path = os.path.join(directory_path, m3u_file)
            
            print(f"[PROCESS] 转换: {txt_file} -> {m3u_file}")
            if txt_to_m3u8_simple(txt_path, m3u_path):
                success_count += 1
        
        print(f"[COMPLETE] 转换完成: {success_count}/{len(txt_files)} 个文件成功")
        
    except Exception as e:
        print(f"[ERROR] 批量转换失败: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        txt_file = sys.argv[1]
        m3u8_file = sys.argv[2]
        txt_to_m3u8_simple(txt_file, m3u8_file)
    elif len(sys.argv) == 2:
        # 指定目录模式
        directory = sys.argv[1]
        convert_all_txt_in_directory(directory)
    else:
        # 缺省状态：转换当前目录所有txt文件
        print("[INFO] 缺省模式：转换当前目录所有txt文件")
        convert_all_txt_in_directory(".")
