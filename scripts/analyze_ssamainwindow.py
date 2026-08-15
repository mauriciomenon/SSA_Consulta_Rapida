import re

with open("gui/gui_ssa.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find SSAMainWindow methods
in_main_window = False
methods = []
current_method = None
current_line = None

for i, line in enumerate(lines, 1):
    if "class SSAMainWindow" in line:
        in_main_window = True
        print(f"SSAMainWindow starts at line {i}")
        continue

    if in_main_window:
        # Check if we've exited the class
        if line.startswith("def ") and not line.startswith("    def "):
            break
        if line.startswith("class ") and "SSAMainWindow" not in line:
            break

        # Check for method definition
        if re.match(r"^    def ", line):
            if current_method and current_line is not None:
                methods.append((current_line, current_method, i - current_line))
            method_name = line.strip().split("(")[0].replace("def ", "")
            current_method = method_name
            current_line = i

# Add last method
if current_method and current_line is not None:
    methods.append((current_line, current_method, len(lines) - current_line))

print(f"\nTotal methods in SSAMainWindow: {len(methods)}")
print("\nMethods by category:\n")

# Categorize methods
theme_methods = []
filter_methods = []
export_methods = []
ui_methods = []
data_methods = []
event_methods = []
other_methods = []

for line_num, method_name, size in methods:
    # Theme related
    if (
        "theme" in method_name.lower()
        or "color" in method_name.lower()
        or "palette" in method_name.lower()
    ):
        theme_methods.append((line_num, method_name))
    # Filter related
    elif "filter" in method_name.lower() or "search" in method_name.lower():
        filter_methods.append((line_num, method_name))
    # Export related
    elif "export" in method_name.lower() or "save" in method_name.lower():
        export_methods.append((line_num, method_name))
    # UI building
    elif any(
        x in method_name.lower()
        for x in [
            "init_ui",
            "create",
            "setup",
            "build",
            "_ui",
            "toolbar",
            "menu",
            "statusbar",
        ]
    ):
        ui_methods.append((line_num, method_name))
    # Data operations
    elif any(
        x in method_name.lower() for x in ["load", "data", "update_table", "populate"]
    ):
        data_methods.append((line_num, method_name))
    # Event handlers
    elif any(x in method_name.lower() for x in ["on_", "_on_", "handle", "click"]):
        event_methods.append((line_num, method_name))
    else:
        other_methods.append((line_num, method_name))

print("=== THEME METHODS ===")
for line_num, method in theme_methods:
    print(f"  {line_num}: {method}")

print("\n=== FILTER METHODS ===")
for line_num, method in filter_methods:
    print(f"  {line_num}: {method}")

print("\n=== EXPORT METHODS ===")
for line_num, method in export_methods:
    print(f"  {line_num}: {method}")

print("\n=== UI BUILDING METHODS ===")
for line_num, method in ui_methods:
    print(f"  {line_num}: {method}")

print("\n=== DATA METHODS ===")
for line_num, method in data_methods:
    print(f"  {line_num}: {method}")

print("\n=== EVENT HANDLERS ===")
for line_num, method in event_methods[:20]:  # First 20
    print(f"  {line_num}: {method}")
if len(event_methods) > 20:
    print(f"  ... and {len(event_methods) - 20} more")

print("\n=== OTHER METHODS ===")
for line_num, method in other_methods:
    print(f"  {line_num}: {method}")

print("\n=== SUMMARY ===")
print(f"Theme methods: {len(theme_methods)}")
print(f"Filter methods: {len(filter_methods)}")
print(f"Export methods: {len(export_methods)}")
print(f"UI methods: {len(ui_methods)}")
print(f"Data methods: {len(data_methods)}")
print(f"Event handlers: {len(event_methods)}")
print(f"Other methods: {len(other_methods)}")
print(f"TOTAL: {len(methods)}")
