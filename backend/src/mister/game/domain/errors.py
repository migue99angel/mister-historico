"""Business errors raised by the private run aggregate."""

from mister.shared_kernel.errors import DomainError


class InvalidRunTransitionError(DomainError):
    """A command is not valid for the current run state."""

    code = "invalid_run_transition"


class InvalidDecisionError(DomainError):
    """A decision does not belong to the current block and dilemma."""

    code = "invalid_decision"


class AlreadyDecidedError(DomainError):
    """A dilemma has already been decided."""

    code = "already_decided"
