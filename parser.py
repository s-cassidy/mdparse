import io
from flob.note import tree, tokeniser
from collections import namedtuple
from flask import url_for
from pathlib import Path
import os

Element = tree.Element
SOURCE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


def node_to_html(node: tree.Node, stream: io.StringIO, indent_level: int) -> io.StringIO:
    if node.value == Element.INTERNAL_LINK:
        stream.write(f"<a href={title_to_url(node.link_to)}>")
    elif node.value == Element.EXTERNAL_LINK:
        stream.write(f"<a href={node.link_to}>")
    elif node.value == Element.INTERNAL_LINK:
        stream.write("<div class='embed'>\n"
                     "content here"
                     f"<a href={title_to_url(node.link_to)}Link</a>"
                     "</div>")
    elif node.value == Element.IMAGE:
        stream.write(generate_image_tag(node))
    elif node.value == Element.ORDERED_LIST:
        stream.write(f'<ol start="{node.start_number}">')
    elif node.value in simple_elements:
        stream.write(f"<{simple_elements[node.value]}>")
    if isinstance(node.value, str):
        stream.write(node.value)
    if node.value in line_breakers:
        stream.write("\n")
        stream.write("\t"*indent_level)

    for child in node.children:
        node_to_html(child, stream, indent_level +
                     int(node.value in line_breakers))

    if node.value in paired_tags:
        if node.value in line_breakers:
            stream.write("\n")
        stream.write(f"</{paired_tags[node.value]}>")
    if node.value in line_breakers:
        stream.write("\n")
    return stream


def title_to_url(title: str) -> str:
    return title.replace(' ', '-')


def generate_image_tag(node: tree.Node) -> str:
    image = node.link_to
    if __name__ == '__main__':
        return (
            '<img src="static/vault/attachments/testimage.jpg" style='
            'max-width:100%;height:auto')
    return (
        f'<img src="{url_for("vault.attachments", filename=image)}" style='
        'max-width:100%;height:auto'
    )


def write_html(tree: tree.Node) -> str:
    stream = io.StringIO("")
    node_to_html(tree, stream, 1)
    return stream.getvalue()


paired_tags: dict[Element, str] = {
    Element.PARAGRAPH: "p",
    Element.STRONG: "strong",
    Element.EM: "em",
    Element.CODE: "code",
    Element.H1: "h1",
    Element.H2: "h2",
    Element.H3: "h3",
    Element.H4: "h4",
    Element.H5: "h5",
    Element.H6: "h6",
    Element.INTERNAL_LINK: "a",
    Element.EXTERNAL_LINK: "a",
    Element.BLOCK_QUOTE: "blockquote",
    Element.UNORDERED_LIST: "ul",
    Element.ORDERED_LIST: "ol",
    Element.ITEM: "li",
}

line_breakers = [
    Element.PARAGRAPH,
    Element.H1,
    Element.H2,
    Element.H3,
    Element.H4,
    Element.H5,
    Element.H6,
    Element.BLOCK_QUOTE,
    Element.LINE_BREAK,
    Element.ITEM,
    Element.UNORDERED_LIST,
    Element.HBAR,
]

simple_unpaired: dict[Element, str] = {
    Element.HBAR: "hr",
    Element.LINE_BREAK: "br",
}

simple_elements = paired_tags | simple_unpaired

Page = namedtuple("Page", "frontmatter content")


def parse(note: str) -> Page:
    S = tokeniser.StringPeek(note)
    tokens = tokeniser.Tokeniser(S).tokenise()
    with open(SOURCE_DIR / "output/tokens-raw.txt", "w", encoding="utf8") as f:
        for t in tokens:
            f.write(t + "\n")
    processed_tokens = tokeniser.DelimiterProcessor(tokens).process_tokens()
    with open(SOURCE_DIR / "output/tokens-processed.txt", "w", encoding="utf8") as f:
        for t in processed_tokens:
            f.write(t + "\n")
    note_tree = tree.Node(Element.ROOT, parent=None, root=None)
    for token in processed_tokens:
        note_tree.catch_token(token)

    with open(SOURCE_DIR / "output/tree.txt", "w", encoding="utf8") as f:
        tree.print_node(note_tree, 0, f)
    frontmatter = None
    if note_tree.children[0].value == Element.FRONTMATTER:
        frontmatter = note_tree.children.pop(0)
    content = write_html(note_tree)
    with open(SOURCE_DIR / "output/content.html", "w", encoding="utf8") as f:
        f.write(content)
    if __name__ == "__main__":
        print(processed_tokens)
        print("\n\n")
        tree.print_node(note_tree, 1)
        print("\n\n")
        print(content)
    output = Page(frontmatter, content)
    return output
