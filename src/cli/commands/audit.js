'use strict';

const { Command } = require('commander');
const colors = require('ansi-colors');
const ora = require('ora');
const Table = require('cli-table3');
const AuditAgent = require('../../agents/audit');
const { saveOutput, generateFilename } = require('../../utils/file-io');
const { formatAuditReport } = require('../../formatters/markdown');
const jsonFormatter = require('../../formatters/json');
const htmlFormatter = require('../../formatters/html');
const logger = require('../../services/logger');

function createAuditCommand() {
  const audit = new Command('audit')
    .description('Run SEO audit on a website')
    .option('--url <url>', 'Website URL to audit')
    .option('--sitemap <sitemap>', 'Sitemap URL to audit')
    .option('--depth <depth>', 'Crawl depth', parseInt, 2)
    .option('--max-pages <maxPages>', 'Maximum pages to crawl', parseInt, 50)
    .action(async (options) => {
      if (!options.url && !options.sitemap) {
        console.error(colors.red('Error: --url or --sitemap is required'));
        process.exitCode = 1;
        return;
      }

      const spinner = ora('Running SEO audit...').start();
      try {
        const agent = new AuditAgent();
        const result = await agent.run({
          url: options.url,
          sitemap: options.sitemap,
          depth: options.depth,
          maxPages: options.maxPages,
        });

        spinner.succeed('Audit complete!');
        displayAuditResults(result);
        saveAuditResults(result);
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  audit
    .command('cwv')
    .description('Run Core Web Vitals analysis only')
    .requiredOption('--url <url>', 'URL to analyze')
    .action(async (options) => {
      const spinner = ora('Measuring Core Web Vitals...').start();
      try {
        const agent = new AuditAgent();
        const result = await agent.run({
          url: options.url,
          mode: 'cwv',
        });

        spinner.succeed('CWV analysis complete!');
        displayAuditResults(result);
        saveAuditResults(result);
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  audit
    .command('links')
    .description('Check for broken links')
    .requiredOption('--url <url>', 'URL to check')
    .option('--depth <depth>', 'Crawl depth', parseInt, 1)
    .option('--max-pages <maxPages>', 'Max pages', parseInt, 20)
    .action(async (options) => {
      const spinner = ora('Checking links...').start();
      try {
        const agent = new AuditAgent();
        const result = await agent.run({
          url: options.url,
          mode: 'links',
          depth: options.depth,
          maxPages: options.maxPages,
        });

        spinner.succeed('Link check complete!');
        displayAuditResults(result);
        saveAuditResults(result);
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  audit
    .command('interactive')
    .description('Interactive audit wizard')
    .action(async () => {
      try {
        const prompts = require('../prompts/audit-prompts');
        await prompts.run();
      } catch (err) {
        console.error(colors.red(`Error: ${err.message}`));
        logger.error(err);
        process.exitCode = 1;
      }
    });

  return audit;
}

function displayAuditResults(result) {
  console.log('');
  console.log(colors.bold(`SEO Audit: ${result.url}`));

  // Score
  const scoreColor = result.score >= 80 ? 'green' : result.score >= 50 ? 'yellow' : 'red';
  console.log(colors[scoreColor](`Score: ${result.score}/100`));
  console.log(colors.gray(result.summary));
  console.log('');

  // Issues table
  if (result.issues.length > 0) {
    const table = new Table({
      head: [colors.bold('Severity'), colors.bold('Issue'), colors.bold('Page')],
      colWidths: [12, 40, 40],
      wordWrap: true,
    });

    const sorted = [...result.issues].sort((a, b) => {
      const order = { critical: 0, warning: 1, info: 2 };
      return (order[a.severity] || 3) - (order[b.severity] || 3);
    });

    for (const issue of sorted.slice(0, 20)) {
      const sev =
        issue.severity === 'critical'
          ? colors.red(issue.severity)
          : issue.severity === 'warning'
            ? colors.yellow(issue.severity)
            : colors.blue(issue.severity);
      table.push([sev, issue.title, issue.page || '-']);
    }

    console.log(table.toString());
    if (result.issues.length > 20) {
      console.log(colors.gray(`... and ${result.issues.length - 20} more issues (see full report)`));
    }
  }

  // CWV
  if (result.cwv) {
    console.log('');
    console.log(colors.bold('Core Web Vitals:'));
    console.log(`  LCP: ${result.cwv.lcp?.displayValue || 'N/A'}`);
    console.log(`  FID: ${result.cwv.fid?.displayValue || 'N/A'}`);
    console.log(`  CLS: ${result.cwv.cls?.displayValue || 'N/A'}`);
  }

  console.log('');
}

function saveAuditResults(result) {
  const mdContent = formatAuditReport(result);
  const jsonContent = jsonFormatter.formatAuditReport(result);
  const htmlContent = htmlFormatter.formatAuditReport(result);

  const mdFile = saveOutput(mdContent, generateFilename('audit', 'md'), 'audit');
  const jsonFile = saveOutput(jsonContent, generateFilename('audit', 'json'), 'audit');
  const htmlFile = saveOutput(htmlContent, generateFilename('audit', 'html'), 'audit');

  console.log(colors.green('Reports saved:'));
  console.log(`  Markdown: ${mdFile}`);
  console.log(`  JSON:     ${jsonFile}`);
  console.log(`  HTML:     ${htmlFile}`);
}

module.exports = createAuditCommand;
