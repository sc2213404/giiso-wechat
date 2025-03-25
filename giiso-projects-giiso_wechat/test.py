# -*- coding: utf-8 -*-
import socket

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return False  # 端口未被占用
        except OSError:
            return True  # 端口被占用

def find_available_port(start_port):
    """找到一个可用的端口"""
    port = start_port
    while True:
        if not is_port_in_use(port) and not is_port_in_use(port + 1):
            return port
        port += 2  # 如果 port 或 port+1 被占用，跳到 port+2 重新开始检查

# 示例使用
start_port = 8000
available_port = find_available_port(start_port)
print(f"找到的可用端口是: {available_port}")




