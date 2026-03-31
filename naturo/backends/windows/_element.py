"""UI element inspection, window/process resolution, and element tree retrieval."""

from __future__ import annotations

import logging
from typing import ClassVar, Optional

from naturo.backends.base import (ElementInfo as BaseElementInfo, WindowInfo as BaseWindowInfo)
from naturo.bridge import populate_hierarchy
from naturo.errors import NaturoError
from naturo.process import _get_console_session_id, _get_process_session_id

logger = logging.getLogger(__name__)


class ElementMixin:
    """UI element inspection, window/process resolution, and element tree retrieval."""

    # === UI Element Inspection (Phase 1) ===

    def find_element(self, selector: str = "", window_title: Optional[str] = None,
                     hwnd: Optional[int] = None) -> Optional[BaseElementInfo]:
        """Find a UI element by selector string.

        The selector format is "role:name" (e.g., "Button:OK") or just a name.

        Args:
            selector: Element selector in "role:name" or "name" format.
            window_title: Not yet used (reserved for future).
            hwnd: Target window handle.  When provided, searches within this
                window instead of the foreground window (#525).

        Returns:
            ElementInfo if found, None otherwise.
        """
        core = self._ensure_core()

        # Parse selector into role and name
        role = None
        name = None
        if ":" in selector:
            parts = selector.split(":", 1)
            role = parts[0] if parts[0] else None
            name = parts[1] if parts[1] else None
        else:
            name = selector if selector else None

        result = core.find_element(hwnd=hwnd or 0, role=role, name=name)
        if result is None:
            return None

        return BaseElementInfo(
            id=result.id,
            role=result.role,
            name=result.name,
            value=result.value,
            x=result.x,
            y=result.y,
            width=result.width,
            height=result.height,
            children=[],
            properties={},
        )

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
            proc_stem = w.process_name.lower()
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
            proc_stem = w.process_name.lower()
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

    @staticmethod
    def _find_uwp_content_hwnd(parent_hwnd: int) -> list:
        """Find content child HWNDs inside an ApplicationFrameHost window.

        UWP and WinUI 3 apps host their actual UI inside child windows of the
        ApplicationFrameHost top-level window.  Classic UWP uses
        ``Windows.UI.Core.CoreWindow``; WinUI 3 (Windows App SDK) may use
        other window classes.  This method enumerates all child windows so
        the caller can try each one for a non-empty UIA element tree.

        The children are returned in priority order: known UWP/WinUI classes
        first (CoreWindow, DesktopWindowXamlSource), then any remaining
        visible children.

        Args:
            parent_hwnd: Handle of the ApplicationFrameHost top-level window.

        Returns:
            List of child HWNDs to try, ordered by priority (best first).
        """
        import sys
        if sys.platform != "win32":
            return []
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # Enumerate all child windows
            children = []
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM,
            )

            def _enum_cb(hwnd, _lparam):
                children.append(int(hwnd))
                return True

            user32.EnumChildWindows(
                wintypes.HWND(parent_hwnd), WNDENUMPROC(_enum_cb), 0,
            )

            if not children:
                return []

            # Classify by window class name for priority ordering
            GetClassNameW = user32.GetClassNameW
            GetClassNameW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
            GetClassNameW.restype = ctypes.c_int

            PRIORITY_CLASSES = {
                "windows.ui.core.corewindow": 0,   # Classic UWP
                "desktopwindowxamlsource": 1,       # WinUI 3
            }

            prioritized = []
            rest = []
            for hwnd in children:
                cls_buf = ctypes.create_unicode_buffer(256)
                GetClassNameW(wintypes.HWND(hwnd), cls_buf, 256)
                cls_name = cls_buf.value.lower()
                prio = PRIORITY_CLASSES.get(cls_name)
                if prio is not None:
                    prioritized.append((prio, hwnd, cls_buf.value))
                else:
                    rest.append(hwnd)

            prioritized.sort(key=lambda t: t[0])
            result = [h for _, h, _ in prioritized] + rest

            if prioritized:
                logger.debug(
                    "UWP child windows for AFH %s: priority=%s, other=%d",
                    parent_hwnd,
                    [(cls, h) for _, h, cls in prioritized],
                    len(rest),
                )

            return result
        except Exception:
            return []

    def _resolve_uwp_child_pid(
        self, afh_hwnd: int,
    ) -> tuple[Optional[int], Optional[str]]:
        """Resolve the real process PID/exe for a UWP app inside AFH (#267).

        ApplicationFrameHost.exe hosts UWP apps as child windows. The
        child CoreWindow belongs to the actual app process (e.g.,
        CalculatorApp.exe). This method finds that child and returns its
        PID and executable path so ``list_apps`` reports the same PID as
        ``app inspect``.

        Args:
            afh_hwnd: Window handle of the ApplicationFrameHost top-level window.

        Returns:
            Tuple of (pid, exe_path) for the real app process, or
            (None, None) if resolution fails.
        """
        import sys
        if sys.platform != "win32":
            return None, None
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            afh_pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(
                wintypes.HWND(afh_hwnd), ctypes.byref(afh_pid),
            )
            afh_pid_val = afh_pid.value

            # Strategy 1: Use FindWindowExW to find CoreWindow directly.
            # This is more reliable than EnumChildWindows because
            # GetWindowThreadProcessId on CoreWindow always returns the
            # real app PID, even in schtask sessions.
            FindWindowExW = user32.FindWindowExW
            FindWindowExW.argtypes = [
                wintypes.HWND, wintypes.HWND,
                wintypes.LPCWSTR, wintypes.LPCWSTR,
            ]
            FindWindowExW.restype = wintypes.HWND

            core_hwnd = FindWindowExW(
                wintypes.HWND(afh_hwnd), None,
                "Windows.UI.Core.CoreWindow", None,
            )
            if core_hwnd:
                core_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(core_hwnd, ctypes.byref(core_pid))
                if core_pid.value != afh_pid_val and core_pid.value != 0:
                    logger.debug(
                        "UWP CoreWindow found: hwnd=%s pid=%d (afh=%d)",
                        core_hwnd, core_pid.value, afh_pid_val,
                    )
                    pid = core_pid.value
                    exe_path = self._get_process_exe_path(pid)
                    return pid, exe_path

            # Strategy 2: Enumerate all child windows and find one with
            # a different PID (fallback for WinUI 3 / non-CoreWindow apps).
            children = self._find_uwp_content_children(afh_hwnd)
            logger.debug(
                "UWP child PID resolution: AFH hwnd=%s pid=%d, children=%d",
                afh_hwnd, afh_pid_val, len(children),
            )
            for child_hwnd in children:
                child_pid = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(
                    wintypes.HWND(child_hwnd), ctypes.byref(child_pid),
                )
                if child_pid.value != afh_pid_val and child_pid.value != 0:
                    pid = child_pid.value
                    exe_path = self._get_process_exe_path(pid)
                    return pid, exe_path

        except Exception as exc:
            logger.debug("UWP child PID resolution failed: %s", exc)

        return None, None

    @staticmethod
    def _get_process_exe_path(pid: int) -> Optional[str]:
        """Get the executable path for a process by PID.

        Tries psutil first, then falls back to Win32 QueryFullProcessImageNameW.

        Args:
            pid: Process ID.

        Returns:
            Full executable path, or None if resolution fails.
        """
        try:
            import psutil  # type: ignore[import-untyped]
            return psutil.Process(pid).exe()
        except Exception as exc:
            logger.debug("psutil exe resolution failed for pid %s: %s", pid, exc)
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if h:
                try:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = wintypes.DWORD(1024)
                    if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                        return buf.value
                finally:
                    kernel32.CloseHandle(h)
        except Exception as exc:
            logger.debug("Win32 exe path resolution failed for pid %s: %s", pid, exc)
        return None

    @staticmethod
    def _afh_has_content_window(afh_hwnd: int) -> bool:
        """Check if an ApplicationFrameHost window has a content child.

        A "content child" is a ``Windows.UI.Core.CoreWindow`` (classic UWP)
        or ``DesktopWindowXamlSource`` (WinUI 3) — these host the actual
        app UI.  Stale AFH windows may only have title bar and input sink
        children, which do NOT contain actionable UI elements.

        Args:
            afh_hwnd: Handle of the ApplicationFrameHost top-level window.

        Returns:
            True if the AFH has at least one content window child.
        """
        import sys
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            GetClassNameW = user32.GetClassNameW
            GetClassNameW.argtypes = [
                wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int,
            ]
            GetClassNameW.restype = ctypes.c_int

            _CONTENT_CLASSES = {
                "windows.ui.core.corewindow",
                "desktopwindowxamlsource",
            }

            found = [False]

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM,
            )

            def _enum_cb(hwnd, _lparam):
                cls_buf = ctypes.create_unicode_buffer(256)
                GetClassNameW(hwnd, cls_buf, 256)
                if cls_buf.value.lower() in _CONTENT_CLASSES:
                    found[0] = True
                    return False  # stop enumeration
                return True

            user32.EnumChildWindows(
                wintypes.HWND(afh_hwnd), WNDENUMPROC(_enum_cb), 0,
            )
            return found[0]
        except Exception:
            return False

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

    def _is_afh_window(self, handle: int) -> bool:
        """Check if a window handle belongs to ApplicationFrameHost.exe.

        Args:
            handle: Window handle to check.

        Returns:
            True if the window process is ApplicationFrameHost.exe.
        """
        for w in self.list_windows():
            if w.handle == handle:
                proc = w.process_name.lower()
                if proc.endswith(".exe"):
                    proc = proc[:-4]
                return proc == "applicationframehost"
        return False

    @staticmethod
    def _is_shallow_tree(element) -> bool:
        """Check if an element tree is too shallow (VB6/ActiveX fallback signal).

        VB6/ActiveX apps often expose a tree with only a few Pane containers
        at depth 1-2, hiding all actual form controls (Static/Edit/Button).
        This heuristic detects that pattern to trigger Win32 HWND enumeration.

        Args:
            element: Root ElementInfo from get_element_tree.

        Returns:
            True if the tree is too shallow (trigger fallback).
        """
        if not element or not element.children:
            return True

        # Count actionable elements (non-Pane roles at any depth)
        actionable_count = 0
        pane_count = 0

        def count_actionable(el):
            nonlocal actionable_count, pane_count
            role = (el.role or "").lower()
            if role == "pane":
                pane_count += 1
            elif role in ("button", "edit", "text", "combobox", "checkbox", "radiobutton"):
                actionable_count += 1
            for child in el.children:
                count_actionable(child)

        count_actionable(element)

        # Shallow tree heuristic: <5 actionable elements or >80% panes
        if actionable_count < 5:
            return True
        if pane_count > 0 and actionable_count / (actionable_count + pane_count) < 0.2:
            return True

        return False

    def get_element_tree(self, window_title: Optional[str] = None,
                         depth: int = 3,
                         app: Optional[str] = None,
                         hwnd: Optional[int] = None,
                         pid: Optional[int] = None,
                         backend: str = "uia") -> Optional[BaseElementInfo]:
        """Get the UI element tree for a window.

        Fills parent_id, children IDs, and keyboard_shortcut for all elements
        via Python-layer post-processing (the C++ DLL does not emit these).

        For UWP/WinUI apps (Calculator, Settings, etc.) the UI tree lives
        inside child windows of the ``ApplicationFrameHost`` top-level window.
        Classic UWP uses ``Windows.UI.Core.CoreWindow``; WinUI 3 apps use
        other classes like ``DesktopWindowXamlSource``.  When the initial
        traversal returns an empty tree from an AFH window, this method
        enumerates all child windows and retries with each until a non-empty
        tree is found.

        Args:
            window_title: Window title pattern (partial match, case-insensitive).
            depth: Maximum depth to traverse (1-10).
            app: Application name to search for (partial match, case-insensitive).
            hwnd: Direct window handle. Overrides app/window_title.
            pid: Process ID.  Filters windows to only those owned by this
                process (#471).
            backend: Accessibility backend — "auto" (default), "uia", "msaa",
                     "win32", "win32hybrid", "ia2", or "jab".
                     "auto" tries UIA first, falls back to hybrid Win32+UIA
                     if UIA returns shallow trees, then IA2/JAB/MSAA.
                     "win32" uses pure Win32 HWND enumeration.
                     "win32hybrid" uses Win32 HWND tree with UIA drill-down
                     for complex controls like grids, list views, and tree
                     views (#312).

        Returns:
            Root ElementInfo with nested children, or None.
        """
        core = self._ensure_core()
        handle = self._resolve_hwnd(app=app, window_title=window_title, hwnd=hwnd, pid=pid)

        def _try_uwp_children(current_result, get_tree_fn):
            """If handle is an AFH window with empty tree, try child windows.

            Enumerates all child HWNDs of the ApplicationFrameHost window
            and returns the first one that yields a non-empty element tree.

            Args:
                current_result: The element tree from the AFH window itself.
                get_tree_fn: Callable(hwnd, depth) -> element tree result.

            Returns:
                A non-empty element tree from a child HWND, or current_result
                if no child yields a better result.
            """
            if (current_result is not None
                    and not current_result.children
                    and handle
                    and self._is_afh_window(handle)):
                child_hwnds = self._find_uwp_content_hwnd(handle)
                for child_hwnd in child_hwnds:
                    logger.debug(
                        "UWP fallback: trying child HWND %s "
                        "(parent AFH %s)", child_hwnd, handle,
                    )
                    child_result = get_tree_fn(child_hwnd, depth)
                    if child_result is not None and child_result.children:
                        logger.info(
                            "UWP fallback: found %d children via child "
                            "HWND %s", len(child_result.children), child_hwnd,
                        )
                        return child_result

                # (#394) WinUI 3 apps may need deeper traversal.
                # Retry child HWNDs with increased depth if original
                # depth was low and yielded nothing.
                if depth < 15:
                    deeper = min(depth * 2, 20)
                    logger.debug(
                        "UWP fallback: retrying children with depth=%d "
                        "(was %d)", deeper, depth,
                    )
                    for child_hwnd in child_hwnds:
                        child_result = get_tree_fn(child_hwnd, deeper)
                        if child_result is not None and child_result.children:
                            logger.info(
                                "UWP fallback (depth=%d): found %d children "
                                "via child HWND %s",
                                deeper, len(child_result.children), child_hwnd,
                            )
                            return child_result
            return current_result

        if backend == "jab":
            result = core.jab_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.jab_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "ia2":
            result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.ia2_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "msaa":
            result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.msaa_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "win32":
            # Pure Win32 HWND enumeration (VB6/ActiveX fallback)
            from naturo.bridge import enumerate_child_windows
            result = enumerate_child_windows(hwnd=handle, depth=depth)
        elif backend == "win32hybrid":
            # Win32 HWND tree + UIA drill-down for complex controls (#312)
            from naturo.bridge import enumerate_hybrid_tree
            result = enumerate_hybrid_tree(
                hwnd=handle, depth=depth, core=core,
            )
        elif backend == "auto":
            result = core.get_element_tree(hwnd=handle, depth=depth)
            # UWP/WinUI fallback: try child windows of AFH
            result = _try_uwp_children(
                result,
                lambda h, d: core.get_element_tree(hwnd=h, depth=d),
            )
            
            # Win32+UIA hybrid fallback for VB6/ActiveX apps (#308, #312)
            # When UIA returns shallow trees (only Pane containers),
            # use hybrid enumeration: Win32 HWND tree as base with UIA
            # drill-down for complex controls (grids, list views, tree views).
            if result is not None and self._is_shallow_tree(result):
                logger.info(
                    "UIA returned shallow tree (%d children), "
                    "trying Win32+UIA hybrid enumeration (VB6/ActiveX)",
                    len(result.children)
                )
                from naturo.bridge import enumerate_hybrid_tree
                hybrid_result = enumerate_hybrid_tree(
                    hwnd=handle, depth=depth, core=core,
                )
                if hybrid_result is not None and len(hybrid_result.children) > len(result.children):
                    logger.info(
                        "Hybrid fallback found %d children (vs %d from UIA), using it",
                        len(hybrid_result.children), len(result.children)
                    )
                    result = hybrid_result
            
            if result is None or (not result.children and not result.name):
                # Try IA2 first (Firefox/Thunderbird/LibreOffice), then MSAA
                ia2_result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
                if ia2_result is not None:
                    result = ia2_result
                else:
                    # Try JAB for Java applications
                    jab_result = core.jab_get_element_tree(hwnd=handle, depth=depth)
                    if jab_result is not None:
                        result = jab_result
                    else:
                        msaa_result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
                        if msaa_result is not None:
                            result = msaa_result
                        else:
                            # Final fallback: hybrid Win32+UIA enumeration
                            from naturo.bridge import enumerate_hybrid_tree
                            hybrid_result = enumerate_hybrid_tree(
                                hwnd=handle, depth=depth, core=core,
                            )
                            if hybrid_result is not None:
                                logger.info("Auto mode: all backends failed, using Win32+UIA hybrid fallback")
                                result = hybrid_result
        else:
            result = core.get_element_tree(hwnd=handle, depth=depth)
            # UWP/WinUI fallback for explicit "uia" backend too
            result = _try_uwp_children(
                result,
                lambda h, d: core.get_element_tree(hwnd=h, depth=d),
            )

        if result is None:
            return None

        # (#613) Fix coordinate mismatch on UWP/high-DPI: UIA may return
        # large negative coords for UWP apps when DPI contexts conflict.
        if handle:
            result = self._fixup_element_coords(result, handle)

        # Post-process: assign sequential IDs and fill parent_id
        populate_hierarchy(result)

        # (#372) Roles that should include a text value preview
        _PREVIEW_ROLES = {"Document", "Edit", "Text"}

        def convert(el) -> BaseElementInfo:
            """Convert bridge ElementInfo to backend ElementInfo."""
            props = {
                k: v for k, v in {
                    "parent_id": el.parent_id,
                    "keyboard_shortcut": el.keyboard_shortcut,
                }.items() if v is not None
            }

            # (#372) Add value preview for Document/Edit/Text elements
            if el.role in _PREVIEW_ROLES and el.value:
                full_text = el.value
                preview = full_text[:100]
                if len(full_text) > 100:
                    preview += "…"
                props["value_preview"] = preview
                props["value_length"] = len(full_text)

            return BaseElementInfo(
                id=el.id,
                role=el.role,
                name=el.name,
                value=el.value,
                x=el.x,
                y=el.y,
                width=el.width,
                height=el.height,
                children=[convert(c) for c in el.children],
                properties=props,
            )

        return convert(result)

    def get_element_value(
        self,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        app: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[dict]:
        """Read the current value/text of a UI element via UIA patterns.

        Supports element refs (e47), AutomationId, or role+name lookup.
        Queries ValuePattern, TogglePattern, SelectionPattern,
        RangeValuePattern, and TextPattern.

        Args:
            ref: Element ref from snapshot (e.g. ``"e47"``).
            automation_id: UIA AutomationId string.
            role: Element role (e.g. ``"Edit"``).
            name: Element name.
            app: Application name (partial match) for window targeting.
            window_title: Window title for targeting.
            hwnd: Window handle.

        Returns:
            Dict with ``value``, ``pattern``, ``role``, ``name``,
            ``automation_id``, and bounding rect; or ``None`` if not found.

        Raises:
            NaturoError: If the element cannot be found or queried.
        """
        core = self._ensure_core()

        # Resolve ref to element metadata via snapshot cache
        resolved_aid = automation_id
        resolved_role = role
        resolved_name = name
        target_hwnd = hwnd or 0

        if ref and not resolved_aid:
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            result = mgr.resolve_ref_element(ref)
            if result:
                elem, _snap_id = result
                # Use the element's identifier (AutomationId) if available
                if elem.identifier:
                    resolved_aid = elem.identifier
                elif elem.role and elem.title:
                    resolved_role = elem.role
                    resolved_name = elem.title
                elif elem.role and elem.label:
                    resolved_role = elem.role
                    resolved_name = elem.label
                else:
                    raise NaturoError(
                        f"Element {ref} has no AutomationId, role, or name "
                        f"for value lookup"
                    )
            else:
                raise NaturoError(
                    f"Element ref '{ref}' not found in snapshot cache. "
                    f"Run 'naturo see' first to capture elements."
                )

        # Resolve app/window_title to HWND for targeted lookup
        if (app or window_title) and not target_hwnd:
            try:
                target_hwnd = self._resolve_hwnd(
                    app=app, window_title=window_title
                )
            except Exception:
                # Fall back to scanning windows manually
                if window_title:
                    wins = core.list_windows()
                    for w in wins:
                        if window_title.lower() in (w.title or "").lower():
                            target_hwnd = w.hwnd
                            break

        if not resolved_aid and not resolved_role and not resolved_name:
            # (#242) Fallback: when no element identifiers are provided but
            # we have a target HWND (e.g., from --app notepad), auto-probe
            # common editable element roles in the window. This enables
            # verification for the common `type --app X --verify` pattern.
            if target_hwnd:
                _editable_roles = ("Edit", "Document", "RichEdit20W")
                for _probe_role in _editable_roles:
                    _probe_result = core.get_element_value(
                        hwnd=target_hwnd,
                        automation_id=None,
                        role=_probe_role,
                        name=None,
                    )
                    if _probe_result is not None:
                        _probe_result["probe_role"] = _probe_role
                        return _probe_result
                # All probes failed — still no identifiers available
                raise NaturoError(
                    "No editable element found in target window. "
                    "Tried probing roles: Edit, Document, RichEdit20W. "
                    "Use --on eN to specify the target element explicitly."
                )
            raise NaturoError(
                "Must specify ref, automation_id, or role/name to get value"
            )

        result = core.get_element_value(
            hwnd=target_hwnd,
            automation_id=resolved_aid,
            role=resolved_role,
            name=resolved_name,
        )

        # (#352) Role alias fallback: when an explicit role search fails,
        # try common aliases.  Win11 Notepad uses "Document" for its text
        # editor, but users naturally try "Edit".  This maps between roles
        # that serve similar purposes in different app frameworks.
        if result is None and resolved_role and not resolved_aid:
            _ROLE_ALIASES: dict[str, list[str]] = {
                "Edit": ["Document", "RichEdit20W"],
                "Document": ["Edit", "RichEdit20W"],
                "RichEdit20W": ["Edit", "Document"],
                "Text": ["StaticText"],
                "StaticText": ["Text"],
            }
            aliases = _ROLE_ALIASES.get(resolved_role, [])
            for alias_role in aliases:
                result = core.get_element_value(
                    hwnd=target_hwnd,
                    automation_id=resolved_aid,
                    role=alias_role,
                    name=resolved_name,
                )
                if result is not None:
                    break

        # (#521) NameProperty fallback: if the C++ core found the element but
        # no UIA pattern returned a value, use the element's Name property.
        # This handles Text/Static elements (e.g. Calculator display) where
        # the value is embedded in the UIA Name (e.g. "显示为 579").
        if isinstance(result, dict) and result.get("value") is None:
            elem_name = result.get("name")
            if elem_name:
                result["value"] = elem_name
                result["pattern"] = "NameProperty"

        # (#229) Fallback: if UIA lookup returned None but we have snapshot
        # data from the ref, return the snapshot metadata so the caller gets
        # at least role/name/bounds instead of ELEMENT_NOT_FOUND.
        if result is None and ref:
            from naturo.snapshot import get_snapshot_manager as _gsm
            _mgr = _gsm()
            _el_result = _mgr.resolve_ref_element(ref)
            if _el_result:
                _elem, _snap = _el_result
                ex, ey, ew, eh = _elem.frame
                result = {
                    "role": _elem.role,
                    "name": _elem.title or _elem.label,
                    "value": _elem.value,
                    "pattern": None,
                    "automation_id": _elem.identifier,
                    "x": ex,
                    "y": ey,
                    "width": ew,
                    "height": eh,
                    "source": "snapshot",
                }

        return result

