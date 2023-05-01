from enum import Enum, auto
from typing import Optional
import string


class Element(Enum):
    ROOT = auto()
    STRONG = auto()
    EM = auto()
    PARAGRAPH = auto()
    H1 = auto()
    H2 = auto()
    H3 = auto()
    H4 = auto()
    H5 = auto()
    H6 = auto()
    TAG = auto()
    LINE_BREAK = auto()
    INTERNAL_LINK = auto()
    EMBED_LINK = auto()
    EXTERNAL_LINK = auto()
    BLOCK_QUOTE = auto()
    ITEM = auto()
    UNORDERED_LIST = auto()
    ORDERED_LIST = auto()
    CODE = auto()
    CODEBLOCK = auto()
    HBAR = auto()
    FRONTMATTER = auto()
    IMAGE = auto()


class Node:
    def __init__(
        self,
        value: Element | str,
        parent: "Optional[Node]",
        root: "Optional[Node]"
    ) -> None:
        self.children: list[Node] = []
        self.value: Element | str = value
        self.closed = self.is_initially_closed()
        self.parent: Optional[Node] = parent
        self.root: Node = root if root else self
        self.link_to: str = ""
        self.list_indent = 0
        self.start_number = 1
        self.tab_count = 0
        self.start_new_list = False
        self.image_width: str = ""
        self.image_height: str = ""

    closed_by_default: list[Element] = [
        Element.TAG,
        Element.LINE_BREAK,
        Element.HBAR,
    ]

    def is_initially_closed(self):
        if isinstance(self.value, str):
            return True
        elif self.value in Node.closed_by_default:
            return True
        else:
            return False

    def __repr__(self) -> str:
        return str(self.value)

    def catch_token(self, token: str):

        if token == "!HBAR" and self.is_frontmatter():
            if not self.children:
                self.add_child(Element.FRONTMATTER)
                return
            if self.children[0].value == Element.FRONTMATTER:
                self.close_children()
                return

        if token == "!TAB" and self.value == Element.ROOT:
            self.tab_count += 1
            return

        if (token == "!ITEM" or token[:5] == "!OLI_") and self.value == Element.ROOT:
            correct_list = self.find_correct_list(token)
            correct_list.add_child(Element.ITEM)
            self.root.tab_count = 0
            return

        # block level elements
        if token in Node.top_level_elements and self.value == Element.ROOT:
            self.remove_trailing_line_breaks()
            self.close_children()
            self.add_child(self.evaluate_token(token))
            return

        if self.last_child_open():
            self.children[-1].catch_token(token)

        # special cases
        elif token == "!CLOSE":
            self.closed = True
            if self.value == Element.EXTERNAL_LINK:
                self.process_external_link()
            if self.internal_link_has_no_display_text():
                link = "".join(str(child) for child in self.children)
                print(link)
                self.link_to = link
            if self.value == Element.EMBED_LINK and self.link_to[-4:] in [".jpg", ".png"]:
                self.value = Element.IMAGE
                if self.children:
                    child_string = "".join([str(child.value)
                                           for child in self.children])
                    self.image_width, _, self.image_height = child_string.partition(
                        "x")
                    if not (self.is_digits(self.image_width) and self.is_digits(self.image_height)):
                        self.image_width, self.image_height = "", ""
                    self.children = []

        elif token == "!LINE_BREAK":
            if self.children and self.children[-1].value == Element.LINE_BREAK:
                self.children.pop()
                self.close_paragraph(token)
            else:
                new_value = self.evaluate_token(token)
                self.add_child(new_value)
        elif token == "!PIPE" and self.value in (Element.INTERNAL_LINK, Element.EMBED_LINK):
            if self.children:
                link = "".join(str(child) for child in self.children)
                self.link_to = link
                self.children = []

        elif token == "!EOF":
            self.remove_trailing_line_breaks()

        # text/em/strong nodes
        else:
            new_value = self.evaluate_token(token)
            if self.value == Element.ROOT:
                # Ensure main body text is always contained in something
                # -- fallback to paragraph
                # never just a child of root.
                if isinstance(new_value, str) or \
                        new_value in [Element.EM, Element.STRONG]:
                    self.remove_trailing_line_breaks()
                    self.add_child(Element.PARAGRAPH)
                    self.root.catch_token(token)
                    return
            self.add_child(new_value)

    def find_correct_list(self, token: str) -> "Node":
        list_nodes = [Element.UNORDERED_LIST, Element.ORDERED_LIST]
        list_type = Element.UNORDERED_LIST if token == "!ITEM" else Element.ORDERED_LIST
        list_number = 0
        try_count = 0
        if list_type == Element.ORDERED_LIST:
            list_number = int(token.partition("_")[2])
        if self.tab_count == 0:
            if self.children[-1].value == list_type:
                correct_list = self.children[-1]
            else:
                self.add_child(list_type)
                if list_number:
                    self.children[-1].start_number = list_number
                correct_list = self.children[-1]
        if self.tab_count > 0:
            current_node = self
            searching = True
            while searching and try_count < 5:
                if current_node.children and current_node.children[-1].value in list_nodes:
                    current_node = current_node.children[-1]
                else:
                    current_node.add_child(list_type)
                    if list_number:
                        current_node.children[-1].start_number = list_number
                    current_node.children[-1].list_indent = current_node.list_indent + 1
                if self.tab_count == current_node.list_indent:
                    correct_list = current_node
                    searching = False
                try_count += 1
                print_node(self, 0)
                print(f"Current node: {current_node}")
                print(f"Indent level: {self.list_indent}")
                print(f"tab count: {self.tab_count}")
        return correct_list

    def is_digits(self, s: str) -> bool:
        for c in s:
            if c not in string.digits:
                return False
        return True

    def add_child(self, value: Element | str):
        self.children.append(Node(value, parent=self, root=self.root))

    def close_children(self) -> None:
        for child in self.children:
            if not child.closed:
                child.close_children()
        self.closed = True

    def is_frontmatter(self) -> bool:
        if self.value == Element.ROOT:
            if not self.children:
                return True
            if len(self.children) == 1 and self.children[0].value == Element.FRONTMATTER:
                return True
        return False

    top_level_elements = [
        "!H1",
        "!H2",
        "!H3",
        "!H4",
        "!H5",
        "!H6",
        "!BLOCK_QUOTE",
        "!HBAR",
    ]

    def remove_trailing_line_breaks(self) -> None:
        while self.children and self.children[-1].value == Element.LINE_BREAK:
            self.children.pop()

    def internal_link_has_no_display_text(self) -> bool:
        if self.value in (Element.INTERNAL_LINK, Element.EMBED_LINK) \
                and self.children \
                and not self.link_to:
            return True
        return False

    def last_child_open(self) -> bool:
        if self.children and not self.children[-1].closed:
            return True
        else:
            return False

    def process_external_link(self) -> None:
        child_values = [str(child.value) for child in self.children]
        break_index = child_values.index("!LINK_BREAK")
        self.link_to = "".join(child for child in child_values[break_index+1:])
        self.children = self.children[:break_index]

    def close_paragraph(self, token) -> None:
        if self.value == Element.PARAGRAPH and not self.closed:
            self.closed = True
            if self.parent:
                self.parent.add_child(self.evaluate_token(token))
        else:
            if self.parent:
                self.parent.close_paragraph(token)

    def evaluate_token(self, token: str) -> str | Element:
        if token[0] == "!":
            try:
                return Element[token[1:]]
            except KeyError:
                return token
        else:
            return token

    def __eq__(self, other):
        return self.children == other.children and self.value == other.value

    def __str__(self):
        if self.link_to:
            return f"{str(self.value)} to {self.link_to}"
        else:
            return f"{str(self.value)}"


def print_node(Node, depth) -> None:
    node_string = f'{"---"*depth}{str(Node)}'
    print(node_string)
    for c in Node.children:
        print_node(c, depth + 1)


if __name__ == '__main__':
    import tokeniser

    with open('../../vault/test file.md', 'r', encoding='utf8') as f:
        note = f.read()
    S = tokeniser.StringPeek(note)
    tokens = tokeniser.process_tokens(tokeniser.Tokeniser(S).tokenise())
    tree = Node(Element.ROOT, parent=None, root=None)
    for token in tokens:
        tree.catch_token(token)
    print_node(tree, 0)
