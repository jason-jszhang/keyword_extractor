# -*- coding: utf-8 -*-
# @Author   : Lawrence Liu
# @Date     : 2017/12/8 14:54
# @Filename : words_utils
import codecs
import json
import logging
import os
import shutil

import yaml
from collections import Counter

from ..helper import init_mongo_collection


def load_config(config_path):
    logging.debug("config file path: {}".format(config_path))
    with open(config_path, "r") as fconfig:
        mongo_cfg = yaml.load(fconfig)
        logging.debug(mongo_cfg)
    return mongo_cfg


def ketyphrase_rank():
    """
    Rank keyphrases by equivalent of IDF, in reverse
    :return: 
    """
    mongo_file = "../mongocfg.yaml"
    output_file = "./phrases.stat"

    mongo_cfg = load_config(mongo_file)
    # db_handler = init_mongo_collection(mongo_cfg["DB_page_source"])
    db_handler = init_mongo_collection(mongo_cfg["DB_com_keyword"])
    query = {}
    # total = db_handler.count(filter=query)
    # logging.info(total)

    phrases_counter = Counter()
    total_size = 0
    for idx, cursor in enumerate(db_handler.find(filter=query)):
        try:
            if cursor["basic"] is None:
                continue

            total_size += 1
            # logging.info(cursor)

            for info in cursor["basic"]:
                keyphrase_list = []

                if isinstance(info["keyword"], list):
                    for keyphrase in info["keyword"]:
                        keyphrase_list.extend(keyphrase.keys())
                    for item in keyphrase_list:
                        phrases_counter[item] += 1
                elif isinstance(info["keyword"], str):
                    content = json.loads(info["keyword"])
                    for keyphrase in content:
                        keyphrase_list.extend(keyphrase.keys())
                    for item in keyphrase_list:
                        phrases_counter[item] += 1
                else:
                    raise Exception
        except Exception as err:
            logging.error(cursor["_id"])
            logging.exception(err)
            exit()

        if (idx+1) % 10000 == 0:
            logging.info("{} item processed.".format(idx+1))
            # break

    # output
    with codecs.open(output_file, "w", "utf-8") as foutput:
        for item, cnt in phrases_counter.most_common(10000):
            print("{}\t{:d}".format(item, cnt), file=foutput)


def artificial_black_list():
    # input_file = "./phrases.stat"
    input_file = "./phrases(3)(1).stat"
    last_file = "./posterior_ban.bak"
    output_file = "./posterior_ban"
    # load old black list
    last_blk = set()
    if os.path.exists(last_file):
        with codecs.open(last_file, "r", "utf-8") as flast:
            for line in flast:
                last_blk.add(line.strip())
    logging.info("Load {}.".format(last_file))
    # update black list
    with codecs.open(input_file, "r", "utf-8") as finput, codecs.open(output_file, "w", "utf-8") as foutput:
        idx = 0
        for line in finput:
            if line.startswith('\t'):
                idx += 1
                keyphrase, cnt = line.strip().split('\t')
                logging.info("[{:d}] {}".format(idx, keyphrase))
                last_blk.add(keyphrase)
        for keyphrase in last_blk:
            print(keyphrase, file=foutput)
    logging.info("Update {}.".format(output_file))
    # copy new black list to old one
    shutil.copy(output_file, last_file)
    logging.info("Copy {} ==> {}".format(output_file, last_file))


def clean_db_keyphrase():
    # load black list
    black_file = "./posterior_ban"
    black_list = set()
    if os.path.exists(black_file):
        with codecs.open(black_file, "r", "utf-8") as fblack:
            for line in fblack:
                black_list.add(line.strip())
    logging.info("Load {}.".format(black_file))

    # connect mongodb & clean keyphrase
    mongo_file = "../mongocfg.yaml"
    mongo_cfg = load_config(mongo_file)
    db_handler = init_mongo_collection(mongo_cfg["DB_com_keyword"])
    query = {}
    total = db_handler.count(filter=query)
    logging.info("Total: {:d}".format(total))

    for idx, cursor in enumerate(db_handler.find(filter=query)):
        curosr_id = cursor["_id"]
        try:
            if cursor["basic"] is None:
                continue

            keyphrases = list()
            for info in cursor["basic"]:
                if isinstance(info["keyword"], list):
                    for keyphrase in info["keyword"]:
                        keyphrases.extend(keyphrase.keys())
                elif isinstance(info["keyword"], str):
                    content = json.loads(info["keyword"])
                    for keyphrase in content:
                        keyphrases.extend(keyphrase.keys())
                else:
                    raise Exception
            final = list(set(keyphrases) - black_list)
            if len(final) > 0:
                db_handler.update_one(filter={"_id": curosr_id}, update={"$set": {"keyphrases": final}})
        except Exception as err:
            logging.error(cursor["_id"])
            logging.exception(err)
            exit(-1)
        if (idx+1) % 1000 == 0:
            logging.info("[{:d}/{:d}] item processed.".format(idx+1, total))


if __name__ == '__main__':
    log_format_str = "%(levelname)s %(asctime)s %(filename)s(%(lineno)d) %(msg)s"
    logging.basicConfig(format=log_format_str, level=logging.INFO)

    # ketyphrase_rank()

    # artificial_black_list()

    clean_db_keyphrase()
