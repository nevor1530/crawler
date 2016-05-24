# coding: utf-8
__author__ = 'nevor'
import re
import time
from urlparse import urljoin
import json

from scrapy.http import Response
from scrapy.selector import Selector
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy.utils.response import get_base_url
from scrapy.selector.unified import SelectorList
from jsonpath_rw_ext import parser as jsonpath_parser

from constants import META_VARS
import os
import sys
PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(PARENT_DIR + '/../')
sys.path.append(ROOT_DIR)
import utils.unstrict_json as myjson


def qualify_link(response, link):
    return urljoin(get_base_url(response), link)


class Procedures():
    def __init__(self, procedures):
        self.procedures = procedures

    def extract(self, input_, **kwargs):
        for p in self.procedures:
            input_ = p.run(input_, **kwargs)
        return input_


def parse_procedures(confs):
    if not confs:
        return None

    if type(confs[0]) != list:
        confs = [confs]
    procedures = list()
    for conf in confs:
        if conf[0] not in procedure_map:
            raise Exception('unknow procedure ', conf[0])
        type_ = procedure_map[conf[0]]
        procedure = type_(*conf[1:])
        procedures.append(procedure)
    return Procedures(procedures)


class BaseProcedure():
    def __init__(self, *args):
        pass

    def run(self, input_, **kwargs):
        if input_ is None:
            return None
        else:
            return self.do(input_, **kwargs)

    def do(self, input_, **kwargs):
        raise Exception('no implementation')


class ListableProcedure(BaseProcedure):
    def do(self, input_, **kwargs):
        if isinstance(input_, list):
            return [self.one(i, **kwargs) if i is not None else None for i in input_]
        else:
            return self.one(input_, **kwargs)


class XpathProcedure(BaseProcedure):
    """
    xpath path [multi] [selector]
    path 要解析的xpath参数
    selector false或无值返回extrator()后的结果, True返回SelectorList

    do输入
    input string|Response|Selector
    """
    def __init__(self, *args):
        """
        :return: string|array|SelectorList
        """
        if len(args) < 1 or len(args) > 3:
            raise Exception(__name__ + 'initialize arguments error')

        self._path = args[0]
        self._return_multi = False
        if len(args) > 1 and args[1]:
            self._return_multi = args[1]

        self._return_selector = False
        if len(args) > 2 and args[2]:
            self._return_selector = args[2]

    def do(self, input_, **kwargs):
        if isinstance(input_, Response) or isinstance(input_, SelectorList):
            res = input_.xpath(self._path)
        elif isinstance(input_, basestring):
            res = Selector(text=input_).xpath(self._path)
        else:
            raise Exception(__name__ + ' unknow type of argument' + str(type(input_)))

        if not self._return_selector:
            res = res.extract()
            if not self._return_multi:
                res = res[0] if res else None
        return res


class CssProcedure(BaseProcedure):
    """
    css选择器，参考http://www.w3school.com.cn/cssref/css_selectors.asp
    css path [multi] [selector]
    path 要解析的css选择参数
    selector false或无值返回extrator()后的结果, True返回SelectorList

    do输入
    input string|Response|Seelctor
    """
    def __init__(self, *args):
        """
        :return: string|array|SelectorList
        """
        if len(args) < 1 or len(args) > 3:
            raise Exception(__name__ + 'initialize arguments error')

        self._path = args[0]
        self._return_multi = False
        if len(args) > 1 and args[1]:
            self._return_multi = args[1]

        self._return_selector = False
        if len(args) > 2 and args[2]:
            self._return_selector = args[2]

    def do(self, input_, **kwargs):
        if isinstance(input_, Response) or isinstance(input_, SelectorList):
            res = input_.css(self._path)
        elif isinstance(input_, basestring):
            res = Selector(text=input_).css(self._path)
        else:
            raise Exception(__name__ + ' unknow type of argument' + str(type(input_)))

        if not self._return_selector:
            res = res.extract()
            if not self._return_multi:
                res = res[0] if res else None
        return res


