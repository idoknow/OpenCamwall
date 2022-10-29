import hashlib
import json
import logging
import os

import pkg.qzone.model
import pkg.chat.manager
import re
import threading
import time

import pkg.database.mediamgr

import requests

from PIL import Image, ImageFont, ImageDraw, ImageEnhance

inst = None

text_render_font = ImageFont.truetype("simhei.ttf", 32, encoding="utf-8")
label_render_font = ImageFont.truetype("simhei.ttf", 20, encoding="utf-8")
anonymous_nick_font = ImageFont.truetype("simhei.ttf", 45, encoding="utf-8")
comment_text = ImageFont.truetype("msyh.ttc", 14, encoding="utf-8")
id_text = ImageFont.truetype("msyh.ttc", 40, encoding="utf-8")


def get_qq_nickname(uin):
    url = "https://r.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={}".format(uin)
    response = requests.get(url)
    text = response.content.decode('gbk', 'ignore')
    json_data = json.loads(text.replace("portraitCallBack(", "")[:-1])
    nickname = json_data[str(uin)][6]
    return nickname


def is_emoji(content):
    if not content:
        return False
    if u"\U0001F300" <= content <= u"\U0001F9EF":
        return True
    else:
        return False


def ensure_emoji(unicode):
    if not os.path.isfile("emojis/{}.png".format(unicode)):
        url = 'https://www.emojiall.com/images/60/apple/{}.png'.format(unicode)
        try:
            res = requests.get(url)
            if res.status_code != 200:
                return False
            with open('emojis/{}.png'.format(unicode), 'wb') as f:
                f.write(res.content)
        except:
            return False
    return True


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


def get_size(file):
    # 获取文件大小:KB
    size = os.path.getsize(file)
    return size / 1024


def get_outfile(infile, outfile):
    if outfile:
        return outfile
    dir, suffix = os.path.splitext(infile)
    outfile = '{}-out{}'.format(dir, suffix)
    return outfile


def compress_image(infile, outfile='', mb=512, step=20, quality=90):
    """不改变图片尺寸压缩到指定大小
    :param infile: 压缩源文件
    :param outfile: 压缩文件保存地址
    :param mb: 压缩目标,KB
    :param step: 每次调整的压缩比率
    :param quality: 初始压缩比率
    :return: 压缩文件地址，压缩文件大小
    """
    o_size = get_size(infile)
    if o_size <= mb:
        return infile
    outfile = get_outfile(infile, outfile)
    while o_size > mb:
        im = Image.open(infile)
        im.save(outfile, quality=quality)
        if quality - step < 0:
            break
        quality -= step
        o_size = get_size(outfile)
    return outfile, get_size(outfile)


def text_color(text):
    md5 = string_to_md5(text)

    rsample = int(md5[:2], 16)  # [0,255]
    gsample = int(md5[12:14], 16)
    bsample = int(md5[-3:-1], 16)

    rn = rsample * rsample  # [0,65025]
    gn = gsample * gsample
    bn = bsample * bsample

    rlimit = int(rn * 0.0039315686)  # [0,255]
    glimit = int(gn * 0.0039315686)
    blimit = int(bn * 0.0039315686)

    r = hex(int(rlimit * 0.7 + 30))[2:].rjust(2, "0")
    g = hex(int(glimit * 0.61 + 58))[2:].rjust(2, "0")
    b = hex(int(blimit * 0.54 + 60))[2:].rjust(2, "0")

    return "#" + r + g + b


def string_to_md5(string):
    md5_val = hashlib.md5(string.encode('utf8')).hexdigest()
    return md5_val


def find_labels(text):
    return re.findall(r'#\[.+?\]#', text)


