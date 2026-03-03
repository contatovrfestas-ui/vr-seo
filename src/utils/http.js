'use strict';

const axios = require('axios');
const logger = require('../services/logger');

async function fetchUrl(url, options = {}) {
  const config = {
    timeout: options.timeout || 10000,
    headers: {
      'User-Agent': options.userAgent || 'VR-SEO-Bot/1.0',
      ...options.headers,
    },
    maxRedirects: options.maxRedirects || 5,
    validateStatus: () => true,
  };

  logger.debug(`HTTP GET ${url}`);
  const response = await axios.get(url, config);

  return {
    status: response.status,
    headers: response.headers,
    data: response.data,
    url: response.request?.res?.responseUrl || url,
    redirected: (response.request?.res?.responseUrl || url) !== url,
  };
}

async function fetchWithRetry(url, options = {}, retries = 3) {
  let lastError;
  for (let i = 0; i < retries; i++) {
    try {
      return await fetchUrl(url, options);
    } catch (err) {
      lastError = err;
      logger.debug(`Retry ${i + 1}/${retries} for ${url}: ${err.message}`);
      if (i < retries - 1) {
        await new Promise((r) => setTimeout(r, 1000 * (i + 1)));
      }
    }
  }
  throw lastError;
}

function resolveUrl(base, relative) {
  try {
    return new URL(relative, base).href;
  } catch {
    return null;
  }
}

function isSameOrigin(url1, url2) {
  try {
    const a = new URL(url1);
    const b = new URL(url2);
    return a.origin === b.origin;
  } catch {
    return false;
  }
}

module.exports = { fetchUrl, fetchWithRetry, resolveUrl, isSameOrigin };
