"""Application listing, launching, and quitting."""

from __future__ import annotations


class AppMixin:
    """List, launch, and quit applications."""

    def list_apps(self) -> list[dict]:
        """List running applications with visible, non-minimized windows.

        Filters out known system/framework host processes that have visible
        windows but are not user-facing applications.

        Returns:
            List of dicts with keys: name, pid, title, path, process.
        """
        import os

        windows = self.list_windows()
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
        import subprocess
        subprocess.Popen([name], shell=True)

    def quit_app(self, name: str = "", force: bool = False) -> None:
        """Quit an application by name or PID.

        Args:
            name: Process name or executable basename.
            force: If True, kills the process immediately (taskkill /F).
        """
        import subprocess
        flag = "/F" if force else ""
        cmd = f'taskkill /IM "{name}" {flag}'.strip()
        subprocess.run(cmd, shell=True, capture_output=True)
