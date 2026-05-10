
Copiar

@echo off
cd /d C:\Videos_Josue\gestor-animaciones
set OPENAI_API_KEY=TU_KEY_AQUI
start /min "" py -3.11 anim_server.py
timeout /t 3 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:5050 --window-size=820,920 --new-window
 rome\Application\chrome.exe" --app=http://localhost:5050 --window-size=800,900 --window-position=100,50