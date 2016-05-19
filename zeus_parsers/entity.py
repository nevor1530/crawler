# coding: utf-8
__author__ = 'nevor'
import copy
import logging

from procedure import parse_procedures


logger = logging.getLogger(__file__)


def is_empty_list(list_):
    if not list_:
        return True
    else:
        for i in list_:
            if i:
                return False
        return True


class Entity():
    def __init__(self):
        self.name = None

        # key is attr's name
        # value is a list consist of several procedures
        self.attrs = dict()

        # 正文多页的配置
        self.pager = None
        pass

    def parse(self, content, **kwargs):
        """
        kwargs中的参数
        url 当前内容来源地址
        response scrapy request返回的Response对象
        attrs 只解析指定的几个字段
        :return:
        """
        results = dict()
        if 'url' in kwargs:
            url = kwargs['url']
        else:
            url = ''

        if 'attrs' in kwargs:
            it_attrs = [(name, self.attrs[name]) for name in kwargs['attrs']]
        else:
            it_attrs = self.attrs.items()

        for name, procedures in it_attrs:
            if not procedures:
                continue
            res = content
            try:
                res = procedures.extract(res, **kwargs)
                results[name] = res
                if res is None or isinstance(res, list) and is_empty_list(res):
                    logger.warn('entity "%s" attr "%s" parse empty in "%s"' % (self.name, name, url))
            except:
                logger.exception('entity "%s" attr "%s" parse error in "%s"' %
                            (self.name, name, url))
        return results


class EntityParser():
    def __init__(self):
        self.all_entities = dict()
        pass

    def parse_entities(self, conf):
        """
        解析配置文件中entities，结果保存在all_entities
        :param conf:
        :return:
        """
        if type(conf) != list:
            conf = [conf]

        for c in conf:
            t = self.parse_entity(c)

        return self.all_entities

    def parse_entity(self, jobj):
        """
        解析单个entiry
        :param jobj:
        :return:
        """
        if 'name' not in jobj or not jobj['name']:
            raise Exception('entity need a name')

        new_ = Entity()

        new_.name = jobj['name']

        # 如果是继承别的模板,先把相应的attrs和pager配置copy过来
        if 'extends' in jobj:
            parent_name = jobj['extends']
            if parent_name not in self.all_entities:
                raise Exception('entity ', parent_name, ' not found')
            else:
                entity = self.all_entities[parent_name]
                new_.attrs = copy.copy(entity.attrs)
                new_.pager = copy.copy(entity.pager)

        # 如果没有继承,则必需定义attrs
        if 'extends' not in jobj and 'attrs' not in jobj:
            raise Exception('"attrs" is expect in entity ', new_.name)
        # 解析attrs
        if 'attrs' in jobj:
            for key, value in jobj['attrs'].items():
                try:
                    procedure_list = parse_procedures(value)
                except Exception, e:
                    raise Exception('the attr "%s" of entity "%s" parse error' % (key, new_.name), e)
                new_.attrs[key] = procedure_list

        # 多页内容
        if 'pager' in jobj:
            pager = dict()
            pager['next_url'] = parse_procedures(jobj['pager']['next_url'])
            pager['pager_attrs'] = jobj['pager']['pager_attrs']
            new_.pager = pager

        self.all_entities[new_.name] = new_

        return new_


if __name__ == '__main__':
    import sys
    import urllib2
    import json
    import logging.config
    import os
    PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.abspath(PARENT_DIR + '/..'))
    #from logging_conf import get_logging_conf_json
    from scrapy.http import HtmlResponse
    from zeus_parsers.jsonex import load as jload

    #logging.config.dictConfig(get_logging_conf_json('', debug=True))

    def usage():
        print 'usage:'
        print '\tpython ', __file__, ' config_file entiry_name url'
        exit()

    if len(sys.argv) != 4:
        usage()
    filename = sys.argv[1]
    entity_name = sys.argv[2]
    url = sys.argv[3]

    jobj = jload(open(filename, 'r'))
    parser = EntityParser()
    parser.parse_entities(jobj['entities'])

    data = urllib2.urlopen(url)
    content = data.read()

    response = HtmlResponse(url=url, body=content)
    entity = parser.all_entities[entity_name].parse(response, response=response, url=url)
    print json.dumps(entity, indent=4)
