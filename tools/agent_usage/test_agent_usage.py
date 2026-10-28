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

    def test_request_repeated_in_several_subagent_files_is_counted_once(self):
        write_jsonl(self.dir / "p1.jsonl", [claude_assistant("m1", "2026-10-28T10:00:00Z")])
        shared = claude_assistant("m2", "2026-10-28T10:01:00Z")
        write_jsonl(self.dir / "p1" / "subagents" / "agent-a1.jsonl", [shared])
        write_jsonl(self.dir / "p1" / "subagents" / "agent-a2.jsonl", [shared, claude_assistant("m3", "2026-10-28T10:02:00Z")])
        calls = sum(len(s.calls) for s in au.load_claude_sessions([self.dir]))
        self.assertEqual(calls, 3)

    def test_call_that_only_sleeps_or_checks_ci_is_a_wait_call(self):
        path = write_jsonl(self.dir / "s1.jsonl", [
            claude_assistant("m1", "2026-10-28T10:00:00Z", tools=[("Bash", {"command": "sleep 60 && gh pr checks 12"})]),
            claude_assistant("m2", "2026-10-28T10:01:00Z", tools=[("Bash", {"command": "sleep 5"}), ("Edit", {"file_path": "x"})]),
        ])
        self.assertEqual([c.wait for c in au.parse_claude(path).calls], [True, False])

    def test_command_that_runs_work_and_then_checks_ci_is_not_a_wait_call(self):
        self.assertFalse(au.is_wait_call([("Bash", json.dumps({"command": "uv run pytest && gh pr checks 107"}))]))
        self.assertTrue(au.is_wait_call([("Bash", json.dumps({"command": "cd /r && sleep 30 && gh pr checks 107 | tail -5"}))]))


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

    def test_exec_cell_with_work_and_a_ci_check_is_not_a_wait_call(self):
        mixed = "await tools.exec_command({cmd: 'uv run pytest'}); await tools.exec_command({cmd: 'gh pr checks 107'})"
        self.assertFalse(au.is_wait_call([("exec", json.dumps({"code": mixed}))]))
        self.assertFalse(au.is_wait_call([("exec", json.dumps({"code": "await tools.exec_command({cmd: 'uv run pytest && gh pr checks 107'})"}))]))

    def test_exec_cell_that_cannot_be_read_is_not_a_wait_call(self):
        self.assertFalse(au.is_wait_call([("exec", json.dumps({"code": "const c = 'gh pr checks 7'; await run(c)"}))]))

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


KNOWN = {"T3.5", "T3.6", "T1.7b", "T4.3", "T4.4", "T4.5", "T4.6"}


class AttributionTest(unittest.TestCase):
    def session(self, branch="main", cwd="/r/mister-historico", prompt=""):
        s = au.Session("s", "claude", prompt=prompt)
        s.branches[branch] += 1
        s.cwds[cwd] += 1
        return s

    def test_task_branch_is_a_direct_attribution(self):
        a = au.attribute(self.session(branch="task/T3.6-api"), KNOWN)
        self.assertEqual((a["tasks"], a["attribution"], a["role"]), (["T3.6"], "directa", "Implementación"))

    def test_task_worktree_is_direct_and_subdeliveries_map_to_their_task(self):
        a = au.attribute(self.session(cwd="/r/mister-historico-T3.5b"), KNOWN)
        self.assertEqual((a["tasks"], a["attribution"]), (["T3.5"], "directa"))

    def test_task_with_its_own_letter_in_tasks_is_kept(self):
        self.assertEqual(au.normalize_task("T1.7b", KNOWN), "T1.7b")

    def test_single_task_named_in_the_prompt_is_inferred(self):
        a = au.attribute(self.session(prompt="Implementa únicamente T4.3 de Míster Histórico"), KNOWN)
        self.assertEqual((a["tasks"], a["attribution"]), (["T4.3"], "inferida"))

    def test_several_tasks_in_the_prompt_are_split_and_flagged_as_estimate(self):
        a = au.attribute(self.session(prompt="Orquesta T4.4, T4.5 y T4.6a"), KNOWN)
        self.assertEqual((a["tasks"], a["attribution"]), (["T4.4", "T4.5", "T4.6"], "repartida"))

    def test_tasks_from_later_user_turns_make_the_session_split(self):
        s = self.session()
        s.add_user_turn("Implementa T4.3")
        s.add_user_turn("Ahora implementa T4.4")
        a = au.attribute(s, KNOWN)
        self.assertEqual((a["tasks"], a["attribution"], a["source"]), (["T4.3", "T4.4"], "repartida", "prompt"))

    def test_session_without_evidence_is_unknown_not_assigned(self):
        a = au.attribute(self.session(prompt="Quiero quitar un MCP"), KNOWN)
        self.assertEqual((a["tasks"], a["attribution"], a["role"]), ([], "desconocida", "Desconocido"))

    def test_manual_override_wins(self):
        a = au.attribute(self.session(branch="task/T3.6-api"), KNOWN, {"tasks": ["ORQ"], "attribution": "directa", "role": "Orquestación"})
        self.assertEqual((a["tasks"], a["role"], a["source"]), (["ORQ"], "Orquestación", "manual"))


