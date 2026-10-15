#!/usr/bin/env python3
"""Check local Markdown links; --fix normalizes existing targets to relative URLs."""
import argparse
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, unquote, urlsplit


def destinations(text):
    """Yield destination spans for inline links/images and reference definitions.

    Skip fenced/indented code and inline backticks. Not a full Markdown parser.
    """
    masked, fence = [], None
    for line in text.splitlines(keepends=True):
        match = re.match(r' {0,3}(`{3,}|~{3,})', line)
        is_code = fence is not None or bool(match) or line.startswith(('    ', '\t'))
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
        masked.append(re.sub(r'[^\r\n]', ' ', line) if is_code else line)
    masked = ''.join(masked)
    masked = re.sub(r'(`+)([^`]|(?!\1)`)*?\1',
                    lambda m: re.sub(r'[^\r\n]', ' ', m[0]), masked)
    starts = [m.end() for m in re.finditer(r'(?<!\\)\[(?:\\.|[^\]\\\n])*\]\(', masked)]
    starts += [m.end() for m in re.finditer(r'^ {0,3}\[(?!\^)[^\]\n]+\]:[ \t]*', masked, re.M)]
    for pos in sorted(set(starts)):
        while pos < len(masked) and masked[pos] in ' \t':
            pos += 1
        start = pos
        if pos < len(masked) and masked[pos] == '<':
            end = masked.find('>', pos + 1)
            if end >= 0 and '\n' not in masked[pos:end]:
                yield start, end + 1, text[pos + 1:end]
            continue
        depth = 0
        while pos < len(masked):
            char = masked[pos]
            if char == '\\' and pos + 1 < len(masked) and masked[pos + 1] in '() ': 
                pos += 2
                continue
            if char.isspace() or (char == ')' and depth == 0):
                break
            depth += (char == '(') - (char == ')')
            pos += 1
        if pos > start:
            yield start, pos, text[start:pos]


def normalize(raw, parent, distro):
    raw = re.sub(r'\\([() ])', r'\1', raw)
    if not raw or raw.startswith('#'):
        return None
    if re.match(r'^[A-Za-z]:[\\/]', raw):
        raise ValueError('Windows盘符路径：请先换成可访问的目标路径')
    local = raw
    if raw.lower().startswith('file:') or raw.startswith('//'):
        parsed = urlsplit(raw)
        if parsed.netloc.lower() in ('wsl.localhost', 'wsl$'):
            first, _, rest = parsed.path.lstrip('/').partition('/')
            if first != distro:
                raise ValueError('WSL发行版未指定或不同：用--wsl-distro指定，不自动猜测')
            local = '/' + rest
        elif parsed.scheme == 'file' and parsed.netloc in ('', 'localhost'):
            local = parsed.path
        else:
            raise ValueError('无法映射的网络文件地址：请手动指定本地目标')
        if parsed.query:
            raise ValueError('本地文件查询参数不自动处理')
        if parsed.fragment:
            local += '#' + parsed.fragment
    elif re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', raw) and not re.match(r'^[^/:\s]+\.[^/:\s]+:\d+(?:#.*)?$', raw):
        return None  # External protocols are outside this tool's scope.
    if local.startswith('\\'):
        raise ValueError('UNC反斜杠路径：请先换成file://wsl.localhost/发行版/...')
    pathpart, sep, fragment = local.partition('#')
    pathpart = unquote(pathpart)
    if re.search(r':\d+$', pathpart):
        raise ValueError('行号不能拼进文件名：请移到链接名称，工具不猜测其语义')
    target = Path(pathpart)
    if not target.is_absolute():
        target = parent / target
    # Use lexical paths so that relative links through symlinks keep their meaning.
    target = Path(os.path.abspath(target))
    if not target.is_file():
        raise ValueError('目标文件不存在或不是文件：' + str(target))
    rel = os.path.relpath(target, parent).replace(os.sep, '/')
    return quote(rel, safe='/~._-') + (('#' + fragment) if sep else '')


def process(doc, fix=False, distro=''):
    doc = Path(doc).absolute()
    text = doc.read_bytes().decode('utf-8')
    edits, errors, total = [], [], 0
    for start, end, raw in destinations(text):
        line = text.count('\n', 0, start) + 1
        try:
            dest = normalize(raw, doc.parent, distro)
            if dest is not None:
                total += 1
                if text[start:end] != dest:
                    edits.append((start, end, dest, line))
        except ValueError as exc:
            errors.append((line, str(exc)))
    for line, message in errors:
        print(f'{doc}:{line}: ERROR {message}')
    for start, end, dest, line in edits:
        print(f'{doc}:{line}: RELATIVE {dest}')
    if fix and edits and not errors:
        for start, end, dest, _ in reversed(edits):
            text = text[:start] + dest + text[end:]
        doc.write_bytes(text.encode('utf-8'))
    print(f'本地文件链接 {total}；待规范 {len(edits)}；错误 {len(errors)}；'
          + ('已修改' if fix and edits and not errors else '未修改'))
    print('未验证阅读器中的实际点击；不检查URL、页内锚点或Mermaid点击行为。')
    return 1 if errors or (edits and not fix) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown', type=Path)
    parser.add_argument('--fix', action='store_true', help='仅无错误时改写为相对链接')
    parser.add_argument('--wsl-distro', default=os.environ.get('WSL_DISTRO_NAME', ''))
    args = parser.parse_args()
    try:
        return process(args.markdown, args.fix, args.wsl_distro)
    except (OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
