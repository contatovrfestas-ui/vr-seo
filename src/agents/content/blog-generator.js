'use strict';

const path = require('path');
const claudeClient = require('../../services/claude-client');
const { readFile } = require('../../utils/file-io');
const logger = require('../../services/logger');

const TEMPLATE_PATH = path.join(__dirname, 'templates', 'blog.md');

async function generate({ topic, keywords, tone, language }) {
  logger.info(`Generating blog post: "${topic}"`);

  const template = readFile(TEMPLATE_PATH);

  const result = await claudeClient.generateContent(template, {
    topic,
    keywords: Array.isArray(keywords) ? keywords.join(', ') : keywords,
    tone: tone || 'professional',
    language: language || 'pt-BR',
  });

  const content = result.text;

  // Extract meta title and description from output
  const titleMatch = content.match(/META_TITLE:\s*(.+)/);
  const descMatch = content.match(/META_DESCRIPTION:\s*(.+)/);

  return {
    type: 'blog',
    title: titleMatch ? titleMatch[1].trim() : topic,
    metaDescription: descMatch ? descMatch[1].trim() : '',
    content: content
      .replace(/META_TITLE:\s*.+\n?/, '')
      .replace(/META_DESCRIPTION:\s*.+\n?/, '')
      .trim(),
    keywords: Array.isArray(keywords) ? keywords : keywords.split(',').map((k) => k.trim()),
    topic,
    tone,
    language,
    usage: result.usage,
  };
}

module.exports = { generate };
