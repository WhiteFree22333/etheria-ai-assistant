# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ['ui/app.py'],
    pathex=[],
    binaries=[
        ('C:/Windows/System32/vcruntime140.dll', '.'),
        ('C:/Windows/System32/vcruntime140_1.dll', '.'),
        ('C:/Windows/System32/msvcp140.dll', '.'),
    ],
    datas=[
        ('ui/static', 'ui/static'),
        ('templates', 'templates'),
        ('.env', '.'),
        ('app.ico', '.'),
    ],
    hiddenimports=[
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'PIL',
        'cv2',
        'numpy',
        'psutil',
        'win32gui',
        'win32con',
        'win32process',
        'win32api',
        'mss',
        'pyautogui',
        'pynput',
        'easyocr',
        'torch',
        'core._base',
        'core._common',
        'core.daily',
        'core.events',
        'core.rta',
        'http.server',
    ],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='瑞玛丽小助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['torch', 'c10', 'fbgemm', 'asmjit', 'libiomp', 'shm'],
    name='瑞玛丽小助手',
)
