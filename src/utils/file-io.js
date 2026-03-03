'use strict';

const fs = require('fs');
const path = require('path');
const configManager = require('../services/config-manager');
const logger = require('../services/logger');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function getOutputDir() {
  const dir = configManager.get('output.dir') || './output';
  const resolved = path.resolve(dir);
  ensureDir(resolved);
  return resolved;
}

function generateFilename(prefix, extension) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  return `${prefix}-${timestamp}.${extension}`;
}

function saveOutput(content, filename, subdir) {
  const outputDir = getOutputDir();
  const dir = subdir ? path.join(outputDir, subdir) : outputDir;
  ensureDir(dir);

  const filePath = path.join(dir, filename);
  fs.writeFileSync(filePath, content, 'utf-8');
  logger.info(`Output saved: ${filePath}`);
  return filePath;
}

function readFile(filePath) {
  return fs.readFileSync(filePath, 'utf-8');
}

module.exports = { ensureDir, getOutputDir, generateFilename, saveOutput, readFile };
