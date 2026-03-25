"""Regression test for #338: see --app crash with multi-window merge path.

When an app has multiple windows, the multi-window merge code creates
virtual BaseElementInfo nodes (app_root, WindowGroup). These must include
the required ``properties`` parameter to avoid TypeError.
"""

from naturo.backends.base import ElementInfo as BaseElementInfo


class TestMultiWindowMergeProperties:
    """Verify virtual merge nodes can be constructed with properties (#338)."""

    def test_app_root_node_requires_properties(self):
        """Creating app_root without properties should raise TypeError."""
        # This is what the buggy code did — confirm it fails without fix
        try:
            BaseElementInfo(
                id="app_root", role="Application", name="notepad",
                value=None, x=0, y=0, width=0, height=0, children=[],
            )
            assert False, "Should have raised TypeError for missing properties"
        except TypeError:
            pass

    def test_app_root_node_with_properties(self):
        """Creating app_root with properties={} should succeed (#338 fix)."""
        node = BaseElementInfo(
            id="app_root", role="Application", name="notepad",
            value=None, x=0, y=0, width=0, height=0,
            children=[], properties={},
        )
        assert node.id == "app_root"
        assert node.properties == {}

    def test_window_group_node_with_properties(self):
        """Creating WindowGroup with properties={} should succeed (#338 fix)."""
        child = BaseElementInfo(
            id="e1", role="Window", name="Notepad",
            value=None, x=0, y=0, width=800, height=600,
            children=[], properties={"hwnd": 12345},
        )
        node = BaseElementInfo(
            id="window_100", role="WindowGroup",
            name="Notepad (HWND:100)",
            value=None, x=0, y=0, width=800, height=600,
            children=[child], properties={},
        )
        assert node.role == "WindowGroup"
        assert node.properties == {}
        assert len(node.children) == 1
