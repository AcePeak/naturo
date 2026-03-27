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

REM Pull latest code
cd /d %REPO%
git pull origin main >> "%LOG_FILE%" 2>&1

REM Read the qa-prompt.md and run it via Claude Code
echo [%date% %time%] Starting QA-Mariana round >> "%LOG_FILE%"

claude -p --dangerously-skip-permissions --verbose --model opus "You are QA-Mariana. Read the file agents/orchestrator/qa-prompt.md and execute ALL phases described in it. You are on a real Windows desktop. Use naturo CLI directly. Use gh CLI for GitHub issues (repo: AcePeak/naturo). Start now." >> "%LOG_FILE%" 2>&1

echo [%date% %time%] QA-Mariana round complete >> "%LOG_FILE%"
