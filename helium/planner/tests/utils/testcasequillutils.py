__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.test import TestCase

from helium.planner.utils.quillutils import html_to_quill


class TestCaseQuillUtils(TestCase):
    def test_empty_input_returns_none(self):
        self.assertIsNone(html_to_quill(''))
        self.assertIsNone(html_to_quill('   \n\t  '))
        self.assertIsNone(html_to_quill(None))

    def test_plain_text(self):
        result = html_to_quill('Hello World')

        self.assertEqual(result['ops'][0]['insert'], 'Hello World')
        # Quill documents must end with newline
        self.assertEqual(result['ops'][-1]['insert'], '\n')

    def test_inline_formatting(self):
        result = html_to_quill('<strong>Bold</strong> <em>Italic</em> <u>Under</u> <s>Strike</s>')

        ops = result['ops']
        self.assertTrue(any(op.get('attributes', {}).get('bold') for op in ops))
        self.assertTrue(any(op.get('attributes', {}).get('italic') for op in ops))
        self.assertTrue(any(op.get('attributes', {}).get('underline') for op in ops))
        self.assertTrue(any(op.get('attributes', {}).get('strike') for op in ops))

    def test_link(self):
        result = html_to_quill('<a href="https://example.com">Link</a>')

        link_op = next(op for op in result['ops'] if op.get('attributes', {}).get('link'))
        self.assertEqual(link_op['insert'], 'Link')
        self.assertEqual(link_op['attributes']['link'], 'https://example.com')

    def test_lists(self):
        result = html_to_quill('<ul><li>Bullet</li></ul><ol><li>Ordered</li></ol>')

        ops = result['ops']
        self.assertTrue(any(op.get('attributes', {}).get('list') == 'bullet' for op in ops))
        self.assertTrue(any(op.get('attributes', {}).get('list') == 'ordered' for op in ops))

    def test_block_elements(self):
        result = html_to_quill('<h1>Heading</h1><blockquote>Quote</blockquote><p>Para</p>')

        ops = result['ops']
        self.assertTrue(any(op.get('attributes', {}).get('header') == 1 for op in ops))
        self.assertTrue(any(op.get('attributes', {}).get('blockquote') for op in ops))

    def test_rgb_color_conversion(self):
        result = html_to_quill('<span style="color: rgb(255, 0, 0);">Red</span>')

        color_op = next(op for op in result['ops'] if op.get('attributes', {}).get('color'))
        self.assertEqual(color_op['attributes']['color'], '#ff0000')

    def test_background_color(self):
        result = html_to_quill('<span style="background-color: rgb(255, 255, 0);">Hi</span>')

        bg_op = next(op for op in result['ops'] if op.get('attributes', {}).get('background'))
        self.assertEqual(bg_op['attributes']['background'], '#ffff00')

    def test_legacy_font_tag(self):
        result = html_to_quill('<font color="#0000ff" face="Arial">Text</font>')

        ops = result['ops']
        font_op = next(op for op in ops if op.get('attributes', {}).get('font'))
        self.assertEqual(font_op['attributes']['color'], '#0000ff')
        self.assertEqual(font_op['attributes']['font'], 'arial')

    def test_font_family_normalization(self):
        result = html_to_quill('<span style="font-family: \'Times New Roman\', serif;">Text</span>')

        font_op = next(op for op in result['ops'] if op.get('attributes', {}).get('font'))
        self.assertEqual(font_op['attributes']['font'], 'times new roman')

    def test_nested_formatting_inherits_attributes(self):
        result = html_to_quill('<strong><em>Both</em></strong>')

        nested_op = next(op for op in result['ops']
                         if op.get('attributes', {}).get('bold')
                         and op.get('attributes', {}).get('italic'))
        self.assertEqual(nested_op['insert'], 'Both')

    def test_html_entities_decoded(self):
        result = html_to_quill('&lt;tag&gt; &amp; &quot;quotes&quot;')

        all_text = ''.join(op.get('insert', '') for op in result['ops'])
        self.assertIn('<tag>', all_text)
        self.assertIn('&', all_text)
        self.assertIn('"quotes"', all_text)

    def test_br_creates_newline(self):
        result = html_to_quill('Line1<br>Line2')

        all_text = ''.join(op.get('insert', '') for op in result['ops'])
        self.assertIn('Line1', all_text)
        self.assertIn('\n', all_text)
        self.assertIn('Line2', all_text)
