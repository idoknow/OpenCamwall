# OpenCamwall


[![OSCS Status](https://www.oscs1024.com/platform/badge//RockChinQ/OpenCamwall.git.svg?size=small)](https://www.murphysec.com/dr/SB70LFWPato6GXzInU)
[![Licence](https://img.shields.io/github/license/RockChinQ/OpenCamwall)](https://github.com/RockChinQ/OpenCamwall/blob/master/LICENSE)

继承自个人闭源项目camwall-backend  
实现从接收投稿、稿件审核到发表说说的自动化

~~前端即将开源,敬请期待!~~  
前端开源计划已取消，此仓库仅供参考使用。

## 包

- audit 系统数据分析
    - analyzer 数据分析
    - recorder 数据监控
- chat QQ机器人模块
- database 包装数据库调用的方法
- qzone 管理QQ空间登录、发表说说等功能
- routines 各功能的一些操作步骤
- webapi 为小程序访问及其他端提供RESTful API接口

## 后端功能

- [x] 通过RESTful API接收用户从小程序端发送的稿件  
- [x] 发送待审核稿件到管理员群,允许管理员在群内进行审核  
- [x] 通过QQ空间接口直接上传发表说说,无需chromedriver  
- [x] 通过RESTful API接收用户反馈,并发送至管理员  
- [x] 分析稿件点赞情况、QQ空间热力、访客增长,供用户通过小程序查看  
- [x] 支持封禁用户  

## 媒体文件存储

通过接口接收前端上传的图片,存放到`media`文件夹,以时间戳命名,同时开放接口以供外部下载图片

## 效果预览

<img alt="稿件文字渲染" src="docs/res/render.jpg" title="&#39;稿件文字渲染&#39;" width="200"/>
<img alt="稿件文字渲染(匿名)" src="docs/res/render_anonymous.jpg" title="&#39;稿件文字渲染(匿名)&#39;" width="200"/>
<img alt="发表说说" src="docs/res/emotion.jpg" title="&#39;发表说说&#39;" width="200"/>
<img alt="发表说说(带图)" src="docs/res/emotion_image.jpg" title="&#39;发表说说(带图)&#39;" width="200"/>

## 依赖

### 库

* flask
* requests
* Pillow
* pymysql
* yiri-mirai
* colorlog

### 框架

* [Mirai](https://github.com/mamoe/mirai) QQ机器人框架
* [YiriMirai](https://github.com/YiriMiraiProject/YiriMirai) Mirai框架Python SDK

## 参考

* [opq-osc/OPQBot](https://github.com/opq-osc/OPQBot) QQ空间发表说说流程
* [【Ono】QQ空间协议分析----扫码登录----【1】](https://www.52pojie.cn/thread-1022123-1-1.html) QQ空间扫码登录流程
* [pillow使用之：圆形头像](https://www.jianshu.com/p/cdea3ba63cd7) 文字渲染器 圆形头像
