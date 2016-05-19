# -*- coding: UTF8 -*-

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from scrapy import signals
from scrapy.http import HtmlResponse
from pydispatch import dispatcher
from scrapy.exceptions import IgnoreRequest

import logging
import importlib

import os
import sys
PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(PARENT_DIR + '/../../')
sys.path.append(ROOT_DIR)


logger = logging.getLogger(__name__)


def check_selenium_service(command_executor, capability):
    browser = WebDriver(command_executor=command_executor, desired_capabilities=capability)
    try:
        browser.get('http://www.baidu.com')
        if len(browser.page_source) > 0:
            logger.info('check remote webdriver (%s) capability (%s) successfully' % (command_executor, capability['browserName']))
            return True
        else:
            logger.warning('check remote webdriver (%s) capability (%s) failed' % (command_executor, capability['browserName']))
            return False
    finally:
        browser.quit()


class SeleniumGridMiddleware(object):
    """
    需要在request.meta中添加键_SELENIUM_GRID_META，结构如下
    {
        'name': 'selenium_grid'
        'action': string,   // zeus_actions下的module名
    }
    """
    def __init__(self, host, port, capability):
        # indicate whether the config and remote server is available
        self.error = False
        self.driver = None

        h = host
        p = port
        self.command_executor = 'http://{h}:{p}/wd/hub'.format(h=h, p=p)
        if capability == 'firefox':
            self.capability = DesiredCapabilities.FIREFOX
        elif capability == 'phantomjs':
            self.capability = DesiredCapabilities.PHANTOMJS
        else:
            logger.warning('unknow capability "%s"' % capability)
            self.error = True

    @classmethod
    def from_crawler(cls, crawler):
        host = crawler.settings.get('SELENIUM_GRID_HOST', None)
        port = crawler.settings.get('SELENIUM_GRID_PORT', None)
        capability = crawler.settings.get('SELENIUM_GRID_CAPABILITY', 'phantomjs')
        return cls(host, port, capability)

    def process_request(self, request, spider):
        if hasattr(request, 'meta') and 'webdriver' in request.meta and request.meta['webdriver'].get('name', '') == 'selenium_grid':
            driver = self.get_driver()
            if driver:
                try:
                    meta = request.meta['webdriver']
                    action = meta.get('module', None)
                    if not action:
                        raise IgnoreRequest('selenium grid request must have "act" item in meta')
                    m = importlib.import_module('zeus_actions.'+action)
                    f = getattr(m, 'act')
                    if f is None or not hasattr(f, '__call__'):
                        raise IgnoreRequest('module %s must implement "act" method' % action)
                    self.driver.get(request.url)
                    f(self.driver)
                    body = self.driver.page_source
                    return HtmlResponse(url=request.url, body=body, request=request, encoding='utf-8')
                finally:
                    #self.driver.close()
                    pass

    def get_driver(self):
        if self.error:
            return None
        if not self.driver:
            checked = check_selenium_service(self.command_executor, self.capability)
            if checked:
                self.driver = WebDriver(command_executor=self.command_executor, desired_capabilities=self.capability)
                dispatcher.connect(self.spider_closed, signals.spider_closed)
            else:
                self.error = True

        return self.driver

    def spider_closed(self):
        if self.driver:
            self.driver.quit()
        logger.info("selenium driver quit.")


if __name__ == '__main__':
    # check_selenium_service('http://127.0.0.1:4444/wd/hub')
    print ROOT_DIR

    def test_action(my_driver):
        my_driver.execute_script("window.scrollTo(0, document.body.offsetHeight);")

    print callable(test_action)
