import requests
import utils.urls
from utils.env2sess import env_to_request_session

def check_if_user_exists(env:dict, country:str, phone:str) -> bool:
    #使用env创建session，同时携带header和cookie
    session = env_to_request_session(env)
    url = utils.urls.USERBASE_URL_WEB + utils.urls.USER_CHECK_URL.format(country=country, phone=phone)
    resp = session.get(url)
    if resp.status_code == 200:
        return resp.content == b"true"
    else:
        return False