def render_text_image(post, path='cache/text.png', watermarker=None, left_bottom_text=None, right_bottom_text=None):
    global text_render_font

    labels = find_labels(post['text'])
    for label in labels:
        post['text'] = post['text'].replace(label, '')

    # 分行
    lines = post['text'].split('\n')

    # 计算并分割
    final_lines = []

    text_width = 525
    for line in lines:
        # 如果长了就分割
        line_width = text_render_font.getlength(line)
        if line_width < text_width:
            final_lines.append(line)
            continue
        else:
            rest_text = line
            while True:
                # 分割最前面的一行
                point = int(len(rest_text) * (text_width / line_width))

                # 检查断点是否在数字中间
                numbers = indexNumber(rest_text)

                for number in numbers:
                    if number[1] < point < number[1] + len(number[0]) and number[1] != 0:
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
    # 准备画布
    img = Image.new('RGBA', (750, max(280, len(final_lines) * 35 + 210)), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img, mode='RGBA')

    # 打平台水印
    if watermarker is not None and watermarker != '':
        marker_size = (250, 250)

        marker = Image.open(watermarker, mode='r').convert('RGBA')
        marker = marker.resize(marker_size)

        for i in range(marker_size[0]):
            for j in range(marker_size[1]):
                p = marker.getpixel((i, j))
                p = p[:-1] + (100,)
                marker.putpixel((i, j), p)
        # 圆角蒙版
        mask = Image.new('RGBA', marker_size, color=(255, 255, 255, 0))
        # 画一个圆
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, marker_size[0], marker_size[1]), fill=(255, 255, 255, 45))

        masked = Image.new("RGBA", marker_size, color=(255, 255, 255, 0))
        masked.paste(marker, box=(0, 0))

        img.paste(masked, box=(img.size[0] - 150, img.size[1] - 150), mask=mask)

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

    # 绘制标签

    x = 0
    for l in labels:
        ltext = l.replace("[", "").replace("]", "")
        draw.rounded_rectangle((168 + x, 102, 168 + x + len(ltext) * 17, 124), radius=5, fill=text_color(ltext))
        draw.text((170 + x, 102), ltext, fill="#FFFFFF", font=label_render_font)
        x += len(ltext * 18)

    # 绘制正文

    line_number = 0
    offset_x = 170
    offset_y = 130
    for final_line in final_lines:
        draw.text((offset_x, offset_y + 35 * line_number), final_line, fill=(0, 0, 0), font=text_render_font)
        # 遍历此行,检查是否有emoji
        idx_in_line = 0
        for ch in final_line:
            if is_emoji(ch):
                emoji_img_valid = ensure_emoji(hex(ord(ch))[2:])
                if emoji_img_valid:  # emoji图像可用,绘制到指定位置
                    emoji_image = Image.open("emojis/{}.png".format(hex(ord(ch))[2:]), mode='r').convert('RGBA')
                    emoji_image = emoji_image.resize((32, 32))

                    x, y = emoji_image.size

                    final_emoji_img = Image.new('RGBA', emoji_image.size, (255, 255, 255))
                    final_emoji_img.paste(emoji_image, (0, 0, x, y), emoji_image)

                    img.paste(final_emoji_img, box=(int(offset_x + idx_in_line * 32), offset_y + 35 * line_number))

            # 检查字符占位宽
            char_code = ord(ch)
            if char_code >= 127:
                idx_in_line += 1
            else:
                idx_in_line += 0.5

        line_number += 1

    # 绘制角落
    if left_bottom_text is None:
        left_bottom_text = ('匿名用户' if post['anonymous'] else post['qq']) + " 发表于 " + (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(post['timestamp'])))
    if right_bottom_text is None:
        right_bottom_text = "开发 @RockChinQ | @Soulter"

    draw.text((25, img.size[1] - 25), left_bottom_text, fill=(130, 130, 130), font=comment_text)
    draw.text((535, img.size[1] - 25), right_bottom_text, fill=(130, 130, 130), font=comment_text)

    # 绘制标号
    id_str = "{}".format(post['id'])
    draw.text((img.size[0] - (len(id_str) * 20 + 90), 20), "##" + id_str, fill=(220, 220, 220), font=id_text)

    img.save(path)

    return path


