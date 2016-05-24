# coding: utf-8
__author__ = 'nevor'

from entity import EntityParser
from extractor import ExtratorParser
from constants import *
from procedure import parse_procedures


class Template():
    def __init__(self):
        self.name = None
        self.entities = None
        self.extractors = None
        self.crawlers = None

    def get_entity(self, name):
        return None if self.entities is None else self.entities[name]

    def get_extractor(self, name):
        return None if self.extractors is None else self.extractors[name]


class Crawler():
    def __init__(self):
        self.name = None
        self.sites = None
        self.extrators = None
        self.meta_procedures = None


def parse(conf):
    template = Template()
    template.name = conf[TEMPLATE_NAME]

    # parse templates
    entity_parser = EntityParser()
    entities_conf = conf[ENTITIES]
    entities = entity_parser.parse_entities(entities_conf)
    template.entities = entities

    # parse crawlers
    crawlers = list()
    extrator_parser = ExtratorParser()
    crawlers_conf = conf[CRAWLERS]
    if type(crawlers_conf) != list:
        crawlers_conf = [crawlers_conf]
    for conf in crawlers_conf:
        crawler = Crawler()
        crawler.name = conf.get('name', None)
        crawler.sites = conf[SITES]
        if EXTRACTORS not in conf:
            raise Exception('"%s" are expected in "crawlers"' % EXTRACTORS)
        crawler.extrators = extrator_parser.parse_extractors(conf[EXTRACTORS], entities)

        #parse meta
        if 'meta' in conf:
            crawler.meta_procedures = dict()
            for key, values in conf['meta'].items():
                crawler.meta_procedures[key] = parse_procedures(values)
        crawlers.append(crawler)
    template.crawlers = crawlers
    template.extractors = extrator_parser.all_extractors

    return template


if __name__ == '__main__':
    import sys
    from crawlers.ycrawler.zeus_parsers.jsonex import load as jload


    def usage():
        print 'usage:'
        print '\t', __name__, ' config_file'
        exit()

    if len(sys.argv) != 2:
        usage()

    filename = sys.argv[1]
    file = open(filename, 'r')
    jconf = jload(file)
    template = parse(jconf)
    print 'parse OK'