class QuotaWindowTest(unittest.TestCase):
    def test_snapshots_with_jittered_reset_belong_to_one_window(self):
        snaps = [
            {"ts": "2026-10-28T13:00:00Z", "limit_id": "codex", "plan": "plus", "used_percent": 10.0, "window_minutes": 300, "resets_at": 1793208200},
            {"ts": "2026-10-28T14:00:00Z", "limit_id": "codex", "plan": "plus", "used_percent": 55.0, "window_minutes": 300, "resets_at": 1793208215},
            {"ts": "2026-10-28T18:00:00Z", "limit_id": "codex", "plan": "plus", "used_percent": 4.0, "window_minutes": 300, "resets_at": 1793226000},
        ]
        windows = au.quota_windows(snaps)
        self.assertEqual([(w["max_used"], w["snapshots"]) for w in windows], [(55.0, 2), (4.0, 1)])
        self.assertEqual(windows[0]["start"], "2026-10-28T12:23:20+00:00")

    def test_window_records_when_the_limit_was_first_reached(self):
        snaps = [{"ts": f"2026-10-28T13:{m:02d}:00Z", "limit_id": "codex", "plan": "plus", "used_percent": u, "window_minutes": 300, "resets_at": 1793208200}
                 for m, u in ((0, 50.0), (10, 99.0), (20, 100.0))]
        self.assertEqual(au.quota_windows(snaps)[0]["first_at_limit"], "2026-10-28T13:10:00Z")


class GithubFieldsTest(unittest.TestCase):
    def test_tool_comes_from_the_pull_request_footer(self):
        self.assertEqual(au.pr_tool("...\n🤖 Generated with Codex"), "Codex")
        self.assertEqual(au.pr_tool("🤖 Generated with [Claude Code](https://claude.com/claude-code)"), "Claude Code")
        self.assertIsNone(au.pr_tool("sin pie"))

    def test_task_comes_from_the_branch(self):
        self.assertEqual(au.task_from_branch("task/CR-T3.5-dated-squads"), "CR-T3.5")
        self.assertEqual(au.task_from_branch("task/T3.5b-use-cases"), "T3.5b")
        self.assertIsNone(au.task_from_branch("task/docs-github-projects"))

    def test_unknown_price_is_not_reported_as_free(self):
        self.assertEqual(au.cost_fields(None), {"cost_usd": None, "cost_estimated": None})
        self.assertEqual(au.cost_fields({"costUSD": 1.5, "models": {"m": {"isFallback": True}}}), {"cost_usd": 1.5, "cost_estimated": True})


class StatuslineTest(unittest.TestCase):
    payload = {"session_id": "s1", "model": {"id": "claude-opus-5-5", "display_name": "Opus 5.5"},
               "context_window": {"used_percentage": 34.4},
               "rate_limits": {"five_hour": {"used_percentage": 23, "resets_at": 1793208210},
                               "seven_day": {"used_percentage": 40, "resets_at": 1793776975}}}

    def test_line_shows_model_context_and_quota(self):
        log = Path(tempfile.mkdtemp()) / "claude-quota.jsonl"
        line = au.statusline(self.payload, log)
        self.assertTrue(line.startswith("Opus 5.5 · ctx 34% · 5h 23% ↻ "), line)
        self.assertTrue(line.endswith(" · 7d 40%"), line)

    def test_quota_is_logged_only_when_it_changes(self):
        log = Path(tempfile.mkdtemp()) / "claude-quota.jsonl"
        au.statusline(self.payload, log)
        au.statusline(self.payload, log)
        changed = json.loads(json.dumps(self.payload))
        changed["rate_limits"]["five_hour"]["used_percentage"] = 24
        au.statusline(changed, log)
        rows = [json.loads(l) for l in log.read_text().splitlines()]
        self.assertEqual([r["five_hour_used"] for r in rows], [23, 24])

    def test_missing_quota_is_shown_as_unavailable(self):
        log = Path(tempfile.mkdtemp()) / "claude-quota.jsonl"
        line = au.statusline({"model": {"display_name": "Opus 5.5"}}, log)
        self.assertEqual(line, "Opus 5.5 · 5h n/d")
        self.assertFalse(log.exists())


