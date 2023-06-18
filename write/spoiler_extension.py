import xml.etree.ElementTree as etree

import markdown
from markdown.inlinepatterns import InlineProcessor


class SpoilerExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        # Create the inline pattern
        SPOILER_RE = r"\[(.*?)\]\(#spoiler\)"
        spoilerPattern = SpoilerInlineProcessor(SPOILER_RE, md)
        md.inlinePatterns.register(spoilerPattern, "spoiler", 175)


class SpoilerInlineProcessor(InlineProcessor):
    def handleMatch(self, m, data):
        el = etree.Element("span")
        el.text = m.group(1)
        el.set("class", "spoiler-text")
        return el, m.start(0), m.end(0)
