'use strict';

const { Command } = require('commander');
const colors = require('ansi-colors');
const Table = require('cli-table3');
const configManager = require('../../services/config-manager');

function createConfigCommand() {
  const config = new Command('config')
    .description('Manage configuration');

  config
    .command('set <key> <value>')
    .description('Set a configuration value')
    .action((key, value) => {
      configManager.set(key, value);
      console.log(colors.green(`Set ${key} = ${maskSensitive(key, value)}`));
    });

  config
    .command('get <key>')
    .description('Get a configuration value')
    .action((key) => {
      const value = configManager.get(key);
      if (value !== undefined) {
        console.log(`${key} = ${maskSensitive(key, value)}`);
      } else {
        console.log(colors.yellow(`${key} is not set`));
      }
    });

  config
    .command('delete <key>')
    .description('Delete a configuration value')
    .action((key) => {
      configManager.delete(key);
      console.log(colors.green(`Deleted ${key}`));
    });

  config
    .command('list')
    .description('List all configuration values')
    .action(() => {
      const values = configManager.list();
      const keys = Object.keys(values);

      if (keys.length === 0) {
        console.log(colors.gray('No user configuration set. Using defaults.'));
        return;
      }

      const table = new Table({
        head: [colors.bold('Key'), colors.bold('Value')],
      });

      for (const key of keys) {
        table.push([key, maskSensitive(key, values[key])]);
      }

      console.log(table.toString());
    });

  return config;
}

function maskSensitive(key, value) {
  const sensitiveKeys = ['api_key', 'apikey', 'secret', 'password', 'token'];
  const lowerKey = key.toLowerCase();
  if (sensitiveKeys.some((k) => lowerKey.includes(k)) && typeof value === 'string' && value.length > 8) {
    return value.slice(0, 7) + '...' + value.slice(-4);
  }
  return String(value);
}

module.exports = createConfigCommand;
