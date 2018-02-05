#!/root/.pyenv/versions/3.6.2/bin/python
# -*- coding:utf8 -*-


import datetime
import json
import logging
import re
from collections import namedtuple
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from bson import ObjectId

# from MongoManager import MongoManager
# from extractor import KeyphraseExtractor
from webanalysis.extractor import KeyphraseExtractor

log_format_str = "%(levelname)s: %(asctime)s %(filename)s(%(lineno)d) %(msg)s"
logging.basicConfig(format=log_format_str, level=logging.INFO)
web_analyst = KeyphraseExtractor()

ExtractResult = namedtuple('ExtractResult', ['company_info_data'])
PageResult = namedtuple('PageResult', ['website_title', 'website_keyword', 'website_description', 'company_logo',
                                       'address', 'social_media', 'emails'])


def fetch_html_by_url(url, timeout=45):
    try:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36"
        }
        logging.info(url)
        with requests.get(url, headers=headers, timeout=timeout) as resp:
            # code = await resp.status
            text = resp.text
            # logging.error(code)
            return text
    # except TimeoutError as e:
    #    logging.error('TimeoutError-> {}:{}'.format(url, e))
    #    # raise
    # except asyncio.CancelledError as e:
    #    logging.error('CancelledError-> {}:{}'.format(url, e))
    #    # raise
    except Exception as e:
        # logging.error(e.with_traceback)
        logging.error('Error-> {}:{}'.format(url, e))


def extract_page(website):
    logging.info(website)
    for k, v in website:
        _id = k
        website = v
    page_keyword = ["about", "product", "service", "company", "profile"]
    company_info_data = company_info_data_formatter()
    company_info_data['_id'] = ObjectId(_id)
    basic_content = []
    dic_basic = {}

    try:
        home_html = ''
        home_html = fetch_html_by_url(website)
        logging.debug("homehtml")
        logging.debug(home_html)
        if not home_html:
            # with MongoManager(host='45.32.1.194', db='company_keyword') as company_keyword:
            #     source_coll = company_keyword["company_search_refinery20"]
            #     source_coll.update({'_id': _id}, {'$set': {'refinery_status': 2}})
            return None
    except Exception as e:
        logging.error(e)
    home_soup = BeautifulSoup(home_html, 'html5lib')
    logging.debug(home_soup)
    cursor_id = 0
    try:
        status_code, key_phrases = web_analyst.get_webpage_phrases(html_doc=home_html)
        logging.info(key_phrases)
        if key_phrases:
            key_phrases = [{item[0]: item[1]} for item in key_phrases]
            key_phrases = json.dumps(key_phrases)
            dic_basic["keyword"] = key_phrases
            dic_basic["url"] = website
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
            url_html = fetch_html_by_url(web_url)
            if url_html:
                cursor_id = 0
                try:
                    status_code, key_phrases = web_analyst.get_webpage_phrases(html_doc=url_html)
                    if key_phrases:
                        key_phrases = [{item[0]: item[1]} for item in key_phrases]
                        key_phrases = json.dumps(key_phrases)
                        dic_basic["keyword"] = key_phrases
                        dic_basic["url"] = web_url
                        basic_content.append(dic_basic)
                        dic_basic = {}
                except ValueError as err:
                    logging.warning("ValueError-> {}: {}".format(cursor_id, err))
                except Exception as err:
                    logging.error('Error-> {}:{}'.format(cursor_id, err))

    if len(basic_content) > 0:
        company_info_data["basic"] = basic_content
    # rs = ExtractResult(company_info_data=filter_companpy_info(company_info_data))
    rs = company_info_data
    logging.info(company_info_data)
    # with MongoManager(host='45.32.1.194', db='company_keyword') as company_keyword:
    #     odm_coll = company_keyword["company_search_improve20"]
    #     odm_coll.save(company_info_data, check_keys=False)
    #     company_coll = company_keyword["company_search_refinery20"]
    #     company_coll.update({'_id': _id}, {'$set': {'refinery_status': 1}})
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
    for website in webs:
        extract_page(website.items())
        # loop = asyncio.get_event_loop()
        # try:
        #     tasks = [extract_page(website.items()) for website in webs]
        #     loop.run_until_complete(asyncio.wait(tasks))
        # except Exception as e:
        #     logging.error(e)


if __name__ == '__main__':
    start = datetime.datetime.now()
    logging.info("program start at :  %s" % datetime.datetime.now())
    websites = []
    # with MongoManager(host='45.32.1.194', db='company_keyword') as company_keyword:
    #     source_coll = company_keyword["company_search_refinery20"]
    #     for element in source_coll.find({"_id": ObjectId('59babb59ef0090ce1bc08b31')},no_cursor_timeout=True):
    # for element in source_coll.find({"refinery_status": {'$exists': False}}).limit(101):
    # for element in source_coll.find({"refinery_status": 2}):
    company_id = ObjectId('59babb59ef0090ce1bc08b31')  # element["_id"]
    url = 'http://www.01distribution.it/'  # element["url"]
    data = {company_id: url}
    websites.append(data)
    logging.debug(websites)
    send_refinery_tasks(websites)

    end = datetime.datetime.now()
    logging.info("program end at :  %s" % datetime.datetime.now())
    logging.info(end - start)
