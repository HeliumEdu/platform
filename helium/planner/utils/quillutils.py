__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

"""
HTML to Quill Delta converter.

Converts legacy HTML content from `comments` (Homework/Event) and `details` (Material)
fields into Quill Delta JSON format for the `notes` field.
"""

import re
from html.parser import HTMLParser


def html_to_quill(html):
    """
    Convert HTML string to Quill Delta format.

    Returns a dict with 'ops' key containing the list of operations,
    or None if the input is empty/blank.
    """
    if not html or not html.strip():
        return None

    parser = _QuillHTMLParser()
    parser.feed(html)
    ops = parser.ops

    if not ops:
        return None

    # Quill requires documents to end with a newline
    if ops and ops[-1].get('insert') != '\n':
        ops.append({'insert': '\n'})

    return {'ops': ops}


class _QuillHTMLParser(HTMLParser):
    """HTML parser that builds Quill Delta operations."""

    def __init__(self):
        super().__init__()
        self.ops = []
        self._attr_stack = [{}]  # Stack of inline attributes
        self._block_stack = []  # Stack of (tag, block_attrs) for block elements
        self._list_type_stack = []  # Track ul/ol nesting

    def _current_attrs(self):
        """Get the current merged inline attributes."""
        return self._attr_stack[-1].copy()

    def _push_attrs(self, new_attrs):
        """Push new attributes merged with current ones."""
        merged = self._current_attrs()
        merged.update(new_attrs)
        self._attr_stack.append(merged)

    def _pop_attrs(self):
        """Pop the attribute stack."""
        if len(self._attr_stack) > 1:
            self._attr_stack.pop()

    def _ensure_newline_before_list(self):
        """Ensure there's a newline before a list starts (if there's preceding content)."""
        if self.ops and self.ops[-1].get('insert', '').rstrip('\n') != '':
            # There's content that doesn't end with a newline - add one
            self.ops.append({'insert': '\n'})

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        inline_attrs = {}
        block_attrs = None
        is_block = False

        # Inline formatting
        if tag in ('strong', 'b'):
            inline_attrs['bold'] = True
        elif tag in ('em', 'i'):
            inline_attrs['italic'] = True
        elif tag == 'u':
            inline_attrs['underline'] = True
        elif tag in ('s', 'strike', 'del'):
            inline_attrs['strike'] = True
        elif tag == 'a':
            href = attrs_dict.get('href')
            if href:
                inline_attrs['link'] = href
        elif tag == 'br':
            self.ops.append({'insert': '\n'})
            return
        elif tag == 'font':
            # Legacy <font> tag from execCommand
            color = attrs_dict.get('color')
            if color:
                inline_attrs['color'] = _normalize_color(color)
            face = attrs_dict.get('face')
            if face:
                inline_attrs['font'] = _normalize_font_name(face)
        elif tag == 'span':
            # <span style="..."> from modern browsers
            style = attrs_dict.get('style')
            if style:
                inline_attrs.update(_parse_inline_styles(style))
        # Block elements
        elif tag in ('p', 'div'):
            is_block = True
        elif tag == 'h1':
            is_block = True
            block_attrs = {'header': 1}
        elif tag == 'h2':
            is_block = True
            block_attrs = {'header': 2}
        elif tag == 'h3':
            is_block = True
            block_attrs = {'header': 3}
        elif tag == 'h4':
            is_block = True
            block_attrs = {'header': 4}
        elif tag == 'h5':
            is_block = True
            block_attrs = {'header': 5}
        elif tag == 'h6':
            is_block = True
            block_attrs = {'header': 6}
        elif tag == 'blockquote':
            is_block = True
            block_attrs = {'blockquote': True}
        elif tag == 'ul':
            self._ensure_newline_before_list()
            self._list_type_stack.append('bullet')
            return
        elif tag == 'ol':
            self._ensure_newline_before_list()
            self._list_type_stack.append('ordered')
            return
        elif tag == 'li':
            is_block = True
            list_type = self._list_type_stack[-1] if self._list_type_stack else 'bullet'
            block_attrs = {'list': list_type}

        if inline_attrs:
            self._push_attrs(inline_attrs)
        else:
            self._push_attrs({})

        if is_block:
            self._block_stack.append((tag, block_attrs))

    def handle_endtag(self, tag):
        # Handle list containers
        if tag in ('ul', 'ol'):
            if self._list_type_stack:
                self._list_type_stack.pop()
            return

        # Check if this was a block element
        if self._block_stack and self._block_stack[-1][0] == tag:
            _, block_attrs = self._block_stack.pop()
            block_op = {'insert': '\n'}
            if block_attrs:
                block_op['attributes'] = block_attrs
            self.ops.append(block_op)

        self._pop_attrs()

    def handle_data(self, data):
        if not data:
            return
        attrs = self._current_attrs()
        op = {'insert': data}
        if attrs:
            op['attributes'] = attrs
        self.ops.append(op)

    def handle_entityref(self, name):
        # Handle named entities like &nbsp;
        from html import unescape
        char = unescape(f'&{name};')
        self.handle_data(char)

    def handle_charref(self, name):
        # Handle numeric entities like &#160;
        from html import unescape
        if name.startswith('x'):
            char = unescape(f'&#{name};')
        else:
            char = unescape(f'&#{name};')
        self.handle_data(char)


def _parse_inline_styles(style):
    """Parse CSS inline styles and return Quill attributes."""
    attrs = {}
    if not style:
        return attrs

    for declaration in style.split(';'):
        if ':' not in declaration:
            continue
        prop, value = declaration.split(':', 1)
        prop = prop.strip().lower()
        value = value.strip()

        if prop == 'color':
            attrs['color'] = _normalize_color(value)
        elif prop == 'background-color':
            attrs['background'] = _normalize_color(value)
        elif prop == 'font-family':
            attrs['font'] = _normalize_font_name(value)

    return attrs


def _normalize_color(value):
    """Convert rgb(r, g, b) to #rrggbb; pass hex/named values through."""
    match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', value)
    if match:
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return f'#{r:02x}{g:02x}{b:02x}'
    return value


def _normalize_font_name(value):
    """Normalize font-family (strip quotes, take first family, lowercase)."""
    first_font = value.split(',')[0].strip()
    return first_font.replace('"', '').replace("'", '').lower()
