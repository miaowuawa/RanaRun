#读取envinfo.json文件，获取可用的所有环境变量
import json
import random
import random_user_agent
import os
from utils.textparser.ua import generate_ua
env_list = []
def init():
    global env_list
    with open("envinfo.json", "r") as f:
        envinfo = json.load(f)
        #获取可用的所有环境变量
        env_list = []
        for mobileSource in envinfo["mobileSource"]:
            for equipmentType in envinfo["equipmentType"]:
                for deviceVersion in envinfo["deviceVersion"]:
                    for deviceSpec in envinfo["deviceSpec"]:
                        for appHeader in envinfo["appHeader"]:
                            env_list.append({
                                "mobileSource": mobileSource,
                                "equipmentType": equipmentType,
                                "deviceVersion": deviceVersion,
                                "deviceSpec": deviceSpec,
                                "appHeader": appHeader
                            })

def generate_random_env(latest_ver: str):
    header_tmp = {}
    """
    随机生成一个环境
    1.从每个可用字段中随机选择一个值，组合起来就是env了
    2.设置一个空的cookies,通过首次请求https://www.allcpp.cn/ 获取服务端给的set cookies头
    """
    # 直接从env_list中随机选择一个完整的环境配置
    random_env = random.choice(env_list)
    for key in random_env:
        header_tmp[key] = random_env[key]
    header_tmp["appVersion"] = latest_ver
    header_tmp["User-Agent"] = generate_ua(latest_ver, header_tmp["deviceVersion"])
    header_tmp["Cookie"] = ""
    #后面这些是固定的，暂时不管
    header_tmp["Accept-Language"] = "zh-CN,zh;q=1"
    header_tmp["Accept-Encoding"] = "gzip, deflate, br"
    header_tmp["Accept"] = "*/*"
    header_tmp["Connection"] = "keep-alive"
    # 到此就完成了环境生成
    # 接下来就把这堆东西导出成一个json就行了
    env = {
        "header": header_tmp
    }
    return env

def generate_browser_ua():
    # 直接返回一个固定的手机浏览器UA
    return "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36 EdgA/46.1.2.5141"
    


    

    

    