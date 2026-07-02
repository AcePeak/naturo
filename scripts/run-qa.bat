@echo off
REM QA-Mariana hourly runner
REM Runs Claude Code with qa-prompt.md in the naturo repo

set REPO=C:\Users\Naturobot\naturo
set LOG_DIR=%REPO%\agents\qa\logs
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%-%time:~0,2%%time:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_FILE=%LOG_DIR%\qa-%TIMESTAMP%.log

REM Ensure log directory exists
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Add GitHub CLI to PATH
set PATH=%PATH%;C:\Program Files\GitHub CLI

REM Pull latest code from develop branch
cd /d %REPO%
git stash >> "%LOG_FILE%" 2>&1
git fetch origin develop >> "%LOG_FILE%" 2>&1
git checkout develop >> "%LOG_FILE%" 2>&1
git pull origin develop >> "%LOG_FILE%" 2>&1
git stash pop >> "%LOG_FILE%" 2>&1

REM Read the qa-prompt.md and run it via Claude Code
echo [%date% %time%] Starting QA-Mariana round >> "%LOG_FILE%"

claude -p --dangerously-skip-permissions --verbose --model opus "Read the file agents/orchestrator/qa-prompt.md and follow all instructions in it exactly." >> "%LOG_FILE%" 2>&1

echo [%date% %time%] QA-Mariana round complete >> "%LOG_FILE%"
