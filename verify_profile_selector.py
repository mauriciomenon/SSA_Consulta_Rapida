
from PyQt6.QtWidgets import QApplication
from gui.widgets.profile_selector import ProfileSelector
import sys

# Mocking file existence
import os
with open("test_profiles.json", "w") as f:
    f.write("{}")

app = QApplication(sys.argv)
ps = ProfileSelector("test_profiles.json", ["col1", "col2"])

# Check methods
assert hasattr(ps, "findData")
assert hasattr(ps, "setCurrentIndex")
assert hasattr(ps, "currentIndex")
assert hasattr(ps, "itemData")

print("ProfileSelector verification passed")

try:
    os.remove("test_profiles.json")
except: pass
