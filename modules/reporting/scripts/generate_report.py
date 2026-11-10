#!/usr/bin/env python3
"""Generate an penetration test report markdown.

Simplified workflow:
    1. Run this script to generate build/report.md (or chosen --out file).
    2. Manually edit the markdown (tweak narrative sections, wording).
    3. Convert to PDF via: python scripts/md_to_pdf_latex.py --input build/report.md --output build/report.pdf
"""
from __future__ import annotations
import argparse
import datetime as dt
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any
import yaml  # type: ignore

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Informational"]
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}
REQUIRED_FIELDS = ["id", "title", "severity", "affected", "status", "remediation_summary"]

# ------------------------- USER CONFIG SECTION ---------------------------------
# Edit these values instead of passing many CLI flags.
CONFIG = {
    'CLIENT_NAME': 'Test',
    'PREPARED_BY': 'Security Team',
    'REPORT_VERSION': '1.0',
    'OVERALL_RISK': 'Edit Manually',
    'SCOPE_TARGETS': 'Edit Manually',
    'METHODOLOGY': 'Edit Manually',
    'TYPES_OF_TESTING': 'Edit Manually',
    'ENGAGEMENT_DATES': '05 Jul 2025 - 10 Jul 2025',
    'TOOLS_USED': 'nmap, Custom Tools', # need to get the data from tools
    # Executive summary narrative
    'OBSERVATIONS_SECTION': 'Most issues are low complexity to fix.',
    'RECOMMENDATIONS_SUMMARY_SECTION': 'Apply security headers, patch WordPress components, enforce session limits.',
    'STRONG_POINTS_SECTION': 'Good WAF and plugin coverage; resilient against injection attempts.',
    # Project description sections
    'CONTEXT_OBJECTIVES': 'Evaluate the security posture of the web application.',
    'SCOPE_LIMITS': 'In-scope: portal, API. Out-of-scope: payment gateway.',
    'TESTING_CONDITIONS': 'Black-box with limited credentials.',
    # Disclaimer
    'LEGAL_DISCLAIMER': 'Confidential – internal use only.',
    'DISCLAIMER_SECTION': 'Confidential – internal use only.',
}
# ------------------------------------------------------------------------------

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

def sev_colored_text(sev: str) -> str:
    """Return LaTeX colored severity label."""
    return f"\\sev{{{sev}}}"

@dataclass
class Finding:
    meta: Dict[str, Any]
    body: str
    sort_key: tuple = field(init=False)

    def __post_init__(self):
        sev_rank = SEVERITY_RANK.get(self.meta.get("severity"), 999)
        self.sort_key = (sev_rank, self.meta.get("title", ""))

    @property
    def title(self) -> str:
        return self.meta.get("title", "Untitled")

    @property
    def severity(self) -> str:
        return self.meta.get("severity", "Unknown")

    def _sev_colored(self) -> str:
        """Return LaTeX-colored severity macro for Pandoc->LaTeX pipeline."""
        sev = self.severity
        return f"\\sev{{{sev}}}"

    def to_summary_row(self) -> str:
        return (
            f"| {self.meta.get('id','')} | {self.title} | {self._sev_colored()} | "
            f"{self.meta.get('affected','')} | {self.meta.get('status','')} |"
        )

    def key_bullet(self) -> str:
        return (
            f"- **{self.title}** (Severity: {self._sev_colored()}) — "
            f"{self.meta.get('remediation_summary','')[:140]}"
        )

    def detail_section(self, idx: int) -> str:
        refs = self.meta.get('references') or []
        refs_md = "\n".join(f"  - {r}" for r in refs) if refs else "None"
        header = f"### {idx}. {self.title} ({self._sev_colored()})\n"
        meta_table = (
            "| Field | Value |\n|-------|-------|\n"
            f"| ID | {self.meta.get('id','')} |\n"
            f"| Severity | {self._sev_colored()} |\n"
            f"| Affected | {self.meta.get('affected','')} |\n"
            f"| Status | {self.meta.get('status','')} |\n"
            f"| CVSS | {self.meta.get('cvss','-')} |\n"
            f"| Remediation Summary | {self.meta.get('remediation_summary','')} |\n"
            f"| References | {'; '.join(refs) if refs else 'None'} |\n"
        )
        return header + "\n" + meta_table + "\n" + self.body.strip() + "\n\n"

    def roadmap_row(self) -> str:
        owner = self.meta.get('owner', 'TBD')
        effort = self.meta.get('effort', 'Unknown')  # Easy | Moderate | Complex
        priority = self.meta.get('priority', self.severity)
        eta = self.meta.get('eta', 'TBD')
        return f"| {self.meta.get('id','')} | {self.title} | {priority} | {effort} | {owner} | {eta} | {self.meta.get('status','')} |"

