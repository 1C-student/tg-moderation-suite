@echo off
python -m pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --name TGModerationManager manager_gui.py
echo EXE file: dist\TGModerationManager.exe
pause
