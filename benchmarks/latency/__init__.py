"""Latency benchmark package (issue #418).

Tracks naturo engine operation latency (``see`` / ``find`` / ``click``) over
time so performance regressions between releases can be detected in CI. The
statistics core (:mod:`benchmarks.latency.harness`) is pure and hermetically
testable; the live fixture wrappers drive naturo's engine against the same
offline Chromium fixture the recognition benchmark ships.
"""
