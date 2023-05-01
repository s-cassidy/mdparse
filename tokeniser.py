import io
import string


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
            " ": self.space_handler,
            "-": self.hyphen_handler,
            "[": self.open_sqbracket_handler,
            "]": self.close_sqbracket_handler,
            "(": self.open_rdbracket_handler,
            ")": self.close_rdbracket_handler,
            "|": self.pipe_handler,
            ">": self.block_quote_handler,
            ":": self.colon_handler,
            "`": self.backtick_handler,
            "!": self.bang_handler,
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
        elif self.is_first_line_character() and char in string.digits:
            self.handle_numbered_list()
        else:
            self.current_token.write(char)

    def tab_handler(self) -> None:
        self._end_current_token()
        self.tokens.append("\t")

    def handle_numbered_list(self):
        peek = 0
        while self.stream.peek_char(peek) in string.digits:
            peek += 1
        if self.stream.peek(peek+2)[-2:] == ". ":
            self.tokens.append(self.stream.peek_char(-1) +
                               self.stream.peek(peek+2))
            self.stream.read(peek+2)
        else:
            self.current_token.write(self.stream.peek_char(0))

    def space_handler(self) -> None:
        if self.stream.peek(3) == "   ":
            self.stream.read(3)
            self.tab_handler()
        else:
            self.current_token.write(" ")

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
        if self.stream.peek_char(-2) == "\n":
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
        if self.stream.peek() == '[':
            self.tokens.append("[[")
            self.stream.read(1)
        else:
            self.tokens.append("[")

    def bang_handler(self) -> None:
        if self.stream.peek(2) == "[[":
            self._end_current_token()
            self.tokens.append("![[")
            self.stream.read(2)

    def close_sqbracket_handler(self) -> None:
        self._end_current_token()
        if self.stream.peek() == "]":
            self.stream.read(1)
            self.tokens.append("]]")
        elif self.stream.peek() == "(":
            self.stream.read(1)
            self.tokens.append("](")
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


openers = {
    "*": "!EM",
    "**": "!STRONG",
    "_": "!EM",
    "__": "!STRONG",
    "#": "!H1",
    "##": "!H2",
    "###": "!H3",
    "####": "!H4",
    "#####": "!H5",
    "######": "!H6",
    "* ": "!ITEM",
    "- ": "!ITEM",
    "> ": "!BLOCK_QUOTE",
    "[[": "!INTERNAL_LINK",
    "![[": "!EMBED_LINK",
    "[": "!EXTERNAL_LINK",
    "`": "!CODE",
    "```": "!CODEBLOCK",
}


def get_opener(token: str) -> str:
    if token in openers:
        return openers[token]
    if token[-2:] == ". ":
        return f"!OLI_{token[:-2]}"


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
delimiters = {
    "*": ["*"],
    "**": ["**"],
    "_": ["_"],
    "__": ["__"],
    "]]": ["![[", "[["],
    "\n": closed_by_newline,
    "\n\n": closed_by_newline,
    "```": ["```"],
    "`": ["`"],
    ")": ["["],
}


def should_close(token: str, stack: list[tuple[int, str]]) -> bool:
    if stack[-1][1] in delimiters[token]:
        return True
    if ". " == stack[-1][1][-2:] and token in "\n\n":
        return True
    return False


def process_tokens(tokens: list[str]) -> list[str]:
    delimiter_stack: list[tuple[int, str]] = []

    processed_tokens: dict[int, str] = {}
    external_link_correct = False
    for i, token in enumerate(tokens):

        if token == "](" and delimiter_stack[-1][1] == "[":
            processed_tokens[i] = "!LINK_BREAK"
            external_link_correct = True
            continue

        # Process closing delimiter
        if token in delimiters.keys():
            if not delimiter_stack:
                pass
            elif should_close(token, delimiter_stack):
                opener_index, opener_token = delimiter_stack.pop()
                if token == ")" and not external_link_correct:
                    # "unfinshed" hyperlink: remove from stack but don't process
                    continue
                if token == ")" and external_link_correct:
                    external_link_correct = False
                closer_index = i
                opening_tag = get_opener(opener_token)
                processed_tokens[opener_index] = opening_tag
                processed_tokens[closer_index] = "!CLOSE"
                continue

        # Process opening delimiter
        if token in openers or token[-2:] == ". ":
            if token[-2:] == ". ":
                try:
                    int(token[:-2])
                except ValueError:
                    continue
            if accept_opener(delimiter_stack, i, token, tokens):
                delimiter_stack.append((i, token))
        if token in "\n\n":
            delimiter_stack = [d for d in delimiter_stack if d[1] in "```"]
            if not delimiter_stack:  # i.e. we are not in a code block
                processed_tokens[i] = "!LINE_BREAK"

        if token == "|":
            if delimiter_stack[-1][1] in "![[":
                processed_tokens[i] = "!PIPE"
        if token == "\t" and (not delimiter_stack or delimiter_stack[-1][1] not in "```"):
            processed_tokens[i] = "!TAB"
        if token == "---" and (not delimiter_stack or delimiter_stack[-1][1] not in "```"):
            processed_tokens[i] = "!HBAR"

    new_tokens = [
        processed_tokens[i] if i in processed_tokens else token
        for i, token in enumerate(tokens)
    ]
    return new_tokens


def accept_opener(
    stack: list[tuple[int, str]],
    index: int,
    token: str,
    tokens: list[str]
) -> bool:
    """Return True if the delimiter stack is not
    currently awaiting a closer for a pre-formatted code block.
    Will reject "alternate" delimiters, e.g. if __ is open, reject **."""
    reject_inside = {
        "__": "**",
        "_": "*",
        "*": "_",
        "**": "__",
    }
    stack_tokens = [token for index, token in stack]
    if reject_inside.get(token, "not a token") in stack_tokens:
        return False
    if stack and stack_tokens[-1] not in "```":
        return True
    if not stack:
        return True
    return False


if __name__ == '__main__':
    with open('../../vault/test file.md', 'r', encoding='utf8') as f:
        note = f.read()
    S = StringPeek(note)
    tokeniser = Tokeniser(S)
    tokens = tokeniser.tokenise()
    processed_tokens = process_tokens(tokens)
    print(tokens)
    print(processed_tokens)
    print("\n\n")
