'use strict';

const { fetchUrl } = require('../../utils/http');
const logger = require('../../services/logger');

async function analyze(baseUrl) {
  const robotsUrl = new URL('/robots.txt', baseUrl).href;
  const issues = [];

  try {
    const response = await fetchUrl(robotsUrl);

    if (response.status === 404) {
      issues.push({
        title: 'Missing robots.txt',
        severity: 'warning',
        description: 'No robots.txt file found. Consider creating one to control crawler access.',
        recommendation: 'Create a robots.txt file at the root of your domain.',
      });
      return { exists: false, issues, rules: [] };
    }

    const content = response.data;
    const rules = parseRobotsTxt(content);

    // Check for common issues
    if (content.includes('Disallow: /')) {
      const line = content.split('\n').find((l) => l.trim() === 'Disallow: /');
      if (line) {
        issues.push({
          title: 'Entire site blocked by robots.txt',
          severity: 'critical',
          description: 'robots.txt contains "Disallow: /" which blocks all crawlers.',
          recommendation: 'Remove or modify the "Disallow: /" rule unless intentional.',
        });
      }
    }

    // Check for sitemap reference
    const hasSitemap = content.toLowerCase().includes('sitemap:');
    if (!hasSitemap) {
      issues.push({
        title: 'No sitemap reference in robots.txt',
        severity: 'info',
        description: 'robots.txt does not reference a sitemap.',
        recommendation: 'Add "Sitemap: https://yoursite.com/sitemap.xml" to robots.txt.',
      });
    }

    logger.debug(`robots.txt analysis: ${issues.length} issues, ${rules.length} rules`);

    return { exists: true, content, issues, rules, hasSitemap };
  } catch (err) {
    logger.warn(`Failed to fetch robots.txt: ${err.message}`);
    issues.push({
      title: 'Could not fetch robots.txt',
      severity: 'info',
      description: err.message,
    });
    return { exists: false, issues, rules: [] };
  }
}

function parseRobotsTxt(content) {
  const rules = [];
  let currentAgent = '*';

  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;

    const [directive, ...valueParts] = line.split(':');
    const value = valueParts.join(':').trim();

    if (directive.toLowerCase() === 'user-agent') {
      currentAgent = value;
    } else {
      rules.push({ agent: currentAgent, directive: directive.trim(), value });
    }
  }

  return rules;
}

module.exports = { analyze };
