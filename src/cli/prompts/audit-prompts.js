'use strict';

const { Select, Input, NumberPrompt } = require('enquirer');
const colors = require('ansi-colors');
const ora = require('ora');
const Table = require('cli-table3');
const AuditAgent = require('../../agents/audit');
const { saveOutput, generateFilename } = require('../../utils/file-io');
const { formatAuditReport } = require('../../formatters/markdown');
const jsonFormatter = require('../../formatters/json');
const htmlFormatter = require('../../formatters/html');

async function run() {
  console.log(colors.bold.cyan('\n  SEO Audit Wizard\n'));

  const mode = await new Select({
    message: 'What type of audit?',
    choices: [
      { name: 'full', message: 'Full SEO Audit' },
      { name: 'cwv', message: 'Core Web Vitals Only' },
      { name: 'links', message: 'Broken Links Check' },
      { name: 'sitemap', message: 'Sitemap Audit' },
    ],
  }).run();

  let params = {};

  if (mode === 'sitemap') {
    params.sitemap = await new Input({
      message: 'Sitemap URL:',
      validate: (v) => (v.startsWith('http') ? true : 'Enter a valid URL'),
    }).run();
  } else {
    params.url = await new Input({
      message: 'Website URL:',
      validate: (v) => (v.startsWith('http') ? true : 'Enter a valid URL'),
    }).run();
  }

  if (mode === 'full' || mode === 'links') {
    params.depth = await new NumberPrompt({
      message: 'Crawl depth:',
      initial: 2,
    }).run();

    params.maxPages = await new NumberPrompt({
      message: 'Maximum pages:',
      initial: 50,
    }).run();
  }

  if (mode !== 'full') {
    params.mode = mode;
  }

  const spinner = ora('Running SEO audit...').start();

  try {
    const agent = new AuditAgent();
    const result = await agent.run(params);

    spinner.succeed('Audit complete!');

    // Display results
    console.log('');
    const scoreColor = result.score >= 80 ? 'green' : result.score >= 50 ? 'yellow' : 'red';
    console.log(colors.bold(`Score: `) + colors[scoreColor](`${result.score}/100`));
    console.log(colors.gray(result.summary));

    if (result.issues.length > 0) {
      const table = new Table({
        head: [colors.bold('Severity'), colors.bold('Issue')],
        colWidths: [12, 60],
        wordWrap: true,
      });

      for (const issue of result.issues.slice(0, 15)) {
        const sev =
          issue.severity === 'critical'
            ? colors.red(issue.severity)
            : issue.severity === 'warning'
              ? colors.yellow(issue.severity)
              : colors.blue(issue.severity);
        table.push([sev, issue.title]);
      }
      console.log(table.toString());
    }

    // Save
    const mdFile = saveOutput(formatAuditReport(result), generateFilename('audit', 'md'), 'audit');
    const jsonFile = saveOutput(jsonFormatter.formatAuditReport(result), generateFilename('audit', 'json'), 'audit');
    const htmlFile = saveOutput(htmlFormatter.formatAuditReport(result), generateFilename('audit', 'html'), 'audit');

    console.log(colors.green('\nReports saved:'));
    console.log(`  Markdown: ${mdFile}`);
    console.log(`  JSON:     ${jsonFile}`);
    console.log(`  HTML:     ${htmlFile}`);
  } catch (err) {
    spinner.fail(`Error: ${err.message}`);
    throw err;
  }
}

module.exports = { run };
