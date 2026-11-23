import os

# Must be set before any Qt import so tests run headless.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
