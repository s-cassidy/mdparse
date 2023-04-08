import io
from enum import Enum, auto
from typing import Optional


class StringPeek(io.StringIO):
    def peek(self, count: int = 1):
        """
        Returns string of <count> characters from the cursor
        without moving the cursor. Count can be negative.
        """
        cursor = self.tell()
        if count < 0:
            self.seek(cursor + count, 0)
        peek = self.read(abs(count))
        self.seek(cursor, 0)
        return peek

    def peek_char(self, offset: int = 1) -> str:
        """
        Return character <offset> characters from the cursor
        without moving the cursor. Count can be negative.
        """
        cursor = self.tell()
        self.seek(cursor + offset, 0)
        peek = self.read(1)
        self.seek(cursor, 0)
        return peek

    def relative_seek(self, offset: int = 1) -> None:
        self.seek(self.tell() + offset)


class Tokeniser:
    def __init__(self, stream: StringPeek):
        self.tokens: list[str] = []
        self.stream = stream
        self.current_token = io.StringIO()
        self.markdown = {
            "*": self.star_handler,
            "\\": self.escape_handler,
            "#": self.hash_handler,
            "\n": self.newline_handler,
            "_": self.underscore_handler,
            "\t": self.tab_handler,
            "-": self.hyphen_handler,
            "[": self.open_sqbracket_handler,
            "]": self.close_sqbracket_handler,
            "(": self.open_rdbracket_handler,
            ")": self.close_rdbracket_handler,
            "|": self.pipe_handler,
            ">": self.block_quote_handler,
            ":": self.colon_handler,
            "`": self.backtick_handler,
        }

    def tokenise(self) -> list[str]:
        while self.next():
            continue
        return self.tokens

    def next(self) -> int:
        c = self.stream.read(1)
        if not c:
            self._end_current_token()
            self.tokens.append("!EOF")
            return 0
        self.process(c)
        return 1

    def _end_current_token(self) -> None:
        if token := self.current_token.getvalue():
            self.tokens.append(token)
        self.current_token.close()
        self.current_token = io.StringIO()

    def process(self, char) -> None:
        if char in self.markdown:
            self.markdown[char]()
        else:
            self.current_token.write(char)

    def tab_handler(self) -> None:
        self._end_current_token()
        self.tokens.append("\t")

    def hyphen_handler(self) -> None:
        if not self.is_first_line_character():
            self.current_token.write("-")
        if self.stream.peek(2) == "--":
            self.insert_bar_token()
            return
        if self.stream.peek(1) == " ":
            self._end_current_token()
            self.tokens.append("- ")
            self.stream.read(1)

    def insert_bar_token(self) -> None:
        self._end_current_token()
        self.tokens.append("---")
        self.stream.read(2)

    def is_first_line_character(self) -> bool:
        if self.stream.tell() == 1:
            return True
        for i in range(2, self.stream.tell()):
            char = self.stream.peek_char(-i)
            if char in " \t":
                continue
            if char == "\n":
                return True
            return False
        return True  # This covers the case of being on the first line

    def is_start_of_line(self) -> bool:
        if self.stream.tell() == 1:
            return True
        if self.stream.peek_char(-1) == "\n":
            return True
        return False

    def star_handler(self) -> None:
        self._end_current_token()
        if self.is_first_line_character() and self.stream.peek(1) == " ":  # list item
            self._end_current_token()
            self.tokens.append("* ")
            self.stream.read(1)
            return
        if self.stream.peek() == "*":
            self.stream.read(1)
            self.tokens.append("**")
        else:
            self.tokens.append("*")

    def underscore_handler(self) -> None:
        self._end_current_token()
        if self.stream.peek() == "_":
            self.stream.read(1)
            self.tokens.append("__")
        else:
            self.tokens.append("_")

    def escape_handler(self) -> None:
        self.current_token.write(self.stream.read(1))

    def newline_handler(self) -> None:
        self._end_current_token()
        self.tokens.append("\n")

    def hash_handler(self) -> None:
        if self.is_first_line_character():
            if heading := self.check_heading():
                self._end_current_token()
                self.handle_heading(heading)
                return
        if tag := self.check_tag():
            self._end_current_token()
            self.tokens.append(tag)
            self.stream.relative_seek(len(tag) - 1)
        else:
            self.current_token.write("#")

    def check_tag(self) -> str:
        cursor = self.stream.tell()
        end = self.stream.seek(0, 2)
        self.stream.seek(cursor)
        tag = io.StringIO("#")
        tag.seek(1)
        for i in range(0, end - cursor):
            char = self.stream.peek_char(i)
            if char.isalnum() or char in "-/_":
                tag.write(char)
            else:
                break
        tag_string = tag.getvalue()
        # tag must contain at least one alphabetic character
        if [char for char in tag_string if char.isalpha()]:
            return tag_string
        else:
            return ""

    def check_heading(self) -> str:
        cursor = self.stream.tell()
        end = self.stream.seek(0, 2)
        self.stream.seek(cursor)
        heading = io.StringIO("#")
        heading.seek(1)
        for i in range(0, end - cursor):
            if i > 6:
                return ""
            char = self.stream.peek_char(i)
            if char == "#":
                heading.write(char)
                continue
            if char == " ":
                heading_string = heading.getvalue()
                heading.close()
                return heading_string
            else:
                return ""
        return ""

    def handle_heading(self, heading: str) -> None:
        heading_level = len(heading)
        self.tokens.append(heading)
        self.stream.read(heading_level)

    def open_sqbracket_handler(self) -> None:
        self._end_current_token()
        if self.stream.peek() == "[":
            self.stream.read(1)
            self.tokens.append("[[")
        else:
            self.tokens.append("[")

    def close_sqbracket_handler(self) -> None:
        self._end_current_token()
        if self.stream.peek() == "]":
            self.stream.read(1)
            self.tokens.append("]]")
        else:
            self.tokens.append("]")

    def open_rdbracket_handler(self) -> None:
        self._end_current_token()
        self.tokens.append("(")

    def close_rdbracket_handler(self) -> None:
        self._end_current_token()
        self.tokens.append(")")

    def pipe_handler(self) -> None:
        self._end_current_token()
        self.tokens.append("|")

    def block_quote_handler(self) -> None:
        if self.is_first_line_character():
            self._end_current_token()
            self.tokens.append("> ")
            self.stream.read(1)
        else:
            self.current_token.write(">")

    def backtick_handler(self) -> None:
        if self.stream.peek(2) == 2:
            self._end_current_token()
            self.tokens.append("```")
            self.stream.read(2)
        else:
            self._end_current_token()
            self.tokens.append("`")

    def colon_handler(self) -> None:
        self._end_current_token()
        if self.stream.peek() == ":":
            self.stream.read(1)
            self.tokens.append("::")
        else:
            self.tokens.append(":")


