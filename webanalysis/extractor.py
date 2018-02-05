# -*- coding: utf-8 -*-
# @Author   : Lawrence Liu
# @Date     : 2017/10/28 17:01
# @Filename : extractor
import codecs
from collections import Counter

import langid
import logging
import nltk
import spacy
from bs4 import BeautifulSoup
from numpy import array

from .nlp_utils.nlp_tools import lang_dectect, Phrase2vec
from .words_clean.cleaner import WordsCleaner
from sklearn.metrics.pairwise import cosine_similarity


class KeyphraseExtractor:
    STATUS_CODE = {'UNKNOWN': -1,
                   'OK': 0,
                   'NULL_HTML': 10,
                   'NO_HTML_CONTENT': 11,
                   'NOT_ENGLISH': 20,
                   'NO_CANDIDATES': 30}

    def __init__(self):
        self._cleaner = WordsCleaner()
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

        return all_np

    def _doc_vector(self, phrases_counter):
        phrase_info = []
        for phrase, cnt in phrases_counter.most_common():
            try:
                vector = self._p2v.vector(phrase)
                phrase_info.append((phrase, cnt, vector.reshape(1, vector.shape[0])))
            except ValueError as err:
                logging.debug(err)
                continue
        if not phrase_info:
            raise ValueError("Unknow content")
        doc_vec = array([vector for _, _, vector in phrase_info]).mean(axis=0)
        return doc_vec, phrase_info

    def _rank_by_p2v(self, phrases_counter, topk=30):
        # calculate doc vector
        doc_vec, phrase_info = self._doc_vector(phrases_counter)
        # similarity
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

            if new_item_key not in candi_set:
                candi_set.add(new_item_key)
                fine_candi.append((new_item_value, cnt))

        # posterior process:
        fine_candi = [(k, v) for k, v in fine_candi if not self._cleaner.posterior_filter(k)]
        fine_candi = [(self._cleaner.miscellaneous_filter(k), v) for k, v in fine_candi]
        fine_candi = [(k, v) for k, v in fine_candi if k]
        return fine_candi

    @staticmethod
    def _soup_clean(soup):
        while soup.link:
            soup.link.extract()
        while soup.script:
            soup.script.extract()
        while soup.style:
            soup.style.extract()
        raw_content = list(soup.stripped_strings)
        return raw_content

    def get_webpage_phrases(self, html_doc="", fromfile=False, filepath=""):
        status_code = KeyphraseExtractor.STATUS_CODE['UNKNOWN']
        candidates = []
        try:
            # check html is real
            if html_doc == "":
                status_code = KeyphraseExtractor.STATUS_CODE['NULL_HTML']
                return (status_code, candidates)

            # html content parser
            if fromfile:
                soup = self._load_raw_page(filepath)
            else:
                soup = BeautifulSoup(html_doc, "html5lib")
            raw_content = self._soup_clean(soup)
            if len(raw_content) == 0:
                status_code = KeyphraseExtractor.STATUS_CODE['NO_HTML_CONTENT']
                return (status_code, candidates)

            # only support english
            if not lang_dectect(raw_content):
                logging.warning("Main language of [{}] is not english.".format(filepath))
                status_code = KeyphraseExtractor.STATUS_CODE['NOT_ENGLISH']
                candidates = []
                return (status_code,candidates)

            # get phrases
            phrases_counter = self._exp_02(raw_content)
            # ranking by phrase vector
            candidates = self._rank_by_p2v(phrases_counter)
            # fine tune candidates
            candidates = self._finetune(candidates)

            if len(candidates) == 0:
                status_code = KeyphraseExtractor.STATUS_CODE['NULL_CANDIDATES']
            else:
                status_code = KeyphraseExtractor.STATUS_CODE['OK']
        except Exception as err:
            logging.exception(err)
        finally:
            return (status_code, candidates)

    def language_check(self, html_doc="", fromfile=False, filepath=""):
        if html_doc == "":
            return []
        if fromfile:
            soup = self._load_raw_page(filepath)
        else:
            soup = BeautifulSoup(html_doc, "html5lib")

        # rough clean
        doc = self._soup_clean(soup)

        language_cnt = Counter()
        with codecs.open('minority_lang', 'a', 'utf-8') as fminority:
            for paragraph in doc:
                length = len(paragraph.split(' '))
                lang_type = langid.classify(paragraph)[0]
                language_cnt[lang_type] += length
                if lang_type != 'en' and lang_type != 'other':
                    print(lang_type + '\t' + paragraph, file=fminority)
                # if langid.classify(paragraph)[0] == 'en':
                #     language_cnt['en'] += length
                # else:
                #     language_cnt['other'] += length
        return language_cnt
