import os
import tempfile

# Keep tests away from the real data directory and SQLite file.
os.environ.setdefault("RC_DATA_DIR", tempfile.mkdtemp(prefix="rc-test-"))