class Element(Enum):
    ROOT = auto()
    STRONG = auto()
    EMP = auto()
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
    EXTERNAL_LINK = auto()
    BLOCK_QUOTE = auto()
    CODE = auto()
    CODEBLOCK = auto()


class NodeType(Enum):
    ELEMENT = auto()
    TEXT = auto()


class Node:
    def __init__(self, value: Element | str, parent: "Optional[Node]") -> None:
        self.children: list[Node] = []
        self.node_type: NodeType = (
            NodeType.ELEMENT if isinstance(value, Element) else NodeType.TEXT
        )
        self.value: Element | str = value
        self.closed = self.is_initially_closed()
        self.parent: Optional[Node] = parent

    closed_by_default: list[Element] = [
        Element.TAG,
        Element.LINE_BREAK,
    ]

    def is_initially_closed(self):
        if self.node_type == NodeType.TEXT:
            return True
        elif self.value in Node.closed_by_default:
            return True
        else:
            return False

    @property
    def delimiter_stack(self) -> list[str]:
        if self.parent is not None:
            return self.parent.delimiter_stack
        else:
            return []

    def add_child(self, value: Element | str):
        self.children.append(Node(value, parent=self))

    def close_children(self):
        for child in self.children:
            if not child.closed:
                self.close_children(child)
        self.closed = True

    top_level_elements = [
            "!H1",
            "!H2",
            "!H3",
            "!H4",
            "!H5",
            "!H6",
            "> ",
            ]

    def catch_token(self, token: str):
        if token == "!EOF":
            if self.children and not self.children[-1].closed:
                self.children[-1].catch_token(token)
            elif self.children[-1].value == Element.LINE_BREAK:
                self.children.pop()
            self.closed = True
            return
        if token in Node.top_level_elements and self.value == Element.ROOT:
            if self.children and self.children[-1].value == Element.LINE_BREAK:
                self.children.pop()
            self.close_children
            self.add_child(self.evaluate_token(token))
            return
        if self.children and not self.children[-1].closed:
            self.children[-1].catch_token(token)
        elif token == "!CLOSE":
            self.closed = True
        elif token == "!LINE_BREAK":
            if self.children and self.children[-1].value == Element.LINE_BREAK:
                self.children.pop()
                self.close_paragraph(token)
            else:
                value = self.evaluate_token(token)
                self.add_child(value)
        else:
            value = self.evaluate_token(token)
            if self.value == Element.ROOT:
                if isinstance(value, str) or \
                        value in [Element.EMP, Element.STRONG]:
                    if self.children and self.children[-1].value == Element.LINE_BREAK:
                        self.children.pop()
                    self.add_child(Element.PARAGRAPH)
                    self.children[-1].add_child(value)
                    return
            self.add_child(value)

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


