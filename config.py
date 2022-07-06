# 配置文件

# QQ机器人账号
qq_bot_uin = 1480613886

# mirai-http的verifykey
mirai_http_verify_key = 'yirimirai'

# QQ空间账号
qzone_uin = 0

# 自动回复消息
auto_reply_message = '[bot]自动化接稿系统接管，请扫码进入小程序投稿(QQ可扫)，信息反馈请到群733524559:\n\n'

# 小程序码路径
qrcode_path = './qrcode.jpg'

# 管理员QQ，用于接收系统内部通知
admin_uins = [1010553892]

# 管理群，用于审核说说
admin_groups = [1025599757]

# MySQL数据库
database_context = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '000112',
    'db': 'camwall_test'
}

# RESTful API 监听端口
api_port = 8989

# RESTful API 域名
api_domain = 'localhost'

# RESTful API SSL 证书路径
api_ssl_context={
    'cert': './cert/cert.pem',
    'key': './cert/key.pem'
}