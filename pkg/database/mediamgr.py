# 媒体文件管理
import os
import uuid

from werkzeug.datastructures import FileStorage

inst = None


class MediaManager:
    root_path = 'media'

    def __init__(self, root_path: str):
        self.root_path = root_path

        if not os.path.exists(self.root_path):
            os.mkdir(self.root_path)

    def upload_image(self, file_obj: FileStorage):
        result = {
            'result': 'success',
            'file_name': '',
        }
        # 计算文件名uuid
        raw_file_name = file_obj.filename
        file_prefix = raw_file_name.split('.')[-1]

        if file_prefix not in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            result['result'] = 'err:不支持的文件类型:{}'.format(file_prefix)
            return result

        file_name = str(uuid.uuid4())

        # 保存文件
        file_path = os.path.join(self.root_path, file_name + '.' + file_prefix)
        file_obj.save(file_path)

        result['file_name'] = file_name + '.' + file_prefix

        return result

    def download_image(self, file_name: str):
        file_path = os.path.join(self.root_path, file_name)
        if not os.path.exists(file_path):
            return None

        return file_path


def get_inst() -> MediaManager:
    global inst
    return inst
