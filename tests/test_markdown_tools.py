"""TASK-005: shared CLI checks protect content and distinguish checks from GUI claims."""
from pathlib import Path
from urllib.parse import quote
from support import ROOT, ProjectTestCase, run


class MarkdownToolsTest(ProjectTestCase):
    def call(self, tool, doc, *args, expected=0):
        return run(ROOT / 'scripts' / tool, doc, *args, expected=expected)

    def test_math_fix_is_read_only_by_default_and_idempotent(self):
        doc = self.temp / 'math.md'
        original = 'Before \\(x^2\\).\r\n\\[\r\ny=1\r\n\\]\r\n$$z=2$$\r\n'
        doc.write_bytes(original.encode())
        self.call('md_math.py', doc, expected=1)
        self.assertEqual(doc.read_bytes(), original.encode())
        self.call('md_math.py', doc, '--fix')
        fixed = doc.read_bytes()
        self.assertIn(b'$x^2$', fixed)
        self.assertIn(b'$$\r\ny=1\r\n$$', fixed)
        self.assertIn(b'$$\r\nz=2\r\n$$', fixed)
        self.call('md_math.py', doc, '--fix')
        self.assertEqual(doc.read_bytes(), fixed)

    def test_math_skips_code_currency_and_plain_brackets(self):
        doc = self.temp / 'code.md'
        content = '```latex\n\\[x\\]\n```\n`\\(x\\)`\nPrice \\$12\n[ordinary text]\n'
        doc.write_text(content)
        self.call('md_math.py', doc, '--fix')
        self.assertEqual(doc.read_text(), content)

    def test_bad_math_prevents_partial_write(self):
        doc = self.temp / 'bad.md'
        for content in ['\\[x\\]\n$unpaired', '$$\nx\n', '\\(x\nnext\\)']:
            doc.write_text(content)
            self.call('md_math.py', doc, '--fix', expected=1)
            self.assertEqual(doc.read_text(), content)

    def test_relative_link_fix_preserves_code_titles_and_fragments(self):
        assets = self.temp / 'assets'; assets.mkdir()
        target = assets / 'alpha beta(a).py'; target.write_text('pass\n')
        folder = self.temp / 'docs'; folder.mkdir()
        doc = folder / 'readme.md'
        uri = 'file://wsl.localhost/ExampleDistro' + target.as_posix()
        content = (f'[source](<{uri}#L1> "title")\r\n'
                   f'[ref]: <{target}>\r\n'
                   '`[example](missing.py)`\r\n```md\r\n[x](missing)\r\n```\r\n'
                   '[web](https://example.invalid:443)\r\n')
        doc.write_bytes(content.encode())
        self.call('md_links.py', doc, '--wsl-distro', 'ExampleDistro', expected=1)
        self.assertEqual(doc.read_bytes(), content.encode())
        self.call('md_links.py', doc, '--fix', '--wsl-distro', 'ExampleDistro')
        fixed = doc.read_bytes()
        self.assertIn(b'../assets/alpha%20beta%28a%29.py#L1 "title"', fixed)
        self.assertIn(b'https://example.invalid:443', fixed)
        self.assertIn(b'\r\n', fixed)
        self.call('md_links.py', doc)
        self.call('md_links.py', doc, '--fix')
        self.assertEqual(doc.read_bytes(), fixed)

    def test_link_errors_prevent_partial_write_and_do_not_guess_distro(self):
        target = self.temp / 'source.py'; target.write_text('pass\n')
        doc = self.temp / 'readme.md'
        for invalid in ['missing.py', 'source.py:120', 'C:/example/source.py',
                        'file://wsl.localhost/OtherDistro' + target.as_posix()]:
            content = f'[good](<{target}>)\n[bad]({invalid})\n'
            doc.write_text(content)
            self.call('md_links.py', doc, '--fix', '--wsl-distro', 'ExampleDistro', expected=1)
            self.assertEqual(doc.read_text(), content)
