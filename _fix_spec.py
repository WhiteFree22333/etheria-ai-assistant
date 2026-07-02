import os

# Read current spec
spec_path = r'e:\etheriaZd\game-ai-assistant\YiseAssistant.spec'
with open(spec_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Revert any bad edits - reset to known good state
# Just add torch.dll binaries using the Analysis binaries list
# Rewrite the whole binaries=[] line with torch DLLs

torch_lib = r'C:\Users\WhiteFree\AppData\Local\Programs\Python\Python312\Lib\site-packages\torch\lib'
dll_files = [f for f in os.listdir(torch_lib) if f.endswith('.dll')]

binaries_entries = []
for dll in dll_files:
    full = os.path.join(torch_lib, dll)
    binaries_entries.append(f"        ('{full}', '.'),")

binaries_block = '    binaries=[\n' + '\n'.join(binaries_entries) + '\n    ],\n'

# Replace binaries=[]
old = '    binaries=[],\n'
content = content.replace(old, binaries_block)

# Also add torch to hiddenimports if not there
if "'torch'," not in content:
    content = content.replace(
        "'easyocr',\n        'core._base',",
        "'easyocr',\n        'torch',\n        'core._base',"
    )

with open(spec_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Done - added {len(dll_files)} torch DLLs to spec')
