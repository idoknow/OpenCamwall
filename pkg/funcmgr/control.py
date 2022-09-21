# 系统功能的控制管理中心
from enum import Enum


class Functions(Enum):
    ALL = 'all'
    NOTIF_OF_USE_OF_DISABLED_FUNC = 'notif_of_use_of_disabled_func'
    AUDIT = 'audit'
    AUDIT_ANALYZER = 'audit_analyzer'
    AUDIT_ANALYZER_VISITOR_HEAT = 'audit_analyzer_visitor_heat'
    AUDIT_ANALYZER_HISTORY_HEAT_RATE_AND_HEAT = 'audit_analyzer_history_heat_rate_and_heat'
    AUDIT_ANALYZER_HISTORY_EMO_POSTED = 'audit_analyzer_history_emo_posted'
    AUDIT_RECORDER = 'audit_recorder'
    AUDIT_RECORDER_VISITOR = 'audit_recorder_visitor'
    AUDIT_RECORDER_LIKER = 'audit_recorder_liker'
    CHAT = 'chat'
    CHAT_GREETING = 'chat_greeting'
    QZONE = 'qzone'
    QZONE_TOKEN_KEEPALIVE = 'qzone_token_keepalive'
    QZONE_PUBLISHER = 'qzone_publisher'
    QZONE_PUBLISHER_WX_ACCESS_TOKEN_KEEPALIVE = 'qzone_publisher_wx_access_token_keepalive'
    QZONE_PUBLISHER_PICTURE_COMPRESSOR = 'qzone_publisher_picture_compress'
    RESTFUL = 'restful'
    RESTFUL_ROUTE_POST_NEW = 'restful_route_post_new'
    RESTFUL_ROUTE_PULL_ONE_POST_STATUS = 'restful_route_pull_one_post_status'
    RESTFUL_ROUTE_PULL_MULTI_POST_STATUS = 'restful_route_pull_multi_post_status'
    RESTFUL_ROUTE_UPDATE_POST_STATUS = 'restful_route_update_post_status'
    RESTFUL_ROUTE_CANCEL_ONE_POST = 'restful_route_cancel_one_post'
    RESTFUL_ROUTE_PULL_LOG_LIST = 'restful_route_pull_log_list'
    RESTFUL_ROUTE_ACCOUNT = 'restful_route_account'
    RESTFUL_ROUTE_CONSTANT = 'restful_route_constant'
    RESTFUL_ROUTE_FETCH_SERVICE_LIST = 'restful_route_fetch_service_list'
    RESTFUL_ROUTE_EVENT_FETCH_STATIC_DATA = 'restful_route_event_fetch_static_data'
    RESTFUL_ROUTE_EVENT_FETCH_CONTENTS = 'restful_route_event_fetch_contents'
    RESTFUL_ROUTE_USER_FEEDBACK = 'restful_route_user_feedback'
    RESTFUL_ROUTE_FETCH_UNIAUTH_INFO = 'restful_route_fetch_uniauth_info'
    RESTFUL_ROUTE_CHANGE_PASSWORD = 'restful_route_change_password'
    RESTFUL_ROUTE_GET_LOGIN_SALT = 'restful_route_get_login_salt'
    RESTFUL_ROUTE_VERIFY_ACCOUNT = 'restful_route_verify_account'
    ROUTINE_FEEDBACK_SEND_TO_ADMINS = 'routine_feedback_send_to_admins'
    ROUTINE_POST_SEND_TO_ADMINS = 'routine_post_send_to_admins'
    ROUTINE_POST_POST_FINISHED = 'routine_post_post_finished'
    ROUTINE_POST_CLEAN_PENDING_POSTS = 'routine_post_clean_pending_posts'


function_switches = {}


# 应用功能开关设置集
def apply_switches(s):
    global function_switches
    function_switches = s


# 检查一个功能是否已开启,未设置False则为开启
def check_function(name):
    global function_switches
    if name in function_switches and (function_switches[name] == False):
        return False
    return True
