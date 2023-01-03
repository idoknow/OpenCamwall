import unittest

import pkg.qzone.login
import pkg.qzone.model


class TestQzoneModel(unittest.TestCase):
    def test_get_emotion_detail(self):
        uin = int(input("请输入QQ号："))
        cookie_str = input("请输入cookie：")
        mgr = pkg.qzone.model.QzoneOperator(uin, cookie_str)

        tid = mgr.publish_emotion("测试", images=['../bag-on-head.png'])
        print("tid:", tid)
        detail = mgr.emotion_detail(tid)
        print("detail:", detail)
        #d4fbc05511b47c633bc80400

    def test_emotion_set_private(self):
        uin = int(input("请输入QQ号："))
        cookie_str = input("请输入cookie：")
        mgr = pkg.qzone.model.QzoneOperator(uin, cookie_str)

        tid=input("请输入说说tid：")
        result=mgr.emotion_set_private(tid)

        print("result:", result)
