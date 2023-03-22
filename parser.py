import io


class StringPeek(io.StringIO):
    def peek(self, count: int = 1):
        head = self.tell()
        peek = self.read(count)
        self.seek(head, 0)
        return peek

class Tokeniser:
    def __init__(self, stream: StringPeek):
        self.tokens: list[str] = []
        self.stream = stream
        self.current_stream = io.StringIO()
        self.markdown = {"*": self.star_handler,
                         "\\": self.escape_handler,
                         }

    def tokenise(self):
        while self.next():
            continue

    def next(self):
        c = self.stream.read(1)
        if not c:
            self.tokens.append(self.current_stream.getvalue())
            return 0
        self.process(c)
        print(self.current_stream.getvalue())
        print(self.tokens)
        return 1

    def process(self, char):
        if char in self.markdown:
            self.tokens.append(self.current_stream.getvalue())
            self.current_stream.close()
            self.current_stream = io.StringIO()
            self.markdown[char]()
        else:
            self.current_stream.write(char)

    def star_handler(self):
        if self.stream.peek() == "*":
            self.stream.read(1)
            self.tokens.append("!BOLD")
            return
        self.tokens.append("!ITALIC")

    def escape_handler(self):
        self.current_stream.close()
        self.current_stream = io.StringIO(self.tokens.pop())
        self.current_stream.seek(0, 2)
        self.current_stream.write(self.stream.read(1))


markdown = "This is \\*escaped\\*, this is **bold** this is *italic*"
tokeniser = Tokeniser(StringPeek(markdown))