openers = {
    "*": "!EMP",
    "**": "!STRONG",
    "_": "!EMP",
    "__": "!STRONG",
    "#": "!H1",
    "##": "!H2",
    "###": "!H3",
    "####": "!H4",
    "#####": "!H5",
    "######": "!H6",
    "* ": "!ITEM",
    "- ": "!ITEM",
    "> ": "!BLOCKQUOTE",
    "`": "!CODE",
    "```": "!CODEBLOCK",
}


def process_delimiters(tokens: list[str]) -> list[str]:
    delimiter_stack: list[tuple[int, str]] = []
    closed_by_newline = [
        "#",
        "##",
        "###",
        "####",
        "####",
        "#####",
        "######",
        "> ",
        "- ",
        "* ",
    ]
    # closers : openers
    delimiters = {
        "*": ["*"],
        "**": ["**"],
        "_": ["_"],
        "__": ["__"],
        "\n": closed_by_newline,
        "\n\n": closed_by_newline,
        "```": ["```"],
        "`": ["`"],
    }

    matched_tokens: dict[int, str] = {}
    for i, token in enumerate(tokens):

        # Process closing delimiter
        if token in delimiters.keys():
            if not delimiter_stack:
                pass
            elif delimiter_stack[-1][1] in delimiters[token]:
                opener_index, opener_token = delimiter_stack.pop()
                closer_index = i
                opening_tag = openers[opener_token]
                closing_tag = openers[opener_token]
                matched_tokens[opener_index] = opening_tag
                matched_tokens[closer_index] = "!CLOSE"
                continue

        # Process opening delimiter
        if token in openers:
            if accept_opener(delimiter_stack, token):
                delimiter_stack.append((i, token))
        if token in "\n\n":
            delimiter_stack = [d for d in delimiter_stack if d[1] in "```"]
            if not delimiter_stack:
                matched_tokens[i] = "!LINE_BREAK"
    processed_tokens = [
        matched_tokens[i] if i in matched_tokens else token
        for i, token in enumerate(tokens)
    ]
    return processed_tokens


def accept_opener(stack: list[tuple[int, str]], token: str) -> bool:
    """Return True if the delimiter stack is not
    currently awaiting a closer for a pre-formatted code block.
    Will reject "alternate" delimiters, e.g. if __ is open, reject **."""
    reject = {
        "__": "**",
        "_": "*",
        "*": "_",
        "**": "__",
    }
    stack_tokens = [token for index, token in stack]
    if reject.get(token, "not a token") in stack_tokens:
        return False
    if stack and stack_tokens[-1] not in "```":
        return True
    if not stack:
        return True
    return False


def parse(note: str) -> Node:
    S = StringPeek(note)
    tokeniser = Tokeniser(S)
    tokens = tokeniser.tokenise()
    processed_tokens = process_delimiters(tokens)
    tree = Node(Element.ROOT, parent=None)
    for token in processed_tokens:
        tree.catch_token(token)
    return tree


def print_node(Node, depth) -> None:
    node_string = f'{"---"*depth}{str(Node.value)}'
    print(node_string)
    for c in Node.children:
        print_node(c, depth + 1)

with open('../../vault/test-file.md', 'r', encoding='utf8') as f:
    S = f.read()

tree = parse(S)
print_node(tree, 0)
