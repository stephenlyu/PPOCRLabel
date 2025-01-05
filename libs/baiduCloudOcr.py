import requests
import yaml
import base64
import hashlib
import os
from urllib.parse import quote
import json

_cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../.baidu-ocr'))

def do_md5(data):
    md5 = hashlib.md5()
    md5.update(data)
    return md5.hexdigest()

class _OcrResultManager:
    def __init__(self):
        os.makedirs(_cache_dir, exist_ok=True)
    
    def to_dirs(self, md5):
        return os.path.join(md5[:2], md5[2:4])

    def save_result(self, image_data, result):
        md5 = do_md5(image_data)
        result_file = os.path.join(_cache_dir, self.to_dirs(md5), md5)
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(result))

    def load_result(self, image_data):
        md5 = do_md5(image_data)
        result_file = os.path.join(_cache_dir, self.to_dirs(md5), md5)
        if not os.path.exists(result_file):
            return None
        with open(result_file, encoding='utf-8') as f:
            return json.loads(f.read())
 
class BaiduCloudOCR:
    def __init__(self):
        try:
            with open('.baidu_key.yaml', 'r') as file:
                config = yaml.load(file, Loader=yaml.FullLoader)
        except:
            print('load baidu key fail')
            return        
        self.api_key = config.get('API_KEY')
        self.secret_key = config.get('SECRET_KEY')
        self.cache = _OcrResultManager()
        self.initialized = True

    def recognize(self, image_file):
        if not self.initialized:
            raise Exception('uninitialized')
        with open(image_file, 'rb') as f:
            data = f.read()
        result = self.cache.load_result(data)
        if result is not None:
            print('load from cache')
            return result

        image_str = quote(base64.b64encode(data).decode('utf-8'), encoding='utf-8')
            
        url = "https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting?access_token=" + self.get_access_token()
        
        payload='detect_direction=false&probability=true&detect_alteration=false&image=' + image_str
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
        if int(response.status_code) != 200:
            raise Exception(response.text)
        obj = json.loads(response.text)
        if 'error_code' in obj:
            raise Exception(obj.get('error_text', ''))
        self.cache.save_result(data, obj)
        return obj

    def get_access_token(self):
        """
        使用 AK，SK 生成鉴权签名（Access Token）
        :return: access_token，或是None(如果错误)
        """
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {"grant_type": "client_credentials", "client_id": self.api_key, "client_secret": self.secret_key}
        return str(requests.post(url, params=params).json().get("access_token"))

    @staticmethod
    def to_ppocr_result(result):
        ret = []
        for o in result.get('words_result', []):
            loc = o['location']
            left = loc['left']
            top = loc['top']
            right = loc['left'] + loc['width']
            bottom = loc['top'] + loc['height']
            box = [
                [left, top],
                [right, top],
                [right, bottom],
                [left, bottom],
            ]
            text = o.get('words', '')
            prob = o.get('probability', {}).get('average', 0.9)
            ret.append([box, [text, prob]])
        return [ret]

    def ocr(self, image_file, **kwargs):
        try:
            result = self.recognize(image_file)
            return self.to_ppocr_result(result)
        except:
            return [[]]

if __name__ == '__main__':
    ocr = BaiduCloudOCR()
    result = ocr.recognize(r'D:\data\tmp\test\5ecbc37011f8a2a7eb502ec8_1.jpg')
    print(json.dumps(ocr.to_ppocr_result(result), indent=2, ensure_ascii=False))
