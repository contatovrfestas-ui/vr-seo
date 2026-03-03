'use strict';

const { google } = require('googleapis');
const { getAuthenticatedClient } = require('./auth');
const logger = require('../../services/logger');

function getClient() {
  const auth = getAuthenticatedClient();
  return google.searchconsole({ version: 'v1', auth });
}

async function listSites() {
  const client = getClient();
  const response = await client.sites.list();
  return response.data.siteEntry || [];
}

async function getSearchAnalytics(siteUrl, options = {}) {
  const client = getClient();

  const endDate = options.endDate || new Date().toISOString().slice(0, 10);
  const startDate =
    options.startDate ||
    new Date(Date.now() - 28 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  const requestBody = {
    startDate,
    endDate,
    dimensions: options.dimensions || ['query'],
    rowLimit: options.rowLimit || 100,
    startRow: options.startRow || 0,
  };

  if (options.dimensionFilterGroups) {
    requestBody.dimensionFilterGroups = options.dimensionFilterGroups;
  }

  logger.debug(`Search Console query: ${siteUrl} ${startDate} → ${endDate}`);

  const response = await client.searchanalytics.query({
    siteUrl,
    requestBody,
  });

  return {
    rows: response.data.rows || [],
    responseAggregationType: response.data.responseAggregationType,
  };
}

async function getTopQueries(siteUrl, limit = 20) {
  const result = await getSearchAnalytics(siteUrl, {
    dimensions: ['query'],
    rowLimit: limit,
  });

  return result.rows.map((row) => ({
    query: row.keys[0],
    clicks: row.clicks,
    impressions: row.impressions,
    ctr: row.ctr,
    position: row.position,
  }));
}

async function getTopPages(siteUrl, limit = 20) {
  const result = await getSearchAnalytics(siteUrl, {
    dimensions: ['page'],
    rowLimit: limit,
  });

  return result.rows.map((row) => ({
    page: row.keys[0],
    clicks: row.clicks,
    impressions: row.impressions,
    ctr: row.ctr,
    position: row.position,
  }));
}

async function getIndexingStatus(siteUrl) {
  const client = getClient();

  try {
    const response = await client.urlInspection.index.inspect({
      requestBody: {
        inspectionUrl: siteUrl,
        siteUrl,
      },
    });
    return response.data;
  } catch (err) {
    logger.warn(`URL inspection failed: ${err.message}`);
    return null;
  }
}

module.exports = {
  listSites,
  getSearchAnalytics,
  getTopQueries,
  getTopPages,
  getIndexingStatus,
};
