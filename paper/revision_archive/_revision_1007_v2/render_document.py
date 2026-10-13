"""Render v2 only through the packaged document renderer and bundled runtime."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent
PYTHON = Path('/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3')
RENDERER = Path('/Users/channtang/.codex/plugins/cache/openai-primary-runtime/documents/26.1005.12141/skills/documents/render_docx.py')
SOFFICE = Path('/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/MacOS/soffice')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'report_1007_v2_full.docx')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--dpi', type=int, default=110)
    args = parser.parse_args()
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    assert args.output_dir.resolve().is_relative_to(WORK)
    assert args.source.is_file() and RENDERER.is_file() and SOFFICE.is_file()
    env = os.environ.copy()
    env['FONTCONFIG_FILE'] = str(WORK / 'fonts.conf')
    env['PATH'] = str(PYTHON.parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(PYTHON), str(RENDERER), str(args.source.resolve()),
                    '--output_dir', str(args.output_dir.resolve()), '--emit_pdf',
                    '--dpi', str(args.dpi)], check=True, env=env)


if __name__ == '__main__':
    main()