def parse_finding(path: pathlib.Path) -> Finding:
    raw = path.read_text(encoding='utf-8')
    m = FRONT_MATTER_RE.match(raw)
    if not m:
        raise ValueError(f"File {path} missing YAML front matter block")
    front, body = m.groups()
    meta = yaml.safe_load(front) or {}
    # Validate
    missing = [f for f in REQUIRED_FIELDS if f not in meta]
    if missing:
        raise ValueError(f"File {path} missing required fields: {missing}")
    return Finding(meta=meta, body=body.strip())

def load_findings(dir_path: pathlib.Path) -> List[Finding]:
    findings = []
    for p in sorted(dir_path.glob('*.md')):
        findings.append(parse_finding(p))
    return findings

def filter_findings(all_findings: List[Finding], include: List[str], exclude: List[str]) -> List[Finding]:
    sel = all_findings
    if include:
        include_set = {s.strip().lower() for s in include}
        sel = [f for f in sel if f.title.lower() in include_set or f.meta.get('id','').lower() in include_set]
    if exclude:
        exclude_set = {s.strip().lower() for s in exclude}
        sel = [f for f in sel if f.title.lower() not in exclude_set and f.meta.get('id','').lower() not in exclude_set]
    return sel

def build_findings_table(findings: List[Finding]) -> str:
    if not findings:
        return "_No findings selected._"
    header = "| ID | Title | Severity | Affected | Status |\n|----|-------|----------|----------|--------|"
    rows = "\n".join(f.to_summary_row() for f in findings)
    return header + "\n" + rows

def build_key_findings(findings: List[Finding], limit: int = 5) -> str:
    top = sorted(findings, key=lambda f: f.sort_key)[:limit]
    return "\n".join(f.key_bullet() for f in top) if top else "_None_"

def build_findings_details(findings: List[Finding]) -> str:
    ordered = sorted(findings, key=lambda f: f.sort_key)
    return "\n".join(f.detail_section(i+1) for i, f in enumerate(ordered))

def build_findings_list(findings: List[Finding]) -> str:
    if not findings:
        return '_No findings._'
    ordered = sorted(findings, key=lambda f: f.sort_key)
    header = "| ID | Title | CVSS | Severity |\n|----|-------|------|---------|"
    rows = []
    for f in ordered:
        cvss = f.meta.get('cvss', '-')
        rows.append(f"| {f.meta.get('id','')} | {f.title} | {cvss} | {f._sev_colored()} |")
    return header + "\n" + "\n".join(rows)

