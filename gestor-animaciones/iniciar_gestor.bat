@echo off
cd /d C:\Videos_Josue\gestor-animaciones
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
start /min "" py -3.11 anim_server.py
timeout /t 3 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:5050 --window-size=820,920 --new-window