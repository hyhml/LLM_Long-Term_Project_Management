#!/usr/bin/env python3
"""Check Markdown math delimiters; --fix normalizes explicit LaTeX delimiters."""
import argparse
from pathlib import Path
import re


def mask_code(text):
    result, fence = [], None
    for line in text.splitlines(keepends=True):
        match = re.match(r' {0,3}(`{3,}|~{3,})', line)
        code = fence is not None or bool(match) or line.startswith(('    ', '\t'))
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
        result.append(re.sub(r'[^\r\n]', ' ', line) if code else line)
    return re.sub(r'(`+)([^`]|(?!\1)`)*?\1',
                  lambda m: re.sub(r'[^\r\n]', ' ', m[0]), ''.join(result))


def normalize(text):
    masked = mask_code(text)
    edits, errors = [], []
    newline = '\r\n' if '\r\n' in text else '\n'
    for match in re.finditer(r'(?<!\\)\\\[([\s\S]*?)(?<!\\)\\\]|(?<!\\)\\\(([^\n]*?)(?<!\\)\\\)', masked):
        body = text[match.start() + 2:match.end() - 2].strip()
        if '$' in body:
            errors.append('旧式分隔符内含美元符号，请人工确认')
            continue
        if match.group(1) is not None:
            before = '' if match.start() == 0 or text[match.start()-1] == '\n' else newline
            after = '' if match.end() == len(text) or text[match.end()] in '\r\n' else newline
            value = before + '$$' + newline + body + newline + '$$' + after
        else:
            value = '$' + body + '$'
        edits.append((match.start(), match.end(), value))
    for start, end, value in reversed(edits):
        text = text[:start] + value + text[end:]
    masked = mask_code(text)
    edits2 = []
    for match in re.finditer(r'(?<![\\$])\$\$([^\n$]+)\$\$(?!\$)', masked):
        body = text[match.start()+2:match.end()-2].strip()
        before = '' if match.start() == 0 or text[match.start()-1] == '\n' else newline
        after = '' if match.end() == len(text) or text[match.end()] in '\r\n' else newline
        edits2.append((match.start(), match.end(), before+'$$'+newline+body+newline+'$$'+after))
    for start, end, value in reversed(edits2):
        text = text[:start] + value + text[end:]
    masked = mask_code(text)
    if re.search(r'(?<!\\)\\[\[\]()]', masked):
        errors.append('旧式数学分隔符未配对或跨行行内公式，请人工修正')
    opened = None
    for number, line in enumerate(masked.splitlines(), 1):
        if line.strip() == '$$':
            opened = number if opened is None else None
            continue
        if re.search(r'(?<!\\)\$\$', line):
            errors.append(f'第{number}行：块公式的$$必须各自独占一行')
        elif opened is None:
            count = len(re.findall(r'(?<!\\)\$', line))
            if count % 2:
                errors.append(f'第{number}行：单美元符号未配对；金额请写成\\$')
    if opened is not None:
        errors.append(f'第{opened}行起：块公式缺少结束$$')
    return text, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown', type=Path)
    parser.add_argument('--fix', action='store_true')
    args = parser.parse_args()
    try:
        original = args.markdown.read_bytes().decode('utf-8')
        updated, errors = normalize(original)
        changed = updated != original
        for error in errors:
            print('ERROR: ' + error)
        if args.fix and changed and not errors:
            args.markdown.write_bytes(updated.encode('utf-8'))
        print(f'待规范：{changed}；错误：{len(errors)}；'
              + ('已修改' if args.fix and changed and not errors else '未修改'))
        print('仅检查分隔符，不验证LaTeX命令、公式含义或阅读器实际显示。')
        return 1 if errors or (changed and not args.fix) else 0
    except (OSError, UnicodeError) as exc:
        print(f'ERROR: {exc}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
