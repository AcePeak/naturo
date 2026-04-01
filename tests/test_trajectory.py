"""Tests for naturo.backends.windows._trajectory — mouse trajectory generation."""
from __future__ import annotations

import math
import statistics

import pytest

from naturo.backends.windows._trajectory import (
    TrajectoryPoint,
    generate_trajectory,
)


# ---------------------------------------------------------------------------
# Instant mode (backward compat)
# ---------------------------------------------------------------------------

class TestInstantTrajectory:

    def test_single_point_at_target(self) -> None:
        pts = generate_trajectory(0, 0, 500, 300, mode="instant")
        assert len(pts) == 1
        assert pts[0].x == 500
        assert pts[0].y == 300

    def test_zero_delay(self) -> None:
        pts = generate_trajectory(100, 100, 200, 200, mode="instant")
        assert pts[0].delay_s == 0.0


# ---------------------------------------------------------------------------
# Linear mode
# ---------------------------------------------------------------------------

class TestLinearTrajectory:

    def test_point_count_with_explicit_steps(self) -> None:
        pts = generate_trajectory(0, 0, 100, 0, mode="linear", steps=20, duration_ms=200)
        assert len(pts) == 20

    def test_endpoints(self) -> None:
        pts = generate_trajectory(10, 20, 500, 300, mode="linear", steps=50, duration_ms=500)
        assert pts[-1].x == 500
        assert pts[-1].y == 300

    def test_straight_line(self) -> None:
        pts = generate_trajectory(0, 0, 100, 100, mode="linear", steps=10, duration_ms=100)
        for pt in pts:
            assert abs(pt.x - pt.y) <= 1, f"Point ({pt.x}, {pt.y}) not on y=x diagonal"

    def test_auto_step_count(self) -> None:
        pts = generate_trajectory(0, 0, 100, 0, mode="linear", duration_ms=500)
        assert len(pts) == 50  # 500ms / 10ms per step

    def test_constant_delay(self) -> None:
        pts = generate_trajectory(0, 0, 100, 0, mode="linear", steps=10, duration_ms=1000)
        delays = [pt.delay_s for pt in pts]
        assert all(abs(d - 0.1) < 0.001 for d in delays)


# ---------------------------------------------------------------------------
# Bezier mode
# ---------------------------------------------------------------------------

class TestBezierTrajectory:

    def test_point_count(self) -> None:
        pts = generate_trajectory(0, 0, 500, 0, mode="bezier", steps=50, duration_ms=800)
        # May have more points due to overshoot correction, but at least 50
        assert len(pts) >= 50

    def test_endpoints(self) -> None:
        pts = generate_trajectory(0, 0, 500, 300, mode="bezier", steps=30, duration_ms=500)
        # Last point should be exactly on target
        assert pts[-1].x == 500
        assert pts[-1].y == 300

    def test_first_point_near_start(self) -> None:
        pts = generate_trajectory(0, 0, 1000, 0, mode="bezier", steps=100, duration_ms=1000)
        # First point should be close to start (within ~10% of distance)
        assert abs(pts[0].x) < 150
        assert abs(pts[0].y) < 150

    def test_no_two_trajectories_identical(self) -> None:
        trajectories = set()
        for _ in range(50):
            pts = generate_trajectory(0, 0, 500, 500, mode="bezier", steps=20, duration_ms=400)
            key = tuple((pt.x, pt.y) for pt in pts)
            trajectories.add(key)
        # At least 90% should be unique (randomness)
        assert len(trajectories) >= 45


# ---------------------------------------------------------------------------
# Jitter
# ---------------------------------------------------------------------------

class TestJitter:

    def test_zero_jitter_follows_ideal_path(self) -> None:
        pts = generate_trajectory(0, 0, 1000, 0, mode="bezier", steps=50,
                                  duration_ms=500, jitter=0.0)
        # With jitter=0, bezier still curves but all Y values should be
        # within the Bezier control point range (not NaN or extreme)
        for pt in pts[:-1]:  # skip last which is pinned
            assert abs(pt.y) < 500  # reasonable bound for a horizontal move

    def test_jitter_within_bounds(self) -> None:
        # Use linear to test jitter bounds more precisely
        # For bezier, jitter adds to the perpendicular direction
        pts = generate_trajectory(0, 0, 1000, 0, mode="bezier", steps=100,
                                  duration_ms=1000, jitter=5.0)
        # Y offsets should be bounded (bezier curve + jitter of 5px)
        # Allow for bezier curvature plus jitter
        max_y = max(abs(pt.y) for pt in pts[:-1])
        # Bezier can curve significantly, but with jitter=5, the extra
        # jitter should be small relative to the curve itself
        assert max_y < 500  # reasonable upper bound


