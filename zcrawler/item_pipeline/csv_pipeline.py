# coding: utf-8
"""
通过配置变量指定的参数
    CSV_OUTPUT  保存的文件名, 不指定默认为out.csv
    CSV_ROW     标题行
"""
__author__ = 'nevor'
import logging
import csv

logger = logging.getLogger(__name__)

class CSVPipeline():

    def __init__(self, output, titles):
        self.fp = open(output, 'wb')
        self.csv_writer = csv.writer(self.fp)
        self.titles = titles
        if self.titles:
            self.csv_writer.writerow(map(self.utf_8_encode, self.titles))
        logger.info('csv pipeline initialized: %s, %s' % (output, self.titles))

    @classmethod
    def from_crawler(cls, crawler):
        titles = crawler.settings.get('CSV_ROW', None)
        if titles:
            titles = titles.split(',')
        return cls(
            crawler.settings.get('CSV_OUTPUT', 'out.csv'),
            titles
        )

    def close_spider(self, spider):
        self.fp.close()

    def process_item(self, item, spider):
        if not self.titles:
            self.titles = item.keys()
            self.csv_writer.writerow(self.titles)

        value = [item[attr] for attr in self.titles]
        self.csv_writer.writerow(map(self.utf_8_encode, value))
        return item

    def utf_8_encode(self, s):
        if s:
            return s.encode('utf-8')
        else:
            return ''



