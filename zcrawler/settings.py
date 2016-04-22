# -*- coding: utf-8 -*-

# Scrapy settings for zcrawler project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'zcrawler'

SPIDER_MODULES = ['zcrawler.spiders']
NEWSPIDER_MODULE = 'zcrawler.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'zcrawler (+http://www.yourdomain.com)'

#LOG_ENABLED = False
LOG_LEVEL = 'DEBUG'


DOWNLOADER_MIDDLEWARES = {
    'zcrawler.download_middlewares.selenium_grid_middleware.SeleniumGridMiddleware': 101
}

SELENIUM_GRID_HOST = '127.0.0.1'
SELENIUM_GRID_PORT = '4444'
SELENIUM_GRID_CAPABILITY = 'firefox'