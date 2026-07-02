import os, re

spec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'YiseAssistant.spec')
torch_lib = r'C:\Users\WhiteFree\AppData\Local\Programs\Python\Python312\Lib\site-packages\torch\lib'

dll_files = [f for f in os.listdir(torch_lib) if f.endswith('.dll')]
binaries_entries = []
for dll in dll_files:
    full_path = os.path.join(torch_lib, dll).replace('\\', '/')
    binaries_entries.append(f"        ('{full_path}', '.'),")

binaries_block = '    binaries=[\n' + '\n'.join(binaries_entries) + '\n    ],\n'

with open(spec_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace binaries section using regex
content = re.sub(
    r'    binaries=\[.*?\],\n',
    binaries_block,
    content,
    flags=re.DOTALL
)

# Ensure torch in hiddenimports
if "'torch'," not in content:
    content = content.replace(
        "'easyocr',\n        'core._base',",
        "'easyocr',\n        'torch',\n        'core._base',"
    )
# Add back console=True if missing
if 'console=True' not in content:
    content = content.replace('console=False', 'console=True')

with open(spec_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Spec fixed: {len(dll_files)} torch DLLs added')
# Verify spec parses OK
try:
    compile(content, spec_path, 'exec')
    print('Spec syntax OK')
except SyntaxError as e:
    print(f'Syntax error: {e}')
