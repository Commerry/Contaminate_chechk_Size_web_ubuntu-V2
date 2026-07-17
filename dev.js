#!/usr/bin/env node
/*
 * PSE Vision dev launcher — starts the Python backend (port 64021) and the
 * Vite dev server (port 64020) together. Cross-platform (Windows / Linux).
 *
 *   npm run dev
 *
 * Vite proxies /api and /socket.io to the backend, so open http://localhost:64020
 */
const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')

const ROOT = __dirname
const isWin = process.platform === 'win32'

// Pick a Python interpreter: prefer a project venv, then fall back to PATH.
function findPython() {
  const candidates = isWin
    ? [
        path.join(ROOT, '.venv_test', 'Scripts', 'python.exe'),
        path.join(ROOT, 'venv', 'Scripts', 'python.exe'),
        path.join(ROOT, '.venv', 'Scripts', 'python.exe'),
      ]
    : [
        path.join(ROOT, 'venv', 'bin', 'python'),
        path.join(ROOT, '.venv', 'bin', 'python'),
        path.join(ROOT, '.venv_test', 'bin', 'python'),
      ]
  for (const c of candidates) {
    if (fs.existsSync(c)) return c
  }
  return isWin ? 'python' : 'python3'
}

const PYTHON = findPython()
const BACKEND_PORT = process.env.FLASK_PORT || '64021'
const FRONTEND_PORT = process.env.FRONTEND_PORT || '64020'

const procs = []

function run(name, cmd, args, opts = {}) {
  const p = spawn(cmd, args, {
    cwd: opts.cwd || ROOT,
    env: { ...process.env, ...(opts.env || {}) },
    stdio: 'inherit',
    shell: false,
  })
  p.on('error', (err) => {
    console.error(`[${name}] failed to start:`, err.message)
  })
  p.on('exit', (code) => {
    console.log(`[${name}] exited with code ${code}`)
    shutdown()
  })
  procs.push(p)
  return p
}

function shutdown() {
  for (const p of procs) {
    if (!p.killed) {
      try { p.kill() } catch (e) { /* ignore */ }
    }
  }
  process.exit()
}

process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)

console.log('PSE Vision dev launcher')
console.log(`  Python : ${PYTHON}`)
console.log(`  Backend: http://localhost:${BACKEND_PORT}`)
console.log(`  UI     : http://localhost:${FRONTEND_PORT}  <-- open this`)
console.log('')

// Backend (serves REST + Socket.IO on 64021)
run('backend', PYTHON, [path.join('python_scripts', 'backend_server.py')], {
  env: { FLASK_PORT: BACKEND_PORT, PYTHONUNBUFFERED: '1' },
})

// Frontend (Vite dev server on 64020, proxies /api + /socket.io to backend).
// Invoke Vite's JS entry with the current Node binary to stay cross-platform
// and avoid spawning a .cmd shim (which Node refuses on Windows).
const viteBin = path.join(ROOT, 'frontend', 'node_modules', 'vite', 'bin', 'vite.js')
if (!fs.existsSync(viteBin)) {
  console.error('[frontend] Vite not found. Run "npm install" inside ./frontend first.')
  shutdown()
}
run('frontend', process.execPath, [viteBin, '--host', '0.0.0.0', '--port', FRONTEND_PORT], {
  cwd: path.join(ROOT, 'frontend'),
})
