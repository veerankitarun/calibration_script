

@REM :start

@REM python "src\app.py" %*

@REM REM Check the exit code of the Python script
@REM if %errorlevel% equ 0 (
@REM     REM Set terminal color to green (2 is green for background, 7 is white for text)
@REM     color 47
@REM ) else (
@REM     REM Set terminal color to red (4 is red for background, 7 is white for text)
@REM     color 27
@REM )

@REM pause
@REM cls

@REM REM Reset terminal color to default
@REM color 07
@REM goto start

@echo off
:start
python src/app.py
pause
cls
goto start