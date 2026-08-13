"""Application listing, launching, and quitting."""

from __future__ import annotations

import logging
import os
import subprocess
import time

logger = logging.getLogger(__name__)


class AppMixin:
    """List, launch, and quit applications."""

    def list_apps(self) -> list[dict]:
        """List running applications with visible, non-minimized windows.

        Filters out known system/framework host processes that have visible
        windows but are not user-facing applications.

        Returns:
            List of dicts with keys: name, pid, title, path, process.
        """
        # Consume the *unresolved* window list: this method runs its own UWP
        # child resolution below, keyed off the ApplicationFrameHost host
        # basename. ``list_windows`` now pre-resolves that host PID (#958), which
        # would hide the marker this detection depends on — so read the raw view.
        windows = self._list_windows_unresolved()
        seen_pids: set[int] = set()
        seen_uwp: set[tuple[int, str]] = set()
        apps: list[dict] = []
        for w in windows:
            if not w.is_visible or w.is_minimized or w.pid in seen_pids:
                continue
            basename = os.path.basename(w.process_name).lower()
            if basename in self._SYSTEM_PROCESS_NAMES:
                continue
            # Skip windows with empty titles (likely invisible/utility windows)
            if not w.title or not w.title.strip():
                continue
            # UWP apps hosted by ApplicationFrameHost.exe: resolve the
            # real child process PID so it matches `app inspect` output
            # (#267).  The AFH window hosts the UWP app's CoreWindow as a
            # child; that child belongs to the actual app process.
            if basename == self._UWP_HOST_PROCESS:
                real_pid, real_exe = self._resolve_uwp_child_pid(w.handle)
                app_pid = real_pid or w.pid
                app_exe = real_exe or w.process_name
                key = (app_pid, w.title)
                if key in seen_uwp:
                    continue
                seen_uwp.add(key)
                apps.append({
                    "name": w.title,
                    "pid": app_pid,
                    "title": w.title,
                    "path": app_exe,
                    "process": app_exe,
                })
                continue
            seen_pids.add(w.pid)
            apps.append({
                "name": os.path.basename(w.process_name),
                "pid": w.pid,
                "title": w.title,
                "path": w.process_name,
                "process": w.process_name,
            })
        return apps

    def launch_app(self, name: str = "") -> None:
        """Launch an application by name or path.

        Args:
            name: Application name or executable path.

        Raises:
            OSError: If the application cannot be launched.
        """
        subprocess.Popen([name], shell=True)

    # === Quit: window-ownership resolution + verify-before-success (#1197) ===

    def _app_windows(self, name_lower: str) -> list:
        """Enumerate the top-level windows the named app actually owns.

        Matches by process **image name / alias** (case-insensitive), not by a
        launcher PID — so it finds the real window-owning process even when the
        launch returned a short-lived stub PID (the #1197 root cause). Also
        resolves UWP apps hosted by ``ApplicationFrameHost.exe`` via
        ``list_apps`` (which reports the real child PID and the AFH window
        title), so packaged apps are matched too.

        Args:
            name_lower: Lowercased app name (friendly / CJK names accepted).

        Returns:
            The ``WindowInfo`` objects belonging to the named app.
        """
        # Alias/CJK-aware process-name matcher (single source of truth).
        from naturo.process import _matches_app_by_process_name

        try:
            windows = list(self.list_windows())
        except Exception:
            logger.debug("list_windows() unavailable while quitting %r", name_lower)
            windows = []

        # Resolve UWP child PIDs + their AFH window titles via list_apps():
        # list_windows() reports UWP apps as ApplicationFrameHost.exe, which
        # never matches a user-facing name by process image alone (#750).
        uwp_titles: set[str] = set()
        try:
            for app in self.list_apps():
                proc_name = os.path.basename(app.get("process", "")).lower()
                if _matches_app_by_process_name(proc_name, name_lower):
                    if app.get("title"):
                        uwp_titles.add(app["title"])
        except Exception:
            logger.debug("list_apps() fallback failed while quitting %r", name_lower)

        owned = []
        for w in windows:
            proc_name = os.path.basename(w.process_name).lower()
            match = _matches_app_by_process_name(proc_name, name_lower)
            if not match and w.title in uwp_titles:
                if proc_name.removesuffix(".exe") == "applicationframehost":
                    match = True
            if match:
                owned.append(w)
        return owned

    def _resolve_window_owning_pids(self, name_lower: str) -> set[int]:
        """Return the DISTINCT set of PIDs that own a window of the named app.

        Args:
            name_lower: Lowercased app name.

        Returns:
            Set of owning process IDs (empty if the app owns no windows).
        """
        return {w.pid for w in self._app_windows(name_lower)}

    def quit_app(self, name: str = "", force: bool = False) -> None:
        """Quit an application, verifying it is actually gone before returning.

        Resolves the real target processes by **window ownership** (not just the
        launched name/PID), terminates that full PID set — graceful WM_CLOSE
        first unless ``force``, then a hard kill — and then **re-enumerates to
        verify**. If any window of the app survives (including a Win11 Notepad
        crash-recovery respawn under a new PID), a truthful
        :class:`QuitIncompleteError` is raised instead of reporting a false
        success (#1197, the Never-Lie contract).

        Args:
            name: Process name or executable basename (friendly / CJK names ok).
            force: If True, skip the graceful WM_CLOSE and hard-kill immediately.

        Raises:
            QuitIncompleteError: If the app still owns a window after the kill.
        """
        from naturo.errors import QuitIncompleteError

        name_lower = (name or "").lower()

        # 1) Resolve the real window-owning PIDs up front (snapshot the target).
        targets = self._resolve_window_owning_pids(name_lower)

        # 2) Terminate.
        if not force and targets:
            # Graceful: WM_CLOSE every owned window, then wait briefly for the
            # owning processes to exit on their own.
            for w in self._app_windows(name_lower):
                try:
                    self.close_window(hwnd=w.handle)
                except Exception:
                    logger.debug("WM_CLOSE failed for hwnd=%s (%r)", w.handle, name)
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if not self._resolve_window_owning_pids(name_lower):
                    break
                time.sleep(0.2)
            # Hard-kill whatever still owns a window after the graceful window.
            leftovers = self._resolve_window_owning_pids(name_lower)
            for pid in leftovers:
                self._force_kill_pid(pid)
        elif targets:
            # force=True: hard-kill the resolved PID set immediately.
            for pid in targets:
                self._force_kill_pid(pid)
        else:
            # No window-owning process resolved — fall back to a name-based
            # taskkill so headless / no-window instances are still terminated.
            flag = "/F" if force else ""
            cmd = f'taskkill /IM "{name}" {flag}'.strip()
            try:
                subprocess.run(cmd, shell=True, capture_output=True)
            except OSError:
                logger.debug("Fallback taskkill /IM failed for %r", name)

        # 3) VERIFY (Never-Lie core, #1197). Settle briefly — a crash-recovery
        # respawn lands within a few hundred ms — then re-enumerate. If the app
        # still owns any window, report the truth instead of a false success.
        time.sleep(0.4)
        survivors = self._resolve_window_owning_pids(name_lower)
        if survivors:
            respawned = bool(targets) and not (survivors & targets)
            raise QuitIncompleteError(name, sorted(survivors), respawned=respawned)

    def _force_kill_pid(self, pid: int) -> None:
        """Hard-kill a process tree by PID (``taskkill /F /T``).

        ``/T`` kills the whole tree — needed for UWP and tabbed apps like Win11
        Notepad. Failures (already-dead PID) are swallowed; the post-kill
        verification is the authority on whether the app is really gone.
        """
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.debug("Force kill of PID %d failed (may be dead): %s", pid, exc)
