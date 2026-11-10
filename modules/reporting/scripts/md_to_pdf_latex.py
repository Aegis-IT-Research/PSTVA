#!/usr/bin/env python3
"""Convert Markdown report to PDF using Pandoc + LaTeX template.

Requirements:
  - pandoc
  - LaTeX distribution (pdflatex) and minted (requires pygments)
  - Python packages: (optional) none, but pygments recommended if using minted via pandoc

Usage:
  python scripts/md_to_pdf_latex.py --input report_rich.md --output report_latex.pdf \
    --template latex/report_template.tex --title "Client Pentest Report" \
    --client ExampleCorp --prepared-by "Security Team" --version 1.2 \
    --classification CONFIDENTIAL --logo assets/logo.png

If --template is omitted, the default template in latex/report_template.tex is used.
"""
from __future__ import annotations
import argparse
import pathlib
import subprocess
import sys
import datetime as dt


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Markdown to PDF")
    ap.add_argument('--input', required=True, help='Markdown input file')
    ap.add_argument('--output', required=True, help='Target PDF output file')
    ap.add_argument('--keep-tex', action='store_true', help='Keep intermediate .tex output next to PDF')
    return ap.parse_args(argv)


def derive_title(md_path: pathlib.Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        for line in md_path.read_text(encoding='utf-8').splitlines():
            if line.startswith('# '):
                return line[2:].strip()
    except Exception:
        pass
    return 'Report'


def ensure_tools():
    for tool in ('pandoc', 'pdflatex'):
        if subprocess.call(['which', tool], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            sys.exit(f"Required tool '{tool}' not found in PATH")


def run_pandoc(args):
    md = pathlib.Path(args.input)
    out_pdf = pathlib.Path(args.output)
    template = pathlib.Path('templates/report_template.tex')
    if not md.exists():
        sys.exit(f"Input markdown not found: {md}")
    if not template.exists():
        sys.exit(f"Template not found: {template}")

    title = derive_title(md, None)
    date_str = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')
    # Extract client (text before the first '–' or '-' in title) simplistic heuristic
    client_guess = title.split('–')[0].split('-')[0].strip()
    TAGLINE = 'Confidential – For Authorized Use Only'
    PREPARED_BY = 'Security Team'
    VERSION = '1.0'
    CLASSIFICATION = 'Confidential'

    pandoc_cmd = [
        'pandoc', str(md), '-o', str(out_pdf),
        # enable raw LaTeX passthrough for severity color macro
        '--from', 'markdown+pipe_tables+table_captions+strikeout+raw_tex',
        '--template', str(template),
        '--pdf-engine', 'pdflatex',
        '--variable', f'title={title}',
        '--variable', f'client={client_guess}',
        '--variable', f'preparedby={PREPARED_BY}',
        '--variable', f'version={VERSION}',
        '--variable', f'classification={CLASSIFICATION}',
        '--variable', f'tagline={TAGLINE}',
        '--variable', f'date={date_str}',
    ]

    logo_path = pathlib.Path('assets/logo.png')
    if logo_path.exists():
        pandoc_cmd.extend(['--variable', f'logo={logo_path}'])
    pandoc_cmd.append('--listings')
    # If arithmetic in column specs still breaks, user can add: --columns=120 via --extra-args

    if args.keep_tex:
        try:
            subprocess.check_call(pandoc_cmd)
            tex_path = out_pdf.with_suffix('.tex')
            subprocess.check_call([
                'pandoc', str(md), '-t', 'latex', '--template', str(template),
                '--variable', f'title={title}', '--variable', f'client={client_guess}',
                '--variable', f'preparedby={PREPARED_BY}', '--variable', f'version={VERSION}',
                '--variable', f'classification={CLASSIFICATION}', '--variable', f'date={date_str}',
                '--variable', f'tagline={TAGLINE}',
                '--output', str(tex_path)
            ])
            print(f"PDF written to {out_pdf}; TEX kept at {tex_path}")
            return
        except subprocess.CalledProcessError as e:
            sys.exit(f"Pandoc error: {e}")

    try:
        subprocess.check_call(pandoc_cmd)
        print(f"PDF written to {out_pdf}")
    except subprocess.CalledProcessError as e:
        sys.exit(f"Pandoc error: {e}")


def main(argv=None):
    a = parse_args(argv)
    ensure_tools()
    run_pandoc(a)

if __name__ == '__main__':
    main()
