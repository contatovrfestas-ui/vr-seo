'use strict';

const { Command } = require('commander');
const colors = require('ansi-colors');
const ora = require('ora');
const Orchestrator = require('../../core/orchestrator');
const logger = require('../../services/logger');

function createOrchestrateCommand() {
  const run = new Command('run')
    .description('Run the full SEO pipeline (audit + content recommendations)')
    .requiredOption('--url <url>', 'Website URL')
    .option('--full', 'Run full pipeline: audit → analyze → content plan → generate')
    .option('--depth <depth>', 'Crawl depth', parseInt, 2)
    .option('--max-pages <maxPages>', 'Maximum pages to crawl', parseInt, 50)
    .option('--lang <language>', 'Content language', 'pt-BR')
    .action(async (options) => {
      const spinner = ora('Starting SEO pipeline...').start();
      try {
        const orchestrator = new Orchestrator();

        orchestrator.on('phase', ({ phase, description }) => {
          spinner.text = `[${phase}] ${description}`;
        });

        orchestrator.on('progress', ({ message }) => {
          spinner.text = message;
        });

        const result = await orchestrator.run({
          url: options.url,
          full: options.full,
          depth: options.depth,
          maxPages: options.maxPages,
          language: options.lang,
        });

        spinner.succeed('Pipeline complete!');

        console.log('');
        console.log(colors.bold('Pipeline Results:'));
        console.log(colors.gray(`  Audit Score: ${result.audit?.score || 'N/A'}/100`));
        console.log(colors.gray(`  Issues Found: ${result.audit?.issues?.length || 0}`));
        console.log(colors.gray(`  Content Generated: ${result.content?.length || 0} pieces`));
        console.log('');

        if (result.outputFiles) {
          console.log(colors.green('Output files:'));
          for (const file of result.outputFiles) {
            console.log(`  ${file}`);
          }
        }
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  return run;
}

module.exports = createOrchestrateCommand;
