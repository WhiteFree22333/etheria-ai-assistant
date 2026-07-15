"""瑞玛丽小助手 — 一键打包脚本 (Python 版, 无编码问题)"""
import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd, cwd=None, desc=""):
    print(f"\n{'='*50}")
    print(f"  {desc}")
    print(f"{'='*50}\n")
    result = subprocess.run(cmd, shell=True, cwd=cwd or ROOT)
    if result.returncode != 0:
        print(f"\n[FAIL] {desc}")
        sys.exit(1)
    print(f"\n[OK] {desc}")


# Step 1: build frontend
run("npm run build", cwd=os.path.join(ROOT, "frontend"), desc="[1/3] 构建前端")

# Step 2: PyInstaller
run("python -m PyInstaller YiseAssistant.spec --noconfirm",
    desc="[2/3] PyInstaller 打包 exe")

# Step 3: zip dist
dist_dir = os.path.join(ROOT, "dist", "瑞玛丽小助手")
zip_path = os.path.join(ROOT, "dist", "瑞玛丽小助手_V1.1.zip")
if os.path.exists(zip_path):
    os.remove(zip_path)
print(f"\n{'='*50}")
print(f"  [3/3] 压缩 dist 文件夹")
print(f"{'='*50}\n")
shutil.make_archive(zip_path.replace(".zip", ""), "zip",
                    os.path.join(ROOT, "dist"), "瑞玛丽小助手")
if os.path.exists(zip_path):
    print(f"\n[OK] 压缩完成: {zip_path}")

# Done
print(f"\n{'='*50}")
print(f"  打包全部完成!")
print(f"  exe: {os.path.join(dist_dir, '瑞玛丽小助手.exe')}")
print(f"  zip: {zip_path}")
print(f"{'='*50}\n")
os.system("pause")
