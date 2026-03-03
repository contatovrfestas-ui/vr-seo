#!/usr/bin/env node
'use strict';

const createCli = require('./src/cli');

const program = createCli();
program.parseAsync(process.argv).catch((err) => {
  console.error(err.message);
  process.exitCode = 1;
});
