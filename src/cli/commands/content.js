'use strict';

const { Command } = require('commander');
const colors = require('ansi-colors');
const ora = require('ora');
const ContentAgent = require('../../agents/content');
const { saveOutput, generateFilename } = require('../../utils/file-io');
const { parseKeywords } = require('../../utils/validators');
const { formatContentOutput } = require('../../formatters/markdown');
const jsonFormatter = require('../../formatters/json');
const logger = require('../../services/logger');

function createContentCommand() {
  const content = new Command('content')
    .description('Generate SEO-optimized content');

  content
    .command('blog')
    .description('Generate an SEO-optimized blog post')
    .requiredOption('--topic <topic>', 'Blog post topic')
    .requiredOption('--keywords <keywords>', 'Target keywords (comma-separated)')
    .option('--tone <tone>', 'Writing tone', 'professional')
    .option('--lang <language>', 'Content language', 'pt-BR')
    .action(async (options) => {
      const spinner = ora('Generating blog post...').start();
      try {
        const agent = new ContentAgent();
        const result = await agent.run({
          type: 'blog',
          topic: options.topic,
          keywords: parseKeywords(options.keywords),
          tone: options.tone,
          language: options.lang,
        });

        spinner.succeed('Blog post generated!');
        saveResults(result);
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  content
    .command('landing-page')
    .description('Generate a conversion-focused landing page')
    .requiredOption('--topic <topic>', 'Landing page topic')
    .requiredOption('--keywords <keywords>', 'Target keywords (comma-separated)')
    .option('--tone <tone>', 'Writing tone', 'professional')
    .option('--lang <language>', 'Content language', 'pt-BR')
    .action(async (options) => {
      const spinner = ora('Generating landing page...').start();
      try {
        const agent = new ContentAgent();
        const result = await agent.run({
          type: 'landing-page',
          topic: options.topic,
          keywords: parseKeywords(options.keywords),
          tone: options.tone,
          language: options.lang,
        });

        spinner.succeed('Landing page generated!');
        saveResults(result);
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  content
    .command('institutional')
    .description('Generate institutional/about page content')
    .requiredOption('--about <about>', 'About the company')
    .requiredOption('--services <services>', 'Services offered (comma-separated)')
    .option('--tone <tone>', 'Writing tone', 'professional')
    .option('--lang <language>', 'Content language', 'pt-BR')
    .action(async (options) => {
      const spinner = ora('Generating institutional page...').start();
      try {
        const agent = new ContentAgent();
        const result = await agent.run({
          type: 'institutional',
          about: options.about,
          services: options.services.split(',').map((s) => s.trim()),
          tone: options.tone,
          language: options.lang,
        });

        spinner.succeed('Institutional page generated!');
        saveResults(result);
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  content
    .command('meta-tags')
    .description('Generate optimized meta tags for a URL')
    .requiredOption('--url <url>', 'Page URL to analyze')
    .option('--lang <language>', 'Content language', 'pt-BR')
    .action(async (options) => {
      const spinner = ora('Generating meta tags...').start();
      try {
        const agent = new ContentAgent();
        const result = await agent.run({
          type: 'meta-tags',
          url: options.url,
          language: options.lang,
        });

        spinner.succeed('Meta tags generated!');
        saveResults(result);
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  content
    .command('schema')
    .description('Generate JSON-LD schema markup')
    .requiredOption('--url <url>', 'Page URL')
    .requiredOption('--type <type>', 'Schema type (Organization, Article, FAQ, Product, LocalBusiness, WebSite, BreadcrumbList)')
    .option('--lang <language>', 'Content language', 'pt-BR')
    .action(async (options) => {
      const spinner = ora('Generating schema markup...').start();
      try {
        const agent = new ContentAgent();
        const result = await agent.run({
          type: 'schema',
          url: options.url,
          schemaType: options.type,
          language: options.lang,
        });

        spinner.succeed('Schema markup generated!');
        saveResults(result);
      } catch (err) {
        spinner.fail(`Error: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  content
    .command('interactive')
    .description('Interactive content generation wizard')
    .action(async () => {
      try {
        const prompts = require('../prompts/content-prompts');
        await prompts.run();
      } catch (err) {
        console.error(colors.red(`Error: ${err.message}`));
        logger.error(err);
        process.exitCode = 1;
      }
    });

  return content;
}

function saveResults(result) {
  const mdContent = formatContentOutput(result);
  const jsonContent = jsonFormatter.formatContentOutput(result);

  const mdFile = saveOutput(mdContent, generateFilename(result.type, 'md'), 'content');
  const jsonFile = saveOutput(jsonContent, generateFilename(result.type, 'json'), 'content');

  console.log(colors.green(`\nFiles saved:`));
  console.log(`  Markdown: ${mdFile}`);
  console.log(`  JSON:     ${jsonFile}`);
  console.log('');
  console.log(colors.cyan('--- Content Preview ---'));
  console.log(result.content.slice(0, 500) + '...');
}

module.exports = createContentCommand;
