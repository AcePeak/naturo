"""Action recording and replay engine.

Records user-initiated CLI actions into replayable JSON sequences.
Supports recording start/stop, listing, and playback with speed control.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


# Default recordings directory
RECORDINGS_DIR = Path.home() / ".naturo" / "recordings"


@dataclass
class ActionStep:
    """A single recorded action step.

    Attributes:
        command: The naturo command name (click, type, press, etc.).
        args: Command arguments as a dictionary.
        timestamp: Unix timestamp when the action was recorded.
        duration_ms: Time taken to execute the action in milliseconds.
    """
    command: str
    args: dict
    timestamp: float
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        """Convert to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ActionStep":
        """Create an ActionStep from a dictionary.

        Args:
            data: Dictionary with command, args, timestamp, and optional duration_ms.

        Returns:
            ActionStep instance.
        """
        return cls(
            command=data["command"],
            args=data["args"],
            timestamp=data["timestamp"],
            duration_ms=data.get("duration_ms", 0.0),
        )


@dataclass
class Recording:
    """A complete action recording.

    Attributes:
        name: Human-readable recording name.
        recording_id: Unique identifier (timestamp-based).
        created_at: ISO 8601 creation timestamp.
        steps: List of recorded action steps.
        metadata: Optional metadata (app context, screen resolution, etc.).
    """
    name: str
    recording_id: str
    created_at: str
    steps: List[ActionStep] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_step(self, command: str, args: dict, duration_ms: float = 0.0) -> None:
        """Add an action step to the recording.

        Args:
            command: The naturo command name.
            args: Command arguments.
            duration_ms: Execution duration in milliseconds.
        """
        step = ActionStep(
            command=command,
            args=args,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )
        self.steps.append(step)

    def to_dict(self) -> dict:
        """Convert to serializable dictionary."""
        return {
            "name": self.name,
            "recording_id": self.recording_id,
            "created_at": self.created_at,
            "step_count": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Recording":
        """Create a Recording from a dictionary.

        Args:
            data: Dictionary with recording fields.

        Returns:
            Recording instance.
        """
        steps = [ActionStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data["name"],
            recording_id=data["recording_id"],
            created_at=data["created_at"],
            steps=steps,
            metadata=data.get("metadata", {}),
        )

    def total_duration_ms(self) -> float:
        """Calculate total recording duration in milliseconds.

        Returns:
            Sum of all step durations plus inter-step delays.
        """
        if len(self.steps) < 2:
            return sum(s.duration_ms for s in self.steps)
        # Total = last timestamp - first timestamp (in ms) + last step duration
        elapsed = (self.steps[-1].timestamp - self.steps[0].timestamp) * 1000
        return elapsed + self.steps[-1].duration_ms


def _ensure_recordings_dir(directory: Optional[Path] = None) -> Path:
    """Ensure the recordings directory exists.

    Args:
        directory: Custom directory path. Uses default if None.

    Returns:
        Path to the recordings directory.
    """
    d = directory or RECORDINGS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _active_file_path(directory: Optional[Path] = None) -> Path:
    """Get the path to the active recording state file.

    Args:
        directory: Custom recordings directory. Uses default if None.

    Returns:
        Path to .active.json in the recordings directory.
    """
    d = _ensure_recordings_dir(directory)
    return d / ".active.json"


def get_active_recording(directory: Optional[Path] = None) -> Optional[Recording]:
    """Load the active recording from the persistent state file.

    Args:
        directory: Custom recordings directory. Uses default if None.

    Returns:
        The active Recording instance, or None if no recording is in progress.
    """
    active_path = _active_file_path(directory)
    if not active_path.exists():
        return None
    try:
        with open(active_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Recording.from_dict(data)
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def set_active_recording(
    rec: Optional[Recording],
    directory: Optional[Path] = None,
) -> None:
    """Persist or clear the active recording state.

    Args:
        rec: Recording instance to persist, or None to clear the active state.
        directory: Custom recordings directory. Uses default if None.
    """
    active_path = _active_file_path(directory)
    if rec is None:
        if active_path.exists():
            active_path.unlink()
    else:
        _ensure_recordings_dir(directory)
        with open(active_path, "w", encoding="utf-8") as f:
            json.dump(rec.to_dict(), f, indent=2, ensure_ascii=False)


def append_step_to_active(
    command: str,
    args: dict,
    duration_ms: float = 0.0,
    directory: Optional[Path] = None,
) -> bool:
    """Append an action step to the active recording on disk.

    This is the cross-process replacement for the in-memory record_action().
    Each CLI invocation calls this to persist the step immediately.

    Args:
        command: The naturo command name (click, type, press, etc.).
        args: Command arguments as a dictionary.
        duration_ms: Execution duration in milliseconds.
        directory: Custom recordings directory. Uses default if None.

    Returns:
        True if a step was appended, False if no active recording.
    """
    rec = get_active_recording(directory)
    if rec is None:
        return False
    rec.add_step(command, args, duration_ms)
    set_active_recording(rec, directory)
    return True


def generate_recording_id() -> str:
    """Generate a unique recording ID based on current timestamp.

    Returns:
        String ID in format 'rec_YYYYMMDD_HHMMSS'.
    """
    now = datetime.now()
    return f"rec_{now.strftime('%Y%m%d_%H%M%S')}"


def save_recording(recording: Recording, directory: Optional[Path] = None) -> Path:
    """Save a recording to disk as JSON.

    Args:
        recording: The Recording to save.
        directory: Custom directory. Uses default if None.

    Returns:
        Path to the saved JSON file.
    """
    d = _ensure_recordings_dir(directory)
    filepath = d / f"{recording.recording_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(recording.to_dict(), f, indent=2, ensure_ascii=False)
    return filepath


def load_recording(recording_id: str, directory: Optional[Path] = None) -> Recording:
    """Load a recording from disk.

    Args:
        recording_id: The recording ID to load.
        directory: Custom directory. Uses default if None.

    Returns:
        Recording instance.

    Raises:
        FileNotFoundError: If the recording file doesn't exist.
    """
    d = _ensure_recordings_dir(directory)
    filepath = d / f"{recording_id}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Recording not found: {recording_id}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Recording.from_dict(data)


def list_recordings(directory: Optional[Path] = None) -> List[dict]:
    """List all recordings in the directory.

    Args:
        directory: Custom directory. Uses default if None.

    Returns:
        List of recording summaries (id, name, created_at, step_count).
    """
    d = _ensure_recordings_dir(directory)
    recordings = []
    for filepath in sorted(d.glob("rec_*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            recordings.append({
                "recording_id": data["recording_id"],
                "name": data["name"],
                "created_at": data["created_at"],
                "step_count": data.get("step_count", len(data.get("steps", []))),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return recordings


def delete_recording(recording_id: str, directory: Optional[Path] = None) -> bool:
    """Delete a recording from disk.

    Args:
        recording_id: The recording ID to delete.
        directory: Custom directory. Uses default if None.

    Returns:
        True if deleted, False if not found.
    """
    d = _ensure_recordings_dir(directory)
    filepath = d / f"{recording_id}.json"
    if filepath.exists():
        filepath.unlink()
        return True
    return False


def replay_recording(
    recording: Recording,
    speed: float = 1.0,
    dry_run: bool = False,
    step_callback=None,
) -> List[dict]:
    """Replay a recorded action sequence.

    Args:
        recording: The Recording to replay.
        speed: Playback speed multiplier (2.0 = twice as fast, 0.5 = half speed).
        dry_run: If True, print actions without executing them.
        step_callback: Optional callback(step_index, step, result) called after each step.

    Returns:
        List of step results with success/error information.

    Raises:
        ValueError: If speed is not positive.
    """
    if speed <= 0:
        raise ValueError(f"Speed must be positive, got {speed}")

    from naturo.backends.base import get_backend
    backend = get_backend()
    results = []

    for i, step in enumerate(recording.steps):
        # Calculate delay between steps (preserve relative timing)
        if i > 0:
            delay = (step.timestamp - recording.steps[i - 1].timestamp) / speed
            if delay > 0 and not dry_run:
                time.sleep(delay)

        result = {"step": i + 1, "command": step.command, "args": step.args}

        if dry_run:
            result["status"] = "skipped"
            result["reason"] = "dry_run"
        else:
            try:
                _execute_step(backend, step)
                result["status"] = "success"
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        results.append(result)
        if step_callback:
            step_callback(i, step, result)

    return results


def _execute_step(backend, step: ActionStep) -> None:
    """Execute a single action step on the backend.

    Args:
        backend: The automation backend instance.
        step: The ActionStep to execute.

    Raises:
        ValueError: If the command is unknown.
    """
    cmd = step.command
    args = step.args

    if cmd == "click":
        x = args.get("x")
        y = args.get("y")
        button = args.get("button", "left")
        double = args.get("double_click", False)
        backend.click(x=x, y=y, button=button, double_click=double)
    elif cmd == "type":
        text = args.get("text", "")
        wpm = args.get("wpm")
        delay_ms = int(60000 / (wpm * 5)) if wpm else 5
        backend.type_text(text, delay_ms=delay_ms)
    elif cmd == "press":
        key = args.get("key", "")
        count = args.get("count", 1)
        for _ in range(count):
            if "+" in key:
                key_list = [k.strip() for k in key.replace("+", " ").split()]
                backend.hotkey(*key_list)
            else:
                backend.press_key(key)
    elif cmd == "hotkey":
        keys = args.get("keys", [])
        hold_duration = args.get("hold_duration", 0.05)
        backend.hotkey(*keys, hold_duration_ms=int(hold_duration * 1000))
    elif cmd == "scroll":
        direction = args.get("direction", "down")
        amount = args.get("amount", 3)
        x = args.get("x")
        y = args.get("y")
        backend.scroll(direction=direction, amount=amount, x=x, y=y)
    elif cmd == "drag":
        backend.drag(
            from_x=args["from_x"], from_y=args["from_y"],
            to_x=args["to_x"], to_y=args["to_y"],
            steps=args.get("steps", 10),
            duration=args.get("duration", 0.5),
        )
    elif cmd == "move":
        backend.move_mouse(x=args["x"], y=args["y"])
    elif cmd == "wait":
        delay = args.get("seconds", 1.0)
        time.sleep(delay)
    else:
        raise ValueError(f"Unknown command in recording: {cmd}")
