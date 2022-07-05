import abc


class Post(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def fetch(self, status=''):
        """获取稿件
        :except: 获取失败
        :return: 倒序[(id,openid,qq,timestamp,text,medias,anonymous,status,review)]
        """
        pass

    @abc.abstractmethod
    def update_status(self, post_id, new_status, review=''):
        """更新一个稿件的状态
        :except: 更新失败
        """
        pass

    @abc.abstractmethod
    def fetch_picture(self, media, save_path=''):
        """获取一张图片,并储存到save_path或返回base64
        :except: 获取失败
        :return: base64或保存路径
        """
        pass
