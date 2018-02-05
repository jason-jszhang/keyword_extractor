import logging
import os
from collections import Counter

import inflect
import nltk
import yaml
from numpy import array, float32 as REAL
from gensim import matutils
from gensim.models import KeyedVectors
from langid import langid

from .translate import BaiduTranslator

translator = BaiduTranslator()


def string_tokenize_and_pos(document):
    sentences = nltk.sent_tokenize(document)
    sentences = [nltk.word_tokenize(sent) for sent in sentences]
    sentences = [nltk.pos_tag(sent) for sent in sentences]
    return sentences


def contain_noun(document):
    sentences = string_tokenize_and_pos(document)
    for sentence in sentences:
        if len([w for w in sentence if w[1] in ['NN', 'NNS', 'NNP', 'NNPS']]) > 0:
            return True
    return False


def number_of_words(document):
    sentences = string_tokenize_and_pos(document)
    number = 0
    for sentence in sentences:
        number += len(sentence)
    return number


def get_phrases(strings):
    return [string for string in strings if number_of_words(string) <= 5]


def get_sentences(strings):
    return [string for string in strings if number_of_words(string) > 5]


def get_noun_phrases_from_sentence(string):
    grammar = "NP:{<JJ>*<NN|NNS|NNP|NNPS>+<CC>?<DT>?<JJ>*<NN|NNS|NNP|NNPS>*<CC>?<DT>?<JJ>*<NN|NNS|NNP|NNPS>*}"
    # grammar = "NP:{<JJ>*<NN|NNS|NNP|NNPS>+<CC>?<IN>?<DT>?<JJ>*<NN|NNS|NNP|NNPS>*<CC>?<DT>?<JJ>*<NN|NNS|NNP|NNPS>*}"
    cp = nltk.RegexpParser(grammar)
    sentences = string_tokenize_and_pos(string)
    phrases = []
    noun_phrases = []
    for sentence in sentences:
        tree = cp.parse(sentence)
        phrases += [each for each in tree if type(each) is nltk.tree.Tree]
    for tree in phrases:
        pos_word = [each for each in tree]
        if pos_word[-1][1] in ['CC', 'IN']:
            del pos_word[-1]
        if pos_word[0][1] in ['CC']:
            del pos_word[0]
        word = [each[0] for each in pos_word]
        string_word = ' '.join(word)
        noun_phrases.append(string_word)
    return noun_phrases


def get_all_noun(strings):
    noun_phrases = []
    for each in strings:
        noun_phrases += get_noun_phrases_from_sentence(each)
    return noun_phrases


def lang_dectect(doc, threshold=0.8):
    # language_cnt = {'en': 0, 'other': 0}
    language_cnt = Counter()
    total_length = 0
    for paragraph in doc:
        length = len(paragraph.split(' '))
        lang_type = langid.classify(paragraph)[0]
        language_cnt[lang_type] += length
        total_length += length
        # if lang_type == 'en':
        #     language_cnt['en'] += length
        # else:
        #     print(lang_type)
        #     language_cnt['other'] += length
    # compute main language
    all = language_cnt.most_common()
    main_name, main_length = all[0]
    is_english = (main_name == 'en') and (float(main_length) > (float(total_length) * threshold))
    logging.debug(main_name)
    return is_english


def language_unify(doc):
    unify_doc = []
    for paragraph in doc:
        paragraph = paragraph.strip()
        lang_type = langid.classify(paragraph)[0]
        if lang_type != 'en' and lang_type != 'other':
            answer = translator.translate(paragraph, lang_type, "en")
            if answer:
                unify_doc.append(answer)
        else:
            unify_doc.append(paragraph)
    return unify_doc


class Phrase2vec:
    def __init__(self):
        self._root = os.path.dirname(__file__)
        logging.info("Initial a {}".format(self.__class__))

        # load config
        config_file = os.path.join(self._root, "text_sugg_cfg.yaml")
        logging.info("Load config from: {}".format(config_file))
        with open(config_file, "r") as fconfig:
            self._config = yaml.load(fconfig)

        # NLP helper
        self._stopwords = self._load_stops(filename=os.path.join(self._root, "./stop-word-list.txt"))
        self._inflect = inflect.engine()

        # load word2vec models
        self._word2vec = KeyedVectors.load_word2vec_format(fname=os.path.join(self._root, "./model_google50w_wv.bin"),
                                                           binary=True)

    @staticmethod
    def _load_stops(filename):
        logging.info("Load stopwords from: {}".format(filename))
        with open(filename, "r") as finput:
            word_set = set([x.strip() for x in finput.readlines()])
        return word_set

    def _remove_stopwords(self, raw_text):
        # remove the stopwords in raw_text
        text_nostops = filter(lambda x: x not in self._stopwords, raw_text.split(' '))
        return text_nostops

    def _recheck_suggs(self, candidate, rough_suggs):
        # sub function of word format
        def word_fmt(word):
            ret_word = word.lower()
            temp = self._inflect.singular_noun(ret_word)  # singular noun
            ret_word = temp if temp else ret_word
            logging.debug("{} ==> {}".format(word, ret_word))
            return ret_word

        # unique the suggestions
        # suggs = set([candidate.lower()])
        suggs = {word_fmt(candidate)}

        checked_suggs = list()
        for sugg, weight in rough_suggs:
            new_sugg = word_fmt(sugg)
            if new_sugg not in suggs:
                suggs.add(new_sugg)
                checked_suggs.append((sugg, weight))
        logging.debug(rough_suggs)
        logging.debug(checked_suggs)
        return list(checked_suggs)

    def vector(self, phrase_text, unify=False):
        # format input phrase
        fmt_word = self._remove_stopwords(phrase_text)
        fmt_word = [x for x in fmt_word if x in self._word2vec.vocab]
        logging.debug(fmt_word)

        # vectorization
        phrase_vector = []
        # compute the weighted average of all words
        for word in fmt_word:
            temp = self._word2vec[word]
            phrase_vector.append(temp)
        if not phrase_vector:
            raise ValueError("Unknow NP: {}".format(phrase_text))
        ret_vetor = array(phrase_vector).mean(axis=0)
        if unify:
            ret_vetor = matutils.unitvec(ret_vetor).astype(REAL)
        return ret_vetor