def build_severity_metrics_longtable(severity_counts: Dict[str, int]) -> str:
    """Return a raw LaTeX longtable that spans full text width.
    Columns: Severity (60%), Count (20%), % (20%).
    """
    total = sum(severity_counts.values()) or 1
    header = (
        "\\begin{longtable}[]{@{}\n"
        "  >{\\raggedright\\arraybackslash}p{(\\columnwidth - 4\\tabcolsep) * \\real{0.60}}\n"
        "  >{\\raggedright\\arraybackslash}p{(\\columnwidth - 4\\tabcolsep) * \\real{0.20}}\n"
        "  >{\\raggedright\\arraybackslash}p{(\\columnwidth - 4\\tabcolsep) * \\real{0.20}}@{}}\n"
        "\\toprule\\noalign{}\n"
        "Severity & Count & \\% \\\\\n"
        "\\midrule\\noalign{}\n"
        "\\endhead\n"
        "\\bottomrule\\noalign{}\n"
        "\\endlastfoot\n"
    )
    rows = []
    for s in SEVERITY_ORDER:
        c = severity_counts.get(s, 0)
        pct = (c / total) * 100
        rows.append(f"\\sev{{{s}}} & {c} & {pct:.1f}\\% \\\\")
    footer = "\\end{longtable}\n"
    return header + "\n".join(rows) + "\n" + footer

def build_remediation_roadmap(findings: List[Finding]) -> str:
    if not findings:
        return '_No items._'
    ordered = sorted(findings, key=lambda f: f.sort_key)
    header = "| ID | Title | Priority | Effort | Owner | ETA | Status |\n|----|-------|----------|--------|-------|-----|--------|"
    rows = [f.roadmap_row() for f in ordered]
    return header + "\n" + "\n".join(rows)

def build_risk_distribution_line(severity_counts: Dict[str,int]) -> str:
    total = sum(severity_counts.values()) or 1
    parts = []
    for sev in SEVERITY_ORDER:
        count = severity_counts.get(sev,0)
        if count:
            pct = (count/total)*100
            parts.append(f"{sev_colored_text(sev)}: {count} ({pct:.1f}%)")
    return ' | '.join(parts) if parts else 'No findings'

def render_template(template_text: str, mapping: Dict[str, str]) -> str:
    out = template_text
    for key, value in mapping.items():
        out = out.replace(f"{{{{ {key} }}}}", value)
    return out