class EmotionPublisher:
    env_id = ''
    app_id = ''
    app_secret = ''
    access_token = ''
    token_refresh_timestamp = 0

    watermarker = ''

    access_token_getting_thread = None

    def __init__(self, env_id, app_id, app_secret, watermarker=''):
        global inst
        self.env_id = env_id
        self.app_id = app_id
        self.app_secret = app_secret

        self.watermarker = watermarker

        inst = self

    def get_access_token_loop(self):
        while True:
            time.sleep(1800)
            try:
                self.refresh_access_token()
            except Exception as e:
                logging.error("获取小程序储存access_token失败")
                logging.exception(e)

    def refresh_access_token(self, attempts=5):
        for i in range(5):
            try:
                url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}".format(
                    self.app_id, self.app_secret)
                res = requests.get(url)
                resjson = json.loads(res.text)
                self.access_token = resjson["access_token"]
                self.token_refresh_timestamp = int(time.time())
                return
            except Exception as e:
                if i == attempts - 1:
                    raise e
                continue

    def prepare_and_publish_post(self, post):
        global text_render_font

        # 渲染文字
        text_image_path = render_text_image(post, watermarker=self.watermarker)

        # 包装发表文字

        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                           post["text"])

        lnk_text = "\n"

        for lnk in links:
            lnk_text += lnk + "\n"

        text = "## {}".format(post['id']) \
               + (("\nQQ:" + post['qq'] + "\n@{{uin:{},nick:{},who:1}}"
                   .format(post["qq"], get_qq_nickname(post['qq']))) if not post['anonymous'] else "") + lnk_text

        image_files = [text_image_path]

        # 下载图片文件

        for media in json.loads(post['media']):
            if media.startswith("cloud:"):
                image_files.append(self.download_cloud_image(media, 'cache/{}'.format(int(time.time()))))
            else:
                image_files.append(pkg.database.mediamgr.get_inst().get_file_path(media))

        return pkg.qzone.model.get_inst().publish_emotion(text, image_files)

    def download_cloud_image(self, cloud, path):
        """从微信云储存下载图片"""
        try:
            try:
                os.mkdir(path)
            except Exception:
                pass

            if int(time.time()) - self.token_refresh_timestamp >= 3600:
                try:
                    pkg.qzone.publisher.get_inst().refresh_access_token()
                except Exception as e:
                    logging.error("刷新小程序储存access_token失败")
                    logging.exception(e)
                    pkg.chat.manager.get_inst().send_message_to_admins(["[bot]刷新小程序储存access_token失败"])
                    raise e

            url = "https://api.weixin.qq.com/tcb/batchdownloadfile?access_token=" + self.access_token
            data = '''{
                "env":"''' + self.env_id + '''",
                "file_list":[{
                    "fileid":"''' + cloud + '''",
                    "max_age":7200
                }]
            }'''
            res = requests.post(url=url, data=data)

            # print(res.text)

            result = json.loads(res.text)
            url = result["file_list"][0]["download_url"]

            res = requests.get(url)
            filetype = url.split("dot")[-1]
            with open(path + "/out." + filetype, 'wb') as f:
                f.write(res.content)

            # 压缩图片文件
            compress_image(path + "/out." + filetype, path + "/out." + filetype)

            return path + "/out." + filetype
        except Exception as e:
            raise e


def get_inst() -> EmotionPublisher:
    global inst
    return inst


if __name__ == '__main__':
    # text = "😀😁😂🤣😃😄😅😆😉😊😋😎😍😘🥰😗😙🥲😚🙂🤗🤩🤔🤨😐😑😶🌫😏😣😥😮🤐😯😪😫🥱😴😌😛😜😝🤤😒😓😔😕🙃🤑😲🙁😞😟😤😢😭😦😧😨😩🤯😬😮💨😰😱🥵🥶😳🤪😵😵💫🥴😠😡🤬😷🤒🤕🤢🤮🤧😇🥳🥸🥺🤠🤡🤥🤫🤭🧐🤓"
    text = "🐢🐢🐢🧔🤴👳🎋🎃🎈🧨✨🎉🎉🎉🎉🎉🪢🪢🥼🥼🥽🥽🖼🖼🎨🎨🧵🎖🥇🥈🥉🏅🎲🍔🍕🍗🍖🥡🥠🍘"
    render_text_image({
        "result": "success",
        "id": 16041,
        "openid": "",
        "qq": "1010553892",
        "timestamp": 1648184113,
        "text": text,
        "media": "[]",
        "anonymous": 0,
        "status": "通过",
        "review": "拒绝:测试"
    }, path='text.png',
        watermarker='cache/watermarker.jpg')
