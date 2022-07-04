# 配置文件

import database.impls.web_api

# QQ机器人账号
qq_bot_uin = 0

# mirai-http的verifykey
mirai_http_verify_key = ''

# QQ空间账号
qzone_uin = 0

# 管理员QQ，用于接收系统内部通知
admin_uins = []

# 管理群，用于审核说说
admin_groups = []

# 数据库接口实例
database_impl = database.impls.web_api.WebAPI(
    database_context={
        'host': 'localhost'
    }
)

