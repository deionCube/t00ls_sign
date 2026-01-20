#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
''' 修改自 https://www.t00ls.net/viewthread.php?tid=55689 '''
import requests
import json
import hashlib
import os
import sys
import time

# 设置请求头，模拟浏览器
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'https://www.t00ls.com',
    'Referer': 'https://www.t00ls.com/members-login.html',
    'X-Requested-With': 'XMLHttpRequest',
}

def debug_response(response):
    """调试响应信息"""
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    print(f"响应内容前500字符: {response.text[:500] if response.text else '空响应'}")
    return response

def main():
    # 从环境变量获取凭证，提供默认值
    uname = os.environ.get('T00LS_USERNAME', '')
    pswd = os.environ.get('T00LS_PASSWORD', '')
    
    # 检查必要的环境变量
    if not uname or not pswd:
        print("错误: 缺少必要的环境变量 T00LS_USERNAME 或 T00LS_PASSWORD")
        sys.exit(1)
    
    # 密码是否为MD5格式
    password_hash = os.environ.get('T00LS_MD5', 'False').lower() == 'true'
    
    # 安全提问
    qesnum = os.environ.get('T00LS_QID', '0')
    qan = os.environ.get('T00LS_QANS', '')
    
    # Server酱的SCKEY
    SCKEY = os.environ.get('T00LS_SCKEY', '')
    
    # 如果不是MD5格式，则转换为MD5
    if not password_hash:
        pswd = hashlib.md5(pswd.encode('utf-8')).hexdigest()
    
    # 创建会话
    session = requests.Session()
    session.headers.update(headers)
    
    # 登录数据
    logindata = {
        'action': 'login',
        'username': uname,
        'password': pswd,
        'questionid': qesnum,
        'answer': qan,
        'cookietime': '2592000'  # 30天保持登录
    }
    
    print(f"尝试登录用户: {uname}")
    print(f"使用安全提问ID: {qesnum}")
    
    try:
        # 登录请求
        rlogin = session.post('https://www.t00ls.com/login.json', data=logindata, timeout=30)
        
        # 调试信息
        debug_response(rlogin)
        
        # 检查响应状态
        if rlogin.status_code != 200:
            print(f"登录请求失败，状态码: {rlogin.status_code}")
            sys.exit(1)
        
        # 检查响应内容是否为JSON
        if not rlogin.text.strip():
            print("错误: 响应内容为空")
            sys.exit(1)
        
        # 尝试解析JSON
        try:
            rlogj = json.loads(rlogin.text)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"实际返回的内容: {rlogin.text}")
            
            # 尝试从响应中提取错误信息
            if "验证码" in rlogin.text or "验证" in rlogin.text:
                print("错误: 可能需要验证码，请手动登录检查")
            elif "密码错误" in rlogin.text:
                print("错误: 用户名或密码错误")
            elif "安全提问" in rlogin.text:
                print("错误: 安全提问设置不正确")
            
            sys.exit(1)
        
        # 检查登录结果
        if rlogj.get("status") != "success":
            message = rlogj.get("message", "未知错误")
            print(f"登录失败: {message}")
            
            # 处理特定错误
            if "密码错误" in message:
                print("提示: 请检查密码是否正确，或者尝试使用MD5格式密码")
            elif "安全提问" in message:
                print("提示: 请检查安全提问ID和答案是否正确")
            elif "频繁" in message:
                print("提示: 登录过于频繁，请稍后再试")
            
            sys.exit(1)
        
        print("登录成功！")
        print(f"Formhash: {rlogj.get('formhash')}")
        
        # 获取cookies
        tscookie = requests.utils.dict_from_cookiejar(rlogin.cookies)
        print(f"获取到的Cookies: {tscookie}")
        
        # 等待一下，避免请求过快
        time.sleep(2)
        
        # 准备签到数据
        formhash = rlogj.get("formhash", "")
        if not formhash:
            print("错误: 未获取到formhash")
            sys.exit(1)
        
        signdata = {
            'formhash': formhash,
            'signsubmit': "true"
        }
        
        print("尝试签到...")
        
        # 签到请求
        rsign = session.post('https://www.t00ls.com/ajax-sign.json', data=signdata, timeout=30)
        
        # 调试信息
        debug_response(rsign)
        
        if rsign.status_code != 200:
            print(f"签到请求失败，状态码: {rsign.status_code}")
            sys.exit(1)
        
        # 解析签到结果
        try:
            rsinj = json.loads(rsign.text)
        except json.JSONDecodeError as e:
            print(f"签到响应JSON解析错误: {e}")
            print(f"实际返回的内容: {rsign.text}")
            sys.exit(1)
        
        # 处理签到结果
        if rsinj.get("status") == "success":
            message = rsinj.get("message", "签到成功")
            print(f"签到成功！消息: {message}")
            
            # Server酱通知
            if SCKEY:
                datamsg = {
                    "text": "T00ls签到成功！",
                    "desp": f"用户: {uname}\n消息: {message}\n原始响应: {rsign.text}"
                }
                try:
                    notify_resp = requests.post(f"https://sctapi.ftqq.com/{SCKEY}.send", 
                                               data=datamsg, timeout=10)
                    print(f"Server酱通知发送状态: {notify_resp.status_code}")
                except Exception as e:
                    print(f"Server酱通知发送失败: {e}")
        
        elif rsinj.get("message") == "alreadysign":
            print("今天已经签到过了！")
        else:
            message = rsinj.get("message", "未知错误")
            print(f"签到失败: {message}")
            
            # Server酱通知失败
            if SCKEY:
                datamsg = {
                    "text": "T00ls签到失败",
                    "desp": f"用户: {uname}\n错误: {message}\n原始响应: {rsign.text}"
                }
                try:
                    requests.post(f"https://sctapi.ftqq.com/{SCKEY}.send", data=datamsg, timeout=10)
                except:
                    pass
            
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"网络请求异常: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
