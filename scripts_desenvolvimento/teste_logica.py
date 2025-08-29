s = '2513402'
print(f'Input: {s}')
print(f'Length: {len(s)}')
print(f'Starts with 25: {s.startswith("25")}')

# Aplicar lógica
if len(s) == 7 and s.startswith(('21','22','23','24','25')):
    result = '20' + s
else:
    result = s

print(f'Result: {result}')
print(f'Expected: 202513402')
print(f'Match: {result == "202513402"}')
