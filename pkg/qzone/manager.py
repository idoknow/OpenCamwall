import login
import model


if __name__ == '__main__':
    qzone_login = login.QzoneLoginManager()

    cookies = qzone_login.login_via_qrcode()
    print(cookies)

    print(cookies['uin'])

    cookie_str = ""

    for k in cookies:
        cookie_str += "{}={};".format(k, cookies[k])

    print(cookie_str)

    oper = model.QzoneOperator(int(str(cookies['uin']).replace("o", "")),
                               cookie_str)

    print(oper.publish_emotion("测试测试", ['login_qr.png', 'login_qr.png']))
