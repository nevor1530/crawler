# coding: utf-8
__author__ = 'nevor'
__email__ = 'nevor1530@163.com'

import ply.lex as lex
import ply.yacc as yacc
import decimal

input_str = None

tokens = ['ID', 'STRING', 'COMMENT', 'NUMBER', 'TRUE', 'FALSE', 'NULL']

literals = ['{', '}', '[', ']', ':', ',']

def t_STRING(t):
    r'''"(\\.|[^"])*?" | '(\\.|[^'])*?' '''
    t.value = eval(t.value)
    return t

def t_COMMENT(t):
    r'//[^\n]*\n | /\*.*?\*/'
    pass

def t_NUMBER(t):
    r"""-?(\d+(\.\d*)?|\.\d+)([eE][-+]? \d+)?"""
    t.value = decimal.Decimal(t.value)
    return t

def t_TRUE(t):
    r'\btrue\b'
    t.value = True
    return t

def t_FALSE(t):
    r'\bfalse\b'
    t.value = False
    return t

def t_NULL(t):
    r'\bnull\b'
    t.value = None
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    column = find_column(input_str, t)
    raise SyntaxError("Unknown symbol %r at %d,%d" % (t.value[0], t.lexer.lineno, column))

t_ignore  = ' \t\n'

# Compute column. 
#     input is the input text string
#     token is a token instance
def find_column(input_,token):
    last_cr = input_.rfind('\n',0,token.lexpos)
    if last_cr < 0:
        last_cr = 0
    column = (token.lexpos - last_cr) + 1
    return column

lexer = lex.lex()

def p_object(p):
    """object : '{' '}'
                | '{' members '}'"""
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = dict()

def p_members(p):
    """members : pair
                | pair ',' members"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[3].update(p[1])
        p[0] = p[3]

def p_pair(p):
    """ pair : STRING ':' value
                | ID ':' value """
    p[0] = {p[1]: p[3]}

def p_array(p):
    """ array : '[' ']'
            |   '[' elements ']' """
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = list()

def p_elements(p):
    """ elements : value
                | value ',' elements """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[3].append(p[1])
        p[0] = p[3]

def p_value(p):
    """ value : STRING
                | NUMBER
                | object
                | array
                | TRUE
                | FALSE
                | NULL """
    p[0] = p[1]

parser = yacc.yacc()


def loads(s):
    """ expose interface """
    global input_str, parser
    input_str = s
    return parser.parse(s, lexer=lexer)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as fin:
            input_str = fin.read()
    else:
        input_str = raw_input()
    print loads(input_str)
