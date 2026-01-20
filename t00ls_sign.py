#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
''' 修改自 https://www.t00ls.net/viewthread.php?tid=55689 '''
import requests
import json
import hashlib
import os
import sys
import time
from typing import Optional, Dict, Any

class T00lsSign:
    def __init__(self):
        self.session = requests.Session()
        self._setup_headers()
        
    def _setup_headers(self):
        """设置请求头"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.t00ls.com',
            'Referer': 'https://www.t00ls.com/members-login.html',
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.session.headers.update(headers)
    
    def _safe_debug_response(self, response: requests.Response, max_chars: int = 300) -> Dict[str, Any]:
        """
        安全的响应调试信息，避免泄露敏感信息
        """
        debug_info = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'text_preview': response.text[:max_chars] if response.text else '空响应',
            'text_length': len(response.text) if response.text else 0,
            'url': response.url,
        }
        
        # 安全地显示部分信息（不显示完整的 cookies）
        print(f"状态码: {debug_info['status_code']}")
        print(f"响应大小: {debug_info['text_length']} 字符")
        
        # 检查响应内容是否包含敏感信息
        text_preview = debug_info['text_preview']
        if debug_info['text_length'] > 0:
            # 检查是否是 JSON
            if text_preview.strip().startswith('{') or text_preview.strip().startswith('['):
                print("响应格式: JSON")
                try:
                    parsed = json.loads(response.text)
                    # 只显示非敏感字段
                    safe_keys = ['status', 'message', 'formhash', 'success']
                    for key in safe_keys:
                        if key in parsed:
                            print(f"  {key}: {parsed[key]}")
                except:
                    print("  JSON解析失败（显示预览）")
                    print(f"  预览: {text_preview}")
            else:
                print(f"响应预览: {text_preview}")
        
        return debug_info
    
    def _get_env_var(self, var_name: str, default: str = '', required: bool = False) -> str:
        """安全地获取环境变量"""
        value = os.environ.get(var_name, default)
        
        if required and not value:
            print(f"错误: 缺少必要的环境变量 {var_name}")
            sys.exit(1)
            
        # 部分环境变量不显示完整值
        if var_name in ['T00LS_PASSWORD', 'T00LS_QANS'] and value:
            print(f"{var_name}: {'已设置（内容已隐藏）'}")
        else:
            print(f"{var_name}: {value if value else '未设置'}")
            
        return value
    
    def login(self) -> Optional[Dict[str, Any]]:
        """登录 T00ls"""
        print("\n=== 登录 T00ls ===")
        
        # 获取登录凭证
        uname = self._get_env_var('T00LS_USERNAME', required=True)
        pswd = self._get_env_var('T00LS_PASSWORD', required=True)
        
        # 密码是否为MD5格式
        password_hash = os.environ.get('T00LS_MD5', 'False').lower() == 'true'
        
        # 安全提问
        qesnum = self._get_env_var('T00LS_QID', '0')
        qan = self._get_env_var('T00LS_QANS', '')
        
        # 如果不是MD5格式，则转换为MD5
        if not password_hash:
            pswd = hashlib.md5(pswd.encode('utf-8')).hexdigest()
        
        # 登录数据
        logindata = {
            'action': 'login',
            'username': uname,
            'password': pswd,
            'questionid': qesnum,
            'answer': qan,
            'cookietime': '2592000'
        }
        
        print(f"登录用户: {uname}")
        print(f"安全提问ID: {qesnum}")
        
        try:
            # 登录请求
            response = self.session.post(
                'https://www.t00ls.com/login.json',
                data=logindata,
                timeout=30
            )
            
            debug_info = self._safe_debug_response(response)
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"登录请求失败，状态码: {response.status_code}")
                return None
            
            # 解析响应
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                
                # 分析常见的非JSON响应
                text = response.text.lower()
                if '验证码' in text or 'captcha' in text:
                    print("错误: 需要验证码，请手动登录检查")
                elif '密码错误' in text or 'password' in text:
                    print("错误: 用户名或密码错误")
                elif '安全提问' in text:
                    print("错误: 安全提问设置不正确")
                elif '频繁' in text:
                    print("错误: 登录过于频繁，请稍后再试")
                
                return None
            
            # 检查登录结果
            if result.get('status') != 'success':
                message = result.get('message', '未知错误')
                print(f"登录失败: {message}")
                return None
            
            print("登录成功！")
            if 'formhash' in result:
                print(f"获取到formhash: {result['formhash'][:8]}...")  # 只显示部分
            
            # 安全地检查cookies（不显示完整值）
            cookie_names = [c.name for c in self.session.cookies]
            print(f"获取到Cookies数量: {len(cookie_names)}")
            if cookie_names:
                print(f"Cookie名称: {', '.join(cookie_names[:3])}...")
            
            return result
            
        except requests.exceptions.Timeout:
            print("登录请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"网络请求异常: {e}")
            return None
    
    def sign(self, formhash: str) -> Optional[Dict[str, Any]]:
        """签到"""
        print("\n=== 执行签到 ===")
        
        if not formhash:
            print("错误: 缺少formhash参数")
            return None
        
        # 准备签到数据
        signdata = {
            'formhash': formhash,
            'signsubmit': "true"
        }
        
        try:
            # 短暂等待，避免请求过快
            time.sleep(1)
            
            # 签到请求
            response = self.session.post(
                'https://www.t00ls.com/ajax-sign.json',
                data=signdata,
                timeout=30
            )
            
            debug_info = self._safe_debug_response(response)
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"签到请求失败，状态码: {response.status_code}")
                return None
            
            # 解析响应
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                print("签到响应不是有效的JSON格式")
                return None
            
        except requests.exceptions.Timeout:
            print("签到请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"网络请求异常: {e}")
            return None
    
    def send_notification(self, title: str, content: str) -> bool:
        """发送Server酱通知"""
        sckey = self._get_env_var('T00LS_SCKEY')
        
        if not sckey:
            return False
        
        print("\n=== 发送通知 ===")
        
        try:
            datamsg = {
                "text": title,
                "desp": content
            }
            
            response = requests.post(
                f"https://sctapi.ftqq.com/{sckey}.send",
                data=datamsg,
                timeout=10
            )
            
            if response.status_code == 200:
                print("通知发送成功")
                return True
            else:
                print(f"通知发送失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"通知发送异常: {e}")
            return False
    
    def run(self):
        """主运行函数"""
        print("=== T00ls 自动签到脚本 ===")
        print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 登录
        login_result = self.login()
        if not login_result:
            print("登录失败，终止执行")
            sys.exit(1)
        
        # 签到
        formhash = login_result.get('formhash', '')
        sign_result = self.sign(formhash)
        
        if not sign_result:
            print("签到失败，无法获取结果")
            sys.exit(1)
        
        # 处理签到结果
        status = sign_result.get('status', '')
        message = sign_result.get('message', '')
        
        if status == 'success':
            print(f"签到成功！消息: {message}")
            
            # 发送成功通知
            content = f"用户登录成功\n签到结果: {message}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            self.send_notification("T00ls签到成功", content)
            
        elif message == 'alreadysign':
            print("今天已经签到过了！")
            
            # 发送重复签到通知
            content = f"用户今天已经签到过了\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            self.send_notification("T00ls重复签到", content)
            
        else:
            print(f"签到失败: {message}")
            
            # 发送失败通知
            content = f"签到失败\n错误信息: {message}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            self.send_notification("T00ls签到失败", content)
            
            sys.exit(1)
        
        print("\n=== 执行完成 ===")

def main():
    """主函数"""
    try:
        signer = T00lsSign()
        signer.run()
    except KeyboardInterrupt:
        print("\n用户中断执行")
        sys.exit(0)
    except Exception as e:
        print(f"程序异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
