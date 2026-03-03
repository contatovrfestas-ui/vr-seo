'use strict';

const { Select, Input } = require('enquirer');
const colors = require('ansi-colors');
const ora = require('ora');
const ContentAgent = require('../../agents/content');
const { saveOutput, generateFilename } = require('../../utils/file-io');
const { formatContentOutput } = require('../../formatters/markdown');
const jsonFormatter = require('../../formatters/json');

async function run() {
  console.log(colors.bold.cyan('\n  Content Generation Wizard\n'));

  const typePrompt = new Select({
    name: 'type',
    message: 'What type of content do you want to generate?',
    choices: [
      { name: 'blog', message: 'Blog Post' },
      { name: 'landing-page', message: 'Landing Page' },
      { name: 'institutional', message: 'Institutional / About Page' },
      { name: 'meta-tags', message: 'Meta Tags' },
      { name: 'schema', message: 'Schema Markup (JSON-LD)' },
    ],
  });

  const type = await typePrompt.run();
  let params = { type };

  if (type === 'blog' || type === 'landing-page') {
    const topic = await new Input({
      message: 'Topic:',
      validate: (v) => (v.length > 0 ? true : 'Topic is required'),
    }).run();

    const keywords = await new Input({
      message: 'Keywords (comma-separated):',
      validate: (v) => (v.length > 0 ? true : 'At least one keyword is required'),
    }).run();

    const tone = await new Select({
      message: 'Tone:',
      choices: ['professional', 'casual', 'technical', 'friendly', 'persuasive'],
    }).run();

    const lang = await new Input({
      message: 'Language:',
      initial: 'pt-BR',
    }).run();

    params = { ...params, topic, keywords: keywords.split(',').map((k) => k.trim()), tone, language: lang };
  } else if (type === 'institutional') {
    const about = await new Input({
      message: 'About the company:',
      validate: (v) => (v.length > 0 ? true : 'Required'),
    }).run();

    const services = await new Input({
      message: 'Services (comma-separated):',
      validate: (v) => (v.length > 0 ? true : 'Required'),
    }).run();

    const tone = await new Select({
      message: 'Tone:',
      choices: ['professional', 'casual', 'technical', 'friendly', 'persuasive'],
    }).run();

    const lang = await new Input({
      message: 'Language:',
      initial: 'pt-BR',
    }).run();

    params = { ...params, about, services: services.split(',').map((s) => s.trim()), tone, language: lang };
  } else if (type === 'meta-tags') {
    const url = await new Input({
      message: 'Page URL:',
      validate: (v) => (v.startsWith('http') ? true : 'Enter a valid URL'),
    }).run();

    params = { ...params, url, language: 'pt-BR' };
  } else if (type === 'schema') {
    const url = await new Input({
      message: 'Page URL:',
      validate: (v) => (v.startsWith('http') ? true : 'Enter a valid URL'),
    }).run();

    const schemaType = await new Select({
      message: 'Schema type:',
      choices: ['Organization', 'Article', 'FAQ', 'Product', 'LocalBusiness', 'WebSite', 'BreadcrumbList'],
    }).run();

    params = { ...params, url, schemaType, language: 'pt-BR' };
  }

  const spinner = ora(`Generating ${type} content...`).start();

  try {
    const agent = new ContentAgent();
    const result = await agent.run(params);

    spinner.succeed(`${type} content generated!`);

    const mdContent = formatContentOutput(result);
    const jsonContent = jsonFormatter.formatContentOutput(result);
    const mdFile = saveOutput(mdContent, generateFilename(result.type, 'md'), 'content');
    const jsonFile = saveOutput(jsonContent, generateFilename(result.type, 'json'), 'content');

    console.log(colors.green('\nFiles saved:'));
    console.log(`  Markdown: ${mdFile}`);
    console.log(`  JSON:     ${jsonFile}`);
    console.log('');
    console.log(colors.cyan('--- Content Preview ---'));
    console.log(result.content.slice(0, 500) + '...');
  } catch (err) {
    spinner.fail(`Error: ${err.message}`);
    throw err;
  }
}

module.exports = { run };
