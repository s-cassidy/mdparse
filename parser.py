import io


class StringPeek(io.StringIO):
    def peek(self, count: int = 1):
        '''
        Returns string of <count> characters from the cursor
        without moving the cursor. Count can be negative.
        '''
        head = self.tell()
        if count < 0:
            self.seek(head + count, 0)
        peek = self.read(abs(count))
        self.seek(head, 0)
        return peek

    def peek_char(self, offset: int = 1) -> str:
        '''
        Return character <offset> characters from the cursor
        without moving the cursor. Count can be negative.
        '''
        head = self.tell()
        self.seek(head + offset, 0)
        peek = self.read(1)
        self.seek(head, 0)
        return peek


class Tokeniser:
    def __init__(self, stream: StringPeek):
        self.tokens: list[str] = []
        self.stream = stream
        self.current_stream = io.StringIO()
        self.markdown = {"*": self.star_handler,
                         "\\": self.escape_handler,
                         "#": self.hash_handler,
                         "\n": self.newline_handler,
                         "_": self.underscore_handler,
                         }

    def tokenise(self):
        while self.next():
            continue

    def next(self) -> int:
        c = self.stream.read(1)
        if not c:
            self.tokens.append(self.current_stream.getvalue())
            return 0
        self.process(c)
        return 1

    def _end_current_token(self) -> None:
        if token := self.current_stream.getvalue():
            self.tokens.append(token)
        self.current_stream.close()
        self.current_stream = io.StringIO()

    def process(self, char) -> None:
        if char in self.markdown:
            self.markdown[char]()
        else:
            self.current_stream.write(char)

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
            self.tokens.append("!ITEM")
            return
        if self.stream.peek() == "*":
            self.stream.read(1)
            self.tokens.append("!*BOLD")
        else:
            self.tokens.append("!*ITALIC")

    def underscore_handler(self) -> None:
        self._end_current_token()
        if self.stream.peek() == "_":
            self.stream.read(1)
            self.tokens.append("!_BOLD")
        else:
            self.tokens.append("!_ITALIC")

    def escape_handler(self) -> None:
        self.current_stream.write(self.stream.read(1))

    def newline_handler(self) -> None:
        self._end_current_token()
        if self.stream.peek() == "\n":
            self.stream.read(1)
            self.tokens.append("!PARA_BREAK")
        else:
            self.tokens.append("!NEWLINE")

    def hash_handler(self) -> None:
        if self.is_first_line_character():
            if heading := self.check_heading():
                self._end_current_token()
                self.handle_heading(heading)
        if tag := self.check_tag():
            pass

    def check_tag(self) -> str | bool:
        pass

    def check_heading(self) -> str | bool:
        head = self.stream.tell()
        end = self.stream.seek(0, 2)
        self.stream.seek(head)
        heading = io.StringIO("#")
        heading.seek(1)
        for i in range(0, end - head):
            if i > 6:
                return False
            char = self.stream.peek_char(i)
            if char == "#":
                heading.write(char)
                continue
            if char == " ":
                heading_string = heading.getvalue()
                heading.close()
                return heading_string
            else:
                return False
        return False

    def handle_heading(self, heading: str) -> None:
        heading_level = len(heading)
        self.tokens.append(f"!H{heading_level}")
        self.stream.read(heading_level)


markdown = """# Heading 1
This is \\*escaped\\*, this is **bold** this is *italic*
## Heading 2
This is __bold__ as well

### Heading 3
This is ## not a heading
"""
tokeniser = Tokeniser(StringPeek(markdown))
tokeniser.tokenise()
tokens = tokeniser.tokens
for t in tokens:
    print(t)
