"""PostgreSQL adapter for Game run snapshots and their append-only history."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import TYPE_CHECKING, cast

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from mister.game.application.ports import (
    ConcurrencyError,
    DecisionLogRewrittenError,
    DecisionRecord,
    IdempotencyKeyExistsError,
    IdempotencyRecord,
    RunAlreadyExistsError,
    RunNotFoundError,
    RunRecord,
    RunRepository,
    RunStatus,
)
from mister.game.application.replay_inputs import ReplayInputs
from mister.game.application.run_content import RunContentSnapshot
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import (
    BlockId,
    DilemmaId,
    OptionId,
    PlayableSeasonId,
    RunId,
)
from mister.shared_kernel.seed import Seed

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from sqlalchemy.engine import Connection, Engine

metadata = sa.MetaData()
runs = sa.Table(
    "runs",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("playable_season_id", sa.String(64), nullable=False),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Column("payload", JSONB, nullable=False),
    sa.Column("replay_content_bytes", sa.LargeBinary, nullable=False),
    sa.Column("replay_content_format", sa.Integer, nullable=False),
    sa.Column("replay_content_digest", sa.String(64), nullable=False),
)
run_decisions = sa.Table(
    "run_decisions",
    metadata,
    sa.Column(
        "run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    ),
    sa.Column("sequence", sa.Integer, primary_key=True),
    sa.Column("payload", JSONB, nullable=False),
)
run_idempotency = sa.Table(
    "run_idempotency",
    metadata,
    sa.Column(
        "run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    ),
    sa.Column("key", sa.String(128), primary_key=True),
    sa.Column("payload", JSONB, nullable=False),
)


def _decision_json(decision: DecisionRecord) -> dict[str, object]:
    return {
        "block_id": decision.block_id.value,
        "dilemma_id": decision.dilemma_id.value,
        "option_id": decision.option_id.value,
        "decided_at": decision.decided_at.isoformat(),
    }


def _decode_decision(sequence: int, payload: Mapping[str, object]) -> DecisionRecord:
    return DecisionRecord(
        sequence=sequence,
        block_id=BlockId(cast("str", payload["block_id"])),
        dilemma_id=DilemmaId(cast("str", payload["dilemma_id"])),
        option_id=OptionId(cast("str", payload["option_id"])),
        decided_at=datetime.fromisoformat(cast("str", payload["decided_at"])),
    )


def _replay_payload(inputs: ReplayInputs) -> dict[str, object]:
    return {
        "initial_state_json": inputs.initial_state_json,
        "rules_configuration_json": inputs.rules_configuration_json,
        "engine_revision": inputs.engine_revision,
        "rules_revision": inputs.rules_revision,
    }


def _record_payload(record: RunRecord) -> dict[str, object]:
    return {
        "seed": record.seed.value,
        "run_token_hash": record.run_token_hash,
        "status": record.status.value,
        "snapshot": dict(record.snapshot),
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "replay": _replay_payload(record.replay_inputs),
    }


class SqlRunRepository(RunRepository):
    """Store one Game run in the supplied transaction or in a short owned transaction."""

    def __init__(self, engine: Engine, connection: Connection | None = None) -> None:
        self._engine = engine
        self._connection = connection

    @contextmanager
    def _connection_scope(self, *, write: bool = False) -> Iterator[Connection]:
        if self._connection is not None:
            yield self._connection
        elif write:
            with self._engine.begin() as connection:
                yield connection
        else:
            with self._engine.connect() as connection:
                yield connection

    @staticmethod
    def _decode(
        row: sa.Row[tuple[object, ...]], decisions: tuple[DecisionRecord, ...]
    ) -> RunRecord:
        payload = cast("dict[str, object]", row.payload)
        replay = cast("dict[str, object]", payload["replay"])
        content_bytes = cast("bytes", row.replay_content_bytes)
        content_json = content_bytes.decode("utf-8")
        content = RunContentSnapshot(
            format_version=cast("int", row.replay_content_format),
            content_json=content_json,
            digest=cast("str", row.replay_content_digest),
            playable_season_id=PlayableSeasonId(cast("str", row.playable_season_id)),
        )
        replay_inputs = ReplayInputs(
            content=content,
            initial_state_json=cast("str", replay["initial_state_json"]),
            rules_configuration_json=cast("str", replay["rules_configuration_json"]),
            engine_revision=cast("str", replay["engine_revision"]),
            rules_revision=cast("str", replay["rules_revision"]),
        )
        return RunRecord(
            run_id=RunId.parse(cast("str", row.id)),
            playable_season_id=PlayableSeasonId(cast("str", row.playable_season_id)),
            seed=Seed(cast("int", payload["seed"])),
            run_token_hash=cast("str", payload["run_token_hash"]),
            version=cast("int", row.version),
            status=RunStatus(cast("str", payload["status"])),
            snapshot=cast("dict[str, object]", payload["snapshot"]),
            decisions=decisions,
            created_at=datetime.fromisoformat(cast("str", payload["created_at"])),
            updated_at=datetime.fromisoformat(cast("str", payload["updated_at"])),
            replay_inputs=replay_inputs,
        )

    def add(self, record: RunRecord) -> None:
        content = record.replay_inputs.content
        values = {
            "id": str(record.run_id),
            "playable_season_id": record.playable_season_id.value,
            "version": record.version,
            "payload": _record_payload(record),
            "replay_content_bytes": content.content_json.encode("utf-8"),
            "replay_content_format": content.format_version,
            "replay_content_digest": content.digest,
        }
        try:
            with (
                self._connection_scope(write=True) as connection,
                connection.begin_nested(),
            ):
                connection.execute(sa.insert(runs).values(**values))
                if record.decisions:
                    connection.execute(
                        sa.insert(run_decisions),
                        [
                            {
                                "run_id": str(record.run_id),
                                "sequence": item.sequence,
                                "payload": _decision_json(item),
                            }
                            for item in record.decisions
                        ],
                    )
        except IntegrityError as error:
            raise RunAlreadyExistsError(record.run_id) from error

    def get(self, run_id: RunId) -> RunRecord | None:
        with self._connection_scope() as connection:
            rows = connection.execute(
                sa.select(
                    runs,
                    run_decisions.c.sequence,
                    run_decisions.c.payload.label("decision_payload"),
                )
                .outerjoin(run_decisions, run_decisions.c.run_id == runs.c.id)
                .where(runs.c.id == str(run_id))
                .order_by(run_decisions.c.sequence)
            ).all()
            if not rows:
                return None
            decisions = tuple(
                _decode_decision(row.sequence, row.decision_payload)
                for row in rows
                if row.sequence is not None
            )
            return self._decode(rows[0], decisions)

    def save(self, record: RunRecord, expected_version: int) -> None:
        with self._connection_scope(write=True) as connection:
            current_rows = connection.execute(
                sa.select(
                    runs,
                    run_decisions.c.sequence,
                    run_decisions.c.payload.label("decision_payload"),
                )
                .outerjoin(run_decisions, run_decisions.c.run_id == runs.c.id)
                .where(runs.c.id == str(record.run_id))
                .order_by(run_decisions.c.sequence)
            ).all()
            if not current_rows:
                raise RunNotFoundError(record.run_id)
            current_row = current_rows[0]
            if current_row.version != expected_version:
                raise ConcurrencyError(record.run_id, expected=expected_version)
            current_decisions = tuple(
                _decode_decision(row.sequence, row.decision_payload)
                for row in current_rows
                if row.sequence is not None
            )
            current = self._decode(current_row, current_decisions)
            if record.version != expected_version + 1:
                raise InvalidValueError("record version must be expected version + 1")
            if (
                record.seed != current.seed
                or record.run_token_hash != current.run_token_hash
                or record.playable_season_id != current.playable_season_id
                or record.created_at != current.created_at
                or record.replay_inputs != current.replay_inputs
            ):
                raise InvalidValueError("run identifying fields are immutable")
            if record.decisions[: len(current.decisions)] != current.decisions:
                raise DecisionLogRewrittenError(record.run_id)
            with connection.begin_nested():
                result = connection.execute(
                    sa.update(runs)
                    .where(runs.c.id == str(record.run_id), runs.c.version == expected_version)
                    .values(version=record.version, payload=_record_payload(record))
                )
                if result.rowcount != 1:
                    raise ConcurrencyError(record.run_id, expected=expected_version)
                additions = record.decisions[len(current.decisions) :]
                if additions:
                    connection.execute(
                        sa.insert(run_decisions),
                        [
                            {
                                "run_id": str(record.run_id),
                                "sequence": item.sequence,
                                "payload": _decision_json(item),
                            }
                            for item in additions
                        ],
                    )

    def get_idempotent(self, run_id: RunId, key: str) -> IdempotencyRecord | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                sa.select(run_idempotency.c.payload).where(
                    run_idempotency.c.run_id == str(run_id), run_idempotency.c.key == key
                )
            ).first()
            if row is None:
                return None
            payload = cast("dict[str, object]", row.payload)
            return IdempotencyRecord(
                run_id=run_id,
                key=key,
                request_hash=cast("str", payload["request_hash"]),
                response=cast("dict[str, object]", payload["response"]),
                created_at=datetime.fromisoformat(cast("str", payload["created_at"])),
            )

    def put_idempotent(self, record: IdempotencyRecord) -> None:
        if self.get(record.run_id) is None:
            raise RunNotFoundError(record.run_id)
        payload = {
            "request_hash": record.request_hash,
            "response": dict(record.response),
            "created_at": record.created_at.isoformat(),
        }
        try:
            with (
                self._connection_scope(write=True) as connection,
                connection.begin_nested(),
            ):
                connection.execute(
                    sa.insert(run_idempotency).values(
                        run_id=str(record.run_id), key=record.key, payload=payload
                    )
                )
        except IntegrityError as error:
            raise IdempotencyKeyExistsError(record.run_id, record.key) from error
