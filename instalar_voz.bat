@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Instalador da voz RVC do Jarvis
echo ============================================================
echo   Instalador do motor de voz RVC (AMD/Intel - DirectML)
echo ============================================================
echo.

if not exist voice_engine mkdir voice_engine
if not exist voices\cortana mkdir voices\cortana

for /r voice_engine %%F in (python.exe) do (
  if exist "%%F" echo %%F | find /i "\runtime\python.exe" >nul && (
    echo [OK] Motor RVC ja instalado: %%F
    goto :model
  )
)

set "PKG=voice_engine\RVC1006AMD_Intel.7z"
set "URL=https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/RVC1006AMD_Intel.7z"

if not exist "%PKG%" (
  echo Baixando o pacote RVC para AMD/Intel ^(varios GB, pode demorar^)...
  curl -L --fail -o "%PKG%" "%URL%"
  if errorlevel 1 (
    echo.
    echo [ERRO] Nao consegui baixar automaticamente.
    echo Baixe manualmente o arquivo RVC1006AMD_Intel.7z da pagina que vai abrir
    echo e coloque dentro da pasta voice_engine, depois rode este instalador de novo.
    start "" "https://huggingface.co/lj1995/VoiceConversionWebUI/tree/main"
    del "%PKG%" 2>nul
    pause
    exit /b 1
  )
)

echo Extraindo...
set "SEVENZIP=%ProgramFiles%\7-Zip\7z.exe"
if exist "%SEVENZIP%" (
  "%SEVENZIP%" x "%PKG%" -o"voice_engine\rvc" -y >nul
) else (
  if not exist voice_engine\rvc mkdir voice_engine\rvc
  tar -xf "%PKG%" -C voice_engine\rvc
)
if errorlevel 1 (
  echo.
  echo [ERRO] Nao consegui extrair. Instale o 7-Zip ^(7-zip.org^) e rode de novo.
  pause
  exit /b 1
)
echo [OK] Motor RVC instalado.
del "%PKG%" 2>nul

:model
echo.
dir /b voices\cortana\*.pth >nul 2>&1
if errorlevel 1 (
  echo [FALTA] Coloque o modelo da Cortana em:  %cd%\voices\cortana\
  echo         - o arquivo .pth  ^(obrigatorio^)
  echo         - o arquivo .index ^(recomendado, use o que comeca com "added_"^)
  start "" explorer "%cd%\voices\cortana"
) else (
  echo [OK] Modelo encontrado em voices\cortana
)
echo.
echo Pronto. Abra o Jarvis normalmente - a voz liga sozinha.
echo No painel CONTROLS ha o botao "VOZ" para alternar entre Cortana e a voz normal.
echo Se algo der errado, veja voice_engine\rvc_server.log
pause
