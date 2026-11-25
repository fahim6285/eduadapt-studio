#!/usr/bin/env python3
"""Optional, input-defined exam inventory audit. Python 3 stdlib only.

Item = group of question options; select_count = number answered from that group.
It can model answer-all (one single-option item per question), either/or
(one item, select_count 1 and two options), or answer-any N (select_count N).
No fixed exam format, marks or subject is encoded.
"""
import argparse
import itertools
import json
import math
import sys
from pathlib import Path


def numeric(v):
    return type(v) in (int, float) and math.isfinite(v) and v >= 0


def audit(data):
    errors, warnings = [], []
    ids = set()
    total_low = 0.0
    total_high = 0.0
    sections = []
    covered_units, covered_outcomes = set(), set()
    allowed_units = set(data.get('units', [])) if isinstance(data.get('units'), list) else None
    allowed_outcomes = set(data.get('outcomes', [])) if isinstance(data.get('outcomes'), list) else None
    expected = data.get('expected_total_marks')
    if not numeric(expected):
        errors.append('expected_total_marks must be a finite nonnegative number')
    all_sections = data.get('sections')
    if not isinstance(all_sections, list) or not all_sections:
        errors.append('sections must be a non-empty list')
        all_sections = []
    sec_ids = set()
    for si, sec in enumerate(all_sections):
        label = str(sec.get('id', '')).strip() if isinstance(sec, dict) else ''
        if not label:
            errors.append(f'Section {si+1}: missing id')
            label = f'index-{si+1}'
        if label in sec_ids:
            errors.append(f'Duplicate section ID: {label}')
        sec_ids.add(label)
        items = sec.get('items') if isinstance(sec, dict) else None
        if not isinstance(items, list) or not items:
            errors.append(f'{label}: items must be a non-empty list')
            continue
        section_low = 0.0
        section_high = 0.0
        item_ids = set()
        for ii, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f'{label} item {ii+1}: must be an object')
                continue
            iid = str(item.get('id', '')).strip()
            if not iid:
                errors.append(f'{label} item {ii+1}: missing item id')
                iid = f'index-{ii+1}'
            if iid in item_ids:
                errors.append(f'{label}: duplicated item ID {iid}')
            item_ids.add(iid)
            opts = item.get('options')
            n = item.get('select_count')
            if not isinstance(opts, list) or not opts:
                errors.append(f'{label}/{iid}: nonempty options list required')
                continue
            if type(n) is not int or not 1 <= n <= len(opts):
                errors.append(f'{label}/{iid}: select_count must be between 1 and option count')
                continue
            marks = []
            for oi, option in enumerate(opts):
                if not isinstance(option, dict):
                    errors.append(f'{label}/{iid} option {oi+1}: must be an object')
                    continue
                qid = str(option.get('id', '')).strip()
                if not qid:
                    errors.append(f'{label}/{iid} option {oi+1}: missing question id')
                elif qid in ids:
                    errors.append(f'Duplicate question ID: {qid}')
                else:
                    ids.add(qid)
                mark = option.get('marks')
                if not numeric(mark):
                    errors.append(f'{label}/{iid}/{qid or oi+1}: invalid marks')
                else:
                    marks.append(float(mark))
                for key, dest, allowed in [('unit',covered_units,allowed_units),('outcome',covered_outcomes,allowed_outcomes)]:
                    val = option.get(key)
                    if val is None or str(val).strip() == '':
                        if allowed is not None and len(allowed) > 0:
                            warnings.append(f'{label}/{iid}/{qid or oi+1}: {key} mapping missing')
                    else:
                        dest.add(str(val))
                        if allowed is not None and str(val) not in allowed:
                            errors.append(f'{label}/{iid}/{qid or oi+1}: {key} {val!r} not in declared list')
            if len(marks) != len(opts):
                continue
            lo = sum(sorted(marks)[:n])
            hi = sum(sorted(marks, reverse=True)[:n])
            if abs(lo-hi)>1e-8:
                errors.append(f'{label}/{iid}: selectable choices have unequal attainable marks ({lo:g}–{hi:g})')
            section_low += lo
            section_high += hi
        sections.append({'id':label,'minimum_attainable_marks':section_low,'maximum_attainable_marks':section_high})
        total_low += section_low
        total_high += section_high
    if numeric(expected):
        if abs(total_low - expected)>1e-8 or abs(total_high-expected)>1e-8:
            errors.append(f'Attainable total ({total_low:g}–{total_high:g}) differs from expected_total_marks ({expected:g})')
    if allowed_units is not None:
        absent = sorted(allowed_units-covered_units)
        if absent:
            warnings.append('Declared syllabus units with no printed question mapping: '+', '.join(absent))
    if allowed_outcomes is not None:
        absent = sorted(allowed_outcomes-covered_outcomes)
        if absent:
            warnings.append('Declared outcomes with no printed question mapping: '+', '.join(absent))
    return {'status':'fail' if errors else 'pass','errors':errors,'warnings':warnings,'sections':sections,
            'minimum_attainable_total':total_low,'maximum_attainable_total':total_high,
            'printed_question_count':len(ids),'covered_units':sorted(covered_units),
            'covered_outcomes':sorted(covered_outcomes),
            'notice':'Structural audit only; verify correctness, regulation compliance, content quality and layout separately.'}


def main():
    p = argparse.ArgumentParser(description='Audit a user-defined question/choice inventory and mark totals')
    p.add_argument('inventory',type=Path)
    p.add_argument('--report',type=Path,help='Save JSON report')
    args=p.parse_args()
    try:
        data=json.loads(args.inventory.read_text(encoding='utf-8'))
        result=audit(data)
    except (OSError,ValueError,TypeError) as ex:
        print(json.dumps({'status':'fail','errors':[f'Input error: {ex}']},indent=2))
        return 2
    print(json.dumps(result,indent=2,ensure_ascii=False))
    if args.report:
        args.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return 0 if result['status']=='pass' else 1


if __name__=='__main__':
    sys.exit(main())