# ---------------------------------------------------------------------------
# Overshoot
# ---------------------------------------------------------------------------

class TestOvershoot:

    def test_overshoot_exceeds_target(self) -> None:
        pts = generate_trajectory(0, 0, 500, 0, mode="bezier", steps=40,
                                  duration_ms=600, overshoot=20.0)
        # Some point should be beyond x=500
        max_x = max(pt.x for pt in pts)
        assert max_x > 500, f"No point exceeded target: max_x={max_x}"

    def test_final_point_at_target(self) -> None:
        pts = generate_trajectory(0, 0, 500, 0, mode="bezier", steps=40,
                                  duration_ms=600, overshoot=20.0)
        assert pts[-1].x == 500
        assert pts[-1].y == 0

    def test_overshoot_adds_correction_points(self) -> None:
        pts_no = generate_trajectory(0, 0, 500, 0, mode="bezier", steps=40,
                                     duration_ms=600, overshoot=0.0)
        pts_yes = generate_trajectory(0, 0, 500, 0, mode="bezier", steps=40,
                                      duration_ms=600, overshoot=20.0)
        assert len(pts_yes) > len(pts_no)


# ---------------------------------------------------------------------------
# 4-phase timing
# ---------------------------------------------------------------------------

class TestFourPhaseTiming:

    def test_variable_step_timing(self) -> None:
        pts = generate_trajectory(0, 0, 1000, 0, mode="bezier", steps=50,
                                  duration_ms=1000)
        delays = [pt.delay_s for pt in pts]
        # Delays should NOT be constant (4-phase model + jitter)
        assert statistics.stdev(delays) > 0.0

    def test_total_duration_roughly_matches(self) -> None:
        pts = generate_trajectory(0, 0, 1000, 0, mode="bezier", steps=50,
                                  duration_ms=1000)
        total = sum(pt.delay_s for pt in pts)
        # Total should be close to requested duration (within 20% due to overshoot)
        assert 0.8 < total < 1.2

    def test_duration_scales_step_count(self) -> None:
        pts_short = generate_trajectory(0, 0, 500, 0, mode="bezier", duration_ms=200)
        pts_long = generate_trajectory(0, 0, 500, 0, mode="bezier", duration_ms=2000)
        assert len(pts_long) > len(pts_short)


# ---------------------------------------------------------------------------
# Velocity profile
# ---------------------------------------------------------------------------

class TestVelocityProfile:

    def test_velocity_not_constant(self) -> None:
        pts = generate_trajectory(0, 0, 1000, 0, mode="bezier", steps=50,
                                  duration_ms=1000)
        # Calculate velocity: distance / delay for each segment
        velocities = []
        prev_x, prev_y = 0, 0
        for pt in pts:
            dist = math.hypot(pt.x - prev_x, pt.y - prev_y)
            if pt.delay_s > 0:
                velocities.append(dist / pt.delay_s)
            prev_x, prev_y = pt.x, pt.y
        # Velocity should vary (not constant like linear)
        if len(velocities) > 5:
            assert statistics.stdev(velocities) > 0.0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:

    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown trajectory mode"):
            generate_trajectory(0, 0, 100, 100, mode="unknown")

    def test_zero_distance(self) -> None:
        pts = generate_trajectory(100, 100, 100, 100, mode="bezier", steps=10,
                                  duration_ms=200)
        assert len(pts) >= 1
        assert pts[-1].x == 100
        assert pts[-1].y == 100

    def test_single_step(self) -> None:
        pts = generate_trajectory(0, 0, 500, 500, mode="bezier", steps=1,
                                  duration_ms=100)
        assert len(pts) >= 1
        assert pts[-1].x == 500
        assert pts[-1].y == 500


# ---------------------------------------------------------------------------
# TrajectoryPoint dataclass
# ---------------------------------------------------------------------------

class TestTrajectoryPoint:

    def test_frozen(self) -> None:
        pt = TrajectoryPoint(x=100, y=200, delay_s=0.01)
        with pytest.raises(AttributeError):
            pt.x = 999  # type: ignore[misc]
