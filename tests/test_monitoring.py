from src.api.monitoring import population_stability_index


def test_psi_is_zero_for_identical_populations():
    values = [0.1, 0.2, 0.4, 0.8, 0.9]
    assert population_stability_index(values, values) == 0.0


def test_psi_detects_distribution_shift():
    expected = [0.1] * 100
    actual = [0.9] * 100
    assert population_stability_index(expected, actual) > 0.25