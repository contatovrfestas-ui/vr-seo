'use strict';

const logger = require('../../services/logger');

function analyze(pages) {
  const issues = [];

  for (const page of pages) {
    if (!page.html || page.status >= 400) continue;

    const html = page.html;
    const url = page.url;

    // Check page size
    const sizeKb = Buffer.byteLength(html, 'utf-8') / 1024;
    if (sizeKb > 500) {
      issues.push({
        title: 'Large HTML page',
        severity: 'warning',
        page: url,
        description: `Page size is ${sizeKb.toFixed(0)}KB (recommended < 500KB)`,
        recommendation: 'Reduce HTML size by removing unnecessary code, comments, or inline styles.',
      });
    }

    // Check for render-blocking resources (basic check)
    const cssInHead = (html.match(/<link[^>]*rel="stylesheet"[^>]*>/gi) || []).length;
    if (cssInHead > 5) {
      issues.push({
        title: 'Too many CSS files in head',
        severity: 'warning',
        page: url,
        description: `${cssInHead} CSS files found in head. Consider combining or deferring.`,
        recommendation: 'Combine CSS files or use critical CSS to reduce render-blocking resources.',
      });
    }

    // Check for inline styles
    const inlineStyles = (html.match(/style="[^"]*"/gi) || []).length;
    if (inlineStyles > 20) {
      issues.push({
        title: 'Excessive inline styles',
        severity: 'info',
        page: url,
        description: `${inlineStyles} inline style attributes found.`,
        recommendation: 'Move inline styles to external CSS for better maintainability and caching.',
      });
    }

    // Check for scripts without async/defer
    const blockingScripts = (html.match(/<script[^>]*src="[^"]*"[^>]*>/gi) || [])
      .filter((s) => !s.includes('async') && !s.includes('defer')).length;
    if (blockingScripts > 3) {
      issues.push({
        title: 'Render-blocking scripts',
        severity: 'warning',
        page: url,
        description: `${blockingScripts} scripts without async/defer found.`,
        recommendation: 'Add async or defer to non-critical scripts.',
      });
    }

    // Check for HTTP resources on HTTPS pages
    if (url.startsWith('https://')) {
      const mixedContent = (html.match(/(?:src|href)="http:\/\//gi) || []).length;
      if (mixedContent > 0) {
        issues.push({
          title: 'Mixed content detected',
          severity: 'critical',
          page: url,
          description: `${mixedContent} HTTP resources on HTTPS page.`,
          recommendation: 'Update all resource URLs to use HTTPS.',
        });
      }
    }

    // Check for compression hint (no actual header check since we have HTML only)
    if (page.headers && !page.headers['content-encoding']) {
      issues.push({
        title: 'No compression detected',
        severity: 'warning',
        page: url,
        description: 'Response does not appear to be compressed (gzip/brotli).',
        recommendation: 'Enable gzip or brotli compression on your server.',
      });
    }
  }

  logger.debug(`Performance analysis: ${issues.length} issues`);
  return { issues };
}

module.exports = { analyze };
