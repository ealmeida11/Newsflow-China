@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ===== Newsflow China =====
echo.
echo [1/2] Rodando NewsFlow-app...
python NewsFlow-app.py
if errorlevel 1 (
    echo Erro ao rodar o app. Abortando.
    pause
    exit /b 1
)

echo.
echo [2/2] Git add, commit e push...
git add .
git commit -m "Newsflow update %date% %time%" 2>nul || echo Nenhuma alteracao para commitar
git push
if errorlevel 1 (
    echo Verifique se o remote origin esta configurado: git remote -v
    pause
    exit /b 1
)

echo.
echo Concluido.
pause
