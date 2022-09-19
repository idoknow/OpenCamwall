# 系统功能的控制管理中心

function_switches = {}


# 应用功能开关设置集
def apply_switches(s):
    global function_switches
    function_switches = s


# 检查一个功能是否已开启,未设置False则为开启
def check_function(name):
    global function_switches
    if name in function_switches and function_switches[name] == False:
        return False
    return True
