#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务模块 - 基于IPTV API框架
"""

import asyncio
from aiohttp import web
from utils.config import config


async def run_service():
    """运行结果页面服务"""
    if not config.open_service:
        return
    
    app = web.Application()
    
    # 添加路由
    app.router.add_get('/', index_handler)
    app.router.add_static('/', path='output', name='static')
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', config.service_port)
    await site.start()
    
    print(f"🌐 服务启动成功: http://0.0.0.0:{config.service_port}")


async def index_handler(request):
    """首页处理器"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>IPTV直播流检测结果</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .file-list { list-style: none; padding: 0; }
            .file-list li { margin: 10px 0; }
            .file-list a { color: #007bff; text-decoration: none; }
            .file-list a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>🎬 IPTV直播流检测结果</h1>
        <p>检测完成时间: """ + str(asyncio.get_event_loop().time()) + """</p>
        <ul class="file-list">
    """
    
    # 添加文件列表
    import os
    if os.path.exists('output'):
        for file in os.listdir('output'):
            if file.endswith('.txt') or file.endswith('.m3u'):
                html += f'<li><a href="{file}">{file}</a></li>'
    
    html += """
        </ul>
    </body>
    </html>
    """
    
    return web.Response(text=html, content_type='text/html')
