# coding: utf-8
import time
import hashlib
import urllib
import logging

from scrapy.item import Item
from scrapy.http import Request
from scrapy.spiders import Spider
from scrapy.utils.response import get_base_url
from urlparse import urljoin

import sys
import os
PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(PARENT_DIR + '/../../')
sys.path.append(ROOT_DIR)
from zeus_parsers.config_parser import parse as config_parse
from zeus_parsers.constants import *
from zeus_parsers.jsonex import load as jsonload
from zeus_parsers.jsonex import loads as jsonloads
import copy


class ZeusSpider(Spider):
    name = 'zeus'

    def __init__(self, **kwargs):
        Spider.__init__(self, **kwargs)

        self.config_file = kwargs.get('config_file', None)
        config = kwargs.get('config', None)
        if self.config_file:
            jconfig = jsonload(open(self.config_file))
        elif config:
            jconfig = jsonloads(config)
        else:
            self.log('config_file or config is expected', level=logging.CRITICAL)
            raise Exception('config_file or config is expected')

        self.template = config_parse(jconfig)

        # 指定单个要爬的入口地址，可用于测试，或者单独爬取某个页面
        self.specify_url = kwargs.get('specify_url', None)

        # 指定抓取页面数
        self.max_pages = kwargs.get('max_pages', None)

    def start_requests(self):
        """
        start job from here
        """
        for crawler in self.template.crawlers:
            for url in crawler.sites:
                if self.specify_url and self.specify_url != url:
                    continue
                meta = {
                    META_EXTRACTORS: crawler.extrators,
                    META_ENTRY_PAGE: url
                }
                if crawler.meta_procedures:
                    vars = dict()
                    for key, procedures in crawler.meta_procedures.items():
                        vars[key] = procedures.extract(None)
                    meta[META_VARS] = vars
                self.log('crawl %s' % url, level=logging.INFO)
                yield Request(url=url, meta=meta, callback=self.traversal)

    def traversal(self, response):
        if META_EXTRACTORS not in response.meta:
            return

        meta = response.meta
        extractors = meta[META_EXTRACTORS]
        entry_page = meta[META_ENTRY_PAGE]
        pre_item = meta.get(META_ITEM, None)

        for extractor in extractors:
            # 先判断condition
            if extractor.condition_procedures and not extractor.condition_procedures.extract(response, response=response):
                self.log('condition fell in %s' % response.url, level=logging.DEBUG)
                continue

            # 判断是否需要webdriver和是否用了webdriver，如果需要，但没用，则重新请求一次
            if extractor.cur_webdriver and 'webdriver' not in meta:
                next_meta = meta.copy()
                next_meta['webdriver'] = extractor.cur_webdriver
                next_meta[META_EXTRACTORS] = [extractor]
                self.log('re-request the page %s' % response.url, level=logging.DEBUG)
                yield Request(url=response.url, meta=next_meta, callback=self.traversal, dont_filter=True)
            else:
                # 如果有entity配置，则先解析item
                # 逻辑上支持entity传递和分页，但不能同时支持传递和分页，如果有分页，则不能传递
                item = None
                if extractor.entity:
                    item = self.parse_entity(extractor.entity, response, response=response, url=response.url)
                    if extractor.entity.pager:
                        # 正文分页
                        url = extractor.entity.pager['next_url'].extract(response, response=response)
                        url = first_url(url)
                        if url:
                            next_meta = meta.copy()
                            next_meta[META_ENTITY] = item
                            next_meta[META_URL] = response.url
                            next_meta[META_ENTITY_CONFIG] = extractor.entity
                            yield Request(url=url, meta=next_meta, callback=self.pages_entity)
                            continue

                # 如果有需要合并的entity，则在此合并
                if pre_item:
                    item.update(pre_item)

                # 如果有下一级，则当前解析的entity不进入item pipeline，传给下一级
                if extractor.urls_procedures:
                    urls = extractor.urls_procedures.extract(response, response=response)
                    if urls:
                        next_meta = {
                            META_EXTRACTORS: extractor.extractors,
                            META_ENTRY_PAGE: entry_page
                        }
                        # 如果当前有解析entity，则传到下一级
                        if item:
                            next_meta[META_ITEM] = item
                        if extractor.webdriver:
                            next_meta['webdriver'] = extractor.webdriver
                        if extractor.meta_procedures:
                            vars = dict()
                            for key, procedures in extractor.meta_procedures.items():
                                vars[key] = procedures.extract(response, response=response)
                            next_meta[META_VARS] = vars
                        for url in urls:
                            yield Request(url=url, meta=next_meta, callback=self.traversal)
                elif item:
                    # 补充id, url等属性
                    item = make_item(response, item)
                    yield ZeusItem(item, self, entry_page=entry_page)

            # 如果需要翻页，则带上当前extractor配置，传给下一页 
            if extractor.pager:
                e_pager = extractor.pager
                cur_page = meta.get(META_PAGE, 1)
                if self.max_pages and cur_page >= self.max_pages \
                        or self.max_pages is None and 'max_pages' in e_pager and cur_page >= e_pager['max_pages']:
                    pass
                else:
                    cur_page += 1
                    url = e_pager['next_url'].extract(response, response=response)
                    url = first_url(url)
                    if url:
                        next_meta = meta.copy()
                        next_meta[META_PAGE] = cur_page
                        yield Request(url=url, meta=next_meta, callback=self.traversal)


            # 不再执行后续的extractor
            if extractor.last:
                break


    def pages_entity(self, response):
        """
        处理正文分页的情况
        :param response:
        :return:
        """
        meta = response.meta
        entity = meta[META_ENTITY]
        entity_config = meta[META_ENTITY_CONFIG]
        entry_page = meta[META_ENTRY_PAGE]

        pager_attrs = entity_config.pager['pager_attrs']
        attrs = pager_attrs.keys()
        new_entity = self.parse_entity(entity_config, response, response=response, url=response.url, attrs=attrs)
        for key, type_ in pager_attrs.items():
            if type_ == True:
                # 按数组合并，先判断原值是不是数组，不是的话，无转成数组
                if not isinstance(entity[key], list):
                    entity[key] = [entity[key]]
                if not isinstance(new_entity[key], list):
                    new_entity[key] = [new_entity[key]]
                entity[key].extend(new_entity[key])
            elif isinstance(type_, basestring):
                # 字符串，join起来就行
                # 处理一下有None的情况
                if not entity[key]:
                    entity[key] = new_entity[key]
                elif not new_entity[key]:
                    pass
                else:
                    entity[key] = type_.join([entity[key], new_entity[key]])
            else:
                raise Exception('entity "%s" wrong "pager" config at field "%s"' % (entity.name, key))

        url = entity_config.pager['next_url'].extract(response, response=response)
        url = first_url(url)
        if url:
            yield Request(url=url, meta=meta, callback=self.pages_entity)
        else:
            item = make_item(response, entity)
            yield ZeusItem(item, self, entry_page=entry_page)

    def parse_entity(self, config, input_, **kwargs):
        item = config.parse(input_, **kwargs)
        self.check_item(item, config, kwargs['url'])
        return item

    def check_item(self, item, entity, url):
        """
        查看item里，是否有None项，有则log下
        :param item:
        :return:
        """
        for key, value in item.items():
            if value is None:
                self.log('attr parse empty or error: entity "%s" attr "%s" in "%s"' % (entity.name, key, url), level=logging.WARNING)


def first_url(urls):
    """
    处理Procedures返回的地址，有的会返回数组，有的会返回字符串，这里提取出复用代码
    """
    if isinstance(urls, list):
        if len(urls) > 0:
            return urls[0]
        return None
    else:
        return urls


def make_item(response, item):
    rel_url = response.meta.get(META_URL)
    if rel_url:
        response = response.replace(url=rel_url)
    item[URL] = response.url
    return item


class ZeusItem(Item):
    """ 为了动态构造 scrapy item 用的辅助类 """

    def __setitem__(self, key, value):
        self._values[key] = value
        self.fields[key] = {}

    def __init__(self, items, spider, **kwargs):
        Item.__init__(self)
        for k, v in items.items():
            self[k] = v


if __name__ == '__main__':
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    process = CrawlerProcess(get_project_settings())
    process.crawl(ZeusSpider)
    process.start()
