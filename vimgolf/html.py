from enum import Enum
from html.parser import HTMLParser

class NodeType(Enum):
    ELEMENT = 1
    TEXT = 2


class Node:
    def __init__(self, node_type):
        self.parent = None
        self.node_type = node_type


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


class HtmlParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.nodes = []
        self._stack = []

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        if self._stack:
            self._stack[-1].children.append(element)
            element.parent = self._stack[-1]
        self.nodes.append(element)
        self._stack.append(element)

    def handle_endtag(self, tag):
        self._stack.pop()

    def handle_data(self, data):
        text_node = TextNode(data)
        if self._stack:
            self._stack[-1].children.append(text_node)
            text_node.parent = self._stack[-1]
        self.nodes.append(text_node)


def parse_html(html):
    parser = HtmlParser()
    parser.feed(html)
    return parser.nodes


def get_element_by_id(nodes, id_):
    for node in nodes:
        if node.node_type == NodeType.ELEMENT and node.get_id() == id_:
            return node
    return None


def get_elements_by_classname(nodes, classname):
    output = []
    for node in nodes:
        if node.node_type == NodeType.ELEMENT and node.has_class(classname):
            output.append(node)
    return output


def get_elements_by_tagname(nodes, tagname):
    output = []
    for node in nodes:
        if node.node_type == NodeType.ELEMENT and node.tag == tagname:
            output.append(node)
    return output
