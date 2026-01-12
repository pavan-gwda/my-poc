const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow () {
  const win = new BrowserWindow({
    width: 1000,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // If you built the frontend, point to file://../frontend/dist/index.html
  // During development, point to http://localhost:5173
  const dev = true;
  if (dev) {
    win.loadURL('http://localhost:5173');
  } else {
    win.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
  }
}

app.whenReady().then(createWindow);
