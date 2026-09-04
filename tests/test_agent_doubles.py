"""The doubles must keep the shape of the real agents. Owner: R2.

conftest.py replaces every model-calling agent with a deterministic double so
the graph tests run offline. That trade is only safe while the doubles accept
what the real functions accept — otherwise R3 changes a signature, src/ breaks,
and the suite stays green because it is exercising the old shape.

This is the test that fails instead.
"""

import inspect

import pytest

from tests.conftest import DOUBLES, REAL_SIGNATURES


@pytest.mark.parametrize(
    "module, name, double",
    DOUBLES,
    ids=[f"{m.__name__.split('.')[-1]}.{n}" for m, n, _ in DOUBLES],
)
def test_double_matches_the_real_signature(module, name, double):
    real = REAL_SIGNATURES[f"{module.__name__}.{name}"]
    assert inspect.signature(double) == real, (
        f"{module.__name__}.{name} changed shape.\n"
        f"  real:   {real}\n"
        f"  double: {inspect.signature(double)}\n"
        f"Update the double in tests/conftest.py to match."
    )
