// Naturo recognition benchmark — owned Electron fixture (issue #933).
//
// This is a REAL Electron main process. It opens a single BrowserWindow that
// renders ``index.html`` (varied interactive controls). The window is launched
// with a Chrome DevTools Protocol (CDP) remote-debugging endpoint so naturo's
// CDP provider can enumerate the renderer DOM — content that the Windows UIA
// accessibility tree collapses into a single opaque node.
//
// The debug port and the requirement to allow CDP WebSocket origins are set
// via command-line switches BEFORE ``app`` is ready, which is the only point
// at which Chromium reads them. The port defaults to 9333 (distinct from
// Chrome's 9222 used by the sibling HTML fixture) and can be overridden with
// ``--remote-debugging-port=<port>`` on the command line or the
// ``NATURO_FIXTURE_CDP_PORT`` environment variable.

'use strict';

const { app, BrowserWindow } = require('electron');
const path = require('path');

/**
 * Resolve the CDP remote-debugging port.
 *
 * Precedence: an explicit ``--remote-debugging-port=<n>`` switch already on the
 * command line, then ``NATURO_FIXTURE_CDP_PORT``, then the default 9333.
 *
 * @returns {string} The port as a string.
 */
function resolveDebugPort() {
  const cliSwitch = process.argv.find((arg) =>
    arg.startsWith('--remote-debugging-port=')
  );
  if (cliSwitch) {
    return cliSwitch.split('=')[1];
  }
  return process.env.NATURO_FIXTURE_CDP_PORT || '9333';
}

const debugPort = resolveDebugPort();

// These switches must be appended before the app is ready. ``--remote-allow-
// origins=*`` is mandatory on modern Chromium, otherwise the CDP WebSocket
// handshake is rejected. Setting the port via appendSwitch is harmless if the
// same switch is already present on the command line (Chromium de-dupes).
app.commandLine.appendSwitch('remote-debugging-port', debugPort);
app.commandLine.appendSwitch('remote-allow-origins', '*');

// Keep the fixture deterministic and headless-friendly on CI/desktop:
// disable GPU acceleration (avoids driver variance) and run in a throwaway
// user-data dir so no profile state leaks between runs.
app.commandLine.appendSwitch('disable-gpu');
if (process.env.NATURO_FIXTURE_USER_DATA_DIR) {
  app.setPath('userData', process.env.NATURO_FIXTURE_USER_DATA_DIR);
}

/**
 * Create the single fixture window and load the renderer.
 *
 * @returns {void}
 */
function createWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 800,
    show: true,
    title: 'Naturo Electron Recognition Fixture',
    webPreferences: {
      // The renderer is a static, trusted local file with no privileged needs.
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  win.setMenuBarVisibility(false);
  win.loadFile(path.join(__dirname, 'index.html'));
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// On Windows/Linux, quitting when all windows close lets the harness control
// the process lifetime cleanly (it terminates us when measurement is done).
app.on('window-all-closed', () => {
  app.quit();
});
