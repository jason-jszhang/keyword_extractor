# -*- coding: utf-8 -*-
# @Author   : Lawrence Liu
# @Date     : 2017/11/30 17:37
# @Filename : helper
import logging
import pymongo


def init_mongo_collection(mongo_cfg):
    if "password" in mongo_cfg:
        # need authorization
        mongo_uri = "mongodb://{}:{}@{}:{}/{}".format(mongo_cfg["user"],
                                                      mongo_cfg["password"],
                                                      mongo_cfg["host"],
                                                      mongo_cfg["port"],
                                                      mongo_cfg["auth_db_name"])
    else:
        mongo_uri = "mongodb://{}:{}/{}".format(mongo_cfg["host"],
                                                mongo_cfg["port"],
                                                mongo_cfg["db_name"])
    logging.info("Connect to :{}".format(mongo_uri))
    db_handler = pymongo.MongoClient(mongo_uri, connect=False)
    mongo_dbname = mongo_cfg["db_name"]
    mongo_collection = mongo_cfg["coll_name"]
    return db_handler[mongo_dbname][mongo_collection]


def url_format(url):
    if url.startswith('http'):
        my_url = url
    else:
        my_url = 'http://' + url
    return my_url