class CollectLogicTest(unittest.TestCase):
    cutoff = datetime(2026, 10, 28, 15, 32, 1, tzinfo=timezone.utc)

    def test_period_uses_timestamps_not_the_day(self):
        self.assertEqual(au.period("2026-10-28T09:00:00+00:00", "2026-10-28T12:00:00+00:00", self.cutoff), "antes")
        self.assertEqual(au.period("2026-10-28T16:00:00+00:00", "2026-10-28T17:00:00+00:00", self.cutoff), "después")
        self.assertEqual(au.period("2026-10-28T14:00:00+00:00", "2026-10-28T17:00:00+00:00", self.cutoff), "cruza")

    def test_tasks_mentioned_in_later_user_turns_are_collected(self):
        d = Path(tempfile.mkdtemp())
        rows = [
            {"type": "user", "timestamp": "2026-10-28T10:00:00Z", "message": {"content": "Implementa T4.3"}},
            claude_assistant("m1", "2026-10-28T10:01:00Z"),
            {"type": "user", "timestamp": "2026-10-28T11:00:00Z", "message": {"content": [{"type": "text", "text": "Ahora sigue con T4.4"}]}},
            {"type": "user", "timestamp": "2026-10-28T11:00:01Z", "message": {"content": [{"type": "tool_result", "content": "T9.9"}]}},
        ]
        session = au.parse_claude(write_jsonl(d / "s.jsonl", rows))
        self.assertEqual((session.user_turns, sorted(session.mentioned)), (2, ["T4.3", "T4.4"]))

    def test_split_tokens_are_kept_apart_from_direct_ones(self):
        rows = [
            {"tasks": ["T4.4"], "attribution": "directa", "role": "Implementación", "total": 100, "tool": "claude", "start": "2026-10-28T10:00:00+00:00"},
            {"tasks": ["T4.4", "T4.5"], "attribution": "repartida", "role": "Revisión", "total": 50, "tool": "codex", "start": "2026-10-28T09:00:00+00:00"},
        ]
        tasks = {t["task"]: t for t in au.aggregate_tasks(rows, [], {})}
        self.assertEqual((tasks["T4.4"]["tokens_directa"], tasks["T4.4"]["tokens_repartida_est"]), (100, 25))
        self.assertEqual(tasks["T4.4"]["first_session"], "2026-10-28T09:00:00+00:00")

    def test_task_state_and_review_rounds_come_from_its_pull_requests(self):
        prs = [{"task": "T4.4", "number": 72, "state": "MERGED", "created": "2026-10-28T11:00:00Z", "merged": "2026-10-28T13:00:00Z",
                "review_verdicts": 2, "ci_failures": 1, "tool": "Claude Code"}]
        rows = [{"tasks": ["T4.4"], "attribution": "directa", "role": "Implementación", "total": 1, "tool": "claude", "start": "2026-10-28T10:00:00+00:00"}]
        task = au.aggregate_tasks(rows, prs, {"T4.4": "M"})[0]
        self.assertEqual((task["state"], task["review_verdicts"], task["ci_failures"], task["size"]), ("integrada", 2, 1, "M"))
        self.assertEqual((task["hours_to_pr"], task["hours_to_merge"]), (1.0, 3.0))

    def test_missing_github_data_is_unavailable_not_zero(self):
        rows = [{"tasks": ["T4.4"], "attribution": "directa", "role": "Implementación", "total": 1, "tool": "claude", "start": "2026-10-28T10:00:00+00:00"}]
        task = au.aggregate_tasks(rows, None, {})[0]
        self.assertEqual((task["state"], task["prs"], task["review_verdicts"], task["ci_failures"], task["hours_to_pr"]), (None, None, None, None, None))

    def test_failed_ci_query_leaves_ci_failures_unknown(self):
        raw = [{"number": 7, "headRefName": "task/T4.4-x", "createdAt": "2026-10-28T11:00:00Z", "mergedAt": None, "state": "OPEN", "body": "", "comments": []}]
        self.assertIsNone(au.pr_rows(raw, None, set())[0]["ci_failures"])
        self.assertEqual(au.pr_rows(raw, [], set())[0]["ci_failures"], 0)
        self.assertIsNone(au.pr_rows(None, [], set()))
        rows = [{"tasks": ["T4.4"], "attribution": "directa", "role": "Implementación", "total": 1, "tool": "claude", "start": "2026-10-28T10:00:00+00:00"}]
        task = au.aggregate_tasks(rows, au.pr_rows(raw, None, {"T4.4"}), {})[0]
        self.assertEqual((task["state"], task["ci_failures"]), ("en revisión", None))

    def test_pull_requests_in_a_window_are_unknown_without_github(self):
        self.assertIsNone(au.prs_in_window(None, "Codex", "created", "2026-10-28T10:00:00+00:00", "2026-10-28T15:00:00+00:00"))
        prs = [{"tool": "Codex", "created": "2026-10-28T11:00:00Z"}, {"tool": "Codex", "created": "2026-10-28T16:00:00Z"}]
        self.assertEqual(au.prs_in_window(prs, "Codex", "created", "2026-10-28T10:00:00+00:00", "2026-10-28T15:00:00+00:00"), 1)


if __name__ == "__main__":
    unittest.main()
