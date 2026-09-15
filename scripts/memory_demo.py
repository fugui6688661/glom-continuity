#!/usr/bin/env python3
"""Synthetic single-assistant memory walkthrough; no models, network or private data."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', newline='\n')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = args.output.resolve()
    try:
        project.mkdir(mode=0o700)  # Never overwrite a prior run, even a failed one.
    except OSError:
        parser.error('Choose a new directory with an existing writable parent; nothing overwritten')
    cli = Path(__file__).with_name('continuity.py')
    events = []

    def save_json(name, value):
        (project / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def call(*arguments):
        result = subprocess.run([sys.executable, '-B', str(cli), '--project', str(project), *arguments],
                                capture_output=True, text=True, encoding='utf-8', timeout=15)
        value = json.loads(result.stdout)
        events.append({'arguments': list(arguments), 'exit_code': result.returncode, 'response': value})
        save_json('events.json', events)
        if result.returncode != 0 or value.get('ok') is not True or value.get('code') != 'OK':
            raise RuntimeError('CLI failed; inspect events.json. No automatic retry.')
        return value['data']

    memory = {'format': 'continuity-memory-v1', 'items': [
        {'id': 'explain', 'kind': 'preference', 'title': '沟通习惯',
         'body': '用中文先讲结论。', 'when': ['*'], 'status': 'active',
         'source': '演示用虚构用户要求', 'expires_at': None},
        {'id': 'film', 'kind': 'workflow', 'title': '视频验收',
         'body': '交付前检查画面、字幕并试听声音。', 'when': ['视频', 'video'], 'status': 'active',
         'source': '演示用虚构流程', 'expires_at': None},
        {'id': 'sheet', 'kind': 'workflow', 'title': '表格验收',
         'body': '核对数据口径与汇总公式。', 'when': ['表格'], 'status': 'active',
         'source': '演示用虚构流程', 'expires_at': None},
        {'id': 'guess', 'kind': 'preference', 'title': '未确认猜测',
         'body': '默认采用卡通风格。', 'when': ['*'], 'status': 'candidate',
         'source': '助手的猜测，尚未由用户确认', 'expires_at': None}
    ]}
    draft = {'objective': '完成一份演示用品牌材料', 'next_action': '整理待审素材',
             'constraints': ['不发布、不删除原始文件'], 'decisions': [], 'unresolved': ['素材授权待确认'],
             'evidence': [{'path': 'project-memory.json', 'role': 'memory'}]}
    try:
        save_json('project-memory.json', memory)
        save_json('checkpoint.json', draft)
        call('init', '--name', '单助手记忆演示')
        call('checkpoint', '--from-file', str(project / 'checkpoint.json'), '--expect-revision', '0')
        video = call('context', '--query', '视频', '--max-chars', '12000')
        sheet = call('context', '--query', '表格', '--max-chars', '12000')
        assert [n['id'] for n in video['memory']['selected']] == ['explain', 'film']
        assert [n['id'] for n in sheet['memory']['selected']] == ['explain', 'sheet']
        memory['items'][0]['body'] = '用中文先讲结论，再讲尚未完成的部分。'
        save_json('project-memory.json', memory)
        review = call('context', '--query', '视频', '--max-chars', '12000')
        assert review['memory']['state'] == 'requires_reference_review' and not review['memory']['selected']
        call('checkpoint', '--from-file', str(project / 'checkpoint.json'), '--expect-revision', '1')
        resumed = call('context', '--query', '视频', '--max-chars', '12000')
        assert resumed['revision'] == 2 and '尚未完成' in resumed['memory']['selected'][0]['body']
        report = ('# 一个助手的记忆恢复演示\n\n'
                  '这是实际 CLI 子进程回放，使用虚构资料，不是新模型会话或效率对照。\n\n'
                  '1. 已保存沟通习惯、视频和表格流程，以及一项未确认猜测。\n'
                  '2. 询问视频：恢复沟通习惯与视频验收；表格流程不加载。\n'
                  '3. 询问表格：恢复沟通习惯与表格验收；视频流程不加载。\n'
                  '4. 修改习惯但未保存：显示需要复核，未采用变化后的正文。\n'
                  '5. 审核并保存第二个节点：恢复新习惯，候选猜测仍未启用。\n\n'
                  '每次调用是新进程。原始响应在 events.json，记忆正文在 project-memory.json。\n'
                  '没有联网、调用模型、发布、全局安装或自动学习私人习惯。\n')
        (project / '演示结果.md').write_text(report, encoding='utf-8')
        print(json.dumps({'state': 'memory_demo_passed', 'calls': len(events),
                          'report': str(project / '演示结果.md'), 'real_model_verified': False}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.SubprocessError) as error:
        print(json.dumps({'state': 'memory_demo_failed', 'error': str(error), 'evidence': str(project),
                          'real_model_verified': False}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
