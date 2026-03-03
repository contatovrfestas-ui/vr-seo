'use strict';

const path = require('path');
const claudeClient = require('../../services/claude-client');
const { readFile } = require('../../utils/file-io');
const { fetchUrl } = require('../../utils/http');
const cheerio = require('cheerio');
const logger = require('../../services/logger');

const TEMPLATE_PATH = path.join(__dirname, 'templates', 'schema.md');

async function generate({ url, schemaType, language }) {
  logger.info(`Generating ${schemaType} schema for: ${url}`);

  // Fetch page content
  const response = await fetchUrl(url);
  const $ = cheerio.load(response.data);

  const pageContent = [
    `Title: ${$('title').text()}`,
    `H1: ${$('h1').first().text()}`,
    `Description: ${$('meta[name="description"]').attr('content') || 'N/A'}`,
    `Body text: ${$('body').text().replace(/\s+/g, ' ').trim().slice(0, 2000)}`,
  ].join('\n');

  const template = readFile(TEMPLATE_PATH);

  const result = await claudeClient.generateContent(template, {
    url,
    schemaType,
    content: pageContent,
    language: language || 'pt-BR',
  });

  return {
    type: 'schema',
    schemaType,
    url,
    content: result.text,
    language,
    usage: result.usage,
  };
}

module.exports = { generate };
