'use strict';

const path = require('path');
const claudeClient = require('../../services/claude-client');
const { readFile } = require('../../utils/file-io');
const logger = require('../../services/logger');

const TEMPLATE_PATH = path.join(__dirname, 'templates', 'institutional.md');

async function generate({ about, services, tone, language }) {
  logger.info(`Generating institutional page`);

  const template = readFile(TEMPLATE_PATH);

  const result = await claudeClient.generateContent(template, {
    about,
    services: Array.isArray(services) ? services.join(', ') : services,
    tone: tone || 'professional',
    language: language || 'pt-BR',
  });

  const content = result.text;
  const titleMatch = content.match(/META_TITLE:\s*(.+)/);
  const descMatch = content.match(/META_DESCRIPTION:\s*(.+)/);

  return {
    type: 'institutional',
    title: titleMatch ? titleMatch[1].trim() : 'About Us',
    metaDescription: descMatch ? descMatch[1].trim() : '',
    content: content
      .replace(/META_TITLE:\s*.+\n?/, '')
      .replace(/META_DESCRIPTION:\s*.+\n?/, '')
      .trim(),
    about,
    services: Array.isArray(services) ? services : services.split(',').map((s) => s.trim()),
    tone,
    language,
    usage: result.usage,
  };
}

module.exports = { generate };
