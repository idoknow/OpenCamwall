# 以下是系统中部分常用功能的开关
# 此文件暂不支持热更新
# 若设置为False,则此功能在被调用时会直接返回,不抛出异常
# 若notif_of_use_of_disabled_func为True
# 那么将以info级别提示此功能被调用
# 所有功能(除了notif_of_use_of_disabled_func)的默认值均为True
function_switches = {
    'all': True,  # 所有功能
    'notif_of_use_of_disabled_func': True,  # 通知使用了被禁用的功能
    'audit': True,  # 审计模块
    'audit_analyzer': True,  # 审计模块的分析器
    'audit_analyzer_visitor_heat': True,  # 分析器:访客热力图
    'audit_analyzer_history_heat_rate_and_heat': True,  # 分析器:历史热度
    'audit_analyzer_history_emo_posted': True,  # 分析器:历史说说发布
    'audit_recorder': True,  # 审计模块的记录器
    'audit_recorder_visitor': True,  # 记录器:访客
    'audit_recorder_liker': True,  # 记录器:说说点赞
    'chat': True,  # 消息机器人
    'chat_greeting': True,  # 消息机器人:问候
    'qzone': True,  # 初始化QQ空间
    'qzone_token_keepalive': True,  # QQ空间:token保活
    'qzone_publisher': True,  # QQ空间:进行说说发表器的初始化
    'qzone_publisher_wx_access_token_keepalive': True,  # QQ空间:说说发表:微信access token保活
    'qzone_publisher_picture_compress': True,  # QQ空间:说说发表:图片压缩
    'restful': True,  # RESTful API
    'restful_route_post_new': True,  # RESTful API:接口:投稿
    'restful_route_pull_one_post_status': True,  # RESTful API:接口:根据状态拉取一条稿件
    'restful_route_pull_multi_post_status': True,  # RESTful API:接口:根据状态拉取多条稿件
    'restful_route_update_post_status': True,  # RESTful API:接口:更新稿件状态
    'restful_route_cancel_one_post': True,  # RESTful API:接口:取消一条稿件
    'restful_route_pull_log_list': True,  # RESTful API:接口:拉取日志列表
    'restful_route_account': True,  # RESTful API:接口:根据openid获取账号信息
    'restful_route_constant': True,  # RESTful API:接口:获取运行常量
    'restful_route_fetch_service_list': True,  # RESTful API:接口:获取服务列表
    'restful_route_event_fetch_static_data': True,  # RESTful API:接口:获取统计数据
    'restful_route_event_fetch_contents': True,  # RESTful API:接口:获取内容列表
    'restful_route_user_feedback': True,  # RESTful API:接口:用户反馈
    'restful_route_fetch_uniauth_info': True,  # RESTful API:接口:获取统一认证账户信息
    'restful_route_change_password': True,  # RESTful API:接口:修改统一账户密码
    'restful_route_get_login_salt': True,  # RESTful API:接口:获取统一账户登录加密salt
    'restful_route_verify_account': True,  # RESTful API:接口:验证统一账户
    'routine_feedback_send_to_admins': True,  # RESTful API:接口:发送反馈到管理员
    'routine_post_send_to_admins': True,  # RESTful API:接口:发送稿件到管理员
    'routine_post_post_finished': True,  # RESTful API:接口:稿件投递完成的事务
    'routine_post_clean_pending_posts': True,  # RESTful API:接口:处理待发表稿件
}
