@echo off
cd /d "%~dp0.."
if /i "%1"=="commit" (
    .venv\Scripts\python -c "import pathlib; root=pathlib.Path('.'); lines=sorted(str(p).replace('\\\\','/') for p in [root]+list(root.rglob('*')) if not any(part in {'.git','.venv','__pycache__'} for part in p.parts) and not str(p).endswith('.pyc')); open('directory_structure.txt','w').write('\n'.join(lines)+'\n')"
    git add -A
    git commit -m "%~2"
) else (
    echo Usage: build\git.bat commit "commit message"
    exit /b 1
)
