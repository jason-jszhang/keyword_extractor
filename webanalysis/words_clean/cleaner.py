# -*- coding: utf-8 -*-
# @Author   : Lawrence Liu
# @Date     : 2017/10/28 16:47
# @Filename : wordscleaner
import csv
import re

from ..nlp_utils.nlp_tools import *


class WordsCleaner:
    # input an list of string
    def __init__(self):
        self._root = os.path.dirname(__file__)
        self._stopwords = self._load_csv_file(os.path.join(self._root, "stop_words_en.csv"))
        self._forbidden_words = self._load_csv_file(os.path.join(self._root, "forbidden_words_en.csv"))
        self._posterior_ban = self._load_word_dict(os.path.join(self._root, "posterior_ban"))
        self._ali_products = self._load_word_dict(os.path.join(self._root, "ali_products.txt"))
        # load white list
        self.dirty_phrases = []

    @staticmethod
    def _load_csv_file(filename):
        # a phrase will be removed only when it's exactly the same with one of the stop words.
        with open(filename, encoding='utf-8') as f1:
            reader = csv.reader(f1)
            words = [each[0] for each in list(reader)]
        return words

    @staticmethod
    def _load_word_dict(filename):
        # a phrase will be removed only when it's exactly the same with one of the stop words.
        with open(filename, encoding='utf-8') as fdict:
            words = [x.lower() for x in fdict.read().split('\n')]
        return set(words)

    def clean(self, doc):
        # init
        all_sent = []
        for paragraph in doc:
            all_sent.extend(nltk.sent_tokenize(paragraph))
        white_list = []
        phrases = []

        # make white list
        for idx, sent in enumerate(all_sent):
            sent = sent.lower()
            if sent in self._ali_products:
                white_list.append(sent)
            else:
                phrases.append(sent)

        # procedures
        self.phrases = self.split_multiple_phrases(phrases)
        self.clean_forbidden_words()
        self.clean_stop_words()
        self.clean_by_postfix()
        # self.clean_none_noun()
        # self.clean_phrase_endwith_or_startwith_conjunction_or_preposition()
        self.clean_email_and_phone()
        self.clean_none_word()
        self.phrases = self.clean_blank_or_symbol(self.phrases)
        self.clean_link()

        return white_list + self.phrases, self.dirty_phrases

    def clean_stop_words(self):
        for phrase in self.phrases[:]:
            if phrase in self._stopwords:
                self.dirty_phrases.append(('stop word', phrase))
                self.phrases.remove(phrase)

    def clean_forbidden_words(self):
        for phrase in self.phrases:
            tokenize_phrase = nltk.word_tokenize(phrase)
            if len([w for w in self._forbidden_words if w in tokenize_phrase]) > 0 and len(tokenize_phrase) <= 5:
                self.dirty_phrases.append(('forbidden words', phrase))
                self.phrases.remove(phrase)

    def clean_none_noun(self):
        for phrase in self.phrases:
            if not contain_noun(phrase):
                self.dirty_phrases.append(('none noun', phrase))
                self.phrases.remove(phrase)

    def clean_none_word(self):
        for phrase in self.phrases:
            if len(re.findall(r'[a-z]', phrase)) <= 1 \
                    or (re.findall(r'&[a-z]', phrase) and len(phrase) <= 10) \
                    or re.findall(r'©', phrase) \
                    or re.findall(r'_', phrase):
                self.dirty_phrases.append(('none word', phrase))
                self.phrases.remove(phrase)

    def clean_phrase_endwith_or_startwith_conjunction_or_preposition(self):
        for phrase in self.phrases:
            pos_phrase = string_tokenize_and_pos(phrase)
            if (pos_phrase[-1][-1][1] in ['CC', 'IN', 'DT'] or pos_phrase[0][0][1] in ['IN', "CC"]) \
                    and len(pos_phrase[0]) <= 5:
                self.dirty_phrases.append(('phrase with CC', phrase))
                self.phrases.remove(phrase)

    def clean_email_and_phone(self):
        for phrase in self.phrases:
            if re.findall(r'([\w-]+(\.[\w-]+)*@[\w-]+(\.[\w-]+)+)', phrase) \
                    or re.findall(r'[+\d(][+\-\d\s().]{8,}', phrase):
                self.dirty_phrases.append(('email or phone', phrase))
                self.phrases.remove(phrase)

    def clean_link(self):
        for phrase in self.phrases:
            if re.findall(r'http', phrase) or re.findall(r'www', phrase):
                self.dirty_phrases.append(('link', phrase))
                self.phrases.remove(phrase)

    def clean_by_postfix(self):
        for phrase in self.phrases:
            if phrase[-4:] in ['.php', '.pdf', '.xls', '.png', '.doc', '.com', '.org', '.net', '.jpg']:
                self.dirty_phrases.append(('postfix', phrase))
                self.phrases.remove(phrase)

    @staticmethod
    def clean_blank_or_symbol(phrases):
        new_phrases = []
        for each in phrases:
            if not each.endswith(')'):
                phrase = re.findall(r'\w.+\w', each)
            else:
                phrase = each
            if phrase:
                new_phrases.append(phrase[0])
        return [re.sub(r' +', ' ', each) for each in new_phrases]

    @staticmethod
    def split_multiple_phrases(text):
        return [y.strip() for x in text for y in re.split(r"\|-+/", x)]

    def posterior_filter(self, text):
        return text in self._posterior_ban

    @staticmethod
    def miscellaneous_filter(keyphrase):
        """
        观察数据后发现的一些去脏规则，by：李志强
        :param keyphrase: 待过滤的keyphrase
        :return: 过滤后的keyphrase或None
        """
        if keyphrase == 'e of the " t':
            return None
        # 查看大量数据，发现有:和 =的大部分是html代码没清洗干净，直接去掉
        if ':' in keyphrase:
            return None
        if '=' in keyphrase:
            return None
        # 下面两个主要清洗网页请求失败的
        if '404 network' in keyphrase:
            return None
        if 'network' in keyphrase and 'error' in keyphrase:
            return None

        # 中文符号转为英文符号
        keyphrase = keyphrase.replace('"', '').replace('“', '').replace('”', '').replace('’', "'").replace('‘', "'")
        # 有些关键词以$ - /开头，截断字符
        if keyphrase.strip().startswith('&'):
            keyphrase = keyphrase.strip()[1:]
        if keyphrase.strip().startswith('-'):
            keyphrase = keyphrase.strip()[1:]
        if keyphrase.strip().startswith('/'):
            keyphrase = keyphrase.strip()[1:]

        # 清洗'1 - 3/4 x 4 - 1/2 center-1/4 " glass'类似的数据，有非字母包围的去掉
        keyphrase = re.sub('[\d$#-].*[\d#-]', ' ', keyphrase.strip())
        # 多个空格换成一个空格
        keyphrase = re.sub('\s{2,}', ' ', keyphrase)
        return keyphrase.strip()


if __name__ == "__main__":
    cleaner = WordsCleaner()
    cleaner.clean('')