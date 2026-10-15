#!/usr/bin/env python3
"""Local issue submissions and a review reminder after three verified failures."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import fcntl

DEFAULT_STORE = Path(__file__).resolve().parent.parent / 'private/problem-reminder/issues.json'


def load(path):
    data = json.loads(path.read_text()) if path.exists() else {'schema': 1, 'issues': {}}
    if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('issues'), dict):
        raise ValueError('问题库格式或版本不支持，不会覆盖')
    for key, issue in data['issues'].items():
        if (not isinstance(key, str) or not isinstance(issue, dict)
                or not all(isinstance(issue.get(k), str) for k in
                           ['title', 'criterion', 'environment', 'status', 'created'])
                or issue['status'] not in ['open', 'pending', 'needs-review', 'resolved']
                or type(issue.get('failures')) is not int or issue['failures'] < 0
                or type(issue.get('round')) is not int or issue['round'] < 1
                or not isinstance(issue.get('events'), list)):
            raise ValueError('问题记录格式不完整，不会覆盖')
        ids = set()
        for event in issue['events']:
            if (not isinstance(event, dict)
                    or not all(isinstance(event.get(k), str) for k in
                               ['id', 'recorded_at', 'result', 'approach', 'evidence'])
                    or event['result'] not in ['pending', 'failed', 'passed']
                    or type(event.get('round')) is not int or event['round'] < 1
                    or event['id'] in ids):
                raise ValueError('问题事件格式不完整或标识重复，不会覆盖')
            ids.add(event['id'])
    return data


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def registry(path, write=False):
    if not write:
        yield load(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load(path)
        yield data
        temp = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                             delete=False) as output:
                temp = output.name
                json.dump(data, output, ensure_ascii=False, indent=2)
                output.write('\n')
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, path)
        finally:
            if temp and os.path.exists(temp):
                os.unlink(temp)


def reminder(issue):
    if issue['failures'] >= 3:
        print('提醒：同一验收条件已至少三次失败。先暂停无新证据的试改，'
              '汇总方案与证据，复查环境和验收条件；再选择复现、补齐条件或按需工具化。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, default=DEFAULT_STORE)
    commands = parser.add_subparsers(dest='command', required=True)
    submit = commands.add_parser('submit')
    submit.add_argument('id')
    submit.add_argument('--title', required=True)
    submit.add_argument('--criterion', required=True)
    submit.add_argument('--environment', required=True, help='区分阅读器、系统或其他相关条件')
    record = commands.add_parser('record')
    record.add_argument('id')
    record.add_argument('--event-id', required=True, help='同一次尝试的稳定标识，防止重复计数')
    record.add_argument('--result', choices=['failed', 'pending', 'passed'], required=True)
    record.add_argument('--approach', required=True)
    record.add_argument('--evidence', required=True)
    listing = commands.add_parser('list')
    listing.add_argument('--all', action='store_true', help='同时显示已解决问题')
    show = commands.add_parser('show')
    show.add_argument('id')
    args = parser.parse_args()
    try:
        with registry(args.store, args.command in ('submit', 'record')) as data:
            issues = data['issues']
            if args.command == 'submit':
                if args.id in issues:
                    raise ValueError('问题ID已存在，请show后复用，勿重复提交')
                if not all(x.strip() for x in [args.id, args.title, args.criterion, args.environment]):
                    raise ValueError('问题ID、标题、验收条件、环境不能为空')
                if any(i['criterion'] == args.criterion and i['environment'] == args.environment for i in issues.values()):
                    raise ValueError('同验收条件和环境已存在，请复用原问题ID')
                issues[args.id] = {'title': args.title, 'criterion': args.criterion,
                                  'environment': args.environment, 'round': 1,
                                  'created': now(), 'status': 'open', 'failures': 0,
                                  'events': []}
            elif args.command == 'record':
                issue = issues[args.id]
                old = next((e for e in issue['events'] if e['id'] == args.event_id), None)
                payload = {'result': args.result, 'approach': args.approach, 'evidence': args.evidence}
                if old:
                    if any(old[k] != v for k, v in payload.items()):
                        raise ValueError('event-id已存在且内容不同；不要覆写历史')
                    print('相同尝试已记录，不重复计数。')
                else:
                    if not all(x.strip() for x in [args.event_id, args.approach, args.evidence]):
                        raise ValueError('尝试标识、方案和证据不能为空')
                    if issue['status'] == 'resolved' and args.result != 'passed':
                        issue['round'] += 1
                    issue['events'].append({'id': args.event_id, 'round': issue['round'],
                                            'recorded_at': now(), **payload})
                    if args.result == 'failed':
                        issue['failures'] += 1
                    elif args.result == 'passed':
                        issue['failures'] = 0
                    issue['status'] = ('resolved' if args.result == 'passed' else
                                       'needs-review' if issue['failures'] >= 3 else
                                       'pending' if args.result == 'pending' else 'open')
            if args.command == 'show':
                print(json.dumps(issues[args.id], ensure_ascii=False, indent=2))
            else:
                selected = issues.items() if args.command == 'list' else [(args.id, issues[args.id])]
                for key, issue in selected:
                    if args.command == 'list' and not args.all and issue['status'] == 'resolved':
                        continue
                    print(f"{key}: {issue['status']}；第{issue['round']}轮；本轮失败{issue['failures']}次；{issue['title']}")
                    reminder(issue)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
