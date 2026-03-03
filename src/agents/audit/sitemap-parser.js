'use strict';

const xml2js = require('xml2js');
const { fetchUrl } = require('../../utils/http');
const logger = require('../../services/logger');

async function parse(sitemapUrl) {
  logger.info(`Parsing sitemap: ${sitemapUrl}`);
  const issues = [];

  try {
    const response = await fetchUrl(sitemapUrl);

    if (response.status !== 200) {
      issues.push({
        title: 'Sitemap not accessible',
        severity: 'critical',
        description: `Sitemap returned status ${response.status}`,
      });
      return { urls: [], issues };
    }

    const parser = new xml2js.Parser({ explicitArray: false });
    const result = await parser.parseStringPromise(response.data);

    let urls = [];

    // Handle sitemap index
    if (result.sitemapindex) {
      const sitemaps = Array.isArray(result.sitemapindex.sitemap)
        ? result.sitemapindex.sitemap
        : [result.sitemapindex.sitemap];

      logger.info(`Sitemap index found with ${sitemaps.length} sitemaps`);

      for (const sm of sitemaps) {
        const subResult = await parse(sm.loc);
        urls = urls.concat(subResult.urls);
        issues.push(...subResult.issues);
      }
    }
    // Handle regular sitemap
    else if (result.urlset) {
      const entries = Array.isArray(result.urlset.url)
        ? result.urlset.url
        : result.urlset.url
          ? [result.urlset.url]
          : [];

      urls = entries.map((entry) => ({
        loc: entry.loc,
        lastmod: entry.lastmod || null,
        changefreq: entry.changefreq || null,
        priority: entry.priority || null,
      }));
    } else {
      issues.push({
        title: 'Invalid sitemap format',
        severity: 'critical',
        description: 'Could not parse sitemap XML. Not a valid sitemap or sitemap index.',
      });
    }

    // Validate URLs
    if (urls.length === 0) {
      issues.push({
        title: 'Empty sitemap',
        severity: 'warning',
        description: 'Sitemap contains no URLs.',
      });
    }

    logger.info(`Sitemap parsed: ${urls.length} URLs`);
    return { urls, issues };
  } catch (err) {
    logger.error(`Sitemap parse error: ${err.message}`);
    issues.push({
      title: 'Sitemap parse error',
      severity: 'critical',
      description: err.message,
    });
    return { urls: [], issues };
  }
}

async function findSitemap(baseUrl) {
  const candidates = [
    new URL('/sitemap.xml', baseUrl).href,
    new URL('/sitemap_index.xml', baseUrl).href,
    new URL('/sitemap/', baseUrl).href,
  ];

  for (const url of candidates) {
    try {
      const response = await fetchUrl(url, { timeout: 5000 });
      if (response.status === 200 && response.data.includes('<urlset') || response.data.includes('<sitemapindex')) {
        return url;
      }
    } catch {
      // continue
    }
  }

  return null;
}

module.exports = { parse, findSitemap };
