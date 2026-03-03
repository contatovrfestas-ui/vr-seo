'use strict';

const cheerio = require('cheerio');
const logger = require('../../services/logger');

function analyze(html, url) {
  const $ = cheerio.load(html);
  const issues = [];

  // Title tag
  const title = $('title').text().trim();
  if (!title) {
    issues.push({ title: 'Missing title tag', severity: 'critical', page: url });
  } else if (title.length > 60) {
    issues.push({ title: 'Title tag too long', severity: 'warning', page: url, description: `${title.length} chars (max 60)` });
  } else if (title.length < 30) {
    issues.push({ title: 'Title tag too short', severity: 'warning', page: url, description: `${title.length} chars (min 30)` });
  }

  // Meta description
  const metaDesc = $('meta[name="description"]').attr('content') || '';
  if (!metaDesc) {
    issues.push({ title: 'Missing meta description', severity: 'critical', page: url });
  } else if (metaDesc.length > 160) {
    issues.push({ title: 'Meta description too long', severity: 'warning', page: url, description: `${metaDesc.length} chars (max 160)` });
  }

  // H1 tags
  const h1Count = $('h1').length;
  if (h1Count === 0) {
    issues.push({ title: 'Missing H1 tag', severity: 'critical', page: url });
  } else if (h1Count > 1) {
    issues.push({ title: 'Multiple H1 tags', severity: 'warning', page: url, description: `Found ${h1Count} H1 tags` });
  }

  // Heading hierarchy
  const headings = [];
  $('h1, h2, h3, h4, h5, h6').each((_, el) => {
    headings.push(parseInt(el.tagName.replace('h', ''), 10));
  });
  for (let i = 1; i < headings.length; i++) {
    if (headings[i] - headings[i - 1] > 1) {
      issues.push({ title: 'Skipped heading level', severity: 'warning', page: url, description: `H${headings[i - 1]} → H${headings[i]}` });
      break;
    }
  }

  // Images without alt
  const imgsNoAlt = $('img:not([alt]), img[alt=""]').length;
  if (imgsNoAlt > 0) {
    issues.push({ title: 'Images missing alt text', severity: 'warning', page: url, description: `${imgsNoAlt} image(s) without alt text` });
  }

  // Canonical
  const canonical = $('link[rel="canonical"]').attr('href');
  if (!canonical) {
    issues.push({ title: 'Missing canonical tag', severity: 'warning', page: url });
  }

  // Meta viewport
  if (!$('meta[name="viewport"]').length) {
    issues.push({ title: 'Missing viewport meta tag', severity: 'warning', page: url });
  }

  // Open Graph
  if (!$('meta[property="og:title"]').length) {
    issues.push({ title: 'Missing Open Graph tags', severity: 'info', page: url });
  }

  // Language
  const htmlLang = $('html').attr('lang');
  if (!htmlLang) {
    issues.push({ title: 'Missing lang attribute on html', severity: 'warning', page: url });
  }

  const data = {
    title,
    metaDescription: metaDesc,
    h1: $('h1').first().text().trim(),
    headingStructure: headings,
    imageCount: $('img').length,
    imagesWithoutAlt: imgsNoAlt,
    canonical,
    lang: htmlLang,
    links: {
      internal: $('a[href^="/"], a[href^="' + url + '"]').length,
      external: $('a[href^="http"]').length,
    },
    wordCount: $('body').text().replace(/\s+/g, ' ').trim().split(' ').length,
  };

  logger.debug(`HTML analysis for ${url}: ${issues.length} issues`);

  return { issues, data };
}

module.exports = { analyze };
