'use strict';

const { fetchUrl } = require('../../utils/http');
const cheerio = require('cheerio');
const { resolveUrl } = require('../../utils/http');
const logger = require('../../services/logger');

async function checkLinks(pages) {
  const issues = [];
  const checkedUrls = new Map();

  for (const page of pages) {
    if (!page.html) continue;

    const $ = cheerio.load(page.html);
    const links = [];

    $('a[href]').each((_, el) => {
      const href = $(el).attr('href');
      const resolved = resolveUrl(page.url, href);
      if (resolved && resolved.startsWith('http')) {
        links.push({ href: resolved, text: $(el).text().trim() });
      }
    });

    for (const link of links) {
      if (checkedUrls.has(link.href)) {
        const cached = checkedUrls.get(link.href);
        if (cached >= 400) {
          issues.push({
            title: `Broken link (${cached})`,
            severity: cached >= 500 ? 'critical' : 'warning',
            page: page.url,
            description: `Link to ${link.href} returns ${cached}`,
            recommendation: 'Fix or remove the broken link.',
          });
        }
        continue;
      }

      try {
        const response = await fetchUrl(link.href, { timeout: 5000 });
        checkedUrls.set(link.href, response.status);

        if (response.status >= 400) {
          issues.push({
            title: `Broken link (${response.status})`,
            severity: response.status >= 500 ? 'critical' : 'warning',
            page: page.url,
            description: `Link to ${link.href} returns ${response.status}`,
            recommendation: 'Fix or remove the broken link.',
          });
        }
      } catch (err) {
        checkedUrls.set(link.href, 0);
        issues.push({
          title: 'Unreachable link',
          severity: 'warning',
          page: page.url,
          description: `Cannot reach ${link.href}: ${err.message}`,
          recommendation: 'Verify the URL is correct and the server is accessible.',
        });
      }
    }
  }

  logger.debug(`Link check: ${checkedUrls.size} URLs checked, ${issues.length} broken`);

  return { issues, totalChecked: checkedUrls.size };
}

module.exports = { checkLinks };
