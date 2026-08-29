"""EEG Artifact Scope -- artifact detection and signal-quality scoring.

Depends only on numpy, scipy and scikit-learn so the whole analysis can run
inside Pyodide, in the user's browser, with the recording never leaving their
machine. MNE-dependent code lives in ``labio`` and is used offline as the
reference implementation that ``tests/test_parity.py`` checks against.
"""

__version__ = "0.1.0"

from .pipeline import Analysis, analyse  # noqa: E402,F401

__all__ = ["analyse", "Analysis", "__version__"]
