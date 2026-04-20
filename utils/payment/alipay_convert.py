import base64
import json
import requests
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AiliPay(object):
    def __init__(self):
        self.private_key = '''-----BEGIN RSA PRIVATE KEY-----
            MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCL1i+fn62CHFUAEIlsuSU8DM4PhqjqiW4itBCne/MRfKIsDCdevuw1OHCV80ICUjd5ke+Rr7AvwO3gU88M6UjGvCrJK/krElYigJswehgjmRMJAay8tO78h2ABgwvoUfkPOP7IHJaxiUaZGGzifd2cFNNRgRN9H20HTvlzmIhgBOcSVEVmJugo2BjzOzU4/Lu10D/arOn9EeofXXpfEBAo799OTm7nqXzKMA9Egdl/8ZIPhXrbMl6CVg4syYV5t46T0W7frRw7L78b2O3inxeH2LchEjDHKDQTNiexJ/xFQVCh1iVgoIwaKBLC6LMTPh06gZVDURKJB9wnfyTJ+hpNAgMBAAECggEABykkryviGrOQtrwiDWs9uOF++9SNedUnyqcl4y25uL+FHnRQ380vE1qciVE3pB7JsHQErJUulINwqvgfti2MCIFCP6L803PQ7Vtglw7phYklLGTlj5REWLIl/G3VgkQQWPM2ONEd9mFtOBHEIaUIYCHA4H+Xm+SsFJ+6rmy1LxV9ZW5ddDeGRIgZLCIDDJtsaEuc18RbvFE2S98lha1LAdL1Una210Rw70IUH358VzsRf/jfsaFeZZGnF1n7PXw5eor5aEKguCioiTqTyRfPtege2KdcRrhUWP2+JuYhFvA6eFq3/87hHizI6/Yrg2AggYUUY6gA6eS1tjE1gqXTEQKBgQDoed+flyVnqsCX3jWYybpsUy5rBDzVZODcoVbvgEl8Xw5R7nR93+R1g2NYmDPnS5XiEKWtNNYewo6Pv2pmRMbuyKX6B41a0IsDMIG1vAqbdc7Xj91eLCfTVPqS0AiGIFJX5CWFOCs70rglG3h/nZe5hcR11ltOAWqSqRlvcGcrUwKBgQCZ/I4O4T0d7s7BJAkHo41LIo3pVA7IkRn4DQTpF1BxElnWMNv6Vov0YbnXz84cfGmq4bTOX8ueHSTP0a0JR0nMvbWukj9p8C7nGmXJuHXpLJjraHTT+O8OkE30VajEyP2CnPNryfR66oi2XpUpRcXTj7KaVb2UyResIgbWUHiP3wKBgQCQUA+UtzQeHW5/GA73cMrMMfrPrgrBgWThMTqRZHa5wRxXmgowlYrxtAU42wrlWxOJCUJ/uhvtbmMnMvEu2SUQ1/fItWV3aZvR+AudMET5anFjeUg3DHwQgWEnQAL6mBflvZfZEhwsf8uWJW5w8fhcz4A8kjuNue1Za6WBeypgRwKBgB4Ml9g1ggy2TmiIVK7F7suruY+/1Ia1MiEiwUOPRiZak2dl73eBrhwJeg+wQKN0b9Zl5zeioASB4W4gl6jI3ZDzsGGZroBI245Dq3ta4L+Y8Vp27t1ypYvtAxlcIewM4NO9Nw9gwLG/1N/pwyfjssAfOZY+hxliyJjRpw3pdC13AoGAETuOBJDCHiGqBAFL7L0ctGdynOKOC4aMxbCeWYLQWYr3FtMJ11rCib4XxfGN6k/dXAcF97ivZjs8xCSHHx4ruzAFJyF9dshpMMeZB6pWDa0NX/jB9zYMGEbFiGz6uBqCYeL028xh8Nn2tmoXl5hEK5/QuUM0XSRt9ELLjFYAm4s=
            -----END RSA PRIVATE KEY-----
            '''
        self.public_key = '''-----BEGIN PUBLIC KEY-----
            MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDENksAVqDoz5SMCZq0bsZwE+I3NjrANyTTwUVSf1+ec1PfPB4tiocEpYJFCYju9MIbawR8ivECbUWjpffZq5QllJg+19CB7V5rYGcEnb/M7CS3lFF2sNcRFJUtXUUAqyR3/l7PmpxTwObZ4DLG258dhE2vFlVGXjnuLs+FI2hg4QIDAQAB
            -----END PUBLIC KEY-----'''
        self.key = '23h4fhdilenbs741kogue1tl'

    def encrypt_3des(self,data):
        cipher = DES3.new(self.key.encode(), DES3.MODE_ECB)
        padded_data = pad(data.encode(), DES3.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        return encrypted_data

    def decrypt_3des(self,data):
        ct_bytes = base64.b64decode(data)
        cipher = DES3.new(self.key.encode(), DES3.MODE_ECB)
        plain_text = unpad(cipher.decrypt(ct_bytes), DES3.block_size)
        return plain_text.decode()

    def rsa_encrypt(self, message):
        cipher = Cipher_pkcs1_v1_5.new(RSA.importKey(self.public_key))
        cipher_text = base64.b64encode(cipher.encrypt(message.encode())).decode()
        return cipher_text

    def rsa_decrypt(self, text):
        cipher = Cipher_pkcs1_v1_5.new(RSA.importKey(self.private_key))
        retval = cipher.decrypt(base64.b64decode(text), 'ERROR').decode('utf-8')
        return retval

    def convert_alipay_to_h5(self,alipay_sdk):
        json_request = '{"tid":"1612f577ee44ef450cc06232719e3404a5d1d855cc6246013f296702c6bdddf5","user_agent":"Msp/9.1.5 (Android 12;Linux 4.4.146;zh_CN;http;540*960;21.0;WIFI;87699552;32617;1;000000000000000;000000000000000;8efce46e85;GOOGLE;H002;false;00:00:00:00:00:00;-1.0;-1.0;sdk-and-lite;65r7u2pfruicqrn;r2agza5c56pzmev;<unknown ssid>;02:00:00:00:00:00)","has_alipay":false,"has_msp_app":false,"external_info":"' + alipay_sdk + '","app_key":"2022002145675770","utdid":"87314235C8AE4E773747689735D33F58","new_client_key":"8efcf8b134","action":{"type":"cashier","method":"main"},"gzip":true}'
        encrypted_data = base64.b64encode(self.encrypt_3des(json_request)).decode()
        parameter1 = self.rsa_encrypt(self.key)
        parameter2 = format(len(parameter1), '08X')
        parameter3 = format(len(encrypted_data), '08X')
        req_data = parameter2 + parameter1 + parameter3 + encrypted_data
        url = 'http://mcgw.alipay.com/gateway.do'
        data = {"data": {"device": "GOOGLE-H002", "namespace": "com.alipay.mobilecashier", "api_name": "com.alipay.mcpay",
                         "api_version": "4.0.2", "params": {"req_data": req_data}}}
        headers = {
            'Accept-Charset': 'UTF-8',
            'Connection': 'Keep-Alive',
            'Content-Type': 'application/octet-stream;binary/octet-stream',
            'Cookie': 'zone=RZ43A',
            'Cookie2': '$Version=1',
            'Host': 'mcgw.alipay.com',
            'Keep-Alive': 'timeout=180, max=100',
            'User-Agent': 'msp'
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        json_data = json.loads(response.text)
        #print(json_data)
        res_data = self.decrypt_3des(json_data['data']['params']['res_data'])
        json_data = json.loads(res_data)
        # print(json_data['form']['onload']['name'])
        print(json_data['form']['onload']['name'].split('\'')[7])
        return json_data['form']['onload']['name'].split('\'')[7]