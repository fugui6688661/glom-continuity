#!/usr/bin/env python3
"""Repeatable local CLI replay with synthetic data, never a model/API demonstration."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New non-existing demo directory')
    args = parser.parse_args()
    root = args.output.expanduser().resolve()
    if root.exists() or args.output.is_symlink():
        parser.error('Output exists; nothing overwritten. Choose a new directory.')
    root.mkdir(mode=0o700, parents=False)
    cli = Path(__file__).resolve().with_name('continuity.py')
    events = []

    def call(*arguments, code='OK'):
        process = subprocess.run([sys.executable, '-B', str(cli), '--project', str(root), *arguments],
                                 capture_output=True, text=True, encoding='utf-8', timeout=15)
        result = json.loads(process.stdout)
        if result.get('code') != code or ((process.returncode == 0) != (code == 'OK')):
            raise RuntimeError('Unexpected CLI result: ' + result.get('code', 'missing code'))
        events.append({'command': arguments[0], 'code': result['code'],
                       'exit_code': process.returncode})
        return result.get('data')

    source = root / 'input.csv'
    source.write_text('item,amount\nA,10\nB,20\n', encoding='utf-8')
    draft = root / 'checkpoint.json'
    draft.write_text(json.dumps({
        'objective': '核对合成表格金额，原数据不可改写',
        'next_action': '确认币种后制作汇总表',
        'constraints': ['不得上传文件', '不得删除原始行'],
        'decisions': ['两个项目金额为10和20'],
        'unresolved': ['币种未确认'],
        'evidence': [{'path': 'input.csv', 'role': 'input'}]}, ensure_ascii=False), encoding='utf-8')
    call('init', '--name', 'Continuity 合成示例')
    call('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
    context = call('context', '--max-chars', '6000')
    if '币种未确认' not in context['text']:
        raise RuntimeError('Unresolved issue missing from restored context')
    handoff = call('handoff', '--recipient', 'demo-receiver', '--expect-revision', '1')
    original = source.read_bytes()
    source.write_text('changed input', encoding='utf-8')
    call('accept', '--id', handoff['handoff_id'], '--recipient', 'demo-receiver', code='EVIDENCE_CHANGED')
    source.write_bytes(original)
    call('accept', '--id', handoff['handoff_id'], '--recipient', 'demo-receiver')
    call('accept', '--id', handoff['handoff_id'], '--recipient', 'demo-receiver', code='ALREADY_ACCEPTED')
    receipt = call('receipt', '--id', handoff['handoff_id'])
    if receipt['state'] != 'accepted':
        raise RuntimeError('Accepted receipt was not restored')
    call('export', '--output', 'handoff-review.json')
    (root / 'events.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
    (root / '演示结果.md').write_text(
        '# Continuity 本机协议回放\n\n'
        '这是合成数据与独立 CLI 进程的真实运行，不是真实 Codex/DeepSeek 模型接力。\n\n'
        '- 新进程读回：目标、限制、下一步与币种未确认。\n'
        '- 故意改输入后领取：EVIDENCE_CHANGED，被拒绝，未消费交接。\n'
        '- 恢复原输入后领取：成功；再次领取：ALREADY_ACCEPTED。\n'
        '- 新进程查回执：accepted。\n'
        '- 导出 handoff-review.json：无原始文件字节，不授予权限。\n\n'
        '没有执行模型、付费 API、发布、外部消息或生成真正业务成品。\n'
        'events.json 为本次调用摘要；.continuity 保留此合成示例状态。\n', encoding='utf-8')
    print(json.dumps({'state': 'protocol_demo_passed', 'real_model_handoff_verified': False,
                      'report': str(root / '演示结果.md'), 'calls': len(events)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
