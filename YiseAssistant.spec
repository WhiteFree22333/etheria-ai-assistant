# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.building.datastruct import TOC

block_cipher = None


a = Analysis(
    ['ui/app.py'],
    pathex=[],
    binaries=[
        ('E:/etheriaZd/game-ai-assistant/venv/Lib/site-packages/pythonnet/runtime/Python.Runtime.dll', 'pythonnet/runtime'),
        # certifi SSL 证书（EasyOCR 下载模型时验证 HTTPS 需要）
        ('E:/etheriaZd/game-ai-assistant/venv/Lib/site-packages/certifi/cacert.pem', 'certifi'),
    ],
    datas=[
        ('ui/static', 'ui/static'),
        ('templates', 'templates'),
        ('easyocr_models', 'easyocr_models'),
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
        # 下面几个是实测确认用不到的死重量，解压后加起来约 297MB。
        #
        # PyQt5（79MB）：我们的代码一处都没引用（全库搜 PyQt5/PySide/qtpy 零命中）。
        #   界面走的是 pywebview 的 edgechromium 后端，跟 Qt 没关系。它是当年 pandas[all]
        #   或 pywebview[qt5] 那两个 extra 顺带装进来的，pandas 早就 exclude 了，所以在用的
        #   包没有一个依赖它 —— pip show PyQt5 的 Required-by 是空的。
        #   实测反直觉的一点：打进去之后运行时 QtCore.pyd / Qt5Core.dll 真的会被加载，
        #   但那是 PyInstaller 自己的运行时钩子干的（_pyi_rth_utils/qt.py 里
        #   create_embedded_qt_conf 会 importlib.import_module('PyQt5.QtCore')）。
        #   包里没有 PyQt5，这个钩子就不会被收集，也就没人 import 它。
        #   另外：Qt5/bin 下那几份 2019 年的老 MSVCP140 就是它带进来的，
        #   正是 c10.dll 报 WinError 1114 的源头（见下面的 _SYS_DLLS）。
        #
        # paddle / paddleocr / paddlex（218MB，光 libpaddle.pyd 就 128MB）：OCR 的另一条路。
        #   core/config.py 里 ocr_engine 默认写的是 "paddle"，但实际业务全绕开了它 ——
        #   core/daily、core/events 里所有认字的地方调的都是 _init_easyocr_reader（EasyOCR）；
        #   唯一会用配置引擎的是 bot.click_text()，它只被 ui/app.py 的 start_dungeon →
        #   bot.run_dungeon() 调用，而前端一处都没引用（frontend/src 搜 dungeon 零命中），
        #   是 V1.0 时代剩下的死 API。实测打包后的进程里 paddle 一个模块都没加载。
        #   副作用：万一以后要复活副本功能，click_text 会抛 ModuleNotFoundError: paddleocr
        #   —— 报错很响、好定位，不会静默失效。到时删掉这几行重新打包即可。
        'PyQt5',
        'paddle',
        'paddleocr',
        'paddlex',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 剔掉 PyInstaller 自动收集的系统 DLL。这些必须由 Windows 从 System32 加载，
# 打包进去会导致 DLL 版本不匹配 → c10.dll 的 DllMain 初始化失败。
#
# 必须比「文件名」，不能比完整相对路径！PyInstaller 给的 n 是
# 'PyQt5/Qt5/bin/MSVCP140.dll' 这种带目录的名字，拿整串去比一个都剔不掉。
# 实测就是这么漏的：PyQt5/Qt5/bin 下 MSVCP140.dll / MSVCP140_1.dll /
# VCRUNTIME140.dll / VCRUNTIME140_1.dll 全留在了包里，而它们是 Qt5 自带的
# 14.26（2019 年）老版本，系统里的是 14.50。老版本先被搜到 → c10.dll 起不来
# → EasyOCR/torch 全废（报 WinError 1114）。
# msvcp140_1.dll 也要剔：实测它和 msvcp140.dll 一样能让 c10.dll 加载失败。
_SYS_DLLS = {
    'ucrtbase.dll',
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'msvcp140.dll',
    'msvcp140_1.dll',
    'concrt140.dll',
    'vccorlib140.dll',
}

# 剔干净之后，再随包带上一份 VC++ 运行时（这叫 app-local 部署，微软允许这么分发）。
#
# 为什么必须带：不带的话这几个 DLL 只能由用户电脑的 System32 提供，而它们不是
# Windows 自带的，是「VC++ 2015-2022 运行库」装进去的 —— 装过 Steam/游戏/很多软件的
# 机器都有，纯净或刚重装的系统就没有，那种机器上程序根本起不来（报「找不到
# msvcp140.dll」）。用户是玩家，指望他们认出这个报错再去装运行库不现实。
#
# 只从打包机的 System32 取这一份：系统里那份是统一的、新的。千万别随手从别的
# 第三方目录抓一份 —— PyQt5 自带的是 2019 年的 14.26，就是它让 torch 的 c10.dll
# 报 WinError 1114 的（见上面 _SYS_DLLS 那段）。
#
# ucrtbase.dll / api-ms-win-crt-* 不带：那是 Win10 以后系统自带的，硬塞反而出事。
_SYSTEM32 = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')
_REDIST_DLLS = [
    'msvcp140.dll',
    'msvcp140_1.dll',
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'concrt140.dll',
]
for _d in _REDIST_DLLS:
    if not os.path.exists(os.path.join(_SYSTEM32, _d)):
        print(f'[spec] 警告：{_SYSTEM32} 里没有 {_d}，这一份不会进包')

# 一步到位：先剔掉所有自动收集来的系统 DLL（来路不明的旧副本），再补上自己这一份。
# 补在剔之后，不然自己这份也会被剔掉。
a.binaries = TOC(
    [(n, p, t) for (n, p, t) in a.binaries
     if os.path.basename(n).lower() not in _SYS_DLLS
     and not os.path.basename(n).lower().startswith('api-ms-win-crt-')]
    + [(d, os.path.join(_SYSTEM32, d), 'BINARY') for d in _REDIST_DLLS
       if os.path.exists(os.path.join(_SYSTEM32, d))]
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
    console=True,
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
    upx_exclude=['torch', 'c10', 'fbgemm', 'asmjit', 'libiomp', 'shm', 'uv', 'torch_cpu'],
    name='瑞玛丽小助手',
)
