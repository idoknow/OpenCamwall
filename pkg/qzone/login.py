# 实现各种登录功能
import os
import re
import time

import requests

inst = None


def callback(path):
    os.system("explorer {}".format(path))


class QzoneLoginManager:
    qrcode_url = "https://ssl.ptlogin2.qq.com/ptqrshow?appid=549000912&e=2&l=M&s=3&d=72&v=4&t=0.31232733520361844&daid=5&pt_3rd_aid=0"

    login_check_url = "https://xui.ptlogin2.qq.com/ssl/ptqrlogin?u1=https://qzs.qq.com/qzone/v5/loginsucc.html?para=izone&ptqrtoken={}&ptredirect=0&h=1&t=1&g=1&from_ui=1&ptlang=2052&action=0-0-1656992258324&js_ver=22070111&js_type=1&login_sig=&pt_uistyle=40&aid=549000912&daid=5&has_onekey=1&&o1vId=1e61428d61cb5015701ad73d5fb59f73"

    check_sig_url = "https://ptlogin2.qzone.qq.com/check_sig?pttype=1&uin={}&service=ptqrlogin&nodirect=1&ptsigx={}&s_url=https://qzs.qq.com/qzone/v5/loginsucc.html?para=izone&f_url=&ptlang=2052&ptredirect=100&aid=549000912&daid=5&j_later=0&low_login_hour=0&regmaster=0&pt_login_type=3&pt_aid=0&pt_aaid=16&pt_light=0&pt_3rd_aid=0"

    def __init__(self):
        global inst
        inst = self
        pass

    def getptqrtoken(self, qrsig):
        e = 0
        for i in range(1, len(qrsig) + 1):
            e += (e << 5) + ord(qrsig[i - 1])
        return str(2147483647 & e)

    def login_via_qrcode(self, qrcode_refresh_callback=callback, attempts=3, path='login_qr.png'):
        for i in range(attempts):
            # 图片URL
            req = requests.get(self.qrcode_url)

            qrsig = ''

            set_cookie = req.headers['Set-Cookie']
            set_cookies_set = req.headers['Set-Cookie'].split(";")
            for set_cookies in set_cookies_set:
                if set_cookies.startswith("qrsig"):
                    qrsig = set_cookies.split("=")[1]
                    break
            if qrsig == '':
                raise Exception("qrsig is empty")

            # 获取ptqrtoken
            ptqrtoken = self.getptqrtoken(qrsig)

            # 使用BytesIO接口
            with open(path, 'wb') as f:
                f.write(req.content)

            qrcode_refresh_callback(path)

            # 检查是否登录成功
            while True:
                time.sleep(2)
                req = requests.get(self.login_check_url.format(ptqrtoken), cookies={"qrsig": qrsig})
                if req.text.find("二维码已失效") != -1:
                    break
                if req.text.find("登录成功") != -1:
                    # 检出检查登录的响应头
                    response_header_dict = req.headers

                    # 检出url
                    url = eval(req.text.replace("ptuiCB", ""))[2]

                    # 获取ptsigx
                    m = re.findall(r"ptsigx=[A-z \d]*&", url)

                    ptsigx = m[0].replace("ptsigx=", "").replace("&", "")

                    # 获取uin
                    m = re.findall(r"uin=[\d]*&", url)
                    uin = m[0].replace("uin=", "").replace("&", "")

                    # 获取skey和p_skey
                    res = requests.get(self.check_sig_url.format(uin, ptsigx), cookies={"qrsig": qrsig},
                                       headers={'Cookie': response_header_dict['Set-Cookie']})

                    final_cookie = res.headers['Set-Cookie']

                    final_cookie_dict = {}
                    for set_cookie in final_cookie.split(";, "):
                        for cookie in set_cookie.split(";"):
                            spt = cookie.split("=")
                            if len(spt) == 2 and final_cookie_dict.get(spt[0]) is None:
                                final_cookie_dict[spt[0]] = spt[1]

                    return final_cookie_dict
        raise Exception("{}次尝试失败".format(attempts))


def get_inst() -> QzoneLoginManager:
    global inst
    return inst


if __name__ == '__main__':
    qzlmgr = QzoneLoginManager()

    # print(qzlmgr.login_via_qrcode(callback))
    print(qzlmgr.getptqrtoken("rockchin"))
