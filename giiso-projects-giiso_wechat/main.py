#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
# giiso客户端依赖库
import os
import socket
import threading
from datetime import timedelta

import requests
import webview
from flask import Flask, render_template
from flask import session
from flask_cors import CORS

from channel import channel_factory
from channel.channel import Channel
from configuration import config
from logger import logger

app = Flask(__name__)
app.secret_key = 'linkco'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
CORS(app)
channel_name = config.Giiso.get('chat_channel')
logger.info("启动channel:"+channel_name)
channel:Channel = channel_factory.create_channel(channel_name)

def start_channel():
    channel.startup()

@app.route('/qr_status', methods=['GET'])
def get_qr_status():
    base_url = config.Giiso.get("base_url")
    channel_type = 1 if channel_name == "wechat" else 2
    data = channel.get_user_info()
    if not data:
        logger.info("get_user_info none,未登录")
        return {'code': 200, "data": {'loginStatus': "未登录", 'channelType': channel_type, "baseURL": base_url}}

    return {'code': 200, "data": {'loginStatus': "已登录", 'channelType': channel_type, "baseURL": base_url, 'userInfo': {
            'wxuin': data.get('wxid'),
            'wxname': data.get('name')
        }}}
    
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/get_alive')
def get_alive():
    return {'code': 200, "data": {'alive': True if channel.get_user_info() else False}}
@app.route('/exit_login')
def set_exit_login():
    if exit_wx_login():
        session['main_run_started']-=1
        os._exit(0)
        return {'code': 200, "data": {'Status': "退出执行完毕"}}
    else:
        return {'code': 500, "data": {'Status': "退出执行失败,请重试"}}


def exit_wx_login():
    if not channel:
        return True
    url = config.Giiso.get("base_url") + "/monitor/report"
    data = channel.get_user_info()
    if not data:
        channel.cleanup()  # 退出前清理环境
        return True
    # 构建请求体
    payload = {
        "type": "1",
        "wxuin": data.get('wxid'),
        "wxname": data.get('name'),
        "alertStatus": "0"
    }
    
    # 设置请求头
    headers = {
        'Content-Type': 'application/json'
    }

    # 发送POST请求
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    logger.info(response.text)
    if(response.json()['code']=="0"):
        channel.cleanup()  # 退出前清理环境
        return True
    channel.cleanup()  # 退出前清理环境
    return False

def exit_callback():
    logger.info("用户主动关闭智能体窗口")
    exit_wx_login()
    # channel.cleanup()
    # exit_event.set()  # 通知退出事件
    logger.info("退出成功")
    os._exit(0)
    # sys.exit(0)
        
@app.before_request
def make_session_temporary():
    session.permanent = False  # session 会在用户关闭浏览器时失效
    session['main_run_started']=0
# 启动 Flask 应用的函数
def start_flask(port=5000):
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    # exit_event.wait()

def find_free_port(start_port=5000):
    """
    查找未被占用的端口
    """
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                port += 1

def get_ip():
    hostname = socket.gethostname()  # 获取本机主机名
    ip_address = socket.gethostbyname(hostname)  # 获取对应的IP地址
    return ip_address

# 使用 pywebview 显示 Flask 应用
if __name__ == '__main__':
    
    # 在后台线程启动 Flask 应用
    port = find_free_port()
    flask_thread = threading.Thread(target=start_flask,args=(port,))
    flask_thread.daemon = True
    flask_thread.start()
    
    main_thread = threading.Thread(target=start_channel)
    main_thread.daemon = True
    main_thread.start()
    
    # 使用 pywebview 创建窗口，指向 Flask 应用的 URL
    ip = get_ip()
    url = f'http://{ip}:{port}'
    logger.info(f"webview加载url： {url}")
    windows = webview.create_window('企业AI智能体', url)
    windows.events.closed += exit_callback
    webview.start()