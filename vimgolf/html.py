from enum import Enum
import html.parser
from typing import Iterable

class NodeType(Enum):
    ELEMENT = 1
    TEXT = 2


class Node:
    def __init__(self, node_type):
        self.parent = None
        self.node_type = node_type


_VOID_ELEMENT_TAGS = [
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wb'
]


class Element(Node):
    def __init__(self, tag, attrs):
        Node.__init__(self, NodeType.ELEMENT)
        self.tag = tag
        self.attrs = attrs
        self.children = []

    def get_attr(self, value):
        for attr in self.attrs:
            if attr[0] == value:
                return attr[1]
        return None

    def get_id(self):
        return self.get_attr('id')

    def get_class_list(self):
        class_list = None
        class_ = self.get_attr('class')
        if class_:
            class_list = class_.split()
        return class_list

    def has_class(self, value):
        class_list = self.get_class_list()
        return class_list and value in class_list


class TextNode(Node):
    def __init__(self, data):
        Node.__init__(self, NodeType.TEXT)
        self.data = data


class HTMLParser(html.parser.HTMLParser):
    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.nodes = []
        self._stack = []
        self.in_startend = False

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        if self._stack:
            self._stack[-1].children.append(element)
            element.parent = self._stack[-1]
        self.nodes.append(element)
        self._stack.append(element)
        if not self.in_startend and tag in _VOID_ELEMENT_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        self._stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.in_startend = True
        html.parser.HTMLParser.handle_startendtag(self, tag, attrs)
        self.in_startend = False

    def handle_data(self, data):
        text_node = TextNode(data)
        if self._stack:
            self._stack[-1].children.append(text_node)
            text_node.parent = self._stack[-1]
        self.nodes.append(text_node)


def parse_html(html: str):
    parser = HTMLParser()
    parser.feed(html)
    return parser.nodes


def get_element_by_id(nodes: Iterable[Node], id_: str):
    for node in nodes:
        if node.node_type == NodeType.ELEMENT and node.get_id() == id_:
            return node
    return None


def get_elements_by_classname(nodes: Iterable[Node], classname: str):
    output = []
    for node in nodes:
        if node.node_type == NodeType.ELEMENT and node.has_class(classname):
            output.append(node)
    return output


def get_elements_by_tagname(nodes: Iterable[Node], tagname: str):
    output = []
    for node in nodes:
        if node.node_type == NodeType.ELEMENT and node.tag == tagname:
            output.append(node)
    return output


def get_text(nodes: Iterable[Node]):
    stack = list(reversed(list(nodes)))
    texts = []
    while stack:
        node = stack.pop()
        if node.node_type == NodeType.ELEMENT:
            stack.extend(reversed(node.children))
        elif node.node_type == NodeType.TEXT:
            texts.append(node.data)
        else:
            raise RuntimeError('Unknown node type: {}'.format(node.node_type))
    return ''.join(texts)
