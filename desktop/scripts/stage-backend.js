#!/usr/bin/env node
'use strict';

const { spawn } = require('child_process');
const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const desktopRoot = path.resolve(__dirname, '..');
const buildRoot = path.join(desktopRoot, 'build');
const backendStagingDir = path.join(buildRoot, 'backend');

async function ensureDirectory(dirPath) {
  await fsp.mkdir(dirPath, { recursive: true });
}

function pickSystemPython() {
  return (
    process.env.RECRUITPRO_PYTHON_BUILD ||
    process.env.PYTHON_FOR_BUILD ||
    process.env.PYTHON ||
    (process.platform === 'win32' ? 'python' : 'python3')
  );
}

function pythonFromVenv(venvPath) {
  if (process.platform === 'win32') {
    return path.join(venvPath, 'Scripts', 'python.exe');
  }
  return path.join(venvPath, 'bin', 'python3');
}

async function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: 'inherit',
      env: process.env,
      ...options
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`${command} ${args.join(' ')} exited with code ${code}`));
      } else {
        resolve();
      }
    });
  });
}

async function copyResource(fromPath, toPath) {
  const stats = await fsp.stat(fromPath);
  if (stats.isDirectory()) {
    await fsp.cp(fromPath, toPath, {
      recursive: true,
      filter: (source) => {
        const name = path.basename(source);
        if (name === '__pycache__' || name.endsWith('.pyc') || name.endsWith('.pyo')) {
          return false;
        }
        return true;
      }
    });
  } else {
    await ensureDirectory(path.dirname(toPath));
    await fsp.copyFile(fromPath, toPath);
  }
}

async function stageBackendSources() {
  const resources = [
    { from: path.join(repoRoot, 'app'), to: path.join(backendStagingDir, 'app') },
    { from: path.join(repoRoot, 'templates'), to: path.join(backendStagingDir, 'templates') },
    { from: path.join(repoRoot, 'pyproject.toml'), to: path.join(backendStagingDir, 'pyproject.toml') },
    { from: path.join(repoRoot, 'README.md'), to: path.join(backendStagingDir, 'README.md') }
  ];

  for (const resource of resources) {
    await copyResource(resource.from, resource.to);
  }
}

async function createVirtualEnv(targetDir) {
  const pythonExecutable = pickSystemPython();
  console.log(`[stage-backend] Using Python executable: ${pythonExecutable}`);

  await runCommand(pythonExecutable, ['-m', 'venv', targetDir]);

  const venvPython = pythonFromVenv(targetDir);
  if (!fs.existsSync(venvPython)) {
    throw new Error(`Virtual environment python binary was not created at ${venvPython}`);
  }

  console.log('[stage-backend] Upgrading pip in staged virtual environment');
  await runCommand(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip', 'wheel', 'setuptools']);

  console.log('[stage-backend] Installing RecruitPro backend and dependencies');
  await runCommand(venvPython, ['-m', 'pip', 'install', '--upgrade', repoRoot]);

  return venvPython;
}

async function writeRuntimeMetadata(venvPythonPath) {
  const metadata = {
    createdAt: new Date().toISOString(),
    python: path.relative(backendStagingDir, venvPythonPath)
  };
  const filePath = path.join(backendStagingDir, 'runtime.json');
  await fsp.writeFile(filePath, JSON.stringify(metadata, null, 2));
}

async function main() {
  console.log('[stage-backend] Preparing backend resources for packaging');
  await ensureDirectory(buildRoot);
  await fsp.rm(backendStagingDir, { recursive: true, force: true });
  await ensureDirectory(backendStagingDir);

  await stageBackendSources();
  const venvDir = path.join(backendStagingDir, 'venv');
  const venvPython = await createVirtualEnv(venvDir);
  await writeRuntimeMetadata(venvPython);
  console.log('[stage-backend] Backend staging complete');
}

main().catch((error) => {
  console.error('[stage-backend] Failed to stage backend', error);
  process.exitCode = 1;
});
