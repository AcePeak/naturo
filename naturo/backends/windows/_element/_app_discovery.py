"""Window and application resolution: map ``--app``/``--window-title``/``--pid`` to a HWND.

:class:`AppDiscoveryMixin` owns the scoring logic that turns a user-supplied
application name, window title, PID, or raw handle into a concrete window
handle (:meth:`_resolve_hwnd` / :meth:`_resolve_hwnds`), including the
session-aware ranking, desktop-shell deprioritization, and the UWP
ApplicationFrameHost fallback (:meth:`_uwp_afh_fallback`).  Split out of the
former monolithic ``_element`` module for maintainability (#720).
"""

from __future__ import annotations

import logging
import ntpath
from typing import ClassVar, Optional

from naturo.backends.base import WindowInfo as BaseWindowInfo
from naturo.process import _get_console_session_id, _get_process_session_id

logger = logging.getLogger(__name__)


class AppDiscoveryMixin:
    """Resolve application names, window titles, and PIDs to window handles."""

    # Cross-locale alias map for --app matching (#469).
    # Maps lowercase alias → set of lowercase process-name stems that
    # should be considered a match.  Values must be English process names
    # (without .exe) since Windows process names are always in English.
    _APP_ALIASES: dict[str, set[str]] = {
        # Calculator
        "calculator": {"calc", "calculatorapp"},
        "calc": {"calc", "calculatorapp"},
        "计算器": {"calc", "calculatorapp"},
        # Notepad
        "notepad": {"notepad"},
        "记事本": {"notepad"},
        # Settings
        "settings": {"systemsettings"},
        "设置": {"systemsettings"},
        # Paint
        "paint": {"mspaint"},
        "画图": {"mspaint"},
        # File Explorer
        "explorer": {"explorer"},
        "file explorer": {"explorer"},
        "文件资源管理器": {"explorer"},
        # Edge
        "edge": {"msedge"},
        "microsoft edge": {"msedge"},
        # Task Manager
        "task manager": {"taskmgr"},
        "任务管理器": {"taskmgr"},
        # Command Prompt
        "command prompt": {"cmd"},
        "命令提示符": {"cmd"},
        # Terminal
        "terminal": {"windowsterminal"},
        "终端": {"windowsterminal"},
        # WordPad
        "wordpad": {"wordpad"},
        "写字板": {"wordpad"},
        # Snipping Tool / Screen Sketch
        "snipping tool": {"snippingtool", "screensketch"},
        "截图工具": {"snippingtool", "screensketch"},
    }
    @staticmethod
    def _get_foreground_hwnd() -> int:
        """Get the currently focused foreground window handle.

        Returns:
            HWND of the foreground window, or 0 on failure.
        """
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            return hwnd or 0
        except Exception:
            return 0
    @staticmethod
    def _get_window_class_name(hwnd: int) -> str:
        """Get the window class name for a given HWND.

        Used to identify special windows like Program Manager ("Progman")
        which should be deprioritized during app resolution (#524).

        Args:
            hwnd: Window handle.

        Returns:
            Window class name, or empty string on failure.
        """
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
            return buf.value
        except Exception:
            return ""
    # Window classes that represent the desktop shell rather than real
    # application windows.  explorer.exe hosts both the desktop and File
    # Explorer; when --app explorer is used, these should be deprioritized
    # so actual File Explorer windows are preferred (#524).
    _DESKTOP_SHELL_CLASSES: ClassVar[frozenset[str]] = frozenset({
        "Progman",   # Program Manager (desktop icons)
        "WorkerW",   # Desktop worker window (wallpaper layer)
    })
    def _resolve_hwnd(self, app: Optional[str] = None,
                      window_title: Optional[str] = None,
                      hwnd: Optional[int] = None,
                      pid: Optional[int] = None) -> int:
        """Resolve a window handle from app name, window title, pid, or direct hwnd.

        Matching strategy (BUG-069/BUG-070):

        When ``app`` is provided, matches against **process name and aliases
        first** (``.exe`` suffix stripped).  If no process name match is
        found, falls back to **window title matching** (#671).  This allows
        ``--app claude`` to find a Terminal window titled "claude" while
        still preventing cross-process contamination when a process name
        match exists (#465).  When ``window_title`` is provided, matches
        against window title only.

        When ``pid`` is provided (alone or combined with app/window_title),
        only windows belonging to that process are considered (#471).  Among
        matching PID windows, the largest-area window in the interactive
        session is preferred.

        Scoring for ``--app`` (higher = better match):
          4 — exact process-name match  (e.g. ``explorer`` == ``explorer.exe``)
          3 — process-name substring    (e.g. ``expl`` in ``explorer.exe``)
        Alias matches (e.g. ``calculator`` → ``calculatorapp``) use the same
        scores as direct process-name matches.

        Session awareness (#230): When multiple windows match with equal
        scores, windows in the active console session are strongly preferred
        over windows in Session 0 (the non-interactive services session).
        This prevents schtasks/remote contexts from targeting ghost windows.

        Foreground preference (#449): When multiple windows match with equal
        scores and session status, the foreground (focused) window is
        preferred.  This ensures consecutive commands (``type`` then
        ``capture``) target the same window deterministically.

        Case-insensitive throughout.  Among equal scores the window with
        the largest area wins (#440: popup menus are tiny top-level windows
        that should not beat the main application window).

        Args:
            app: Application/process name to search for (case-insensitive,
                partial match).  Compared against process name first, then
                window title as fallback.
            window_title: Window title pattern (case-insensitive, partial
                match).  Compared against window title only.
            hwnd: Direct window handle (takes priority).
            pid: Process ID.  When provided, only windows owned by this
                process are considered.  Can be combined with app/window_title
                for additional filtering, or used alone (#471).

        Returns:
            Window handle (HWND), or 0 for the foreground window.

        Raises:
            WindowNotFoundError: When no matching window is found.  The error
                message includes up to 5 candidate windows.
        """
        if hwnd:
            # (#788) Validate that a directly-passed HWND is still alive.
            from naturo.cli.interaction._common import _is_hwnd_alive
            if not _is_hwnd_alive(hwnd):
                from naturo.errors import WindowNotFoundError
                raise WindowNotFoundError(
                    f"HWND {hwnd}",
                    suggested_action=(
                        f"Window handle {hwnd} is no longer valid — the window "
                        f'was closed. Run "naturo app list" to find current windows.'
                    ),
                )
            return hwnd

        search = app or window_title
        if not search and not pid:
            return 0  # foreground window

        search_lower = search.lower() if search else ""
        windows = self.list_windows()

        # (#471) Filter by PID when provided — only consider windows owned
        # by the specified process.  This is applied before scoring so that
        # PID-based targeting is never overridden by a higher-scoring window
        # from a different process.
        if pid is not None:
            windows = [w for w in windows if w.pid == pid]
            if not windows:
                from naturo.errors import WindowNotFoundError
                raise WindowNotFoundError(
                    f"PID {pid}",
                    suggested_action=(
                        f"No visible window found for PID {pid}. "
                        "The process may have exited or has no visible windows.\n"
                        "Tip: use 'naturo list windows' to see all windows."
                    ),
                )

        # Get console session for session-aware ranking (#230)
        console_session = _get_console_session_id()

        # Get foreground HWND for deterministic tie-breaking (#449)
        fg_hwnd = self._get_foreground_hwnd()

        # --app → match process name first; --window-title → match title only
        match_process = app is not None

        # (#471) When only --pid is given (no app/window_title), all windows
        # belonging to the PID are valid candidates — assign a base score of 1
        # so that the best-window selection logic (session, foreground, area)
        # picks the most appropriate one.
        pid_only = pid is not None and not search

        best_score = 0
        best_session_bonus = False  # True if best_window is in console session
        best_is_foreground = False  # True if best_window is the foreground window
        best_window = None

        for w in windows:
            score = 0
            # (#789) Extract basename before matching — process_name may
            # contain a full path (e.g. C:\Windows\System32\notepad.exe)
            # and matching against the full path causes --app system to
            # incorrectly match any process in System32.
            proc_stem = ntpath.basename(w.process_name).lower()
            # Strip .exe suffix for comparison
            if proc_stem.endswith(".exe"):
                proc_stem = proc_stem[:-4]
            title_lower = w.title.lower()

            if pid_only:
                # All PID-filtered windows are valid candidates
                score = 1
            elif match_process:
                # Process-name matching (priority)
                if search_lower == proc_stem:
                    score = 4  # exact process name
                elif search_lower in proc_stem:
                    score = 3  # substring in process name
                # (#465) Title-only fallback removed from --app matching.
                # When --app is used, we only match by process name or alias.
                # Title-only matches caused cross-process contamination: e.g.
                # --app notepad picking a Chrome window titled "help with notepad".
                # Use --window-title for title-based matching.
                #
                # Alias matching: cross-locale app name resolution
                if score == 0:
                    aliases = self._APP_ALIASES.get(search_lower, set())
                    for alias in aliases:
                        if alias == proc_stem:
                            score = 4  # alias → exact process name
                            break
                        if alias in proc_stem:
                            score = 3  # alias → substring in process name
                            break
            else:
                # --window-title: only match window title
                if search_lower == title_lower:
                    score = 4  # exact title
                elif search_lower in title_lower:
                    score = 1  # substring in title

            if score == 0:
                continue

            # (#524) Desktop shell deprioritization: explorer.exe hosts both
            # File Explorer and the desktop (Program Manager, class "Progman").
            # When --app explorer is used, users expect File Explorer, not the
            # desktop.  Detect shell windows by class name and reduce their
            # score to 1, so any real File Explorer window (score 3-4) wins.
            # If no File Explorer windows exist, the desktop still matches.
            if match_process:
                wclass = self._get_window_class_name(w.handle)
                if wclass in self._DESKTOP_SHELL_CLASSES:
                    score = 1  # demote desktop shell windows

            # Session-aware ranking (#230): prefer windows in the active
            # console session over windows in Session 0 (services session).
            # This prevents schtasks-launched commands from targeting ghost
            # processes that exist in the non-interactive session.
            in_console = False
            if console_session >= 0:
                w_session = _get_process_session_id(w.pid)
                in_console = (w_session == console_session)

            # (#449) Check if this window is the foreground window
            is_foreground = (fg_hwnd != 0 and w.handle == fg_hwnd)

            # Decision: pick this window if it has a higher score, or if
            # scores are equal but this window is in the console session
            # while the current best is not.  Among equal score + session,
            # prefer the foreground window (#449: consecutive commands
            # should target the same window deterministically).  Finally,
            # prefer the larger window area (#440: popup menus are tiny
            # top-level windows that should not beat the main window).
            if score > best_score:
                best_score = score
                best_session_bonus = in_console
                best_is_foreground = is_foreground
                best_window = w
            elif score == best_score and best_window is not None:
                if in_console and not best_session_bonus:
                    # Same score but this one is in the interactive session
                    best_session_bonus = in_console
                    best_is_foreground = is_foreground
                    best_window = w
                elif in_console == best_session_bonus:
                    # (#449) Prefer the foreground window for deterministic
                    # resolution when multiple windows match equally.
                    if is_foreground and not best_is_foreground:
                        best_is_foreground = True
                        best_window = w
                    elif is_foreground == best_is_foreground:
                        w_area = w.width * w.height
                        best_area = best_window.width * best_window.height
                        if w_area > best_area:
                            best_window = w

        if best_window is not None:
            # UWP/WinUI apps: the real UI tree lives under
            # ApplicationFrameHost.exe, not the inner process window
            # (e.g. CalculatorApp.exe).  When we matched a non-frame
            # process, check for an ApplicationFrameHost window with the
            # same title and prefer it — its element tree is complete.
            # Extract basename for comparison — process_name may be a
            # full path (e.g. "C:\...\CalculatorApp.exe")
            import os as _os
            best_proc = _os.path.basename(best_window.process_name).lower()
            if best_proc.endswith(".exe"):
                best_proc = best_proc[:-4]
            if best_proc != "applicationframehost":
                # (#394) Collect ALL AFH windows with matching title, then
                # prefer one that actually has a CoreWindow child (live UI).
                # Stale AFH windows (e.g., from schtasks-launched instances)
                # may linger without a CoreWindow child, producing empty
                # UIA trees.
                afh_candidates = []
                for w in windows:
                    frame_proc = _os.path.basename(w.process_name).lower()
                    if frame_proc.endswith(".exe"):
                        frame_proc = frame_proc[:-4]
                    if (
                        frame_proc == "applicationframehost"
                        and w.title == best_window.title
                        and w.handle != best_window.handle
                    ):
                        afh_candidates.append(w)

                if afh_candidates:
                    # (#394 v2) Prefer AFH window with a CoreWindow or
                    # DesktopWindowXamlSource child — these host the actual
                    # app UI.  Stale AFH windows may have title bar and
                    # input sink children but no content window, yielding
                    # empty UIA trees.
                    chosen_afh = None
                    for afh_w in afh_candidates:
                        if self._afh_has_content_window(afh_w.handle):
                            chosen_afh = afh_w
                            logger.debug(
                                "UWP fixup: AFH hwnd=%s has content "
                                "window (CoreWindow/XAML), selecting it",
                                afh_w.handle,
                            )
                            break
                    if chosen_afh is None:
                        # No AFH has content children — fall back to first
                        chosen_afh = afh_candidates[0]
                        logger.debug(
                            "UWP fixup: no AFH has content children, "
                            "falling back to first AFH hwnd=%s",
                            chosen_afh.handle,
                        )
                    best_window = chosen_afh

            return best_window.handle

        # (#569) UWP fallback: UWP apps (Calculator, Settings, etc.) have
        # their windows owned by ApplicationFrameHost.exe, not by the
        # actual app process (e.g. CalculatorApp.exe).  When process-name
        # matching finds nothing, probe each AFH window's content child
        # to find the real app process and match against that.
        if match_process and best_window is None:
            best_window = self._uwp_afh_fallback(
                search_lower, windows, console_session,
            )
            if best_window is not None:
                return best_window.handle

        # (#671) Window title fallback for --app: when no process name
        # matched, try matching against window titles.  This allows
        # `--app claude` to find a Terminal window titled "claude" when
        # no process named "claude" exists.  Title matches use score 2
        # (below process name matches at 3-4) so they never override
        # a valid process name match.  The initial process-name-only
        # pass above (#465) prevents cross-process contamination when
        # a process name match exists.
        if match_process and best_window is None:
            for w in windows:
                title_lower = w.title.lower()
                if not title_lower:
                    continue

                score = 0
                if search_lower == title_lower:
                    score = 4  # exact title match
                elif search_lower in title_lower:
                    score = 2  # substring in title

                if score == 0:
                    continue

                in_console = False
                if console_session >= 0:
                    w_session = _get_process_session_id(w.pid)
                    in_console = (w_session == console_session)

                is_foreground = (fg_hwnd != 0 and w.handle == fg_hwnd)

                if score > best_score:
                    best_score = score
                    best_session_bonus = in_console
                    best_is_foreground = is_foreground
                    best_window = w
                elif score == best_score and best_window is not None:
                    if in_console and not best_session_bonus:
                        best_session_bonus = in_console
                        best_is_foreground = is_foreground
                        best_window = w
                    elif in_console == best_session_bonus:
                        if is_foreground and not best_is_foreground:
                            best_is_foreground = True
                            best_window = w
                        elif is_foreground == best_is_foreground:
                            w_area = w.width * w.height
                            best_area = best_window.width * best_window.height
                            if w_area > best_area:
                                best_window = w

            if best_window is not None:
                return best_window.handle

        # No match — build candidate suggestions (BUG-070)
        from naturo.errors import WindowNotFoundError

        candidates = []
        seen = set()
        for w in windows:
            label = f"{w.process_name} — \"{w.title}\""
            if label not in seen and w.title:
                seen.add(label)
                candidates.append(label)
            if len(candidates) >= 5:
                break

        search_label = search or f"PID {pid}"
        hint = f"No window matching '{search_label}'."
        if candidates:
            hint += " Did you mean:\n" + "\n".join(f"  • {c}" for c in candidates)
        hint += "\nTip: use 'naturo list windows' to see all windows."

        raise WindowNotFoundError(search_label, suggested_action=hint)
    def _resolve_hwnds(self, app: Optional[str] = None,
                       window_title: Optional[str] = None) -> list[int]:
        """Resolve ALL window handles matching app name or window title.

        Same matching logic as _resolve_hwnd, but returns ALL windows that
        match (score > 0), sorted by score descending.

        Used by `see --app` to enumerate all windows of an application (#304).

        Args:
            app: Application/process name (case-insensitive, partial match).
            window_title: Window title pattern (case-insensitive, partial match).

        Returns:
            List of window handles (HWNDs), sorted by match quality (best first).
            Empty list if no matches found.

        Note:
            Does NOT accept `hwnd` parameter (use [hwnd] if you have a handle).
            Skips foreground window fallback (returns [] if no search term).
        """
        search = app or window_title
        if not search:
            return []

        search_lower = search.lower()
        windows = self.list_windows()
        console_session = _get_console_session_id()
        match_process = app is not None

        # Collect all matching windows with their scores
        matches = []  # [(score, in_console, title_len, WindowInfo), ...]

        for w in windows:
            score = 0
            # (#789) Extract basename — see _resolve_hwnd for rationale.
            proc_stem = ntpath.basename(w.process_name).lower()
            if proc_stem.endswith(".exe"):
                proc_stem = proc_stem[:-4]
            title_lower = w.title.lower()

            if match_process:
                # Process-name matching
                if search_lower == proc_stem:
                    score = 4
                elif search_lower in proc_stem:
                    score = 3
                # (#465) No title fallback for --app (see _resolve_hwnd)
                # Alias matching
                if score == 0:
                    aliases = self._APP_ALIASES.get(search_lower, set())
                    for alias in aliases:
                        if alias == proc_stem:
                            score = 4
                            break
                        if alias in proc_stem:
                            score = 3
                            break
            else:
                # --window-title: only match window title
                if search_lower == title_lower:
                    score = 4
                elif search_lower in title_lower:
                    score = 1

            if score == 0:
                continue

            # Session-aware ranking
            in_console = False
            if console_session >= 0:
                w_session = _get_process_session_id(w.pid)
                in_console = (w_session == console_session)

            matches.append((score, in_console, len(w.title), w))

        # Sort by: score desc, console first, shorter title first
        # (in_console: True > False, so negate for descending)
        matches.sort(key=lambda x: (x[0], x[1], -x[2]), reverse=True)

        # Extract HWNDs
        hwnds = [m[3].handle for m in matches]

        # UWP/ApplicationFrameHost fixup: prefer frame windows when available.
        # Search ALL windows (not just scored matches) for AFH counterparts,
        # matching the same logic as _resolve_hwnd (#559).  UWP apps like
        # Calculator run under CalculatorApp.exe but their UI tree lives
        # under the ApplicationFrameHost.exe window.  The AFH window may
        # not score any points for the search term (e.g. "计算器") so we
        # must search the full window list.
        import os as _os
        fixed_hwnds = []
        for hwnd in hwnds:
            # Find the WindowInfo for this hwnd
            w_info = next((m[3] for m in matches if m[3].handle == hwnd), None)
            if not w_info:
                fixed_hwnds.append(hwnd)
                continue

            proc = _os.path.basename(w_info.process_name).lower()
            if proc.endswith(".exe"):
                proc = proc[:-4]

            if proc != "applicationframehost":
                # (#559) Search ALL windows for AFH with matching title,
                # then prefer one with a CoreWindow child (live UI),
                # mirroring _resolve_hwnd logic (#394).
                afh_candidates = []
                for w in windows:
                    frame_proc = _os.path.basename(w.process_name).lower()
                    if frame_proc.endswith(".exe"):
                        frame_proc = frame_proc[:-4]
                    if (
                        frame_proc == "applicationframehost"
                        and w.title == w_info.title
                        and w.handle != hwnd
                    ):
                        afh_candidates.append(w)

                if afh_candidates:
                    # Prefer AFH with content window (CoreWindow/XAML)
                    chosen_afh = None
                    for afh_w in afh_candidates:
                        if self._afh_has_content_window(afh_w.handle):
                            chosen_afh = afh_w
                            break
                    if chosen_afh is None:
                        chosen_afh = afh_candidates[0]
                    fixed_hwnds.append(chosen_afh.handle)
                else:
                    fixed_hwnds.append(hwnd)
            else:
                fixed_hwnds.append(hwnd)

        # Deduplicate (in case of frame window replacements)
        seen = set()
        result = []
        for h in fixed_hwnds:
            if h not in seen:
                seen.add(h)
                result.append(h)

        # (#569) UWP fallback: when no windows matched by process name,
        # probe AFH windows' content children for the real app process.
        if not result and match_process:
            console_session = _get_console_session_id()
            afh_match = self._uwp_afh_fallback(
                search_lower, windows, console_session,
            )
            if afh_match is not None:
                result.append(afh_match.handle)

        # (#671) Window title fallback for --app: when no process name
        # matched, try matching against window titles.  This allows
        # `--app claude` to find a Terminal window titled "claude".
        if not result and match_process:
            title_matches = []
            for w in windows:
                title_lower = w.title.lower()
                if not title_lower:
                    continue
                score = 0
                if search_lower == title_lower:
                    score = 4
                elif search_lower in title_lower:
                    score = 2
                if score > 0:
                    in_console = False
                    if console_session >= 0:
                        w_session = _get_process_session_id(w.pid)
                        in_console = (w_session == console_session)
                    title_matches.append((score, in_console, len(w.title), w))

            if title_matches:
                title_matches.sort(
                    key=lambda x: (x[0], x[1], -x[2]), reverse=True,
                )
                result = [m[3].handle for m in title_matches]

        return result
    def _uwp_afh_fallback(
        self,
        search_lower: str,
        windows: list,
        console_session: int,
    ) -> Optional["BaseWindowInfo"]:
        """UWP fallback: find an AFH window whose child process matches (#569).

        UWP apps (Calculator, Settings, etc.) have their top-level windows
        owned by ApplicationFrameHost.exe.  Normal process-name matching
        cannot find these because the AFH process name never matches
        user-facing app names like "calculator".

        This method probes each AFH window's content child (CoreWindow) to
        discover the real app process (e.g. CalculatorApp.exe), then checks
        if that process name matches the search term or its aliases.

        Only called when the primary scoring loop found no matches.

        Args:
            search_lower: Lowercase search term from ``--app``.
            windows: Full window list from ``list_windows()``.
            console_session: Console session ID for session-aware ranking.

        Returns:
            The best matching AFH WindowInfo, or None if no match.
        """
        import os as _os

        # Build the set of process stems to match against (search + aliases)
        target_stems: set[str] = {search_lower}
        aliases = self._APP_ALIASES.get(search_lower, set())
        target_stems.update(aliases)

        best_afh = None
        best_in_console = False

        for w in windows:
            proc = _os.path.basename(w.process_name).lower()
            if proc.endswith(".exe"):
                proc = proc[:-4]
            if proc != "applicationframehost":
                continue
            if not self._afh_has_content_window(w.handle):
                continue

            # Resolve the real app PID/exe inside this AFH window
            child_pid, child_exe = self._resolve_uwp_child_pid(w.handle)
            if child_pid is None or child_exe is None:
                continue

            child_stem = _os.path.basename(child_exe).lower()
            if child_stem.endswith(".exe"):
                child_stem = child_stem[:-4]

            # Check if the child process matches any target stem
            matched = False
            for stem in target_stems:
                if stem == child_stem or stem in child_stem:
                    matched = True
                    break
            if not matched:
                continue

            # Session-aware ranking: prefer console session
            in_console = False
            if console_session >= 0:
                w_session = _get_process_session_id(w.pid)
                in_console = (w_session == console_session)

            if best_afh is None or (in_console and not best_in_console):
                best_afh = w
                best_in_console = in_console

        if best_afh is not None:
            logger.debug(
                "UWP AFH fallback (#569): matched AFH hwnd=%s for "
                "search '%s'",
                best_afh.handle, search_lower,
            )

        return best_afh