class ReProcedure(ListableProcedure):
    """
    正则表达式提取
    re pattern
    """
    def __init__(self, *args):
        if len(args) != 1:
            raise Exception('re procedure paraments error')
        self._reg = args[0]
        pass

    def one(self, string, **kwargs):
        if not string:
            return None
        match = re.search(self._reg, string)
        if match:
            return match.group(0)
        else:
            return None


class JoinProcedure(BaseProcedure):
    """
    同string.join
    join seperator
    seperator间隔符
    """
    def __init__(self, *args):
        if len(args) != 1:
            raise Exception('join procedure paraments error')
        self._sep = args[0]

    def do(self, input_, **kwargs):
        if type(input_) != list:
            raise Exception("%s's argument must be list" % 'JoinProcedure')
        elif not input_:
            return None
        else:
            return self._sep.join(input_)


class ConstProcedure(BaseProcedure):
    """
    const value
    value 固定返回的值
    """
    def __init__(self, *args):
        if len(args) != 1:
            raise Exception('const procedure paraments error')
        self._value = args[0]

    def run(self, *args, **kwargs):
        return self._value


class TimeProcedure(ListableProcedure):
    """
    时间格式化, 如果不指定output_pattern，则输出时间戳, 可处理数组
    time format_pattern [output_pattern]
    format_pattern 输入的格式，转成时间类型数据
    transfer_pattern 输出格式, 如'%Y-%m-%d %H:%M:%S'
    """
    def __init__(self, *args):
        self._format_pattern = args[0]
        self._output_pattern = None
        if len(args) > 1:
            self._output_pattern = args[1]

    def one(self, s):
        ret = time.strptime(s, self._format_pattern)
        if self._output_pattern:
            ret = time.strftime(self._output_pattern, ret)
        else:
            ret = time.mktime(ret)

        return ret


class LinkProcedure(BaseProcedure):
    """
    基于scrapy的LxmlLinkExtractor的链接提取器
    link xpath css
    xpath string|array  参考LxmlLinkExtractor的restrict_xpaths
    css string|array  参考LxmlLinkExtractor的restrict_css
    """
    def __init__(self, *args):
        xpath = args[0]
        css = len(args) >= 2 and args[1] or None
        self._extractor = LxmlLinkExtractor(restrict_xpaths=xpath, restrict_css=css)

    def do(self, input_, **kwargs):
        if isinstance(input_, Response):
            links = self._extractor.extract_links(input_)
            return [i.url.strip() for i in links]
        else:
            raise Exception('link input error')


class MetaProcedure(BaseProcedure):
    """
    从response的meta中取值
    meta key
    key string 存入meta中对应的值
    """
    def __init__(self, *args):
        self._key = args[0]

    def do(self, input_, **kwargs):
        if not isinstance(input_, Response):
            raise Exception('meta procedure need response')
        try:
            value = input_.meta[META_VARS][self._key]
        except:
            value = None
        return value


class EvalProcedure(BaseProcedure):
    """
    参考python eval用法
    eval exp
    exp string 用法 exp % input, exp中可以包含%s %d等格式化参数，用input格式化
    @return 返回eval的执行结果
    """
    def __init__(self, *args):
        self._exp = args[0]

    def do(self, input_, **kwargs):
        return eval(self._exp % input_)


class UrlJoinProcedure(BaseProcedure):
    def __init__(self, *args):
        pass

    def do(self, input_, **kwargs):
        if 'response' not in kwargs:
            raise Exception('url_join needs response')
        response = kwargs['response']
        if not isinstance(response, Response):
            raise Exception('url_join argument response must be scrapy.http.Response')
        if isinstance(input_, list):
            return [self.one(response, url) for url in input_]
        else:
            return self.one(response, input_)

    def one(self, response, url):
        return qualify_link(response, url)


class ReplaceProcedure(ListableProcedure):
    """
    参考str.replace
    replace old new
    """
    def __init__(self, *args):
        self._old = args[0]
        self._new = args[1]

    def one(self, input_, **kwargs):
        return input_.replace(self._old, self._new)


