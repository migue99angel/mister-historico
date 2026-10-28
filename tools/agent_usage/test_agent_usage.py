"""Tests for the local agent usage audit. All fixtures are synthetic."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import agent_usage as au


def write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def claude_assistant(msg_id, ts, tools=(), model="claude-opus-5-5", inp=10, out=5, read=1000, write=100, branch="main", cwd="/r/mister-historico"):
    content = [{"type": "tool_use", "id": f"{msg_id}-{i}", "name": n, "input": a} for i, (n, a) in enumerate(tools)]
    return {
        "type": "assistant", "timestamp": ts, "requestId": f"req-{msg_id}", "gitBranch": branch, "cwd": cwd,
        "message": {"id": msg_id, "model": model, "content": content,
                    "usage": {"input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": read, "cache_creation_input_tokens": write}},
    }


def codex_token_count(ts, total, inp, cached, out, used=None, resets=None):
    payload = {"type": "token_count", "info": {
        "total_token_usage": {"total_tokens": total},
        "last_token_usage": {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out, "total_tokens": inp + out}}}
    if used is not None:
        payload["rate_limits"] = {"limit_id": "codex", "plan_type": "plus",
                                  "primary": {"used_percent": used, "window_minutes": 300, "resets_at": resets}}
    return {"timestamp": ts, "type": "event_msg", "payload": payload}


def codex_call(ts, name, args):
    return {"timestamp": ts, "type": "response_item", "payload": {"type": "function_call", "name": name, "arguments": json.dumps(args)}}


class ClaudeParsingTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_message_split_over_several_lines_is_counted_once(self):
        line = claude_assistant("m1", "2026-10-28T10:00:00Z")
        path = write_jsonl(self.dir / "s1.jsonl", [line, line])
        session = au.parse_claude(path)
        self.assertEqual(len(session.calls), 1)

    def test_context_of_a_call_includes_cache_reads_and_writes(self):
        path = write_jsonl(self.dir / "s1.jsonl", [claude_assistant("m1", "2026-10-28T10:00:00Z", inp=10, read=1000, write=100)])
        call = au.parse_claude(path).calls[0]
        self.assertEqual(call.context, 1110)
        self.assertEqual(call.total, 1115)

    def test_subagent_file_is_a_separate_session_linked_to_its_parent(self):
        write_jsonl(self.dir / "p1.jsonl", [claude_assistant("m1", "2026-10-28T10:00:00Z")])
        write_jsonl(self.dir / "p1" / "subagents" / "agent-a1.jsonl", [claude_assistant("m2", "2026-10-28T10:01:00Z")])
        sessions = {s.id: s for s in au.load_claude_sessions([self.dir])}
        self.assertEqual(set(sessions), {"p1", "p1/agent-a1"})
        self.assertEqual(sessions["p1/agent-a1"].parent, "p1")

    def test_call_that_only_sleeps_or_checks_ci_is_a_wait_call(self):
        path = write_jsonl(self.dir / "s1.jsonl", [
            claude_assistant("m1", "2026-10-28T10:00:00Z", tools=[("Bash", {"command": "sleep 60 && gh pr checks 12"})]),
            claude_assistant("m2", "2026-10-28T10:01:00Z", tools=[("Bash", {"command": "sleep 5"}), ("Edit", {"file_path": "x"})]),
        ])
        self.assertEqual([c.wait for c in au.parse_claude(path).calls], [True, False])


class CodexParsingTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def rollout(self, rows):
        meta = {"timestamp": "2026-10-28T09:59:00Z", "type": "session_meta",
                "payload": {"id": "c1", "cwd": "/r/mister-historico", "git": {"branch": "task/T3.6-api"}}}
        ctx = {"timestamp": "2026-10-28T09:59:01Z", "type": "turn_context", "payload": {"model": "gpt-6.1-sol"}}
        return au.parse_codex(write_jsonl(self.dir / "rollout-c1.jsonl", [meta, ctx, *rows]))

    def test_repeated_token_count_with_unchanged_total_is_counted_once(self):
        tc = codex_token_count("2026-10-28T10:00:00Z", 1100, 1000, 900, 100)
        session = self.rollout([tc, tc])
        self.assertEqual(len(session.calls), 1)

    def test_cached_input_is_separated_from_new_input(self):
        call = self.rollout([codex_token_count("2026-10-28T10:00:00Z", 1100, 1000, 900, 100)]).calls[0]
        self.assertEqual((call.fresh_input, call.cache_read, call.output, call.context), (100, 900, 100, 1000))
        self.assertEqual(call.model, "gpt-6.1-sol")

    def test_calls_that_only_wait_for_agents_or_ci_are_wait_calls(self):
        session = self.rollout([
            codex_call("2026-10-28T10:00:00Z", "wait_agent", {"timeout_ms": 60000}),
            codex_token_count("2026-10-28T10:01:00Z", 1100, 1000, 900, 100),
            codex_call("2026-10-28T10:02:00Z", "exec", {"code": "await tools.exec_command({cmd: 'gh pr checks 7'})"}),
            codex_token_count("2026-10-28T10:03:00Z", 2200, 1000, 900, 100),
            codex_call("2026-10-28T10:04:00Z", "exec", {"code": "await tools.exec_command({cmd: 'uv run pytest'})"}),
            codex_token_count("2026-10-28T10:05:00Z", 3300, 1000, 900, 100),
        ])
        self.assertEqual([c.wait for c in session.calls], [True, True, False])

    def test_quota_snapshots_come_from_the_rate_limits_codex_writes(self):
        session = self.rollout([codex_token_count("2026-10-28T10:00:00Z", 1100, 1000, 900, 100, used=42.0, resets=1793208210)])
        snap = session.quota[0]
        self.assertEqual((snap["used_percent"], snap["resets_at"], snap["window_minutes"]), (42.0, 1793208210, 300))


class MetricsTest(unittest.TestCase):
    def test_percentile_uses_nearest_rank(self):
        self.assertEqual(au.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90), 9)
        self.assertIsNone(au.percentile([], 50))

    def test_active_time_ignores_gaps_longer_than_the_idle_threshold(self):
        ts = [datetime(2026, 10, 28, 10, m, tzinfo=timezone.utc) for m in (0, 2, 4, 40, 41)]
        self.assertEqual(au.active_minutes(ts, idle_gap_min=5), 5)

    def test_session_metrics_report_wait_share_and_context_spread(self):
        calls = [au.Call(datetime(2026, 10, 28, 10, i, tzinfo=timezone.utc), "m", 0, 10, ctx, 0, wait=i == 0) for i, ctx in enumerate([100, 200, 300, 400])]
        m = au.session_metrics(au.Session("s", "claude", calls=calls))
        self.assertEqual((m["calls"], m["wait_calls"], m["ctx_max"], m["ctx_median"]), (4, 1, 400, 200))
        self.assertEqual(m["wait_share"], 0.25)


if __name__ == "__main__":
    unittest.main()
