#!/root/.pyenv/versions/3.6.2/bin/python
# -*- coding:utf8 -*-


import asyncio
import datetime
import json
import logging
import re
import sys
from collections import namedtuple
from urllib.parse import urlparse, urljoin

import aiohttp
from bs4 import BeautifulSoup
from bson import ObjectId

from MongoManager import MongoManager
from webanalysis.extractor import KeyphraseExtractor

log_format_str = "%(levelname)s: %(asctime)s %(filename)s(%(lineno)d) %(msg)s"
logging.basicConfig(format=log_format_str, level=logging.INFO)
web_analyst = KeyphraseExtractor()

ExtractResult = namedtuple('ExtractResult', ['company_info_data'])
PageResult = namedtuple('PageResult', ['website_title', 'website_keyword', 'website_description', 'company_logo',
                                       'address', 'social_media', 'emails'])

if len(sys.argv) == 3:
    header = "company_search_"
    source_collection = (header + sys.argv[1])
    logging.info(source_collection)
    target_collection = (header + sys.argv[2])
    logging.info(target_collection)
else:
    sys.exit()


async def fetch_html_by_home_page(_id, url, timeout=45):
    try:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.request('GET', url, headers=headers, timeout=timeout) as resp:
                text = await resp.text()
                return text
    except Exception as err:
        with MongoManager(host='165.227.5.92', db='company_keyword') as company_keyword:
            source_coll = company_keyword[source_collection]
            source_coll.update({'_id': _id}, {'$set': {'request_status': 2}})
        logging.error('Error-> {}:{}'.format(url, err))
        raise


async def fetch_html_by_second_page(url, timeout=45):
    try:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.request('GET', url, headers=headers, timeout=timeout) as resp:
                text = await resp.text()
                return text
    except Exception as err:
        logging.error('Error-> {}:{}'.format(url, err))
        raise


async def extract_page(website):
    logging.debug(website)
    for k, v in website:
        _id = k
        website = v
    page_keyword = ["about", "product", "service", "company", "profile"]
    company_info_data = company_info_data_formatter()
    company_info_data['_id'] = ObjectId(_id)
    basic_content = []
    dic_basic = {}

    home_html = ''
    home_html = await fetch_html_by_home_page(_id, website)
    logging.debug("homehtml")
    logging.debug(home_html)
    home_soup = BeautifulSoup(home_html, 'html5lib')
    logging.debug(home_soup)
    cursor_id = 0
    try:
        status_code, key_phrases = web_analyst.get_webpage_phrases(html_doc=home_html)
        logging.debug(key_phrases)
        logging.debug(status_code)
        if key_phrases:
            key_phrases = [{item[0]: item[1]} for item in key_phrases]
            key_phrases = json.dumps(key_phrases)
            dic_basic["keyword"] = key_phrases
            dic_basic["url"] = website
            dic_basic["status_code"] = status_code
            basic_content.append(dic_basic)
            dic_basic = {}
        else:
            dic_basic["url"] = website
            dic_basic["status_code"] = status_code
            basic_content.append(dic_basic)
            dic_basic = {}
    except ValueError as err:
        logging.warning("ValueError-> {}: {}".format(cursor_id, err))
    except Exception as err:
        logging.error('Error-> {}:{}'.format(cursor_id, err))
    url_list = set()
    for kw in page_keyword:
        desc_url = get_url_from_soup(home_soup, website, kw)
        if desc_url:
            url_list.add(desc_url)
    url_list = list(url_list)
    if url_list:
        for web_url in url_list:
            url_html = await fetch_html_by_second_page(web_url)
            if url_html:
                cursor_id = 0
                try:
                    status_code, key_phrases = web_analyst.get_webpage_phrases(html_doc=url_html)
                    if key_phrases:
                        key_phrases = [{item[0]: item[1]} for item in key_phrases]
                        key_phrases = json.dumps(key_phrases)
                        dic_basic["keyword"] = key_phrases
                        dic_basic["url"] = web_url
                        dic_basic["status_code"] = status_code
                        basic_content.append(dic_basic)
                        dic_basic = {}
                    else:
                        dic_basic["url"] = website
                        dic_basic["status_code"] = status_code
                        basic_content.append(dic_basic)
                        dic_basic = {}
                except ValueError as err:
                    logging.warning("ValueError-> {}: {}".format(cursor_id, err))
                except Exception as err:
                    logging.error('Error-> {}:{}'.format(cursor_id, err))

    if len(basic_content) > 0:
        company_info_data["basic"] = basic_content
    rs = company_info_data
    logging.info(company_info_data)
    with MongoManager(host='165.227.5.92', db='company_keyword') as company_key:
        odm_coll = company_key[target_collection]
        odm_coll.save(company_info_data, check_keys=False)
        company_coll = company_keyword[source_collection]
        company_coll.update({'_id': _id}, {'$set': {'request_status': 1}})
    return rs


def filter_dict(obj):
    return {k: v for k, v in obj.items() if v}


def filter_companpy_info(company_info_data):
    return filter_dict({
        'basic': filter_dict(company_info_data['basic'])
    })


def company_info_data_formatter():
    return {
        'basic': None
    }


def get_url_from_soup(soup, domain, kw):
    pattern = (".*" + kw + ".*")
    links = soup.find_all('a', attrs={'href': re.compile(pattern, re.I)})
    domain_parse_result = urlparse(domain)
    contact_url = None
    for link_tag in links:
        if 'href' not in link_tag.attrs:
            continue
        link_parse_result = urlparse(link_tag['href'])
        if link_parse_result.scheme and link_parse_result.netloc != domain_parse_result.netloc:
            # print('not match')
            continue
        # contruct contact url
        contact_url = urljoin(domain, link_parse_result.path)
        break
    return contact_url


def send_refinery_tasks(webs):
    loop = asyncio.get_event_loop()
    try:
        tasks = [extract_page(website.items()) for website in webs]
        loop.run_until_complete(asyncio.wait(tasks))
    except Exception as e:
        logging.error(e)


if __name__ == '__main__':
    start = datetime.datetime.now()
    logging.info("program start at :  %s" % datetime.datetime.now())
    websites = []
    with MongoManager(host='165.227.5.92', db='company_keyword') as company_keyword:
        source_coll = company_keyword[source_collection]
        # for element in source_coll.find({"_id": ObjectId('593a6013e13823174b0d545e')}).limit(1):
        for element in source_coll.find({"request_status": {'$exists': False}}, no_cursor_timeout=True):
            company_id = element["_id"]
            url = element["url"]
            data = {company_id: url}
            if len(websites) < 50:
                websites.append(data)
            if len(websites) == 50:
                send_refinery_tasks(websites)
                websites = []
        if len(websites) > 0:
            send_refinery_tasks(websites)
    end = datetime.datetime.now()
    logging.info("program end at :  %s" % datetime.datetime.now())
    logging.info("program total time %s" % (end - start))
