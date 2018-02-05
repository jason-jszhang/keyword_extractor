# -*- coding: utf-8 -*-
# @Author   : Lawrence Liu
# @Date     : 2017/11/30 19:17
# @Filename : demo
import logging

from keyword_extractor.extractor import KeyphraseExtractor

# logging config
log_format_str = "%(levelname)s %(asctime)s %(filename)s(%(lineno)d) %(msg)s"
logging.basicConfig(format=log_format_str, level=logging.DEBUG)


def demo():
    import os
    import time
    web_analyst = KeyphraseExtractor()
    for dirpath, dirnames, filenames in os.walk(
            'F:\\H盘\\users\\administrator\\Desktop\\keyword_extractor\\sample_cases'):
        for file in filenames:
            fullpath = os.path.join(dirpath, file)
            # fullpath = 'F:\\H盘\\users\\administrator\\Desktop\\keyword_extractor\\test.html'
            if fullpath.endswith('html'):
                # 1. load sample page
                fhandle = open(fullpath, "r", encoding='utf-8')
                html = fhandle.read()
                # print(html)

                # 2. initialize keyphrase extractor
                # web_analyst = KeyphraseExtractor()
                fhandle2 = open(fullpath + 'phrases2', "w", encoding='utf-8')
                # 3. run
                cursor_id = 0  # fake ID, if recorded will helpful for log analysis
                try:
                    start = time.time()
                    keyphrases = web_analyst.get_webpage_phrases(html_doc=html)
                    print('--' * 40, time.time() - start)
                    for item in keyphrases:
                        fhandle2.writelines(item[0])
                        fhandle2.writelines('\n')
                    logging.debug(type(keyphrases))
                    logging.debug(keyphrases)
                except ValueError as err:
                    # logging.warning("ValueError-> {}: {}".format(cursor_id, err))
                    pass
                except Exception as err:
                    # logging.error('Error-> {}:{}'.format(cursor_id, err))
                    pass

                fhandle.close()
                fhandle2.close()


def demo2():
    import time
    web_analyst = KeyphraseExtractor()

    fullpath = './samplepage.html'  # 1. load sample page
    fhandle = open(fullpath, "r", encoding='utf-8')
    html = fhandle.read()
    # print(html)

    # 2. initialize keyphrase extractor
    # web_analyst = KeyphraseExtractor()
    fhandle2 = open(fullpath + 'phrases2', "w", encoding='utf-8')
    # 3. run
    cursor_id = 0  # fake ID, if recorded will helpful for log analysis
    try:
        start = time.time()
        keyphrases = web_analyst.get_webpage_phrases(html_doc=html)
        for item in keyphrases:
            fhandle2.writelines(item[0])
            fhandle2.writelines('\n')
        logging.debug(type(keyphrases))
        logging.debug(keyphrases)
    except ValueError as err:
        # logging.warning("ValueError-> {}: {}".format(cursor_id, err))
        pass
    except Exception as err:
        # logging.error('Error-> {}:{}'.format(cursor_id, err))
        pass

    fhandle.close()


if __name__ == "__main__":
    demo2()