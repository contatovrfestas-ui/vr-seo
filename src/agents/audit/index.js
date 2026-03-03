'use strict';

const AgentBase = require('../../core/agent-base');
const Crawler = require('./crawler');
const htmlAnalyzer = require('./html-analyzer');
const robotsAnalyzer = require('./robots-analyzer');
const errorChecker = require('./error-checker');
const sitemapParser = require('./sitemap-parser');
const performanceAnalyzer = require('./performance-analyzer');
const coreWebVitals = require('./core-web-vitals');
const claudeClient = require('../../services/claude-client');
const logger = require('../../services/logger');
const { isValidUrl } = require('../../utils/validators');

class AuditAgent extends AgentBase {
  constructor() {
    super('AuditAgent');
  }

  validate(params) {
    if (!params.url && !params.sitemap) {
      throw new Error('URL or sitemap is required for audit');
    }
    if (params.url && !isValidUrl(params.url)) {
      throw new Error(`Invalid URL: ${params.url}`);
    }
  }

  async execute(params) {
    const allIssues = [];
    let pages = [];
    let cwvData = null;

    // Step 1: Crawl or parse sitemap
    if (params.sitemap) {
      const sitemap = await sitemapParser.parse(params.sitemap);
      allIssues.push(...sitemap.issues);

      // Crawl each URL from sitemap (limited)
      const crawler = new Crawler({ maxDepth: 0, maxPages: params.maxPages });
      for (const entry of sitemap.urls.slice(0, params.maxPages || 50)) {
        const crawled = await crawler.crawl(entry.loc);
        pages.push(...crawled);
      }
    } else if (params.mode === 'cwv') {
      // Only Core Web Vitals
      cwvData = await coreWebVitals.measure(params.url);
      allIssues.push(...cwvData.issues);
    } else if (params.mode === 'links') {
      // Only link checking
      const crawler = new Crawler({ maxDepth: params.depth || 1, maxPages: params.maxPages });
      pages = await crawler.crawl(params.url);
      const linkResult = await errorChecker.checkLinks(pages);
      allIssues.push(...linkResult.issues);
    } else {
      // Full audit
      const crawler = new Crawler({
        maxDepth: params.depth,
        maxPages: params.maxPages,
      });
      pages = await crawler.crawl(params.url);

      // Analyze HTML for each page
      for (const page of pages) {
        if (page.html && page.status < 400) {
          const htmlResult = htmlAnalyzer.analyze(page.html, page.url);
          allIssues.push(...htmlResult.issues);
        }
      }

      // Check robots.txt
      const robotsResult = await robotsAnalyzer.analyze(params.url);
      allIssues.push(...robotsResult.issues);

      // Performance analysis
      const perfResult = performanceAnalyzer.analyze(pages);
      allIssues.push(...perfResult.issues);

      // Check broken links
      const linkResult = await errorChecker.checkLinks(pages);
      allIssues.push(...linkResult.issues);

      // Core Web Vitals (if available)
      cwvData = await coreWebVitals.measure(params.url);
      allIssues.push(...cwvData.issues);

      // Check sitemap
      const sitemapUrl = await sitemapParser.findSitemap(params.url);
      if (!sitemapUrl) {
        allIssues.push({
          title: 'No sitemap found',
          severity: 'warning',
          description: 'Could not find sitemap.xml.',
          recommendation: 'Create a sitemap.xml and submit it to Google Search Console.',
        });
      }
    }

    // Calculate score
    const score = this._calculateScore(allIssues);

    // Generate AI recommendations
    let recommendations = '';
    if (allIssues.length > 0) {
      try {
        const response = await claudeClient.analyze(
          'You are an expert SEO consultant. Analyze the following SEO audit issues and provide prioritized, actionable recommendations. Be specific and practical. Write in the same language the issues are described in.',
          {
            url: params.url || params.sitemap,
            issues: allIssues.slice(0, 30),
            score,
            pagesAnalyzed: pages.length,
          }
        );
        recommendations = response.text;
      } catch (err) {
        logger.warn(`Could not generate AI recommendations: ${err.message}`);
        recommendations = 'AI recommendations unavailable. Review issues manually.';
      }
    }

    return {
      url: params.url || params.sitemap,
      score,
      summary: `Analyzed ${pages.length} pages. Found ${allIssues.length} issues.`,
      issues: allIssues,
      cwv: cwvData?.cwv || null,
      pages: pages.map((p) => ({ url: p.url, status: p.status })),
      recommendations,
    };
  }

  _calculateScore(issues) {
    let score = 100;
    for (const issue of issues) {
      if (issue.severity === 'critical') score -= 10;
      else if (issue.severity === 'warning') score -= 3;
      else if (issue.severity === 'info') score -= 1;
    }
    return Math.max(0, Math.min(100, score));
  }

  getCapabilities() {
    return {
      name: this.name,
      capabilities: [
        { type: 'full-audit', description: 'Complete SEO audit' },
        { type: 'cwv', description: 'Core Web Vitals analysis' },
        { type: 'links', description: 'Broken link check' },
        { type: 'sitemap', description: 'Sitemap audit' },
      ],
    };
  }
}

module.exports = AuditAgent;
