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
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

# Tools whose only purpose is waiting for something outside the model.
WAIT_TOOLS = {"sleep", "wait", "wait_agent", "list_agents", "TaskOutput", "Monitor"}
# Shell commands that wait for, or poll, a process outside the model.
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


def parse_claude(path: Path, session_id: str | None = None, parent: str | None = None) -> Session:
    session = Session(session_id or path.stem, "claude", parent=parent)
    calls: dict[str, Call] = {}
    tools: dict[str, list[tuple[str, str]]] = {}
    for row in iter_jsonl(path):
        if row.get("gitBranch"):
            session.branches[row["gitBranch"]] += 1
        if row.get("cwd"):
            session.cwds[row["cwd"]] += 1
        message = row.get("message") or {}
        if row.get("type") == "user" and not session.prompt:
            text = _text(message.get("content"))
            if text.strip() and "<local-command" not in text and "<command-name>" not in text:
                session.prompt = text
        if row.get("type") != "assistant" or message.get("model") == "<synthetic>":
            continue
        key = f"{message.get('id')}:{row.get('requestId')}"
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tools.setdefault(key, []).append((block.get("name", ""), json.dumps(block.get("input"))))
        if key in calls:
            continue
        usage = message.get("usage") or {}
        calls[key] = Call(
            parse_ts(row["timestamp"]), message.get("model", ""),
            usage.get("input_tokens", 0), usage.get("output_tokens", 0),
            usage.get("cache_read_input_tokens", 0), usage.get("cache_creation_input_tokens", 0),
        )
    for key, call in calls.items():
        call.wait = is_wait_call(tools.get(key, []))
    session.calls = sorted(calls.values(), key=lambda c: c.ts)
    return session


def load_claude_sessions(project_dirs: Iterable[Path]) -> list[Session]:
    """Main sessions and their subagents, each subagent as its own session."""
    sessions = []
    for project in project_dirs:
        for path in sorted(project.glob("*.jsonl")):
            sessions.append(parse_claude(path))
        for path in sorted(project.glob("*/subagents/*.jsonl")):
            parent = path.parent.parent.name
            sessions.append(parse_claude(path, f"{parent}/{path.stem}", parent))
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
        elif kind == "response_item" and payload.get("type") == "message" and payload.get("role") == "user" and not session.prompt:
            text = _text(payload.get("content"))
            if text.strip() and not text.lstrip().startswith("<") and "AGENTS.md" not in text[:200]:
                session.prompt = text
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
