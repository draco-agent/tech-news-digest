"""Regression/security coverage shared by email and PDF inline renderers."""
import importlib.util
from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Fragment(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.links = []
        self.text = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == 'a':
            self.links.append(dict(attrs)['href'])

    def handle_data(self, data):
        self.text.append(data)


class InlineRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderers = [load_script('sanitize-html'), load_script('generate-pdf')]

    def check_renderers(self, source, urls, label=None):
        for module in self.renderers:
            with self.subTest(renderer=module.__name__, source=source):
                result = module._process_inline(source)
                parsed = Fragment(result)
                self.assertEqual(parsed.links, urls, result)
                if label is not None:
                    self.assertEqual(''.join(parsed.text), label, result)
                for tag, attrs in parsed.tags:
                    self.assertIn(tag, ('a', 'strong', 'code'))
                    self.assertFalse(any(key.startswith('on') for key in attrs))
                    self.assertTrue(set(attrs) <= {'href', 'style'})

    def test_suppressed_link_retains_label(self):
        self.check_renderers('[来源](<https://example.com/news>)',
                             ['https://example.com/news'], '来源')

    def test_normal_link_retains_label(self):
        self.check_renderers('[Source](https://example.com/news)',
                             ['https://example.com/news'], 'Source')

    def test_query_strings_and_escaped_labels(self):
        url = 'https://example.com/?a=1&b=2'
        for destination in (url, f'<{url}>'):
            self.check_renderers(f'[A & B <em> "quoted"]({destination})',
                                 [url], 'A & B <em> "quoted"')
        self.check_renderers(f'<{url}>', [url], 'example.com')

    def test_parentheses_in_destinations(self):
        url = 'https://example.com/article_(details)?a=1&b=2'
        for destination in (url, f'<{url}>'):
            self.check_renderers(f'[source]({destination})', [url], 'source')

    def test_plain_angle_link(self):
        self.check_renderers('<https://example.com/news>',
                             ['https://example.com/news'], 'example.com')

    def test_mixed_links_do_not_reparse_generated_html(self):
        self.check_renderers('[one](<https://one.example>) [two](https://two.example) '
                             '<https://three.example>',
                             ['https://one.example', 'https://two.example',
                              'https://three.example'], 'one two three.example')

    def test_unsafe_schemes_never_become_links(self):
        for url in ('javascript:alert(1)', 'JaVaScRiPt:evil', 'data:text/html,evil',
                    'vbscript:evil', 'file:///etc/passwd', '//example.com',
                    'javascript&#58;evil', 'java\tscript:evil'):
            for destination in (url, f'<{url}>'):
                self.check_renderers(f'[source]({destination})', [])

    def test_quotes_cannot_inject_attributes(self):
        url = 'https://example.com/?x="onmouseover="evil&y=\'quoted\''
        for destination in (url, f'<{url}>'):
            self.check_renderers(f'[<img src=x onerror=evil>]({destination})',
                                 [url], '<img src=x onerror=evil>')
        self.check_renderers(f'<{url}>', [url], 'example.com')

    def test_markup_in_url_stays_attribute_text(self):
        url = 'https://example.com/**bold**/`code`'
        self.check_renderers(f'[source]({url})', [url], 'source')

    def test_code_is_literal_and_raw_html_is_escaped(self):
        self.check_renderers('`[source](<https://example.com>)`', [],
                             '[source](<https://example.com>)')
        self.check_renderers('<script>alert(1)</script>', [], '<script>alert(1)</script>')
        self.check_renderers('**[source](<https://example.com>)**',
                             ['https://example.com'], 'source')

    def test_document_conversion_preserves_editorial_links(self):
        source = '# Report\n\n- **Story** — [来源](<https://example.com/?a=1&b=2>)\n'
        for module in self.renderers:
            with self.subTest(renderer=module.__name__):
                convert = getattr(module, 'markdown_to_safe_html', None) or module.markdown_to_html
                result = convert(source)
                self.assertEqual(Fragment(result).links, ['https://example.com/?a=1&b=2'])


if __name__ == '__main__':
    unittest.main()
