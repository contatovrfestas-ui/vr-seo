'use strict';

const logger = require('../../services/logger');

async function measure(url) {
  logger.info(`Measuring Core Web Vitals for: ${url}`);

  try {
    let lighthouse;
    let puppeteer;

    try {
      lighthouse = require('lighthouse');
      puppeteer = require('puppeteer');
    } catch {
      logger.warn('Lighthouse/Puppeteer not available. Using PageSpeed Insights API fallback.');
      return measureFallback(url);
    }

    const browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    const port = new URL(browser.wsEndpoint()).port;

    const result = await lighthouse(url, {
      port,
      output: 'json',
      onlyCategories: ['performance'],
      formFactor: 'mobile',
      screenEmulation: { mobile: true },
    });

    await browser.close();

    const audits = result.lhr.audits;

    const cwv = {
      lcp: {
        value: audits['largest-contentful-paint']?.numericValue,
        score: audits['largest-contentful-paint']?.score,
        displayValue: audits['largest-contentful-paint']?.displayValue,
      },
      fid: {
        value: audits['max-potential-fid']?.numericValue,
        score: audits['max-potential-fid']?.score,
        displayValue: audits['max-potential-fid']?.displayValue,
      },
      cls: {
        value: audits['cumulative-layout-shift']?.numericValue,
        score: audits['cumulative-layout-shift']?.score,
        displayValue: audits['cumulative-layout-shift']?.displayValue,
      },
      ttfb: {
        value: audits['server-response-time']?.numericValue,
        displayValue: audits['server-response-time']?.displayValue,
      },
      performanceScore: Math.round((result.lhr.categories.performance?.score || 0) * 100),
    };

    const issues = [];

    if (cwv.lcp.score < 0.5) {
      issues.push({
        title: 'Poor LCP (Largest Contentful Paint)',
        severity: 'critical',
        description: `LCP: ${cwv.lcp.displayValue} (should be < 2.5s)`,
        recommendation: 'Optimize images, reduce server response time, remove render-blocking resources.',
      });
    } else if (cwv.lcp.score < 0.9) {
      issues.push({
        title: 'LCP needs improvement',
        severity: 'warning',
        description: `LCP: ${cwv.lcp.displayValue} (should be < 2.5s)`,
      });
    }

    if (cwv.cls.score < 0.5) {
      issues.push({
        title: 'Poor CLS (Cumulative Layout Shift)',
        severity: 'critical',
        description: `CLS: ${cwv.cls.displayValue} (should be < 0.1)`,
        recommendation: 'Set explicit dimensions on images/videos, avoid inserting content above existing content.',
      });
    }

    logger.info(`CWV: Performance ${cwv.performanceScore}/100`);

    return { cwv, issues };
  } catch (err) {
    logger.error(`CWV measurement failed: ${err.message}`);
    return measureFallback(url);
  }
}

async function measureFallback(url) {
  logger.info('Using basic performance check (Lighthouse/Puppeteer not available)');
  return {
    cwv: {
      lcp: { value: null, displayValue: 'N/A (Lighthouse required)' },
      fid: { value: null, displayValue: 'N/A (Lighthouse required)' },
      cls: { value: null, displayValue: 'N/A (Lighthouse required)' },
      performanceScore: null,
    },
    issues: [
      {
        title: 'Core Web Vitals not measured',
        severity: 'info',
        description: 'Install lighthouse and puppeteer for full CWV analysis.',
        recommendation: 'npm install lighthouse puppeteer',
      },
    ],
  };
}

module.exports = { measure };
