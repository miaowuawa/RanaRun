import random
import requests

# 常用桌面浏览器User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def _get_random_user_agent():
    """获取随机User-Agent"""
    return random.choice(USER_AGENTS)

def _get_headers():
    """获取请求头"""
    return {
        "User-Agent": _get_random_user_agent(),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.allcpp.cn/"
    }

# 硬编码的省份/城市数据，作为API请求失败时的备用
PROVINCE_CITY_DATA = [
    {"code": 110000, "name": "北京", "cityList": [{"code": 110100, "name": "北京", "provinceCode": 110000}]},
    {"code": 310000, "name": "上海", "cityList": [{"code": 310100, "name": "上海", "provinceCode": 310000}]},
    {"code": 440000, "name": "广东", "cityList": [
        {"code": 440000, "name": "全部", "provinceCode": 440000},
        {"code": 440100, "name": "广州", "provinceCode": 440000},
        {"code": 440300, "name": "深圳", "provinceCode": 440000},
        {"code": 440400, "name": "珠海", "provinceCode": 440000},
        {"code": 440500, "name": "汕头", "provinceCode": 440000},
        {"code": 440600, "name": "佛山", "provinceCode": 440000},
        {"code": 440700, "name": "江门", "provinceCode": 440000},
        {"code": 440800, "name": "湛江", "provinceCode": 440000},
        {"code": 440900, "name": "茂名", "provinceCode": 440000},
        {"code": 441300, "name": "惠州", "provinceCode": 440000},
        {"code": 441500, "name": "汕尾", "provinceCode": 440000},
        {"code": 442000, "name": "中山", "provinceCode": 440000},
        {"code": 445100, "name": "潮州", "provinceCode": 440000},
        {"code": 445200, "name": "揭阳", "provinceCode": 440000}
    ]},
    {"code": 340000, "name": "安徽", "cityList": [
        {"code": 340000, "name": "全部", "provinceCode": 340000},
        {"code": 340100, "name": "合肥", "provinceCode": 340000},
        {"code": 340200, "name": "芜湖", "provinceCode": 340000},
        {"code": 340300, "name": "蚌埠", "provinceCode": 340000},
        {"code": 341300, "name": "宿州", "provinceCode": 340000}
    ]},
    {"code": 500000, "name": "重庆", "cityList": [{"code": 500100, "name": "重庆", "provinceCode": 500000}]},
    {"code": 350000, "name": "福建", "cityList": [
        {"code": 350000, "name": "全部", "provinceCode": 350000},
        {"code": 350100, "name": "福州", "provinceCode": 350000},
        {"code": 350200, "name": "厦门", "provinceCode": 350000},
        {"code": 350500, "name": "泉州", "provinceCode": 350000},
        {"code": 350600, "name": "漳州", "provinceCode": 350000},
        {"code": 350900, "name": "宁德", "provinceCode": 350000}
    ]},
    {"code": 620000, "name": "甘肃", "cityList": [{"code": 620100, "name": "兰州", "provinceCode": 620000}]},
    {"code": 450000, "name": "广西", "cityList": [
        {"code": 450000, "name": "全部", "provinceCode": 450000},
        {"code": 450100, "name": "南宁", "provinceCode": 450000},
        {"code": 450200, "name": "柳州", "provinceCode": 450000},
        {"code": 450300, "name": "桂林", "provinceCode": 450000}
    ]},
    {"code": 520000, "name": "贵州", "cityList": [
        {"code": 520000, "name": "全部", "provinceCode": 520000},
        {"code": 520100, "name": "贵阳", "provinceCode": 520000},
        {"code": 522700, "name": "黔南", "provinceCode": 520000}
    ]},
    {"code": 460000, "name": "海南", "cityList": [
        {"code": 460000, "name": "全部", "provinceCode": 460000},
        {"code": 460100, "name": "海口", "provinceCode": 460000},
        {"code": 460200, "name": "三亚", "provinceCode": 460000}
    ]},
    {"code": 130000, "name": "河北", "cityList": [
        {"code": 130000, "name": "全部", "provinceCode": 130000},
        {"code": 130100, "name": "石家庄", "provinceCode": 130000},
        {"code": 130200, "name": "唐山", "provinceCode": 130000},
        {"code": 130500, "name": "邢台", "provinceCode": 130000},
        {"code": 130800, "name": "承德", "provinceCode": 130000},
        {"code": 130900, "name": "沧州", "provinceCode": 130000}
    ]},
    {"code": 410000, "name": "河南", "cityList": [
        {"code": 410000, "name": "全部", "provinceCode": 410000},
        {"code": 410100, "name": "郑州", "provinceCode": 410000},
        {"code": 410200, "name": "开封", "provinceCode": 410000},
        {"code": 410300, "name": "洛阳", "provinceCode": 410000},
        {"code": 410400, "name": "平顶山", "provinceCode": 410000},
        {"code": 411100, "name": "漯河", "provinceCode": 410000}
    ]},
    {"code": 230000, "name": "黑龙江", "cityList": [{"code": 230100, "name": "哈尔滨", "provinceCode": 230000}]},
    {"code": 420000, "name": "湖北", "cityList": [
        {"code": 420000, "name": "全部", "provinceCode": 420000},
        {"code": 420100, "name": "武汉", "provinceCode": 420000},
        {"code": 420600, "name": "襄阳", "provinceCode": 420000}
    ]},
    {"code": 430000, "name": "湖南", "cityList": [
        {"code": 430000, "name": "全部", "provinceCode": 430000},
        {"code": 430100, "name": "长沙", "provinceCode": 430000},
        {"code": 430200, "name": "株洲", "provinceCode": 430000},
        {"code": 430300, "name": "湘潭", "provinceCode": 430000},
        {"code": 430400, "name": "衡阳", "provinceCode": 430000},
        {"code": 433100, "name": "湘西", "provinceCode": 430000}
    ]},
    {"code": 220000, "name": "吉林", "cityList": [
        {"code": 220000, "name": "全部", "provinceCode": 220000},
        {"code": 220100, "name": "长春", "provinceCode": 220000},
        {"code": 220200, "name": "吉林市", "provinceCode": 220000}
    ]},
    {"code": 320000, "name": "江苏", "cityList": [
        {"code": 320000, "name": "全部", "provinceCode": 320000},
        {"code": 320100, "name": "南京", "provinceCode": 320000},
        {"code": 320200, "name": "无锡", "provinceCode": 320000},
        {"code": 320300, "name": "徐州", "provinceCode": 320000},
        {"code": 320400, "name": "常州", "provinceCode": 320000},
        {"code": 320500, "name": "苏州", "provinceCode": 320000},
        {"code": 320600, "name": "南通", "provinceCode": 320000},
        {"code": 320700, "name": "连云港", "provinceCode": 320000},
        {"code": 320800, "name": "淮安", "provinceCode": 320000},
        {"code": 320900, "name": "盐城", "provinceCode": 320000},
        {"code": 321000, "name": "扬州", "provinceCode": 320000},
        {"code": 321100, "name": "镇江", "provinceCode": 320000},
        {"code": 321200, "name": "泰州", "provinceCode": 320000},
        {"code": 321300, "name": "宿迁", "provinceCode": 320000}
    ]}
]

def get_province_city_list():
    """
    从API获取省份/城市列表，如果失败则返回硬编码数据
    :return: 包含省份和城市信息的字典列表
    """
    url = "https://www.allcpp.cn/api/event/cityList.do"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess') and data.get('result'):
            return data['result']
        return PROVINCE_CITY_DATA
    except Exception:
        return PROVINCE_CITY_DATA

def get_provinces():
    """
    获取所有省份列表
    :return: 省份列表，每个元素为 {"code": 省份代码, "name": 省份名称}
    """
    province_city_list = get_province_city_list()
    return [
        {"code": province["code"], "name": province["name"]}
        for province in province_city_list
    ]

def get_cities_by_province(province_code):
    """
    根据省份代码获取城市列表
    :param province_code: 省份代码
    :return: 城市列表，每个元素为 {"code": 城市代码, "name": 城市名称}
    """
    province_city_list = get_province_city_list()
    for province in province_city_list:
        if province["code"] == province_code:
            return province.get("cityList", [])
    return []
