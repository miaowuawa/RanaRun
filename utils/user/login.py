import requests
import utils.urls
from utils.env2sess import env_to_request_session

def get_login_code(env:dict, country:str, phone:str) -> tuple[bool, str]:
    #使用env创建session，同时携带header和cookie
    session = env_to_request_session(env)
    url = utils.urls.USERBASE_URL_WEB + utils.urls.USER_LOGINCODE_URL.format(country=country, phone=phone)
    
    #get请求，获取验证码
    resp = session.get(url)

    
    if resp.status_code == 200:
        return True, "验证码已发送"
    else:
        # 返回失败状态和服务端响应内容
        try:
            response_text = resp.text
        except:
            response_text = str(resp.content)
        return False, response_text

def user_login_sms(env:dict, country:str, phone:str, code:str) -> tuple[requests.Session, bool, str]:
    #使用env创建session，同时携带header和cookie
    session = env_to_request_session(env)
    url = utils.urls.USERBASE_URL_WEB + utils.urls.USER_SMSLOGIN_URL
    data = {"phone": phone, "country": country, "phoneCode": code}

    #post请求，登录，urlencodedform
    #{
    #    "phone":?,
    #    "country:?",
    #    "phoneCode:?"
    #}
    #以上是请求体格式
    resp = session.post(url, data=data)
    
    if resp.status_code == 200:
        return session, True, "登录成功"
    else:
        # 返回失败状态和服务端响应内容
        try:
            response_text = resp.text
        except:
            response_text = str(resp.content)
        return session, False, response_text