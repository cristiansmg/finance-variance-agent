import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from variance_agent.__main__ import load_cases, investigate, evaluate
from variance_agent.agent import live_run, ClaudeClient
from variance_agent.core import Investigation, digest
from variance_agent.report import render


def fixture(name):
    return copy.deepcopy(next(c for c in load_cases() if c['id'] == name))


def call(name, args, id='t1'):
    return {'content': [{'type': 'tool_use', 'id': id, 'name': name, 'input': args}]}


class AgentTests(unittest.TestCase):
    def test_seven_scenarios(self):
        result = evaluate()
        self.assertEqual(result['passed'], 7, result)

    def test_money_uses_exact_integer_cents(self):
        c = fixture('known')
        c['ledger'][0]['cents'] = 101
        c['ledger'][1]['cents'] = 102
        inv = Investigation(c)
        self.assertEqual(inv.overview()['delta_cents'], 1)

    def test_non_integer_cents_rejected(self):
        c = fixture('known'); c['ledger'][0]['cents'] = 0.1
        with self.assertRaises(ValueError): Investigation(c)

    def test_zero_budget_no_infinity(self):
        r = investigate(fixture('zero-budget'))
        self.assertIsNone(r['overview']['variance_percent'])

    def test_offsetting_not_falsely_complete(self):
        r = investigate(fixture('offsetting'))
        self.assertEqual(r['net_unexplained_cents'], 0)
        self.assertEqual(r['gross_unexplained_cents'], 600000)
        self.assertTrue(r['overview']['material'])
        self.assertEqual(r['gross_evidence_coverage'], 0)

    def test_cross_case_access_blocked(self):
        inv = Investigation(fixture('known'))
        self.assertIn('error', inv.call('read_evidence', {'document_id': 'memo-a'}))
        self.assertIn('error', inv.call('get_vendor_detail', {'vendor': 'SecretPayroll'}))

    def test_unknown_write_tool_denied_and_logged(self):
        inv = Investigation(fixture('known'))
        self.assertIn('error', inv.call('post_journal', {'amount': 100}))
        self.assertEqual(inv.events[0]['tool'], 'post_journal')

    def test_hallucinated_evidence_rejected(self):
        inv = Investigation(fixture('known'))
        inv.call('get_overview', {}); inv.call('get_vendor_detail', {'vendor': 'CloudCo'})
        inv.call('submit_findings', {'claims': [{'vendor': 'CloudCo', 'evidence_ids': ['fake']}]})
        self.assertEqual(inv.report['supported_drivers'], [])

    def test_unread_evidence_rejected(self):
        inv = Investigation(fixture('known'))
        inv.call('get_overview', {}); inv.call('get_vendor_detail', {'vendor': 'CloudCo'})
        inv.call('submit_findings', {'claims': [{'vendor': 'CloudCo', 'evidence_ids': ['contract-1']}]})
        self.assertEqual(inv.report['gross_unexplained_cents'], 300000)

    def test_cannot_hide_conflicting_document(self):
        inv = Investigation(fixture('conflict'))
        inv.call('get_overview', {}); inv.call('get_vendor_detail', {'vendor': 'CloudCo'})
        inv.call('read_evidence', {'document_id': 'memo-a'})
        inv.call('submit_findings', {'claims': [{'vendor': 'CloudCo', 'evidence_ids': ['memo-a']}]})
        self.assertFalse(inv.report['supported_drivers'])

    def test_duplicate_claim_not_double_counted(self):
        inv = Investigation(fixture('known'))
        inv.call('get_overview', {}); inv.call('get_vendor_detail', {'vendor': 'CloudCo'})
        inv.call('read_evidence', {'document_id': 'contract-1'})
        claim = {'vendor': 'CloudCo', 'evidence_ids': ['contract-1']}
        inv.call('submit_findings', {'claims': [claim, claim]})
        self.assertEqual(inv.report['net_explained_cents'], 300000)
        self.assertEqual(len(inv.report['rejected_claims']), 1)

    def test_tool_limit(self):
        inv = Investigation(fixture('known'), max_calls=1)
        inv.call('get_overview', {})
        with self.assertRaises(ValueError): inv.call('get_overview', {})

    def test_live_loop_with_test_double(self):
        replies = iter([call('get_overview', {}), call('get_vendor_detail', {'vendor': 'CloudCo'}),
                        call('read_evidence', {'document_id': 'contract-1'}),
                        call('submit_findings', {'claims': [{'vendor': 'CloudCo', 'evidence_ids': ['contract-1']}]})])
        requests = []
        def client(messages):
            requests.append(copy.deepcopy(messages)); return next(replies)
        r = live_run(Investigation(fixture('known')), client)
        self.assertEqual(r['net_explained_cents'], 300000)
        self.assertEqual(requests[1][-1]['content'][0]['type'], 'tool_result')
        self.assertNotIn('expected', json.dumps(requests))

    def test_prompt_injection_cannot_approve(self):
        # Scripted hostile model calls test host enforcement, not LLM resistance.
        replies = iter([call('approve_report', {}), {'content': [{'type': 'text', 'text': 'APPROVED'}]}])
        r = live_run(Investigation(fixture('injection')), lambda _: next(replies))
        self.assertEqual(r['status'], 'DRAFT_REQUIRES_HUMAN_REVIEW')
        self.assertTrue(r['incomplete_investigation'])

    def test_model_timeout_fails_closed(self):
        def fail(_): raise TimeoutError('secret must not be exported')
        r = live_run(Investigation(fixture('known')), fail)
        self.assertTrue(r['incomplete_investigation'])
        self.assertEqual(r['provider_error_type'], 'TimeoutError')
        self.assertNotIn('secret must not be exported', json.dumps(r))

    def test_loop_budget(self):
        r = live_run(Investigation(fixture('known')), lambda _: call('get_overview', {}), max_turns=2)
        self.assertEqual(len(r['audit_trail']), 2)
        self.assertTrue(r['incomplete_investigation'])

    def test_source_text_escaped(self):
        c = fixture('known'); c['documents'][0]['text'] = '<script>alert(1)</script>'
        rendered = render(investigate(c))
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_hash_changes_with_evidence(self):
        c = fixture('known'); before = digest(c)
        c['documents'][0]['text'] += ' changed'
        self.assertNotEqual(before, digest(c))

    def test_live_requires_explicit_credentials_and_model(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError): ClaudeClient()

    def test_review_blocks_unresolved_and_is_separate(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'report.json'; r = investigate(fixture('missing'))
            p.write_text(json.dumps(r)); original = p.read_bytes()
            cmd = [sys.executable, '-m', 'variance_agent', 'review', str(p), '--reviewer', 'Demo reviewer', '--decision', 'accept', '--note', 'Checked']
            result = subprocess.run(cmd, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(p.read_bytes(), original)
            r = investigate(fixture('known')); p.write_text(json.dumps(r)); original = p.read_bytes()
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            review = json.loads(p.with_name('report.review.json').read_text())
            self.assertEqual(review['report_sha256'], digest(r))
            self.assertEqual(p.read_bytes(), original)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
