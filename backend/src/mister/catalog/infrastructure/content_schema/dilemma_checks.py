"""Checks of `dilemmas.yaml`: counts per block and the references made by every effect."""

from collections import Counter
from datetime import date

from mister.catalog.infrastructure.content_schema.base import season_window
from mister.catalog.infrastructure.content_schema.context import SeasonContext
from mister.catalog.infrastructure.content_schema.effects import (
    CompetitionPriorityEffect,
    Effect,
    FitnessEffect,
    InjuryEffect,
    PlayerMoraleEffect,
    SellPlayerEffect,
    SignPlayerEffect,
    YouthMinutesEffect,
)

MIN_DILEMMAS_PER_BLOCK = 1
MAX_DILEMMAS_PER_BLOCK = 3
MIN_DILEMMAS = 8
MAX_DILEMMAS = 12


def check_dilemmas(ctx: SeasonContext) -> None:
    """Counts per block and in total, plus the references of every effect."""
    dilemmas = ctx.content.dilemmas.dilemmas
    block_ids = {b.id for b in ctx.blocks}
    per_block = Counter(d.block for d in dilemmas)
    for index, dilemma in enumerate(dilemmas):
        if dilemma.block not in block_ids:
            ctx.add("dilemmas", f"dilemmas.{index}.block", f"unknown block {dilemma.block!r}")
    for block in ctx.blocks:
        count = per_block[block.id]
        if not MIN_DILEMMAS_PER_BLOCK <= count <= MAX_DILEMMAS_PER_BLOCK:
            ctx.add(
                "dilemmas",
                "dilemmas",
                f"block {block.id} has {count} dilemmas; expected between "
                f"{MIN_DILEMMAS_PER_BLOCK} and {MAX_DILEMMAS_PER_BLOCK}",
            )
    if not MIN_DILEMMAS <= len(dilemmas) <= MAX_DILEMMAS:
        ctx.add(
            "dilemmas",
            "dilemmas",
            f"{len(dilemmas)} dilemmas in total; "
            f"expected between {MIN_DILEMMAS} and {MAX_DILEMMAS}",
        )
    signed = {
        e.player_id
        for d in dilemmas
        for o in d.options
        for e in o.effects
        if isinstance(e, SignPlayerEffect)
    }
    usable = ctx.own_players | signed
    for di, dilemma in enumerate(dilemmas):
        for oi, option in enumerate(dilemma.options):
            for ei, effect in enumerate(option.effects):
                _check_effect(ctx, f"dilemmas.{di}.options.{oi}.effects.{ei}", effect, usable)


def _check_effect(ctx: SeasonContext, field: str, effect: Effect, usable: set[str]) -> None:
    match effect:
        case SignPlayerEffect():
            _check_sign(ctx, field, effect)
        case SellPlayerEffect():
            _check_player(ctx, f"{field}.player_id", effect.player_id, usable)
            if effect.to_club_season is not None:
                _check_squad_ref(ctx, f"{field}.to_club_season", effect.to_club_season)
        case PlayerMoraleEffect() | YouthMinutesEffect():
            _check_player(ctx, f"{field}.player_id", effect.player_id, usable)
        case InjuryEffect():
            _check_player(ctx, f"{field}.player_id", effect.player_id, usable)
            _check_injury_date(ctx, field, effect.date)
        case FitnessEffect() if effect.player_id is not None:
            _check_player(ctx, f"{field}.player_id", effect.player_id, usable)
        case CompetitionPriorityEffect():
            if effect.competition_id not in ctx.competitions:
                ctx.add(
                    "dilemmas",
                    f"{field}.competition_id",
                    f"unknown competition {effect.competition_id!r}",
                )
        case _:
            pass


def _check_player(ctx: SeasonContext, field: str, player_id: str, usable: set[str]) -> None:
    if player_id not in usable:
        ctx.add("dilemmas", field, f"player {player_id!r} is not in the own squad")


def _check_squad_ref(ctx: SeasonContext, field: str, club_season: str) -> bool:
    if not ctx.exists(club_season):
        ctx.add("dilemmas", field, f"unknown club-season {club_season!r}")
    elif not ctx.has_squad(club_season):
        ctx.add("dilemmas", field, f"{club_season!r} has no squad (aggregate rival)")
    elif club_season == ctx.own:
        ctx.add("dilemmas", field, "cannot be the own team")
    else:
        return True
    return False


def _check_sign(ctx: SeasonContext, field: str, effect: SignPlayerEffect) -> None:
    if effect.player_id in ctx.own_players:
        ctx.add(
            "dilemmas",
            f"{field}.player_id",
            f"player {effect.player_id!r} is already in the own squad",
        )
        return
    source = effect.from_club_season
    if source is not None:
        _check_signing_source(ctx, field, effect.player_id, source)
        return
    owners = sorted(
        slug
        for slug, squad in ctx.tree.squads.items()
        if not squad.is_market and any(p.player_id == effect.player_id for p in squad.players)
    )
    everyone = {p.player_id for s in ctx.tree.squads.values() for p in s.players}
    if owners:
        ctx.add(
            "dilemmas",
            f"{field}.player_id",
            f"player {effect.player_id!r} belongs to {owners[0]}: set from_club_season",
        )
    elif effect.player_id not in everyone:
        ctx.add("dilemmas", f"{field}.player_id", f"unknown player {effect.player_id!r}")


def _check_signing_source(ctx: SeasonContext, field: str, player_id: str, source: str) -> None:
    if not _check_squad_ref(ctx, f"{field}.from_club_season", source):
        return
    squad = ctx.tree.squads.get(source)
    if squad is not None and player_id not in {p.player_id for p in squad.players}:
        ctx.add(
            "dilemmas",
            f"{field}.from_club_season",
            f"player {player_id!r} is not in the squad of {source}",
        )


def _check_injury_date(ctx: SeasonContext, field: str, day: date) -> None:
    first, last = season_window(ctx.content.season.season)
    if not first <= day <= last:
        ctx.add("dilemmas", f"{field}.date", f"{day} is outside the season ({first}..{last})")
