from __future__ import unicode_literals
import sys, re, html

class Reader(object):
    def __init__(self, stream):
        self.index = 0
        self.lines = [unicode(line, 'utf-8').rstrip() for line in stream.readlines()]

    def __iter__(self):
        return self

    def peek(self):
        if self.index != len(self.lines):
            return self.lines[self.index]
        raise StopIteration()

    def next(self):
        if self.index == len(self.lines):
            raise StopIteration()
        line = self.lines[self.index]
        self.index += 1
        return line


class ParagraphBlock(object):
    def __init__(self, text):
        self.text = text


class HeaderBlock(object):
    def __init__(self, level, text):
        self.level = level
        self.text = text


class Anchor(object):
    def __init__(self, id):
        self.id = id


class SourceBlock(object):
    def __init__(self, lang, text):
        self.lang = lang
        self.text = text


class OrderedList(object):
    def __init__(self, items):
        self.items = items


class UnorderedList(object):
    def __init__(self, items):
        self.items = items


class References(object):
    def __init__(self, refs):
        self.refs = refs


class Markdown(object):
    def __init__(self, blocks, refs):
        self.blocks = blocks
        self.refs = refs


class MarkdownParser(object):
    def __init__(self, reader):
        self.reader = reader

    def parse_paragraph(self):
        block = []
        for line in self.reader:
            if not line:
                break
            block.append(line.lstrip())
        return ParagraphBlock(' '.join(block))

    def parse_header(self):
        level, line = 0, self.reader.next()
        while line[level] == '#':
            level += 1
        return HeaderBlock(level, line[level:].lstrip())

    def parse_anchor(self):
        line = self.reader.next()
        return Anchor(line[line.find('"')+1:line.rfind('"')])

    def parse_source(self):
        lang, block = self.reader.next()[3:], []
        for line in self.reader:
            if line == '```':
                break
            if line == '#' or line.startswith('# '):
                continue
            block.append(line)
        return SourceBlock(lang, '\n'.join(block))

    def parse_ordered_list(self):
        text, items = [], []
        for line in self.reader:
            if not line:
                break
            pos = line.find('.')
            if pos < 0 or not line[:pos].isdigit():
                text.append(line.lstrip())
            else:
                if text:
                    items.append(' '.join(text))
                text = [line[pos+1:].lstrip()]
        if text:
            items.append(' '.join(text))
        return OrderedList(items)

    def parse_unordered_list(self):
        text, items = [], []
        for line in self.reader:
            if not line:
                break
            pos = line.find('*')
            if pos < 0 or (pos > 0 and not line[:pos].isspace()):
                text.append(line.lstrip())
            else:
                if text:
                    items.append(' '.join(text))
                text = [line[pos+1:].lstrip()]
        if text:
            items.append(' '.join(text))
        return UnorderedList(items)

    def parse_references(self):
        refs = {}
        for line in self.reader:
            pos1, pos2 = line.find('['), line.find(']:')
            if pos1 != 0 or pos2 < 0:
                break
            try:
                key = int(line[pos1+1:pos2])
            except:
                break
            refs[key] = line[pos2+2:].lstrip()
        return References(refs)

    def parse_next(self, line):
        if line.startswith('```'):
            return self.parse_source()
        if line.startswith('#'):
            return self.parse_header()
        if line.startswith('1. '):
            return self.parse_ordered_list()
        if line.startswith('* '):
            return self.parse_unordered_list()
        if line.startswith('[1]: '):
            return self.parse_references()
        if line.startswith('<a name='):
            return self.parse_anchor()
        return self.parse_paragraph()

    def parse(self):
        blocks, refs = [], {}
        while True:
            try:
                line = self.reader.peek()
            except StopIteration:
                break
            if not line or line.startswith('% '):
                self.reader.next()
                continue
            block = self.parse_next(line)
            if isinstance(block, References):
                refs.update(block.refs)
            else:
                blocks.append(block)
        return Markdown(blocks, refs)


class HabrahabrFormatter(object):
    def __init__(self, markdown):
        self.markdown = markdown

    def format_code(self, text):
        return "<code>%s</code>" % text

    def format_italic(self, text):
        return "<i>%s</i>" % text

    def format_bold(self, text):
        return "<b>%s</b>" % text

    def format_link(self, text, ref):
        if ref.isdigit():
            ref = self.markdown.refs[int(ref)]
        if not ref.startswith('http://') and \
           not ref.startswith('https://') and \
           not ref.startswith('#'):
            ref = "http://kgv.github.io/rust_book_ru/src/" + ref
        return "<a href='{ref}'>{text}</a>".format(ref=ref, text=text)

    def format_text(self, text):
        FORMAT_TABLE = [
            ("`([^`]+)`", self.format_code),
            ("\*\*([^\*]+)\*\*", self.format_bold),
            ("\*([^\*]+)\*", self.format_italic),
            ("\[([^\[\]]+)\]\(([^\(\)]+)\)", self.format_link),
            ("\[([^\[\]]+)\]\[(\d+)\]", self.format_link)
        ]
        for regexp, callback in FORMAT_TABLE:
            text = re.sub(regexp, lambda m: callback(*m.groups()), text)
        return text

    def format_header(self, header):
        return '<h{level}>{text}</h{level}>\n'.format(
            level=header.level+1,
            text=self.format_text(header.text)
        )

    def format_paragraph(self, paragraph):
        return '<p>{text}</p>\n\n'.format(
            text=self.format_text(paragraph.text)
        )

    def format_anchor(self, anchor):
        return '<anchor>%s</anchor>' % anchor.id

    def format_source(self, source):
        if source.lang.startswith("rust"):
            return '<source lang="rust">\n%s\n</source>\n' % html.escape(source.text)
        return '<source>\n%s\n</source>\n' % html.escape(source.text)

    def format_ordered_list(self, lst):
        return '<ol>\n%s\n</ol>\n' % '\n'.join(
            '<li>%s</li>' % self.format_text(item) for item in lst.items
        )

    def format_unordered_list(self, lst):
        return '<ul>\n%s\n</ul>\n' % '\n'.join(
            '<li>%s</li>' % self.format_text(item) for item in lst.items
        )

    def format(self):
        FORMAT_TABLE = {
            HeaderBlock: self.format_header,
            ParagraphBlock: self.format_paragraph,
            Anchor: self.format_anchor,
            SourceBlock: self.format_source,
            OrderedList: self.format_ordered_list,
            UnorderedList: self.format_unordered_list
        }
        parts = []
        for block in self.markdown.blocks:
            parts.append(FORMAT_TABLE[type(block)](block))
        return ''.join(parts)

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding("utf-8")
    print HabrahabrFormatter(MarkdownParser(Reader(open(sys.argv[1]))).parse()).format()
