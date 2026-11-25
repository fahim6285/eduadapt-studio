"""Execute: python -m unittest discover -s tests -v (in skill root)."""
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_assessment import audit as exam_audit
from audit_plan import audit as plan_audit

class AssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ex=json.loads((ROOT/'examples/neutral_assessment.json').read_text())
        cls.plan=json.loads((ROOT/'examples/neutral_lesson_plan.json').read_text())
    def test_valid_alternatives_and_choose_two(self):
        result=exam_audit(self.ex)
        self.assertEqual(result['status'],'pass',result)
        self.assertEqual(result['minimum_attainable_total'],14)
        self.assertEqual(result['maximum_attainable_total'],14)
        self.assertEqual(result['printed_question_count'],6)
    def test_detect_unequal_alternative(self):
        ex=copy.deepcopy(self.ex)
        ex['sections'][0]['items'][0]['options'][0]['marks']=5
        result=exam_audit(ex)
        self.assertEqual(result['status'],'fail')
        self.assertTrue(any('unequal' in x for x in result['errors']))
    def test_detect_total_mismatch(self):
        ex=copy.deepcopy(self.ex);ex['expected_total_marks']=18
        result=exam_audit(ex)
        self.assertEqual(result['status'],'fail')
        self.assertTrue(any('differs' in x for x in result['errors']))
    def test_duplicate_question_detected(self):
        ex=copy.deepcopy(self.ex)
        ex['sections'][0]['items'][1]['options'][0]['id']='Q-A'
        self.assertEqual(exam_audit(ex)['status'],'fail')
    def test_syllabus_id_mismatch(self):
        ex=copy.deepcopy(self.ex)
        ex['sections'][0]['items'][1]['options'][0]['unit']='Out-of-scope'
        self.assertEqual(exam_audit(ex)['status'],'fail')
    def test_valid_plan(self):
        out=plan_audit(self.plan)
        self.assertEqual(out['status'],'pass',out)
        self.assertEqual(out['scheduled_time'],6)
        self.assertFalse(out['uncovered_scope'])
    def test_overloaded_plan(self):
        data=copy.deepcopy(self.plan)
        data['lessons'][0]['time']=5
        self.assertEqual(plan_audit(data)['status'],'fail')
    def test_uncovered_scope_warns(self):
        data=copy.deepcopy(self.plan)
        data['lessons'].pop()
        out=plan_audit(data)
        self.assertEqual(out['status'],'pass')
        self.assertIn('Scope-C',out['uncovered_scope'])

if __name__=='__main__':unittest.main()

