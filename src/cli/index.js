'use strict';

const { Command } = require('commander');
const colors = require('ansi-colors');
const pkg = require('../../package.json');

function createCli() {
  const program = new Command();

  program
    .name('vr-seo')
    .description(colors.bold('VR SEO — AI-Powered SEO Agency CLI'))
    .version(pkg.version);

  // Register commands
  program.addCommand(require('./commands/content')());
  program.addCommand(require('./commands/audit')());
  program.addCommand(require('./commands/orchestrate')());
  program.addCommand(require('./commands/auth')());
  program.addCommand(require('./commands/config')());

  return program;
}

module.exports = createCli;
