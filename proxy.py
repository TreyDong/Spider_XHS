#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用requests请求代理服务器
请求http和https网页均适用
"""
import random
import re
from concurrent.futures import ThreadPoolExecutor

import requests


# 提取代理API接口，获取1个代理IP

# 假设这是从文件中读取的代理列表
def read_proxies():
    """从文件中读取代理列表"""
    with open("https.txt", "r") as file:
        proxies = file.read().splitlines()

    return proxies

def get_proxies():
    """获取代理列表"""
    api_url = "http://api.89ip.cn/tqdl.html?api=1&num=100&port=&address=&isp="

    # 获取API接口返回的代理IP
    proxy_ip = requests.get(api_url)
    # 使用正则表达式提取 IP:端口 格式的字符串
    ip_port_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}\b')
    ip_list = ip_port_pattern.findall(proxy_ip.text)
    if not ip_list:
        print("未找到有效的代理IP")
        return []
    return ip_list

def check_proxy(proxy):
    """验证代理是否有效"""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

    try:
        # 使用 httpbin.org 测试代理
        response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=5)
        if response.status_code == 200:
            print(f"代理 {proxy} 有效")
            return proxy
    except Exception as e:
        # 代理无效，忽略
        pass
    return None

def get_working_proxy(proxy_list=None):
    """获取一个有效的代理"""
    # 随机打乱代理列表
    if proxy_list is None:
        proxy_list = read_proxies()
    random.shuffle(proxy_list)

    # 使用线程池并行验证代理
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(check_proxy, proxy_list[:20]))  # 验证前20个代理

    # 过滤出有效的代理
    working_proxies = [p for p in results if p is not None]

    if working_proxies:
        proxy =  random.choice(working_proxies)
        return {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
    else:
        print("没有找到有效的代理")
        return None


def make_request_with_proxy(url):
    """使用随机选择的有效代理发送请求"""
    proxies = get_working_proxy()

    try:
        response = requests.get(url, proxies=proxies, timeout=10)
        return response
    except Exception as e:
        # 失败时尝试直接连接
        return requests.get(url, timeout=10)

# 使用示例
if __name__ == "__main__":
    url = "https://www.baidu.com"  # 替换为你要请求的URL
    response = make_request_with_proxy(url)

    if response.status_code == 200:
        print(f"请求成功，响应长度: {len(response.text)}")
    else:
        print(f"请求失败，状态码: {response.status_code}")