def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate report markdown (minimal flags)")
    ap.add_argument('--findings-dir', required=True, help='Directory of finding markdown files')
    ap.add_argument('--out', required=True, help='Output report markdown file')
    ap.add_argument('--include', help='Comma-separated finding titles or IDs to include')
    ap.add_argument('--exclude', help='Comma-separated finding titles or IDs to exclude')
    args = ap.parse_args(argv)

    template_path = pathlib.Path('templates/template.md')
    findings_dir = pathlib.Path(args.findings_dir)
    out_path = pathlib.Path(args.out)

    findings = load_findings(findings_dir)

    include_list = [s for s in (args.include.split(',') if args.include else []) if s.strip()]
    exclude_list = [s for s in (args.exclude.split(',') if args.exclude else []) if s.strip()]
    findings = filter_findings(findings, include_list, exclude_list)

    # Sort findings for consistent ordering
    findings_sorted = sorted(findings, key=lambda f: f.sort_key)

    # Metrics
    severity_counts: Dict[str, int] = {s: 0 for s in SEVERITY_ORDER}
    for f in findings_sorted:
        if f.severity in severity_counts:
            severity_counts[f.severity] += 1
    total_findings = sum(severity_counts.values()) or 1
    # Build Severity Metrics as a full-width LaTeX longtable
    findings_metrics_md = build_severity_metrics_longtable(severity_counts)
    list_of_findings_md = build_findings_list(findings_sorted)
    risk_distribution_line = build_risk_distribution_line(severity_counts)

    severity_definitions_md = """| Severity | Description |
|----------|-------------|
| \\sev{Critical} | Exploitable immediately with business-wide / catastrophic impact |
| \\sev{High} | High impact or high likelihood leading to significant compromise |
| \\sev{Medium} | Moderate impact or requires specific conditions |
| \\sev{Low} | Limited impact or hard to exploit |
| \\sev{Informational} | Best practice / no direct exploit impact |"""

    risk_matrix_md = """| Likelihood \\ Impact | Low | Medium | High |
|------------------|-----|--------|------|
| High | Medium | High | Critical |
| Medium | Low | Medium | High |
| Low | Informational | Low | Medium |"""

    risk_rating_grid_md = """| Technical Impact \\ Likelihood | High | Medium | Low |
|---------------------------|------|--------|-----|
| High | Critical | High | Medium |
| Medium | High | Medium | Low |
| Low | Medium | Low | Low |"""

    remediation_effort_md = """| Effort | Description |
    |--------|-------------|
    | Easy | Configuration or minor change; minimal code impact |
    | Moderate | Moderate code/system modification required |
    | Complex | Significant refactor or architectural change required |
    """

    # Table of contents (static structure matching template ordering)
    toc_md = """0. Table of Contents
    1. List of Findings
    2. Project Description
        2.1 Context and Objectives
        2.2 Scope and Limits
        2.3 Testing Conditions
    3. Detailed Findings
    4. Attack & Penetration Testing Methodology
        4.1 Types of Testing
        4.2 Methodology"""

    mapping = {
        'SCOPE_TARGETS': CONFIG['SCOPE_TARGETS'],
    'METHODOLOGY': CONFIG['METHODOLOGY'],
    'TYPES_OF_TESTING': CONFIG['TYPES_OF_TESTING'],
        'ENGAGEMENT_DATES': CONFIG['ENGAGEMENT_DATES'],
        'OVERALL_RISK': CONFIG['OVERALL_RISK'],
        'KEY_FINDINGS_BULLETS': build_key_findings(findings_sorted),
        'FINDINGS_TABLE': build_findings_table(findings_sorted),
    'FINDINGS_DETAILS': build_findings_details(findings_sorted),
    'REMEDIATION_ROADMAP_TABLE': build_remediation_roadmap(findings_sorted),
        'TOOLS_USED': CONFIG['TOOLS_USED'],
        'GENERATION_DATE': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        'FINDINGS_SEVERITY_METRICS': findings_metrics_md,
        'SEVERITY_DEFINITIONS': severity_definitions_md,
        'RISK_MATRIX': risk_matrix_md,
        'TABLE_OF_CONTENTS': toc_md,
        'CLIENT_NAME': CONFIG['CLIENT_NAME'],
        'PREPARED_BY': CONFIG['PREPARED_BY'],
        'REPORT_VERSION': CONFIG['REPORT_VERSION'],
        'LEGAL_DISCLAIMER': CONFIG['LEGAL_DISCLAIMER'],
        'LIST_OF_FINDINGS': list_of_findings_md,
        'RISK_DISTRIBUTION_LINE': risk_distribution_line,
        'OBSERVATIONS_SECTION': CONFIG['OBSERVATIONS_SECTION'],
        'RECOMMENDATIONS_SUMMARY_SECTION': CONFIG['RECOMMENDATIONS_SUMMARY_SECTION'],
        'STRONG_POINTS_SECTION': CONFIG['STRONG_POINTS_SECTION'],
        'DISCLAIMER_SECTION': CONFIG['DISCLAIMER_SECTION'],
        'REMEDIATION_EFFORT_TABLE': remediation_effort_md,
        'CONTEXT_OBJECTIVES': CONFIG['CONTEXT_OBJECTIVES'],
        'SCOPE_LIMITS': CONFIG['SCOPE_LIMITS'],
        'TESTING_CONDITIONS': CONFIG['TESTING_CONDITIONS'],
        'PROJECT_DESCRIPTION': CONFIG.get('PROJECT_DESCRIPTION', ''),
    }

    template_text = template_path.read_text(encoding='utf-8')
    report_text = render_template(template_text, mapping)

    # Warn about unreplaced placeholders
    unreplaced = re.findall(r"{{ (.*?) }}", report_text)
    if unreplaced:
        sys.stderr.write(f"Warning: unreplaced placeholders remain: {unreplaced}\n")

    out_path.write_text(report_text, encoding='utf-8')
    print(f"Report written to {out_path}")

if __name__ == '__main__':
    main()
