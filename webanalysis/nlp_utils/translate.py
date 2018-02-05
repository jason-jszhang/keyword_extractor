# -*- coding: utf-8 -*-
# @Author   : Lawrence Liu
# @Date     : 2018/1/22 17:50
# @Filename : google_translate

import json
import logging
import http.client
import hashlib
import urllib.parse
import random

# from google.cloud import translate


# def google_translate():
#     translate_client = translate.Client().from_service_account_json("service_account.json")
#     ret1 = translate_client.detect_language(['Me llamo', 'I am'])
#     ret2 = translate_client.translate('koszula')
#     print(ret1)
#     print(ret2)
    # translation = translate_client.translate(
    #     text,
    #     target_language=target)

    # return {
    #     'ret': 0,
    #     'text': translation['translatedText']
    #     }


class BaiduTranslator:
    # language code map from langid code (ISO 639-1) to Baidu API
    LANG_MAP = {"other": "auto",
                "zh": "zh",
                "en": "en",
                "jp": "jp",
                "ko": "kor",
                "fr": "fra",
                "es": "spa",
                "th": "th",
                "ar": "ara",
                "ru": "ru",
                "pt": "pt",
                "de": "de",
                "it": "it",
                "el": "el",
                "nl": "nl",
                "pl": "pl",
                "bg": "bul",
                "et": "est",
                "da": "dan",
                "fi": "fin",
                "cs": "cs",
                "ro": "rom",
                "sk": "slo",
                "sv": "swe",
                "hu": "hu",
                "vi": "vie"}

    def __init__(self):
        self._appid = '20161019000030469'
        self._secretKey = 'Rpk4Y27AujHT79nOCb2v'
        # self._appid = '20151113000005349'
        # self._secretKey = 'osubCEzlGjzvw8qdQc41'
        self._apiurl = '/api/trans/vip/translate'

    def translate(self, text, fromLang, toLang):
        srcLang = BaiduTranslator.LANG_MAP.get(fromLang, "auto")
        ret = None
        httpClient = None
        salt = random.randint(32768, 65536)
        sign = self._appid + text + str(salt) + self._secretKey
        m1 = hashlib.md5()
        m1.update(sign.encode("utf-8"))
        sign = m1.hexdigest()
        # myurl = myurl+'?appid='+appid+'&q='+urllib.quote(q)+'&from='+fromLang+'&to='+toLang+'&salt='+str(salt)+'&sign='+sign
        myurl = "{}?appid={}&q={}&from={}&to={}&salt={}&sign={}".format(self._apiurl,
                                                                        self._appid,
                                                                        urllib.parse.quote(text),
                                                                        srcLang, toLang,
                                                                        str(salt), sign)

        try:
            httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
            httpClient.request('GET', myurl)

            # response是HTTPResponse对象
            response = httpClient.getresponse()
            ret = json.loads(response.read())
            ret = '\n'.join([x["dst"] for x in ret["trans_result"]])
        except Exception as err:
            logging.warning(ret)
            logging.exception(err)
        finally:
            if httpClient:
                httpClient.close()
            return ret


if __name__ == "__main__":
    # google_translate()
    translator = BaiduTranslator()
    print(translator.translate(text="▲ページTOPへ", fromLang="jp", toLang="en"))