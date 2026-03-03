'use strict';

const path = require('path');
const fs = require('fs');
const os = require('os');

const dotenvPath = path.resolve(process.cwd(), '.env');
if (fs.existsSync(dotenvPath)) {
  require('dotenv').config({ path: dotenvPath });
}

const defaults = require('../../config/default');

class ConfigManager {
  constructor() {
    this._configDir = path.join(os.homedir(), '.vr-seo');
    this._configFile = path.join(this._configDir, 'config.json');
    this._userConfig = this._load();
  }

  _ensureDir() {
    if (!fs.existsSync(this._configDir)) {
      fs.mkdirSync(this._configDir, { recursive: true });
    }
  }

  _load() {
    try {
      if (fs.existsSync(this._configFile)) {
        return JSON.parse(fs.readFileSync(this._configFile, 'utf-8'));
      }
    } catch {
      // ignore corrupt config
    }
    return {};
  }

  _save() {
    this._ensureDir();
    fs.writeFileSync(this._configFile, JSON.stringify(this._userConfig, null, 2));
  }

  get(key) {
    // Priority: env var → user config → defaults
    const envKey = key.toUpperCase().replace(/\./g, '_');
    if (process.env[envKey] !== undefined) return process.env[envKey];
    if (this._userConfig[key] !== undefined) return this._userConfig[key];

    // Resolve dotted key from defaults
    const parts = key.split('.');
    let val = defaults;
    for (const p of parts) {
      if (val == null) return undefined;
      val = val[p];
    }
    return val;
  }

  set(key, value) {
    this._userConfig[key] = value;
    this._save();
  }

  delete(key) {
    delete this._userConfig[key];
    this._save();
  }

  list() {
    return { ...this._userConfig };
  }

  getConfigDir() {
    this._ensureDir();
    return this._configDir;
  }

  getDefaults() {
    return { ...defaults };
  }
}

module.exports = new ConfigManager();
