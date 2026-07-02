import os, re

spec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'YiseAssistant.spec')

with open(spec_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove custom binaries (PyInstaller auto-collects torch DLLs)
content = re.sub(
    r'    binaries=\[.*?\],\n',
    '    binaries=[],\n',
    content,
    flags=re.DOTALL
)

# 2. Add MSVC runtime hook hidden imports
if 'pyi_rth_multiprocessing' not in content:
    content = content.replace(
        "'easyocr',",
        "'torch',\n        'torchvision',\n        'torchvision.ops',\n        'torchaudio',\n        'easyocr',"
    )

# 3. Ensure console off again for release
if 'console=True' in content:
    content = content.replace('console=True', 'console=False')

# 4. Add UPX exclude for torch DLLs (UPX can corrupt them)
if "upx_exclude=['torch']" not in content:
    content = content.replace(
        "upx_exclude=[]",
        "upx_exclude=['torch*', '*.pyd', 'c10*', 'fbgemm*']"
    )

# 5. Add collect-all for torch
content = content.replace(
    "    hookspath=[],\n    hooksconfig={},\n    runtime_hooks=[]",
    "    hookspath=[],\n    hooksconfig={},\n    runtime_hooks=[],\n    module_collection_mode={'torch': 'pyz+py'}"
)

with open(spec_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Spec simplified — PyInstaller auto-collects torch now")
print("Run: pyinstaller YiseAssistant.spec --noconfirm")
