'use strict';

const cheerio = require('cheerio');
const { fetchUrl } = require('../../utils/http');
const { resolveUrl, isSameOrigin } = require('../../utils/http');
const logger = require('../../services/logger');
const configManager = require('../../services/config-manager');

class Crawler {
  constructor(options = {}) {
    this.maxDepth = options.maxDepth || configManager.get('crawler.maxDepth');
    this.maxPages = options.maxPages || configManager.get('crawler.maxPages');
    this.timeout = options.timeout || configManager.get('crawler.timeout');
    this.userAgent = options.userAgent || configManager.get('crawler.userAgent');
    this.visited = new Map();
    this.queue = [];
    this.results = [];
  }

  async crawl(startUrl) {
    logger.info(`Starting crawl: ${startUrl} (depth=${this.maxDepth}, maxPages=${this.maxPages})`);

    this.queue.push({ url: startUrl, depth: 0 });

    while (this.queue.length > 0 && this.results.length < this.maxPages) {
      const { url, depth } = this.queue.shift();

      if (this.visited.has(url) || depth > this.maxDepth) continue;
      this.visited.set(url, true);

      try {
        const response = await fetchUrl(url, {
          timeout: this.timeout,
          userAgent: this.userAgent,
        });

        const pageData = {
          url,
          status: response.status,
          depth,
          headers: response.headers,
          links: [],
          html: typeof response.data === 'string' ? response.data : '',
        };

        if (typeof response.data === 'string' && response.status < 400) {
          const $ = cheerio.load(response.data);

          // Extract links
          $('a[href]').each((_, el) => {
            const href = $(el).attr('href');
            const resolved = resolveUrl(url, href);
            if (resolved && isSameOrigin(startUrl, resolved)) {
              pageData.links.push(resolved);
              if (depth + 1 <= this.maxDepth && !this.visited.has(resolved)) {
                this.queue.push({ url: resolved, depth: depth + 1 });
              }
            }
          });
        }

        this.results.push(pageData);
        logger.debug(`Crawled ${url} (${response.status}) - ${pageData.links.length} links`);
      } catch (err) {
        logger.warn(`Failed to crawl ${url}: ${err.message}`);
        this.results.push({
          url,
          status: 0,
          depth,
          error: err.message,
          links: [],
          html: '',
        });
      }
    }

    logger.info(`Crawl complete: ${this.results.length} pages`);
    return this.results;
  }

  getVisitedUrls() {
    return [...this.visited.keys()];
  }
}

module.exports = Crawler;
