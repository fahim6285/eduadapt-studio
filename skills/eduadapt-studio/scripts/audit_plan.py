#!/usr/bin/env python3
"""Optional scope/time audit using only user-defined scope IDs and durations."""
import argparse
import json
import math
import sys
from pathlib import Path


def number(v):
    return type(v) in (float,int) and math.isfinite(v) and v >= 0


def audit(data):
    errors, warnings = [], []
    scope = data.get('declared_scope', [])
    if not isinstance(scope, list) or not scope or any(not isinstance(x,str) or not x.strip() for x in scope):
        errors.append('declared_scope must be a list of scope ID strings')
        scope = []
    if len(scope)!=len(set(scope)):
        errors.append('declared_scope contains duplicate identifiers')
    units = set(scope)
    lessons = data.get('lessons', [])
    if not isinstance(lessons,list) or not lessons:
        errors.append('lessons must be a nonempty list')
        lessons=[]
    seen, taught = set(), set()
    duration = 0.0
    for i, lesson in enumerate(lessons):
        if not isinstance(lesson,dict):
            errors.append(f'lesson {i+1} must be an object')
            continue
        label = str(lesson.get('id','')).strip()
        if not label:
            errors.append(f'lesson {i+1} missing id')
        if label in seen:
            errors.append(f'duplicate lesson ID {label}')
        seen.add(label)
        allotted = lesson.get('time')
        if not number(allotted):
            errors.append(f'{label}: invalid time allocation')
        else:
            duration+=allotted
        covered = lesson.get('scope')
        if not isinstance(covered,list) or not covered:
            warnings.append(f'{label}: scope map is empty')
        else:
            for sid in covered:
                if sid not in units:
                    errors.append(f'{label}: topic {sid!r} not in declared_scope')
                else:taught.add(sid)
    available = data.get('available_time')
    if available is not None:
        if not number(available):errors.append('available_time must be finite nonnegative')
        elif duration>available+1e-8:errors.append(f'Scheduled time {duration:g} exceeds available time {available:g}')
        elif available-duration>1e-8:warnings.append(f'Unallocated time: {available-duration:g} {data.get("time_unit","units")}')
    absent=sorted(units-taught)
    if absent:warnings.append('Declared scope not covered in lesson mapping: '+', '.join(absent))
    return {'status':'fail' if errors else 'pass','errors':errors,'warnings':warnings,
            'scheduled_time':duration,'available_time':available,'time_unit':data.get('time_unit','unspecified'),
            'covered_scope':sorted(taught),'uncovered_scope':absent,
            'notice':'Mapping/time arithmetic only; inspect educational appropriateness and source requirements separately.'}


def main():
    p=argparse.ArgumentParser(description='Audit an input-defined instructional scope/time plan')
    p.add_argument('plan',type=Path)
    p.add_argument('--report',type=Path)
    a=p.parse_args()
    try:result=audit(json.loads(a.plan.read_text(encoding='utf-8')))
    except (OSError,ValueError,TypeError) as ex:
        print(json.dumps({'status':'fail','errors':[f'Input error: {ex}']},indent=2))
        return 2
    print(json.dumps(result,indent=2,ensure_ascii=False))
    if a.report:a.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return 0 if result['status']=='pass' else 1

if __name__=='__main__':
    sys.exit(main())

