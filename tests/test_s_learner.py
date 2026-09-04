from ml.features import (
    METHOD_HISTORY_NUMERIC_FEATURES,
)

from ml.s_learner import (
    ACTION_NUMERIC_FEATURES,
    NUMERIC_FEATURES,
    PooledSLearner,
)


def test_default_s_learner_keeps_original_features():
    learner = PooledSLearner()

    expected = (
        NUMERIC_FEATURES
        + ACTION_NUMERIC_FEATURES
    )

    assert (
        learner._all_numeric_features()
        == expected
    )


def test_enhanced_s_learner_adds_method_history_features():
    learner = PooledSLearner(
        extra_numeric_features=(
            METHOD_HISTORY_NUMERIC_FEATURES
        )
    )

    expected = (
        NUMERIC_FEATURES
        + METHOD_HISTORY_NUMERIC_FEATURES
        + ACTION_NUMERIC_FEATURES
    )

    assert (
        learner._all_numeric_features()
        == expected
    )

    assert len(
        learner._all_numeric_features()
    ) == 32

def test_candidate_method_history_adds_only_three_numeric_features():
    learner = PooledSLearner(
        use_candidate_method_history=True
    )

    assert len(
        learner._all_numeric_features()
    ) == 23

def test_default_s_learner_does_not_enable_candidate_method_history():
    learner = PooledSLearner()

    assert (
        learner.use_candidate_method_history
        is False
    )