"""Tests for agents/config/cost-guardrails.yaml structure and value constraints."""

from pathlib import Path

import pytest
import yaml

GUARDRAILS_PATH = Path(__file__).resolve().parent.parent / "agents" / "config" / "cost-guardrails.yaml"


@pytest.fixture(scope="module")
def config():
    assert GUARDRAILS_PATH.exists(), f"Missing {GUARDRAILS_PATH}"
    with open(GUARDRAILS_PATH) as fh:
        return yaml.safe_load(fh)


class TestCostGuardrails:
    """Validate cost-guardrails.yaml structure and values."""

    def test_has_pause_all(self, config):
        assert "pause_all" in config
        assert isinstance(config["pause_all"], bool)

    def test_has_agents_section(self, config):
        assert "agents" in config
        assert isinstance(config["agents"], dict)
        assert len(config["agents"]) >= 1

    def test_required_agent_keys(self, config):
        required = {"daily_run_limit", "consecutive_failure_pause", "notification_threshold_pct"}
        for name, agent in config["agents"].items():
            missing = required - set(agent.keys())
            assert not missing, f"Agent {name} missing keys: {missing}"

    def test_daily_run_limit_positive(self, config):
        for name, agent in config["agents"].items():
            assert agent["daily_run_limit"] > 0, f"{name}: daily_run_limit must be > 0"

    def test_consecutive_failure_pause_non_negative(self, config):
        for name, agent in config["agents"].items():
            assert agent["consecutive_failure_pause"] >= 0, (
                f"{name}: consecutive_failure_pause must be >= 0"
            )

    def test_notification_threshold_range(self, config):
        for name, agent in config["agents"].items():
            pct = agent["notification_threshold_pct"]
            assert 0 < pct <= 100, f"{name}: threshold must be in (0, 100], got {pct}"

    def test_dev_sirius_present(self, config):
        assert "Dev-Sirius" in config["agents"]

    def test_qa_mariana_present(self, config):
        assert "QA-Mariana" in config["agents"]

    def test_pause_all_default_false(self, config):
        assert config["pause_all"] is False, "pause_all should default to false"

    def test_daily_limits_reasonable(self, config):
        for name, agent in config["agents"].items():
            assert agent["daily_run_limit"] <= 100, (
                f"{name}: daily_run_limit={agent['daily_run_limit']} seems unreasonably high"
            )

    def test_yaml_round_trips(self, config):
        """Config should survive a dump/load cycle without data loss."""
        roundtripped = yaml.safe_load(yaml.dump(config))
        assert roundtripped == config
