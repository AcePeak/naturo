# Naturo Error Codes Reference

All Naturo CLI commands return structured errors in `--json` mode with the format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "suggested_action": "What to do to recover (for AI agents)",
    "recoverable": true
  }
}
```

## Error Codes

### Input Validation

| Code | Recoverable | Description |
|------|------------|-------------|
| `INVALID_INPUT` | No | Parameter value is invalid. Check `--help` for valid options. |
| `INVALID_COORDINATES` | No | Coordinates are outside screen bounds. |

### Not Found

| Code | Recoverable | Description |
|------|------------|-------------|
| `APP_NOT_FOUND` | Yes | Application is not running. Use `app list` to check, or `app launch` to start. |
| `WINDOW_NOT_FOUND` | Yes | No matching window. Use `list windows` to see available windows. |
| `ELEMENT_NOT_FOUND` | Yes | UI element not in tree. Use `see` to inspect, or `wait --element` to wait. |
| `MENU_NOT_FOUND` | Yes | Menu item not found. Use `menu-inspect` to see the menu structure. |
| `SNAPSHOT_NOT_FOUND` | No | Snapshot ID doesn't exist. Use `snapshot list` to see available snapshots. |
| `FILE_NOT_FOUND` | No | Specified file path doesn't exist. |
| `PROCESS_NOT_FOUND` | Yes | Process exited. Use `app list` to verify. |

### Operation Failures

| Code | Recoverable | Description |
|------|------------|-------------|
| `CAPTURE_FAILED` | Yes | Screenshot failed. Ensure window is not minimized. |
| `CAPTURE_ERROR` | Yes | Screenshot failed (legacy code, same as CAPTURE_FAILED). |
| `INTERACTION_FAILED` | Yes | Click/type/etc. failed. Verify element exists and window is focused. |
| `TIMEOUT` | Yes | Operation timed out. Increase `--timeout` or verify UI state. |
| `WINDOW_OPERATION_FAILED` | Yes | Window management operation failed. |

### AI Errors

| Code | Recoverable | Description |
|------|------------|-------------|
| `AI_PROVIDER_UNAVAILABLE` | No | No API key set. Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. |
| `AI_ANALYSIS_FAILED` | Yes | AI inference failed. Try a different provider or simpler prompt. |
| `AGENT_ERROR` | Yes | Agent execution failed. Simplify instruction or increase `--max-steps`. |

### System Errors

| Code | Recoverable | Description |
|------|------------|-------------|
| `PLATFORM_ERROR` | No | Feature requires Windows desktop session. |
| `NOT_IMPLEMENTED` | No | Feature not yet available. |
| `PERMISSION_DENIED` | No | Insufficient permissions. May need Administrator. |
| `MISSING_DEPENDENCY` | No | Required package not installed. |
| `UNKNOWN_ERROR` | No | Unexpected error. |

## Recovery Strategy for AI Agents

1. **Check `recoverable`**: If `true`, the operation might succeed if retried after the suggested fix.
2. **Read `suggested_action`**: Contains specific naturo commands to diagnose or fix the issue.
3. **Common patterns**:
   - `WINDOW_NOT_FOUND` → `naturo list windows` to find the correct window name
   - `ELEMENT_NOT_FOUND` → `naturo see --app <name>` to inspect the UI tree
   - `TIMEOUT` → increase `--timeout` or `naturo capture live` to check UI state
   - `APP_NOT_FOUND` → `naturo app launch <name>` to start the application

## Exit Codes

- `0` — Success
- `1` — Error (all error types)
- Non-zero exit code always accompanies `"success": false` in JSON output.
