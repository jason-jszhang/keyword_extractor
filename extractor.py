# -*- coding: utf-8 -*-
# @Author   : Lawrence Liu
# @Date     : 2017/10/28 17:01
# @Filename : extractor
import codecs
import logging
import os
import json
from collections import Counter
import csv
import nltk
import spacy
from bs4 import BeautifulSoup
from numpy import array

from nlp_utils.nlp_tools import lang_dectect
from nlp_utils.nlp_tools import Phrase2vec
from words_clean.cleaner import WordsCleaner
from sklearn.metrics.pairwise import cosine_similarity


class KeyphraseExtractor:
    def __init__(self):
        self._cleaner = WordsCleaner()
        self._stopwords = self._load_csv_file()
        # use spacy parser
        self.nlp = spacy.load("en")
        # embedding model
        self._p2v = Phrase2vec()

    @staticmethod
    def _load_raw_page(webfile):
        with codecs.open(webfile, "r", "utf-8") as finput:
            html_doc = finput.read()
            soup = BeautifulSoup(html_doc, "html5lib")
        return soup

    @staticmethod
    def _load_csv_file():
        # a phrase will be removed only when it's exactly the same with one of the stop words.
        with open('words_clean/stop_words_en.csv', encoding='utf-8') as f1:
            reader = csv.reader(f1)
            stop_words = [each[0] for each in list(reader)]
        return stop_words

    def _exp_02(self, raw_doc):
        # do words clean
        clean_sent, dirty_sent = self._cleaner.clean(raw_doc)
        short_text = [x for x in clean_sent if len(nltk.word_tokenize(x)) <= 5]
        all_np = Counter()
        for phrase in short_text:
            all_np[phrase.lower()] += 1

        for doc in clean_sent:
            info = self.nlp(doc)
            for np in list(info.noun_chunks):
                all_np[np.text.lower()] += 1

        final, _ = self._cleaner.clean(all_np.keys())

        new_final = {}
        for item in final:
            new_final[item] = all_np[item]
        # just for debug
        logging.debug("=" * 100)
        for item in final:
            logging.debug(item)
        return Counter(new_final)

    def _doc_vector(self, phrases_counter):
        phrase_info = []
        for phrase, cnt in phrases_counter.most_common():
            try:
                vector = self._p2v.vector(phrase)
                phrase_info.append((phrase, cnt, vector.reshape(1, vector.shape[0])))
            except ValueError as err:
                continue
        if not phrase_info:
            raise ValueError("Unknow content")
        doc_vec = array([vector for _, _, vector in phrase_info]).mean(axis=0)
        return doc_vec, phrase_info

    def _rank_by_p2v(self, phrases_counter, topk=20):
        # calculate doc vector
        doc_vec, phrase_info = self._doc_vector(phrases_counter)
        # similarity  这个什么意思？短语向量与短语里的单词计算cos sim？
        phrase_info = [(x, cnt, cosine_similarity(doc_vec, vec).flatten()) for x, cnt, vec in phrase_info]
        phrase_info = sorted(phrase_info, key=lambda x: x[2], reverse=True)

        candidates = [(x, cnt) for x, cnt, _, in phrase_info]
        return candidates[:topk]

    def _finetune(self, candidates):
        candi_set = set()
        fine_candi = list()

        for item, cnt in candidates:
            info = [(x.text, x.lemma_, x.is_stop) for x in self.nlp(item)]
            idx = 0
            while info[idx][2] is True:
                idx += 1
            last_word = info[-1]
            new_item = [text for text, _, _ in info[idx:-1]]
            new_item_key = ' '.join(new_item + [last_word[1]])  # lemma
            new_item_value = ' '.join(new_item + [last_word[0]])  # raw text
            if new_item_value in self._stopwords:
                continue
            if new_item_key not in candi_set:
                candi_set.add(new_item_key)
                fine_candi.append((new_item_value, cnt))
        return fine_candi

    def get_webpage_phrases(self, html_doc="", fromfile=False, filepath=""):
        if html_doc == "":
            return []
        if fromfile:
            soup = self._load_raw_page(filepath)
        else:
            soup = BeautifulSoup(html_doc, "html5lib")
        # rough clean
        while soup.link:
            soup.link.extract()
        while soup.script:
            soup.script.extract()
        while soup.style:
            soup.style.extract()
        raw_content = list(soup.stripped_strings)

        # only support english
        if not lang_dectect(raw_content):
            raise ValueError("Main language of [{}] is not english.".format(filepath))

        # get phrases
        phrases_counter = self._exp_02(raw_content)
        # ranking by phrase vector
        candidates = self._rank_by_p2v(phrases_counter)
        # fine tune candidates
        candidates = self._finetune(candidates)
        return candidates