class ResubProcedure(ListableProcedure):
    """
    参考re.sub
    resub regx repl
    """
    def __init__(self, *args):
        self._pattern = args[0]
        self._repl = args[1]

    def one(self, input_, **kwargs):
        return re.sub(self._pattern, self._repl, input_)


class SubstrProcedure(ListableProcedure):
    """
    参考python的切片
    sustr start [end]
    """
    def __init__(self, *args):
        self._start = args[0]
        self._end = None
        if len(args) > 1:
            self._end = args[1]

    def one(self, input_, **kwargs):
        if self._end != None:
            return input_[self._start:self._end]
        else:
            return input_[self._start:]


class SliceProcedure(BaseProcedure):
    """
    参考python的切片
    slice start [end]
    """
    def __init__(self, *args):
        self._start = args[0]
        self._end = None
        if len(args) > 1:
            self._end = args[1]

    def do(self, input_, **kwargs):
        if self._end != None:
            return input_[self._start:self._end]
        else:
            return input_[self._start:]

class DefaultProcedure(BaseProcedure):
    """
    如果输入为None，则输入默认值，如果不为空，则输出输入值
    default value
    """
    def __init__(self, *args):
        self._value = args[0]

    def run(self, input_, **kwargs):
        if input_ is None:
            return self._value
        else:
            return input_


class JsonProcedure(BaseProcedure):
    """
    json解析，一个参数jsonpath,参考https://pypi.python.org/pypi/jsonpath-rw, https://github.com/sileht/python-jsonpath-rw-ext
    json jsonpath [multi]
    jsonpath
    multi 是否返回数组，默认为false
    """

    mul_comment = re.compile(r'/\*.*?\*/')
    single_comment = re.compile('//.*?(?=\n)')

    def __init__(self, *args):
        path = args[0]
        self.jsonpath = jsonpath_parser.parse(path)
        self._return_multi = False
        if len(args) > 1 and args[1]:
            self._return_multi = args[1]

    def do(self, input_, **kwargs):
        if isinstance(input_, Response):
            input_ = input_.body_as_unicode()
        if isinstance(input_, basestring):
            input_ = self.remove_comment(input_)
        try:
            input_ = json.loads(input_)
        except:
            # not legal json
            input_ = myjson.loads(input_)
        res = [match.value for match in self.jsonpath.find(input_)]
        if res:
            if not self._return_multi:
                res = res[0]
        else:
            res = None
        return res

    @classmethod
    def remove_comment(cls, s):
        s = re.sub(cls.mul_comment, '', s)
        s = re.sub(cls.single_comment, '', s)
        return s


class ListElementProcedure(BaseProcedure):
    """
    返回数组的某个元素
    list_element index
    index 下标
    """
    def __init__(self, *args):
        self.index = int(args[0])

    def do(self, input_, **kwargs):
        if not isinstance(input_, list):
            raise Exception("list_element needs 'list' type input, but %s given" % (str(type(input_))))
        if self.index < 0 or self.index >= len(input_):
            raise Exception("index %d out range" % self.index)
        return input_[self.index]


class URLProcedure():
    """
    特珠Procedure，获取当前response的url
    URL
    """
    def run(self, res, **kwargs):
        return res.url

procedure_map = {
    'const': ConstProcedure,
    'css': CssProcedure,
    'default': DefaultProcedure,
    'eval': EvalProcedure,
    'join': JoinProcedure,
    'json': JsonProcedure,
    'link': LinkProcedure,
    'list_element': ListElementProcedure,
    'meta': MetaProcedure,
    're': ReProcedure,
    'replace': ReplaceProcedure,
    'resub': ResubProcedure,
    'slice': SliceProcedure,
    'substr': SubstrProcedure,
    'time': TimeProcedure,
    'url_join': UrlJoinProcedure,
    'xpath': XpathProcedure,
    'URL': URLProcedure
}

if __name__ == '__main__':
    s = '/*abd*/fda\nfd// fda\n abc'
    print JsonProcedure.remove_comment(s)
    pass
