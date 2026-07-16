"""Test-only compatibility hooks for optional property-test dependencies."""
from __future__ import annotations

import importlib.util
import sys
import types

import pytest


if importlib.util.find_spec("hypothesis") is None:
    hypothesis = types.ModuleType("hypothesis")

    def given(*_strategies, **_named_strategies):
        def decorate(function):
            return pytest.mark.skip(
                reason="Hypothesis is not installed in this test environment"
            )(function)
        return decorate

    class _Strategies:
        def __getattr__(self, _name):
            return lambda *_args, **_kwargs: None

    hypothesis.given = given
    hypothesis.strategies = _Strategies()
    sys.modules["hypothesis"] = hypothesis
