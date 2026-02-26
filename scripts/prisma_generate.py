import os
import site
import subprocess
import sys
from pathlib import Path


def main() -> int:
    scripts_dir = Path(site.getusersitepackages()).parent / "Scripts"
    prisma_executable = scripts_dir / ("prisma.exe" if os.name == "nt" else "prisma")

    env = os.environ.copy()
    env["PATH"] = f"{scripts_dir}{os.pathsep}{env.get('PATH', '')}"

    command = [str(prisma_executable), "generate"] if prisma_executable.exists() else ["prisma", "generate"]
    process = subprocess.run(command, env=env, cwd=Path(__file__).resolve().parents[1], check=False)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
