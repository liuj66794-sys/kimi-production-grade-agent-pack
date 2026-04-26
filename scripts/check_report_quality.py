#!/usr/bin/env python3
"""
Report Quality Check Engine - Non-LLM Rules Engine
Checks report quality based on structured rules.

Usage:
    python check_report_quality.py --report <path> [--evidence-map <path>] [--output <path>]
    python check_report_quality.py --report report.md --evidence-map evidence-map.json
    python check_report_quality.py --report report.md --output report-quality.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REQUIRED_SECTIONS = [
    "executive_summary",
    "introduction",
    "methodology",
    "findings",
    "evidence_analysis",
    "uncertainties",
    "recommendations",
    "conclusion",
    "references",
]

SECTION_PATTERNS = {
    "executive_summary": [
        r"(?i)#+\s*executive\s*summary",
        r"(?i)^##\s*\u6267\u884c\u6458\u8981",
        r"(?i)^##\s*\u6458\u8981",
    ],
    "introduction": [
        r"(?i)#+\s*introduction",
        r"(?i)^##\s*\u5f15\u8a00",
        r"(?i)^##\s*\u4ecb\u7ecd",
    ],
    "methodology": [
        r"(?i)#+\s*methodology",
        r"(?i)^##\s*\u65b9\u6cd5\u8bba",
        r"(?i)^##\s*\u7814\u7a76\u65b9\u6cd5",
    ],
    "findings": [
        r"(?i)#+\s*findings?",
        r"(?i)^##\s*\u4e3b\u8981\u53d1\u73b0",
        r"(?i)^##\s*\u53d1\u73b0",
        r"(?i)^##\s*\u7ed3\u679c",
    ],
    "evidence_analysis": [
        r"(?i)#+\s*evidence\s*analysis",
        r"(?i)^##\s*\u8bc1\u636e\u5206\u6790",
        r"(?i)^##\s*\u6570\u636e\u5206\u6790",
    ],
    "uncertainties": [
        r"(?i)#+\s*uncertainties?",
        r"(?i)^##\s*\u4e0d\u786e\u5b9a\u6027",
        r"(?i)^##\s*\u98ce\u9669",
        r"(?i)^##\s*\u5c40\u9650\u6027",
    ],
    "recommendations": [
        r"(?i)#+\s*recommendations?",
        r"(?i)^##\s*\u5efa\u8bae",
        r"(?i)^##\s*\u63a8\u8350",
    ],
    "conclusion": [
        r"(?i)#+\s*conclusion",
        r"(?i)^##\s*\u7ed3\u8bba",
        r"(?i)^##\s*\u603b\u7ed3",
    ],
    "references": [
        r"(?i)#+\s*references?",
        r"(?i)^##\s*\u53c2\u8003\u6587\u732e",
        r"(?i)^##\s*\u5f15\u7528",
        r"(?i)^##\s*\u6765\u6e90",
    ],
}

CITATION_PATTERN = re.compile(r"\[\^(\d+)\^\]")
UNCERTAINTY_PATTERN = re.compile(
    r"(?i)(?:\[?!NOTE\]?|\u26a0\ufe0f|\u26a0|\buncertain|\buncertainty|\b\u4e0d\u786e\u5b9a|\b\u5c40\u9650\u6027|\blimitation|\bcaveat|\bdisclaimer)",
    re.IGNORECASE,
)
CODE_BLOCK_PATTERN = re.compile(r"```(\w+)?\n", re.MULTILINE)
TABLE_PATTERN = re.compile(r"\|.*\|.*\|", re.MULTILINE)
TABLE_HEADER_SEPARATOR = re.compile(r"\|[\s:]*-+[-\s:]*\|", re.MULTILINE)


def find_section(text: str, section_patterns: List[str]) -> bool:
    """Check if any pattern matches the text."""
    for pattern in section_patterns:
        if re.search(pattern, text):
            return True
    return False


def check_structure_completeness(report_text: str) -> Tuple[float, List[str], Dict]:
    """Check if all required sections are present. Score: 0-20."""
    missing = []
    present = 0
    for section_name, patterns in SECTION_PATTERNS.items():
        if find_section(report_text, patterns):
            present += 1
        else:
            missing.append(section_name)

    score = (present / len(REQUIRED_SECTIONS)) * 20
    findings = []
    if missing:
        findings.append(f"Missing sections: {', '.join(missing)}")
    else:
        findings.append("All 9 required sections present")

    return round(score, 1), findings, {
        "required_sections_present": present,
        "missing_sections": missing,
    }


def check_citation_quality(report_text: str) -> Tuple[float, List[str], Dict]:
    """Check citation format and count. Score: 0-20."""
    citations = CITATION_PATTERN.findall(report_text)
    citation_count = len(citations)

    findings = []
    score = 0.0

    # Check citation count (max 10 points)
    if citation_count >= 10:
        score += 10
        findings.append(f"Good citation count: {citation_count}")
    elif citation_count >= 5:
        score += 7
        findings.append(f"Adequate citation count: {citation_count}")
    elif citation_count >= 1:
        score += 3
        findings.append(f"Low citation count: {citation_count}")
    else:
        findings.append("No citations found")

    # Check citation format (max 10 points)
    invalid_citations = []
    all_refs = re.findall(r"\[\^.*?\^\]", report_text)
    for ref in all_refs:
        if not CITATION_PATTERN.match(ref):
            invalid_citations.append(ref)

    if not invalid_citations:
        score += 10
        findings.append("All citations use correct [^N^] format")
    else:
        deduction = min(10, len(invalid_citations) * 2)
        score += (10 - deduction)
        findings.append(f"Invalid citation formats found: {invalid_citations[:5]}")

    valid_citations = citation_count
    return round(max(0, score), 1), findings, {
        "valid_citations": valid_citations,
        "invalid_citations": invalid_citations,
    }


def check_uncertainty_annotation(report_text: str) -> Tuple[float, List[str], Dict]:
    """Check for uncertainty annotations. Score: 0-15."""
    matches = UNCERTAINTY_PATTERN.findall(report_text)
    annotation_count = len(matches)

    findings = []
    score = 0.0

    # Check for explicit uncertainty annotations (blockquotes with NOTE)
    explicit_notes = len(re.findall(r">\s*\[!NOTE.*?\].*?\n", report_text, re.DOTALL))
    if explicit_notes > 0:
        score += 8
        findings.append(f"Found {explicit_notes} explicit uncertainty annotations")
    else:
        findings.append("No explicit [!NOTE] uncertainty annotations")

    # Check for general uncertainty language
    if annotation_count >= 3:
        score += 7
        findings.append(f"Adequate uncertainty language usage: {annotation_count} matches")
    elif annotation_count >= 1:
        score += 4
        findings.append(f"Minimal uncertainty language: {annotation_count} matches")
    else:
        findings.append("No uncertainty indicators found")

    return round(min(15, score), 1), findings, {
        "annotations_found": annotation_count,
        "explicit_note_blocks": explicit_notes,
    }


def check_format_consistency(report_text: str) -> Tuple[float, List[str], Dict]:
    """Check format consistency (code blocks, tables). Score: 0-15."""
    findings = []
    score = 0.0

    # Check code blocks for language tags
    code_blocks = CODE_BLOCK_PATTERN.findall(report_text)
    total_code_blocks = len(code_blocks)
    code_with_lang = sum(1 for cb in code_blocks if cb.strip())
    code_without_lang = total_code_blocks - code_with_lang

    if total_code_blocks == 0:
        score += 7  # No code blocks, neutral
        findings.append("No code blocks in report")
    elif code_without_lang == 0:
        score += 7
        findings.append(f"All {total_code_blocks} code blocks have language tags")
    else:
        ratio = code_with_lang / total_code_blocks
        score += round(ratio * 7, 1)
        findings.append(
            f"{code_without_lang}/{total_code_blocks} code blocks missing language tags"
        )

    # Check tables for headers
    table_rows = TABLE_PATTERN.findall(report_text)
    table_separators = TABLE_HEADER_SEPARATOR.findall(report_text)
    total_tables = max(len(table_separators), len(table_rows) // 3 if table_rows else 0)

    if total_tables == 0:
        score += 8  # No tables, neutral
        findings.append("No tables in report")
    elif len(table_separators) >= 1:
        score += 8
        findings.append(f"All tables appear to have proper headers ({len(table_separators)} tables)")
    else:
        findings.append("Tables found without proper header separators")

    return round(min(15, score), 1), findings, {
        "code_blocks_with_language": code_with_lang,
        "code_blocks_without_language": code_without_lang,
        "tables_with_header": len(table_separators),
        "tables_without_header": max(0, total_tables - len(table_separators)),
    }


def check_content_richness(report_text: str) -> Tuple[float, List[str], Dict]:
    """Check content richness (word count, paragraphs). Score: 0-15."""
    findings = []
    score = 0.0

    # Word count
    words = report_text.split()
    word_count = len(words)

    if word_count >= 2000:
        score += 8
        findings.append(f"Excellent word count: {word_count}")
    elif word_count >= 1000:
        score += 6
        findings.append(f"Good word count: {word_count}")
    elif word_count >= 500:
        score += 4
        findings.append(f"Acceptable word count: {word_count}")
    else:
        score += 2
        findings.append(f"Low word count: {word_count}")

    # Paragraph count
    paragraphs = [p.strip() for p in report_text.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs)

    if paragraph_count >= 10:
        score += 7
        findings.append(f"Good paragraph structure: {paragraph_count} paragraphs")
    elif paragraph_count >= 5:
        score += 5
        findings.append(f"Adequate paragraphs: {paragraph_count}")
    else:
        score += 2
        findings.append(f"Few paragraphs: {paragraph_count}")

    return round(min(15, score), 1), findings, {}


def check_traceability(
    report_text: str, evidence_map_path: Optional[str]
) -> Tuple[float, List[str], Dict]:
    """Check traceability to evidence map. Score: 0-15."""
    findings = []
    score = 0.0

    # Check if evidence map reference exists in report
    has_evidence_ref = bool(
        re.search(r"(?i)evidence.?map|evidence.?id|EVD-\\d+", report_text)
    )

    evidence_map_references = 0
    if evidence_map_path and os.path.exists(evidence_map_path):
        try:
            with open(evidence_map_path, "r", encoding="utf-8") as f:
                evidence_map = json.load(f)
            evidence_ids = set()
            if isinstance(evidence_map, list):
                for item in evidence_map:
                    if isinstance(item, dict) and "evidence_id" in item:
                        evidence_ids.add(item["evidence_id"])
                    elif isinstance(item, str):
                        evidence_ids.add(item)
            elif isinstance(evidence_map, dict):
                for key in ["evidence_map", "evidence", "sources", "items"]:
                    if key in evidence_map:
                        items = evidence_map[key]
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict):
                                    eid = item.get("evidence_id", item.get("id", ""))
                                    if eid:
                                        evidence_ids.add(eid)

            # Check how many evidence IDs are referenced
            for eid in evidence_ids:
                if eid in report_text:
                    evidence_map_references += 1

            if evidence_ids:
                ref_ratio = evidence_map_references / len(evidence_ids)
                if ref_ratio >= 0.5:
                    score += 10
                    findings.append(
                        f"Good evidence traceability: {evidence_map_references}/{len(evidence_ids)} references"
                    )
                elif ref_ratio > 0:
                    score += 5
                    findings.append(
                        f"Partial evidence traceability: {evidence_map_references}/{len(evidence_ids)} references"
                    )
                else:
                    findings.append("No evidence IDs referenced in report")
            else:
                findings.append("Evidence map exists but no IDs found")

        except (json.JSONDecodeError, IOError) as e:
            findings.append(f"Could not read evidence map: {e}")
            score += 3
    else:
        findings.append("No evidence map provided")
        if has_evidence_ref:
            score += 5
            findings.append("Report references evidence (but map not available)")

    # Check for reference section with actual citations (5 points)
    ref_section = re.search(
        r"(?i)#+\s*references?.*?\n(.*?)(?=\n#+\s|\Z)", report_text, re.DOTALL
    )
    if ref_section:
        ref_content = ref_section.group(1)
        if len(ref_content.strip()) > 50:
            score += 5
            findings.append("References section has substantive content")
        else:
            score += 2
            findings.append("References section is sparse")
    else:
        findings.append("No references section found")

    return round(min(15, score), 1), findings, {
        "evidence_map_references": evidence_map_references
    }


def compute_stats(report_text: str) -> Dict:
    """Compute basic statistics about the report."""
    words = report_text.split()
    paragraphs = [p.strip() for p in report_text.split("\n\n") if p.strip()]
    citations = CITATION_PATTERN.findall(report_text)
    code_blocks = CODE_BLOCK_PATTERN.findall(report_text)
    tables_sep = TABLE_HEADER_SEPARATOR.findall(report_text)
    uncertainty_matches = UNCERTAINTY_PATTERN.findall(report_text)

    return {
        "word_count": len(words),
        "paragraph_count": len(paragraphs),
        "citation_count": len(citations),
        "code_block_count": len(code_blocks),
        "table_count": len(tables_sep),
        "uncertainty_annotation_count": len(uncertainty_matches),
    }


def assess_quality(
    report_path: str,
    evidence_map_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Dict:
    """Main quality assessment function."""
    if not os.path.exists(report_path):
        return {
            "error": f"Report file not found: {report_path}",
            "report_id": Path(report_path).stem,
            "version": "1.5",
            "timestamp": "",
            "total_score": 0,
            "passed_threshold": False,
        }

    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    stats = compute_stats(report_text)

    struct_score, struct_findings, struct_extra = check_structure_completeness(report_text)
    cite_score, cite_findings, cite_extra = check_citation_quality(report_text)
    unc_score, unc_findings, unc_extra = check_uncertainty_annotation(report_text)
    fmt_score, fmt_findings, fmt_extra = check_format_consistency(report_text)
    rich_score, rich_findings, _ = check_content_richness(report_text)
    trace_score, trace_findings, trace_extra = check_traceability(report_text, evidence_map_path)

    total_score = round(
        struct_score + cite_score + unc_score + fmt_score + rich_score + trace_score, 1
    )

    result = {
        "report_id": Path(report_path).stem,
        "version": "1.5",
        "timestamp": _iso_timestamp(),
        "word_count": stats["word_count"],
        "section_count": len(REQUIRED_SECTIONS) - struct_extra.get("missing_sections", []).__len__(),
        "citation_count": stats["citation_count"],
        "paragraph_count": stats["paragraph_count"],
        "code_block_count": stats["code_block_count"],
        "table_count": stats["table_count"],
        "uncertainty_annotation_count": stats["uncertainty_annotation_count"],
        "quality_dimensions": {
            "structure_completeness": {
                "score": struct_score,
                "findings": struct_findings,
                **struct_extra,
            },
            "citation_quality": {
                "score": cite_score,
                "findings": cite_findings,
                **cite_extra,
            },
            "uncertainty_annotation": {
                "score": unc_score,
                "findings": unc_findings,
                **unc_extra,
            },
            "format_consistency": {
                "score": fmt_score,
                "findings": fmt_findings,
                **fmt_extra,
            },
            "content_richness": {
                "score": rich_score,
                "findings": rich_findings,
            },
            "traceability": {
                "score": trace_score,
                "findings": trace_findings,
                **trace_extra,
            },
        },
        "total_score": total_score,
        "passed_threshold": total_score >= 70,
        "threshold_used": 70,
        "metadata": {
            "assessed_by": "check_report_quality.py v1.5",
            "assessment_method": "automated",
        },
    }

    # Write output
    if output_path:
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Quality report written to: {output_path}")

    return result


def _iso_timestamp() -> str:
    """Return current ISO-8601 timestamp."""
    import datetime
    return datetime.datetime.now().isoformat()


def main():
    parser = argparse.ArgumentParser(
        description="Report Quality Check Engine (Non-LLM)"
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to the report markdown file",
    )
    parser.add_argument(
        "--evidence-map",
        dest="evidence_map",
        default=None,
        help="Path to evidence-map.json for traceability check",
    )
    parser.add_argument(
        "--output",
        default="report-quality.json",
        help="Output path for quality report JSON (default: report-quality.json)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output the JSON result to stdout",
    )

    args = parser.parse_args()

    result = assess_quality(
        report_path=args.report,
        evidence_map_path=args.evidence_map,
        output_path=args.output,
    )

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"\n{'='*60}")
        print(f"  Report Quality Assessment: {result['report_id']}")
        print(f"{'='*60}")
        print(f"  Word Count:        {result['word_count']}")
        print(f"  Paragraphs:        {result['paragraph_count']}")
        print(f"  Citations:         {result['citation_count']}")
        print(f"  Code Blocks:       {result['code_block_count']}")
        print(f"  Tables:            {result['table_count']}")
        print(f"  Uncertainty Notes: {result['uncertainty_annotation_count']}")
        print(f"\n  --- Scores ---")
        for dim, data in result["quality_dimensions"].items():
            print(f"  {dim:30s}: {data['score']:5.1f}")
        print(f"\n  TOTAL SCORE: {result['total_score']}/100")
        print(f"  THRESHOLD:   {result['threshold_used']}")
        print(
            f"  RESULT:      {'PASS' if result['passed_threshold'] else 'FAIL'}"
        )
        print(f"{'='*60}")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
