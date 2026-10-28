"""Local audit of Claude Code and Codex usage for this repository.

Reads the session logs both tools write on this machine and turns them into
per-session metrics. Nothing is sent anywhere: the output goes to a directory
outside the repository, and prompts are never written to it.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

# Tools whose only purpose is waiting for something outside the model.
WAIT_TOOLS = {"sleep", "wait", "wait_agent", "list_agents", "TaskOutput", "Monitor"}
# Shell commands that wait for, or poll, a process outside the model.
TASK_ID = re.compile(r"(?<![\w-])(CR-T\d+\.\d+[a-z]?|T\d+\.\d+[a-z]?)(?![\w.])")
# Text a tool injects as a user turn, not written by the person.
SYSTEM_TEXT = ("<local-command", "<command-name>", "<task-notification", "<system-reminder")
POLL_COMMAND = re.compile(r"(?:^|[\s;&|(])sleep\s+\d|gh pr checks|gh run (?:watch|view|list)|statusCheckRollup")


@dataclass
class Call:
    """One model request with its token usage."""

    ts: datetime
    model: str
    fresh_input: int
    output: int
    cache_read: int
    cache_write: int
    wait: bool = False

    @property
    def context(self) -> int:
        return self.fresh_input + self.cache_read + self.cache_write

    @property
    def total(self) -> int:
        return self.context + self.output


@dataclass
class Session:
    id: str
    tool: str
    parent: str | None = None
    calls: list[Call] = field(default_factory=list)
    branches: Counter = field(default_factory=Counter)
    cwds: Counter = field(default_factory=Counter)
    prompt: str = ""
    agent: str = ""
    quota: list[dict] = field(default_factory=list)
    user_turns: int = 0
    mentioned: Counter = field(default_factory=Counter)

    def add_user_turn(self, text: str) -> None:
        if not self.prompt:
            self.prompt = text
        self.user_turns += 1
        self.mentioned.update(TASK_ID.findall(text))


def iter_jsonl(path: Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_wait_call(tools: list[tuple[str, str]]) -> bool:
    """A call is a wait call when every tool it asked for only waits or polls."""
    return bool(tools) and all(name in WAIT_TOOLS or bool(POLL_COMMAND.search(args)) for name, args in tools)


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") in ("text", "input_text"))
    return ""


def parse_claude(path: Path, session_id: str | None = None, parent: str | None = None, seen: set[str] | None = None) -> Session:
    """Parse one Claude Code log. `seen` holds request keys already counted in other logs."""
    seen = set() if seen is None else seen
    session = Session(session_id or path.stem, "claude", parent=parent)
    calls: dict[str, Call] = {}
    tools: dict[str, list[tuple[str, str]]] = {}
    for row in iter_jsonl(path):
        if row.get("gitBranch"):
            session.branches[row["gitBranch"]] += 1
        if row.get("cwd"):
            session.cwds[row["cwd"]] += 1
        message = row.get("message") or {}
        if row.get("type") == "user" and not row.get("isMeta"):
            text = _text(message.get("content"))
            if text.strip() and not text.lstrip().startswith(SYSTEM_TEXT):
                session.add_user_turn(text)
        if row.get("type") != "assistant" or message.get("model") == "<synthetic>":
            continue
        key = f"{message.get('id')}:{row.get('requestId')}"
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tools.setdefault(key, []).append((block.get("name", ""), json.dumps(block.get("input"))))
        if key in calls or key in seen:
            continue
        usage = message.get("usage") or {}
        calls[key] = Call(
            parse_ts(row["timestamp"]), message.get("model", ""),
            usage.get("input_tokens", 0), usage.get("output_tokens", 0),
            usage.get("cache_read_input_tokens", 0), usage.get("cache_creation_input_tokens", 0),
        )
    for key, call in calls.items():
        call.wait = is_wait_call(tools.get(key, []))
    seen.update(calls)
    session.calls = sorted(calls.values(), key=lambda c: c.ts)
    return session


def load_claude_sessions(project_dirs: Iterable[Path]) -> list[Session]:
    """Main sessions and their subagents, each subagent as its own session."""
    sessions, seen = [], set()
    for project in project_dirs:
        for path in sorted(project.glob("*.jsonl")):
            sessions.append(parse_claude(path, seen=seen))
        for path in sorted(project.glob("*/subagents/*.jsonl")):
            parent = path.parent.parent.name
            sessions.append(parse_claude(path, f"{parent}/{path.stem}", parent, seen))
    return sessions


def parse_codex(path: Path) -> Session:
    rows = iter_jsonl(path)
    session = Session(path.stem, "codex")
    model, pending, last_total = "", [], None
    for row in rows:
        kind, payload = row.get("type"), row.get("payload") or {}
        if kind == "session_meta":
            session.id = payload.get("id", session.id)
            session.parent = payload.get("parent_thread_id")
            session.agent = payload.get("agent_path") or ""
            if payload.get("cwd"):
                session.cwds[payload["cwd"]] += 1
            branch = (payload.get("git") or {}).get("branch")
            if branch:
                session.branches[branch] += 1
        elif kind == "turn_context":
            model = payload.get("model", model)
        elif kind == "response_item" and payload.get("type") in ("function_call", "custom_tool_call"):
            pending.append((payload.get("name", ""), str(payload.get("arguments") or payload.get("input") or "")))
        elif kind == "response_item" and payload.get("type") == "message" and payload.get("role") == "user":
            text = _text(payload.get("content"))
            if text.strip() and not text.lstrip().startswith("<") and "AGENTS.md" not in text[:200]:
                session.add_user_turn(text)
        elif kind == "event_msg" and payload.get("type") == "token_count":
            limits = payload.get("rate_limits") or {}
            primary = limits.get("primary")
            if primary:
                session.quota.append({"ts": row["timestamp"], "limit_id": limits.get("limit_id"), "plan": limits.get("plan_type"), **primary})
            info = payload.get("info")
            if not info:
                continue
            total = info["total_token_usage"]["total_tokens"]
            if total == last_total:
                continue
            last_total = total
            last = info["last_token_usage"]
            cached = last.get("cached_input_tokens", 0)
            session.calls.append(Call(
                parse_ts(row["timestamp"]), model, last.get("input_tokens", 0) - cached, last.get("output_tokens", 0),
                cached, last.get("cache_write_input_tokens", 0), wait=is_wait_call(pending),
            ))
            pending = []
    return session


def percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile; None for no data."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q / 100 * len(ordered)) - 1)]


def active_minutes(timestamps: list[datetime], idle_gap_min: float = 5) -> float:
    """Minutes between consecutive calls, skipping gaps longer than the idle threshold."""
    gaps = ((b - a).total_seconds() / 60 for a, b in zip(timestamps, timestamps[1:]))
    return round(sum(g for g in gaps if g <= idle_gap_min), 1)


def session_metrics(session: Session) -> dict:
    calls = session.calls
    ctx = [c.context for c in calls]
    waits = sum(c.wait for c in calls)
    models = Counter()
    for c in calls:
        models[c.model] += c.total
    deciles = []
    for i in range(10):
        chunk = ctx[len(ctx) * i // 10: len(ctx) * (i + 1) // 10]
        deciles.append(percentile(chunk, 50))
    start, end = (calls[0].ts, calls[-1].ts) if calls else (None, None)
    return {
        "calls": len(calls),
        "wait_calls": waits,
        "wait_share": round(waits / len(calls), 4) if calls else None,
        "ctx_mean": round(sum(ctx) / len(ctx)) if ctx else None,
        "ctx_median": percentile(ctx, 50),
        "ctx_p90": percentile(ctx, 90),
        "ctx_max": max(ctx) if ctx else None,
        "ctx_deciles": deciles,
        "fresh_input": sum(c.fresh_input for c in calls),
        "output": sum(c.output for c in calls),
        "cache_read": sum(c.cache_read for c in calls),
        "cache_write": sum(c.cache_write for c in calls),
        "total": sum(c.total for c in calls),
        "wait_tokens": sum(c.total for c in calls if c.wait),
        "models": dict(models),
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
        "elapsed_min": round((end - start).total_seconds() / 60, 1) if calls else None,
        "active_min": active_minutes([c.ts for c in calls]),
    }


BRANCH_TASK = re.compile(r"^task/(CR-T\d+\.\d+[a-z]?|T\d+\.\d+[a-z]?)(?:-|$)")
WORKTREE_TASK = re.compile(r"mister-historico-(CR-T\d+\.\d+[a-z]?|T\d+\.\d+[a-z]?)(?:-|$)")
REVIEW_PROMPT = re.compile(r"\brevis(?:a|or|ión)\b|\breview(?:er)?\b|fact-checker|verificador", re.IGNORECASE)


def normalize_task(task_id: str, known: set[str]) -> str:
    """Map a sub-delivery (T3.5b) to its TASKS entry (T3.5) unless it has its own entry."""
    if task_id in known or not task_id[-1].isalpha():
        return task_id
    return task_id[:-1] if task_id[:-1] in known else task_id


def _unique(ids: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(ids))


def attribute(session: Session, known: set[str], override: dict | None = None) -> dict:
    """Assign a session to tasks and say how certain that assignment is."""
    if override:
        return {"tasks": override.get("tasks", []), "attribution": override.get("attribution", "desconocida"),
                "role": override.get("role", "Desconocido"), "source": "manual", "label": override.get("label", "")}
    from_git = [m.group(1) for b in session.branches if (m := BRANCH_TASK.match(b))]
    from_git += [m.group(1) for c in session.cwds if (m := WORKTREE_TASK.search(Path(c).name))]
    tasks = _unique(normalize_task(t, known) for t in from_git)
    if tasks:
        kind, source = ("directa" if len(tasks) == 1 else "repartida"), "git"
    else:
        tasks = _unique(normalize_task(t, known) for t in TASK_ID.findall(session.prompt[:3000]))
        kind = {0: "desconocida", 1: "inferida"}.get(len(tasks), "repartida")
        source = "prompt" if tasks else "ninguna"
    if REVIEW_PROMPT.search(session.prompt[:400]):
        role = "Revisión"
    elif source == "git":
        role = "Implementación"
    else:
        role = "Desconocido"
    return {"tasks": tasks, "attribution": kind, "role": role, "source": source, "label": ""}


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def quota_windows(snapshots: list[dict], tolerance_s: int = 180) -> list[dict]:
    """Group quota snapshots by the reset time the provider reported (it jitters by seconds)."""
    windows: list[dict] = []
    for snap in sorted(snapshots, key=lambda s: s["ts"]):
        current = windows[-1] if windows else None
        if not current or current["limit_id"] != snap.get("limit_id") or abs(current["_reset"] - snap["resets_at"]) > tolerance_s:
            current = {"limit_id": snap.get("limit_id"), "plan": snap.get("plan"), "window_minutes": snap["window_minutes"],
                       "_reset": snap["resets_at"], "first_ts": snap["ts"], "first_used": snap["used_percent"],
                       "max_used": snap["used_percent"], "snapshots": 0}
            windows.append(current)
        current["last_ts"] = snap["ts"]
        current["max_used"] = max(current["max_used"], snap["used_percent"])
        current["snapshots"] += 1
    for w in windows:
        reset = w.pop("_reset")
        w["resets_at"] = _iso(reset)
        w["start"] = _iso(reset - w["window_minutes"] * 60)
    return windows


def pr_tool(body: str | None) -> str | None:
    """The tool a pull request was made with, from the footer the project requires."""
    body = body or ""
    if "Generated with Codex" in body:
        return "Codex"
    if "Generated with [Claude Code]" in body or "Generated with Claude Code" in body:
        return "Claude Code"
    return None


def task_from_branch(branch: str) -> str | None:
    match = BRANCH_TASK.match(branch or "")
    return match.group(1) if match else None


def cost_fields(ccusage_row: dict | None) -> dict:
    """API-equivalent cost from ccusage; None when ccusage has no row, never 0."""
    if ccusage_row is None:
        return {"cost_usd": None, "cost_estimated": None}
    cost = ccusage_row.get("costUSD", ccusage_row.get("totalCost"))
    fallback = any(m.get("isFallback") for m in (ccusage_row.get("models") or {}).values() if isinstance(m, dict))
    return {"cost_usd": cost, "cost_estimated": fallback}


def statusline(payload: dict, log_path: Path) -> str:
    """Render the Claude Code status line and log quota changes reported by Claude Code."""
    parts = [(payload.get("model") or {}).get("display_name") or "?"]
    used = (payload.get("context_window") or {}).get("used_percentage")
    if used is not None:
        parts.append(f"ctx {round(used)}%")
    limits = payload.get("rate_limits") or {}
    five, week = limits.get("five_hour"), limits.get("seven_day")
    if five:
        reset = datetime.fromtimestamp(five["resets_at"]).strftime("%H:%M")
        parts.append(f"5h {round(five['used_percentage'])}% ↻ {reset}")
    else:
        parts.append("5h n/d")
    if week:
        parts.append(f"7d {round(week['used_percentage'])}%")
    if five or week:
        _log_quota(payload, five or {}, week or {}, log_path)
    return " · ".join(parts)


def _log_quota(payload: dict, five: dict, week: dict, log_path: Path) -> None:
    snapshot = {"five_hour_used": five.get("used_percentage"), "five_hour_resets_at": five.get("resets_at"),
                "seven_day_used": week.get("used_percentage"), "seven_day_resets_at": week.get("resets_at")}
    state = log_path.with_suffix(".last")
    key = json.dumps(snapshot, sort_keys=True)
    if state.exists() and state.read_text() == key:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(timezone.utc).isoformat(), "session_id": payload.get("session_id"),
           "model": (payload.get("model") or {}).get("id"), **snapshot}
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    state.write_text(key)


def period(start: str | None, end: str | None, cutoff: datetime) -> str | None:
    """Whether a session ran before, after or across a workflow change."""
    if not start:
        return None
    if datetime.fromisoformat(end) < cutoff:
        return "antes"
    return "después" if datetime.fromisoformat(start) >= cutoff else "cruza"


def _hours(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    return round((parse_ts(b) - parse_ts(a)).total_seconds() / 3600, 1)


def aggregate_tasks(rows: list[dict], prs: list[dict], sizes: dict[str, str], board: dict[str, str] | None = None) -> list[dict]:
    """Usage and delivery per task. Split sessions count as an estimate, apart from direct ones."""
    board = board or {}
    tasks: dict[str, dict] = {}

    def entry(task_id: str) -> dict:
        return tasks.setdefault(task_id, {
            "task": task_id, "size": sizes.get(task_id), "sessions": 0, "tokens_directa": 0, "tokens_inferida": 0,
            "tokens_repartida_est": 0, "tokens_by_role": Counter(), "tools": Counter(), "first_session": None, "prs": []})

    for row in rows:
        for task_id in row["tasks"]:
            t = entry(task_id)
            share = row["total"] / len(row["tasks"])
            bucket = {"directa": "tokens_directa", "inferida": "tokens_inferida"}.get(row["attribution"], "tokens_repartida_est")
            t[bucket] += share
            t["tokens_by_role"][row["role"]] += share
            t["tools"][row["tool"]] += share
            t["sessions"] += 1
            if row.get("start") and (t["first_session"] is None or row["start"] < t["first_session"]):
                t["first_session"] = row["start"]
    for pr in prs:
        if pr.get("task"):
            entry(pr["task"])["prs"].append(pr)
    out = []
    for t in tasks.values():
        prs_t = sorted(t.pop("prs"), key=lambda p: p["created"])
        states = {p["state"] for p in prs_t}
        state = ("integrada" if "MERGED" in states else "en revisión" if "OPEN" in states
                 else "cerrada sin integrar" if states else "sin PR")
        if board.get(t["task"]) == "Blocked":
            state = "bloqueada"
        merged = [p["merged"] for p in prs_t if p.get("merged")]
        t.update({
            "tokens_by_role": dict(t["tokens_by_role"]), "tools": dict(t["tools"]),
            "prs": [p["number"] for p in prs_t], "pr_tools": sorted({p["tool"] for p in prs_t if p.get("tool")}),
            "state": state, "review_verdicts": sum(p.get("review_verdicts", 0) for p in prs_t),
            "ci_failures": sum(p.get("ci_failures", 0) for p in prs_t),
            "hours_to_pr": _hours(t["first_session"], prs_t[0]["created"]) if prs_t else None,
            "hours_to_merge": _hours(t["first_session"], max(merged)) if merged else None,
        })
        out.append(t)
    return sorted(out, key=lambda t: t["task"])
