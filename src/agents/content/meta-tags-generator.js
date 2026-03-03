'use strict';

const path = require('path');
const claudeClient = require('../../services/claude-client');
const { readFile } = require('../../utils/file-io');
const { fetchUrl } = require('../../utils/http');
const cheerio = require('cheerio');
const logger = require('../../services/logger');

const TEMPLATE_PATH = path.join(__dirname, 'templates', 'meta-tags.md');

async function generate({ url, language }) {
  logger.info(`Generating meta tags for: ${url}`);

  // Fetch page content
  const response = await fetchUrl(url);
  const $ = cheerio.load(response.data);

  // Extract text content
  const pageContent = [
    `Title: ${$('title').text()}`,
    `H1: ${$('h1').first().text()}`,
    `Description: ${$('meta[name="description"]').attr('content') || 'N/A'}`,
    `Body text: ${$('body').text().replace(/\s+/g, ' ').trim().slice(0, 2000)}`,
  ].join('\n');

  const template = readFile(TEMPLATE_PATH);

  const result = await claudeClient.generateContent(template, {
    url,
    content: pageContent,
    language: language || 'pt-BR',
  });

  // Try to parse JSON from response
  let metaTags;
  try {
    const jsonMatch = result.text.match(/\{[\s\S]*\}/);
    metaTags = jsonMatch ? JSON.parse(jsonMatch[0]) : { raw: result.text };
  } catch {
    metaTags = { raw: result.text };
  }

  return {
    type: 'meta-tags',
    url,
    metaTags,
    content: result.text,
    language,
    usage: result.usage,
  };
}

module.exports = { generate };
