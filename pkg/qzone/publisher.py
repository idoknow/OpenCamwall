import json
import pkg.qzone.model
import re
import threading
import time

import requests

from PIL import Image, ImageFont, ImageDraw

inst = None

text_render_font = ImageFont.truetype("simhei.ttf", 32, encoding="utf-8")
anonymous_nick_font = ImageFont.truetype("simhei.ttf", 45, encoding="utf-8")
comment_text = ImageFont.truetype("msyh.ttc", 14, encoding="utf-8")


def get_qq_nickname(uin):
    url = "https://r.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={}".format(uin)
    response = requests.get(url)
    text = response.content.decode('gbk', 'ignore')
    json_data = json.loads(text.replace("portraitCallBack(", "")[:-1])
    nickname = json_data[str(uin)][6]
    return nickname


def indexNumber(path=''):
    """
    查找字符串中数字所在串中的位置
    :param path:目标字符串
    :return:<class 'list'>: <class 'list'>: [['1', 16], ['2', 35], ['1', 51]]
    """
    kv = []
    nums = []
    beforeDatas = re.findall('[\d]+', path)
    for num in beforeDatas:
        indexV = []
        times = path.count(num)
        if times > 1:
            if num not in nums:
                indexs = re.finditer(num, path)
                for index in indexs:
                    iV = []
                    i = index.span()[0]
                    iV.append(num)
                    iV.append(i)
                    kv.append(iV)
            nums.append(num)
        else:
            index = path.find(num)
            indexV.append(num)
            indexV.append(index)
            kv.append(indexV)
    # 根据数字位置排序
    indexSort = []
    resultIndex = []
    for vi in kv:
        indexSort.append(vi[1])
    indexSort.sort()
    for i in indexSort:
        for v in kv:
            if i == v[1]:
                resultIndex.append(v)
    return resultIndex


def render_text_image(post, path='cache/text.png', left_bottom_text=None, right_bottom_text=None):
    global text_render_font

    # 分行
    lines = post['text'].split('\n')

    # 计算并分割
    final_lines = []

    text_width = 475
    for line in lines:
        # 如果长了就分割
        line_width = text_render_font.getlength(line)
        if line_width < text_width:
            final_lines.append(line)
            continue
        else:
            rest_text = line
            while True:
                # print("rest:",rest_text)
                # 分割最前面的一行
                point = int(len(rest_text) * (text_width / line_width))

                # 检查断点是否在数字中间
                numbers = indexNumber(rest_text)

                for number in numbers:
                    if number[1] < point < number[1] + len(number[0]):
                        point = number[1]
                        break

                final_lines.append(rest_text[:point])
                rest_text = rest_text[point:]
                line_width = text_render_font.getlength(rest_text)
                if line_width < text_width:
                    final_lines.append(rest_text)
                    break
                else:
                    continue

    # 渲染文字
    img = Image.new('RGBA', (680, max(280, len(final_lines) * 35 + 210)), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img, mode='RGBA')

    # 头像
    show_avatar_path = ''

    if post['anonymous'] == 1:
        show_avatar_path = 'bag-on-head.png'
    else:
        res = requests.get('https://q1.qlogo.cn/g?b=qq&nk=' + str(post['qq']) + '&s=640')
        # 使用BytesIO接口
        with open('cache/avatar.png', 'wb') as f:
            f.write(res.content)
        show_avatar_path = 'cache/avatar.png'

    avatar_size = (120, 120)

    avatar_image = Image.open(show_avatar_path, mode='r').convert('RGBA')
    avatar_image = avatar_image.resize(avatar_size)

    # 圆角蒙版
    # 新建一个蒙板图, 注意必须是 RGBA 模式
    mask = Image.new('RGBA', avatar_size, color=(0, 0, 0, 0))
    # 画一个圆
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, avatar_size[0], avatar_size[1]), fill=(0, 0, 0, 255))

    img.paste(avatar_image, box=(28, 34), mask=mask)

    # 绘制Nick
    nick_name = ''
    nick_color = (0, 0, 0)
    if post['anonymous'] == 1:
        nick_name = '匿名'
        nick_color = (120, 120, 120)
    else:
        nick_name = get_qq_nickname(post['qq'])

    draw.text((170, 55), nick_name, fill=nick_color, font=anonymous_nick_font)

    # 绘制正文

    line_number = 0
    offset_x = 170
    offset_y = 130
    for final_line in final_lines:
        draw.text((offset_x, offset_y + 35 * line_number), final_line, fill=(0, 0, 0), font=text_render_font)
        line_number += 1

    # 绘制角落

    if left_bottom_text == None:
        left_bottom_text = ('匿名用户' if post['anonymous'] else nick_name) + " 发表于 " + (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(post['timestamp'])))
    if right_bottom_text == None:
        right_bottom_text = "开发 @RockChinQ | @Soulter"

    draw.text((25, img.size[1] - 25), left_bottom_text, fill=(130, 130, 130), font=comment_text)
    draw.text((465, img.size[1] - 25), right_bottom_text, fill=(130, 130, 130), font=comment_text)

    img.save(path)

    return path


class EmotionPublisher:
    app_id = ''
    app_secret = ''
    access_token = ''

    access_token_getting_thread = None

    def __init__(self, app_id, app_secret):
        global inst
        self.app_id = app_id
        self.app_secret = app_secret

        inst = self

        self.refresh_access_token()

        self.access_token_getting_thread = threading.Thread(target=self.get_access_token_loop, args=(), daemon=True)

        self.access_token_getting_thread.start()

    def get_access_token_loop(self):
        while True:
            time.sleep(1800)
            try:
                self.refresh_access_token()
            except Exception as e:
                print("获取小程序储存access_token失败:", e)

    def refresh_access_token(self):
        url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}".format(
            self.app_id, self.app_secret)
        res = requests.get(url, verify=False)
        resjson = json.loads(res.text)
        self.access_token = resjson["access_token"]

    def prepare_post(self, post):
        global text_render_font
        # 渲染文字
        text_image_path = render_text_image(post)

        # 包装发表文字

        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                           post["text"])

        lnk_text = "\n"

        for lnk in links:
            lnk_text += lnk + "\n"

        text = "## {}".format(post['id']) \
               + (("\nQQ:" + post['qq'] + "\n@{{uin:{},nick:{},who:1}}"
                   .format(post["qq"], get_qq_nickname(post['qq']))) if not
        post['anonymous'] else "") + lnk_text

        pkg.qzone.model.get_inst().publish_emotion(text, [text_image_path])


def get_inst() -> EmotionPublisher:
    global inst
    return inst


if __name__ == '__main__':
    render_text_image({
        "result": "success",
        "id": 764,
        "openid": "",
        "qq": "",
        "timestamp": 1648184113,
        "text": "我",
        "media": "[]",
        "anonymous": 1,
        "status": "通过",
        "review": "拒绝:测试"
    }, path='text.png')
