"""
把 03 MD 中的「改写新视频脚本」模块拆出来，独立保存到 04-原视频脚本改写/，
然后从 03 MD 删除该段。

用法：
    python extract_rewrite_script.py <项目根目录>

依赖：
    pip install regex
"""
import re
import sys
from pathlib import Path


REWRITE_SECTION_RE = re.compile(
    r'##\s*🎬\s*改写新视频脚本.*?(?=\n##\s|\Z)',
    re.DOTALL
)


def extract_one(md_path: Path, project_root: Path) -> Path | None:
    """从单个 03 MD 提取改写脚本段，存到 04/对应文件"""
    text = md_path.read_text(encoding='utf-8')

    m = REWRITE_SECTION_RE.search(text)
    if not m:
        print(f'  [跳过] {md_path.name}: 无「改写新视频脚本」段')
        return None

    rewrite_section = m.group(0).strip()

    # 拼 04 文件头
    new_filename = md_path.stem + '_改写脚本.md'
    new_path = project_root / '04-原视频脚本改写' / new_filename
    new_path.parent.mkdir(parents=True, exist_ok=True)

    # 读取原 MD 头部的元信息（若有）
    meta_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    meta_yaml = meta_match.group(1) if meta_match else ''

    # 拼接 04 文件
    content_parts = []
    if meta_yaml:
        content_parts.append('---\n' + meta_yaml + '\n---\n\n')
    content_parts.append(f'# {md_path.stem} 改写脚本\n\n')
    content_parts.append('> 本脚本由 AI 基于原视频逐字稿提炼改写，新标题 + 新口播。\n> 原始视频：[03-逐字稿MD/](../03-逐字稿MD/) 同名 MD\n\n')
    content_parts.append('---\n\n')
    content_parts.append(rewrite_section + '\n')

    new_path.write_text(''.join(content_parts), encoding='utf-8')

    # 从 03 MD 删除该段
    new_text = text[:m.start()] + text[m.end():]
    # 清理尾部多余空行
    new_text = re.sub(r'\n{3,}', '\n\n', new_text).rstrip() + '\n'
    md_path.write_text(new_text, encoding='utf-8')

    print(f'  ✅ {md_path.name} → 04-原视频脚本改写/{new_filename}')
    return new_path


def main():
    if len(sys.argv) != 2:
        print('用法: python extract_rewrite_script.py <项目根目录>')
        sys.exit(1)

    project_root = Path(sys.argv[1])
    md_dir = project_root / '03-逐字稿MD'

    if not md_dir.exists():
        print(f'❌ {md_dir} 不存在')
        sys.exit(1)

    md_files = sorted(md_dir.glob('*.md'))
    if not md_files:
        print(f'❌ {md_dir} 无 MD 文件')
        sys.exit(1)

    print(f'🔍 扫描 {md_dir}，共 {len(md_files)} 个 MD')
    ok, skip = 0, 0
    for md_path in md_files:
        result = extract_one(md_path, project_root)
        if result:
            ok += 1
        else:
            skip += 1

    print(f'\n✨ 完成：成功 {ok} / 跳过 {skip} / 总计 {len(md_files)}')


if __name__ == '__main__':
    main()