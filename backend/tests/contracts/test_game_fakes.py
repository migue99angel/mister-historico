"""Game fakes: the port contract suites plus the behaviour only the fakes have."""

import pytest

from mister.game.application.ports import RunTokenGenerator, RunTokenHasher, SeasonSimulator
from mister.game.application.ports import UnitOfWork
from mister.game.infrastructure.in_memory.run_repository import (
    InMemoryRunRepository,
    InMemoryRunStore,
    InMemoryUnitOfWork,
)
from mister.game.infrastructure.in_memory.run_tokens import FakeRunTokenGenerator
from mister.game.infrastructure.security.run_tokens import (
    SecretsRunTokenGenerator,
    Sha256RunTokenHasher,
)
from mister.game.infrastructure.in_memory.season_simulator import (
    ScriptedSeasonSimulator,
    UnscriptedBlockError,
)
from tests.contracts.suites.game_samples import (
    make_run_record,
    make_simulation_request,
    make_simulation_result,
)
from tests.contracts.suites.run_repository import RepoFactory, RunRepositoryContract
from tests.contracts.suites.run_token import (
    GeneratorFactory,
    HasherFactory,
    RunTokenGeneratorContract,
    RunTokenHasherContract,
)
from tests.contracts.suites.season_simulator import SeasonSimulatorContract, SimulatorFactory
from tests.contracts.suites.unit_of_work import UnitOfWorkContract, UowPairFactory


class TestInMemoryRunRepository(RunRepositoryContract):
    @pytest.fixture
    def make_repo(self) -> RepoFactory:
        return InMemoryRunRepository


class TestInMemoryUnitOfWork(UnitOfWorkContract):
    @pytest.fixture
    def make_uows(self) -> UowPairFactory:
        def make() -> tuple[UnitOfWork, UnitOfWork]:
            store = InMemoryRunStore()
            return InMemoryUnitOfWork(store), InMemoryUnitOfWork(store)

        return make


class TestScriptedSeasonSimulator(SeasonSimulatorContract):
    @pytest.fixture
    def make_simulator(self) -> SimulatorFactory:
        def make() -> SeasonSimulator:
            simulator = ScriptedSeasonSimulator()
            simulator.script(make_simulation_result("b1"))
            return simulator

        return make


class TestFakeRunTokenGenerator(RunTokenGeneratorContract):
    @pytest.fixture
    def make_generator(self) -> GeneratorFactory:
        def make() -> RunTokenGenerator:
            return FakeRunTokenGenerator()

        return make


class TestSecretsRunTokenGenerator(RunTokenGeneratorContract):
    @pytest.fixture
    def make_generator(self) -> GeneratorFactory:
        def make() -> RunTokenGenerator:
            return SecretsRunTokenGenerator()

        return make


class TestSha256RunTokenHasher(RunTokenHasherContract):
    @pytest.fixture
    def make_hasher(self) -> HasherFactory:
        def make() -> RunTokenHasher:
            return Sha256RunTokenHasher()

        return make


# --------------------------------------------------------------------- fake-only behaviour


def test_a_repository_used_on_its_own_commits_every_write_at_once() -> None:
    repo = InMemoryRunRepository()
    record = make_run_record()

    repo.add(record)

    assert InMemoryRunRepository(repo.store).get(record.run_id) == record


def test_scripted_simulator_records_the_requests_it_received() -> None:
    simulator = ScriptedSeasonSimulator()
    simulator.script(make_simulation_result("b1"))
    request = make_simulation_request("b1")

    simulator.simulate_block(request)

    assert simulator.requests == [request]


def test_scripted_simulator_without_a_script_for_the_block_fails_loudly() -> None:
    simulator = ScriptedSeasonSimulator()

    with pytest.raises(UnscriptedBlockError, match="b2"):
        simulator.simulate_block(make_simulation_request("b2"))


def test_scripted_simulator_can_be_told_to_fail() -> None:
    simulator = ScriptedSeasonSimulator()
    simulator.script(make_simulation_result("b1"))
    simulator.fail_with(RuntimeError("engine down"))

    with pytest.raises(RuntimeError, match="engine down"):
        simulator.simulate_block(make_simulation_request("b1"))

    simulator.fail_with(None)
    assert simulator.simulate_block(make_simulation_request("b1")).block_id.value == "b1"


def test_fake_token_generator_is_deterministic_across_instances() -> None:
    assert FakeRunTokenGenerator().generate() == FakeRunTokenGenerator().generate()
