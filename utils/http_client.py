import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 禁用 SSL 验证警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class HttpClient:
    """HTTP 客户端，默认禁用 SSL 验证"""

    def __init__(self, verify_ssl=False):
        self.session = requests.Session()
        self.session.verify = verify_ssl

    def get(self, url, **kwargs):
        return self.session.get(url, **kwargs)

    def post(self, url, **kwargs):
        return self.session.post(url, **kwargs)

    def put(self, url, **kwargs):
        return self.session.put(url, **kwargs)

    def delete(self, url, **kwargs):
        return self.session.delete(url, **kwargs)

    def request(self, method, url, **kwargs):
        return self.session.request(method, url, **kwargs)


# 全局 HTTP 客户端实例（默认禁用 SSL 验证）
http = HttpClient(verify_ssl=False)
