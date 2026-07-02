"""Human-like mouse trajectory generation.

Generates smooth, natural-looking mouse paths using Bezier curves,
4-phase acceleration profiles, random jitter, and overshoot correction.

This module is pure math — no platform dependencies. The generated
trajectories are lists of ``TrajectoryPoint`` that callers iterate over,
calling ``mouse_move`` at each point with the specified delay.

Trajectory modes:
- ``instant``: Single point at target (teleport, backward compatible).
- ``linear``: Straight line with constant speed.
- ``bezier``: Human-like curve with 4-phase timing and optional jitter/overshoot.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TrajectoryPoint:
    """A single point in a mouse trajectory.

    Attributes:
        x: Screen X coordinate (pixels).
        y: Screen Y coordinate (pixels).
        delay_s: Seconds to sleep AFTER moving to this point.
    """

    x: int
    y: int
    delay_s: float


def generate_trajectory(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    *,
    mode: str = "instant",
    duration_ms: int = 500,
    steps: Optional[int] = None,
    jitter: float = 0.0,
    overshoot: float = 0.0,
) -> list[TrajectoryPoint]:
    """Generate a mouse movement trajectory.

    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Target X coordinate.
        end_y: Target Y coordinate.
        mode: Trajectory type — ``"instant"``, ``"linear"``, or ``"bezier"``.
        duration_ms: Total movement time in milliseconds.
        steps: Number of intermediate points. Auto-calculated from
            duration if omitted (roughly 1 point per 10ms).
        jitter: Max random perpendicular offset per step in pixels.
            Only affects ``bezier`` mode.
        overshoot: Pixels to overshoot past target then correct back.
            Only affects ``bezier`` mode. 0 = disabled.

    Returns:
        List of TrajectoryPoint. First point is near ``(start_x, start_y)``,
        last point is exactly ``(end_x, end_y)``.

    Raises:
        ValueError: If *mode* is not recognized.
    """
    if mode == "instant":
        return [TrajectoryPoint(x=end_x, y=end_y, delay_s=0.0)]

    if mode == "linear":
        return _linear_trajectory(
            start_x, start_y, end_x, end_y,
            duration_ms=duration_ms, steps=steps,
        )

    if mode == "bezier":
        return _bezier_trajectory(
            start_x, start_y, end_x, end_y,
            duration_ms=duration_ms, steps=steps,
            jitter=jitter, overshoot=overshoot,
        )

    raise ValueError(f"Unknown trajectory mode: {mode!r}. Use 'instant', 'linear', or 'bezier'.")


# ── Linear Trajectory ──────────────────────────────────────────────────────


def _linear_trajectory(
    sx: int, sy: int, ex: int, ey: int,
    *, duration_ms: int, steps: Optional[int],
) -> list[TrajectoryPoint]:
    """Straight-line interpolation with constant speed."""
    n = steps if steps is not None else max(1, duration_ms // 10)
    n = max(1, n)
    delay = (duration_ms / 1000.0) / n
    points: list[TrajectoryPoint] = []
    for i in range(1, n + 1):
        t = i / n
        x = int(round(sx + (ex - sx) * t))
        y = int(round(sy + (ey - sy) * t))
        points.append(TrajectoryPoint(x=x, y=y, delay_s=delay))
    # Ensure last point is exact target
    if points:
        last = points[-1]
        if last.x != ex or last.y != ey:
            points[-1] = TrajectoryPoint(x=ex, y=ey, delay_s=last.delay_s)
    return points


# ── Bezier Trajectory ──────────────────────────────────────────────────────


# Phase boundaries and speed weights for 4-phase acceleration model:
#   Phase 1 (0-20%):  slow start, ease-in
#   Phase 2 (20-60%): main acceleration, fast
#   Phase 3 (60-85%): deceleration, ease-out
#   Phase 4 (85-100%): micro-adjustment, very slow
_PHASES = (
    (0.00, 0.20, 0.5),   # (start_t, end_t, speed_weight)
    (0.20, 0.60, 1.5),
    (0.60, 0.85, 0.8),
    (0.85, 1.00, 0.3),
)


def _bezier_trajectory(
    sx: int, sy: int, ex: int, ey: int,
    *, duration_ms: int, steps: Optional[int],
    jitter: float, overshoot: float,
) -> list[TrajectoryPoint]:
    """Human-like trajectory with Bezier curve and 4-phase timing."""
    n = steps if steps is not None else max(1, duration_ms // 10)
    n = max(1, n)

    # Generate control points for a cubic Bezier curve.
    # Two random control points create natural-looking arcs.
    dx = ex - sx
    dy = ey - sy
    dist = math.hypot(dx, dy) or 1.0

    # Control point offsets: perpendicular to the line, random magnitude
    perp_x = -dy / dist
    perp_y = dx / dist

    # Random control point placement — keeps curves subtle (±15-30% of distance)
    offset1 = dist * random.uniform(0.15, 0.30) * random.choice([-1, 1])
    offset2 = dist * random.uniform(0.10, 0.25) * random.choice([-1, 1])

    cp1_x = sx + dx * 0.3 + perp_x * offset1
    cp1_y = sy + dy * 0.3 + perp_y * offset1
    cp2_x = sx + dx * 0.7 + perp_x * offset2
    cp2_y = sy + dy * 0.7 + perp_y * offset2

    # Generate time distribution using 4-phase model
    delays = _four_phase_delays(n, duration_ms)

    # Build main curve points
    points: list[TrajectoryPoint] = []
    for i in range(1, n + 1):
        t = i / n
        bx, by = _cubic_bezier(t, sx, sy, cp1_x, cp1_y, cp2_x, cp2_y, ex, ey)

        # Add jitter (perpendicular offset)
        if jitter > 0:
            jitter_offset = random.uniform(-jitter, jitter)
            bx += perp_x * jitter_offset
            by += perp_y * jitter_offset

        points.append(TrajectoryPoint(
            x=int(round(bx)),
            y=int(round(by)),
            delay_s=delays[i - 1],
        ))

    # Overshoot: extend past target, then correct back
    if overshoot > 0 and n >= 4:
        points = _add_overshoot(points, sx, sy, ex, ey, overshoot, duration_ms)

    # Ensure final point is exactly on target
    if points:
        last = points[-1]
        points[-1] = TrajectoryPoint(x=ex, y=ey, delay_s=last.delay_s)

    return points


def _cubic_bezier(
    t: float,
    x0: float, y0: float,
    x1: float, y1: float,
    x2: float, y2: float,
    x3: float, y3: float,
) -> tuple[float, float]:
    """Evaluate a cubic Bezier curve at parameter *t* (0..1)."""
    u = 1.0 - t
    u2 = u * u
    t2 = t * t
    a = u2 * u
    b = 3.0 * u2 * t
    c = 3.0 * u * t2
    d = t2 * t
    return (
        a * x0 + b * x1 + c * x2 + d * x3,
        a * y0 + b * y1 + c * y2 + d * y3,
    )


def _four_phase_delays(n: int, duration_ms: int) -> list[float]:
    """Generate per-step delays following a 4-phase acceleration model.

    Steps in fast phases get shorter delays; steps in slow phases get
    longer delays. Randomness is added to each step (±30%) to avoid
    mechanical regularity.

    Args:
        n: Total number of steps.
        duration_ms: Total duration in milliseconds.

    Returns:
        List of *n* delay values in seconds.
    """
    total_s = duration_ms / 1000.0

    # Assign each step to a phase based on its normalized position
    raw_weights: list[float] = []
    for i in range(n):
        t = (i + 0.5) / n  # midpoint of this step
        weight = _phase_weight(t)
        raw_weights.append(weight)

    # Inverse weight: higher speed → shorter delay
    inv = [1.0 / w if w > 0 else 1.0 for w in raw_weights]
    inv_sum = sum(inv)

    # Distribute total duration proportionally to inverse weights
    delays: list[float] = []
    for w in inv:
        base = total_s * (w / inv_sum)
        # Add ±30% jitter to timing for naturalism
        jittered = base * random.uniform(0.7, 1.3)
        delays.append(max(0.001, jittered))

    # Normalize so total equals target duration
    actual_sum = sum(delays)
    if actual_sum > 0:
        scale = total_s / actual_sum
        delays = [d * scale for d in delays]

    return delays


def _phase_weight(t: float) -> float:
    """Return the speed weight for normalized time *t* (0..1)."""
    for start, end, weight in _PHASES:
        if t < end:
            return weight
    return _PHASES[-1][2]


def _add_overshoot(
    points: list[TrajectoryPoint],
    sx: int, sy: int, ex: int, ey: int,
    overshoot_px: float, duration_ms: int,
) -> list[TrajectoryPoint]:
    """Append overshoot and correction points to a trajectory.

    Extends the path past the target by *overshoot_px* pixels along
    the movement direction, then adds correction points back to the
    target. The overshoot phase takes ~10% of total duration.

    Args:
        points: Existing trajectory points.
        sx, sy: Start coordinates.
        ex, ey: End (target) coordinates.
        overshoot_px: Pixels to overshoot past target.
        duration_ms: Original total duration in ms.

    Returns:
        New list with overshoot + correction appended.
    """
    dx = ex - sx
    dy = ey - sy
    dist = math.hypot(dx, dy) or 1.0

    # Direction unit vector
    ux = dx / dist
    uy = dy / dist

    # Overshoot point
    ox = int(round(ex + ux * overshoot_px))
    oy = int(round(ey + uy * overshoot_px))

    # Correction timing: ~10% of total duration
    correction_time = (duration_ms / 1000.0) * 0.10
    correction_steps = max(3, len(points) // 8)
    step_delay = correction_time / correction_steps

    # Build correction path (overshoot → target)
    correction: list[TrajectoryPoint] = []
    # First: overshoot point
    correction.append(TrajectoryPoint(x=ox, y=oy, delay_s=step_delay))
    # Then: ease back to target
    for i in range(1, correction_steps + 1):
        t = i / correction_steps
        # Ease-out cubic for smooth deceleration
        t_eased = 1.0 - (1.0 - t) ** 3
        cx = int(round(ox + (ex - ox) * t_eased))
        cy = int(round(oy + (ey - oy) * t_eased))
        correction.append(TrajectoryPoint(x=cx, y=cy, delay_s=step_delay))

    return points + correction
