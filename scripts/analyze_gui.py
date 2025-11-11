import re

with open('gui/gui_ssa.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all classes
classes = []
for i, line in enumerate(lines, 1):
    if line.startswith('class '):
        class_name = line.split('(')[0].replace('class ', '').strip()
        classes.append((i, class_name))

print("CLASSES IN gui_ssa.py:")
print("="*60)
for line_num, class_name in classes:
    print(f"Line {line_num}: {class_name}")

print("\n" + "="*60)
print("\nSSAMAINWINDOW METHODS:")
print("="*60)

# Find SSAMainWindow methods
in_main_window = False
method_count = 0
method_list = []

for i, line in enumerate(lines, 1):
    if 'class SSAMainWindow' in line:
        in_main_window = True
        start_line = i
    elif in_main_window and line.startswith('class '):
        break
    elif in_main_window and re.match(r'^    def ', line):
        method_name = line.strip().split('(')[0].replace('def ', '')
        method_count += 1
        if method_count <= 40:
            method_list.append((i, method_name))

for line_num, method_name in method_list:
    print(f"Line {line_num}: {method_name}")

if method_count > 40:
    print(f"... and {method_count - 40} more methods")

print(f"\nTotal methods: {method_count}")
print(f"SSAMainWindow size: ~{4223 - start_line} lines")
