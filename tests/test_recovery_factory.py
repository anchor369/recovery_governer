from backend.services import (
    recovery_factory,
)

from backend.services.recovery_decision import (
    RecoveryDecisionService,
)


class FakeLearner:
    pass


def test_factory_loads_and_builds_decision_service(
    monkeypatch,
    tmp_path,
):
    fake_model_path = (
        tmp_path
        / "fake_model.joblib"
    )

    fake_model_path.write_text(
        "placeholder"
    )

    fake_learner = FakeLearner()

    load_calls = []

    def fake_joblib_load(path):
        load_calls.append(
            path
        )

        return fake_learner

    monkeypatch.setattr(
        recovery_factory.joblib,
        "load",
        fake_joblib_load,
    )

    recovery_factory.load_recovery_learner.cache_clear()

    service_1 = (
        recovery_factory
        .create_recovery_decision_service(
            model_path=(
                fake_model_path
            )
        )
    )

    service_2 = (
        recovery_factory
        .create_recovery_decision_service(
            model_path=(
                fake_model_path
            )
        )
    )

    assert isinstance(
        service_1,
        RecoveryDecisionService,
    )

    assert isinstance(
        service_2,
        RecoveryDecisionService,
    )

    assert (
        service_1.governor.learner
        is fake_learner
    )

    assert (
        service_2.governor.learner
        is fake_learner
    )

    assert len(
        load_calls
    ) == 1

    recovery_factory.load_recovery_learner.cache_clear()