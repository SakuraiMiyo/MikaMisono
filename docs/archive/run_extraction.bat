@echo off
chcp 65001 >nul
echo ============================================
echo Blue Archive JP - Story Data Extraction
echo ============================================
set PYTHON=C:\Users\Misono Mika\AppData\Local\Programs\Python\Python313\python.exe
echo Using Python: %PYTHON%
echo.
echo [Step 1] Extracting story tables from TableBundles...
%PYTHON% "%~dp0extract_story.py"
echo.
echo [Step 2] Extracting media files from MediaPatch...
%PYTHON% "%~dp0extract_media.py"
echo.
echo Done!
pause
