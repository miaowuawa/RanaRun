import requests
import utils.urls
from utils.env2sess import env_to_request_session

def get_login_code(env:dict, country:str, phone:str, password:str) -> tuple[bool, str]:
    #使用env创建session，同时携带header和cookie
    session = env_to_request_session(env)
    url = utils.urls.USERBASE_URL_WEB + utils.urls.USER_LOGINCODE_URL.format(country=country, phone=phone)
    
    # 打印请求信息
    print(f"[调试][获取验证码]请求URL: {url}")
    print(f"[调试][获取验证码]请求Headers: {dict(session.headers)}")
    try:
        print(f"[调试][获取验证码]请求Cookies: {dict(session.cookies)}")
    except Exception:
        # 处理可能的CookieConflictError
        cookie_dict = {}
        for cookie in session.cookies:
            cookie_dict[cookie.name] = cookie.value
        print(f"[调试][获取验证码]请求Cookies: {cookie_dict}")
    
    #get请求，获取验证码
    resp = session.get(url)
    
    # 打印响应信息
    print(f"[调试][获取验证码]响应状态码: {resp.status_code}")
    print(f"[调试][获取验证码]响应Headers: {dict(resp.headers)}")
    print(f"[调试][获取验证码]响应内容: {resp.text}")
    
    if resp.status_code == 200:
        return True, "验证码已发送"
    else:
        # 返回失败状态和服务端响应内容
        try:
            response_text = resp.text
        except:
            response_text = str(resp.content)
        return False, response_text

def user_login_sms(env:dict, country:str, phone:str, code:str) -> tuple[bool, str]:
    #使用env创建session，同时携带header和cookie
    session = env_to_request_session(env)
    url = utils.urls.USERBASE_URL_WEB + utils.urls.USER_SMSLOGIN_URL
    data = {"phone": phone, "country": country, "phoneCode": code}
    
    # 打印请求信息
    print(f"[调试][短信登录]请求URL: {url}")
    print(f"[调试][短信登录]请求Headers: {dict(session.headers)}")
    try:
        print(f"[调试][短信登录]请求Cookies: {dict(session.cookies)}")
    except Exception:
        # 处理可能的CookieConflictError
        cookie_dict = {}
        for cookie in session.cookies:
            cookie_dict[cookie.name] = cookie.value
        print(f"[调试][短信登录]请求Cookies: {cookie_dict}")
    print(f"[调试][短信登录]请求数据: {data}")
    
    #post请求，登录，urlencodedform
    #{
    #    "phone":?,
    #    "country:?",
    #    "phoneCode:?"
    #}
    #以上是请求体格式
    resp = session.post(url, data=data)
    
    # 打印响应信息
    print(f"[调试][短信登录]响应状态码: {resp.status_code}")
    print(f"[调试][短信登录]响应Headers: {dict(resp.headers)}")
    print(f"[调试][短信登录]响应内容: {resp.text}")
    
    if resp.status_code == 200:
        return True, "登录成功"
    else:
        # 返回失败状态和服务端响应内容
        try:
            response_text = resp.text
        except:
            response_text = str(resp.content)
        return False, response_text