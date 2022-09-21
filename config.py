# 配置文件
import logging

# QQ机器人账号
# 务必与Mirai-console登录的QQ一致
qq_bot_uin = 0

# mirai-http的地址
mirai_http_host = 'localhost'

# mirai-http的verifykey
mirai_http_verify_key = 'yirimirai'

# QQ空间账号
qzone_uin = 0

# 预置Qzone cookie,若没有,将会在启动时请求管理员扫码
# 如果预置的cookie不可用,将会自动请求管理员扫码
# 扫码登录之后,cookie会被写入此字段
qzone_cookie = ''

# 自动回复消息
# 用户私聊发送消息给机器人时,机器人会回复此消息及小程序码
auto_reply_message = '[bot]bot收到私发QQ消息时回复的文字\n\n'

# 小程序码路径
# 用于自动回复消息,若此文件不存在,将仅回复文字消息
qrcode_path = './qrcode.jpg'

# 管理员QQ，用于接收系统内部通知
# 支持多个管理员,用逗号分隔
admin_uins = [1111111111]

# 管理群，用于审核说说
# 支持多个管理群,用逗号分隔
admin_groups = [1234567890]

# MySQL数据库
database_context = {
    'host': 'localhost',
    'port': 3306,
    'user': 'camwall',
    'password': '123456',
    'db': 'camwall'
}

# RESTful API 监听端口
api_port = 8989

# RESTful API 域名
# 此字段并不是必须的,如果不填写,将使用http协议进行监听
# 填写之后,启动时将认证证书是否匹配
# 注意:如果需要使用http协议而不是https,请删除此字符串默认内容
api_domain = 'test.host'

# RESTful API SSL 证书路径
api_ssl_context = (
    './cert/cert.pem',
    './cert/key.pem'
)

# 小程序相关字段的获取方式请查阅微信官方文档
# 小程序云开发的环境id
cloud_env_id = 'dev-0'

# 小程序的appid
mini_program_appid = 'wx8f8f8f8f8f8f8f8f'

# 小程序的secret
mini_program_secret = '1234567890'

# logging的日志级别
logging_level = logging.INFO

# 发表完成之后提示原作者的赞助语,若为空则不提示
# 注意:频繁发送收款二维码可能会导致QQ账号被腾讯冻结
sponsor_message = ''

# 赞助收款码
sponsor_qrcode_path = ['res/wechat_qrcode.jpg', 'res/alipay_qrcode.jpg']
