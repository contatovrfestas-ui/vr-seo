'use strict';

const { google } = require('googleapis');
const { getAuthenticatedClient } = require('./auth');
const logger = require('../../services/logger');

function getClient() {
  const auth = getAuthenticatedClient();
  return google.analyticsdata({ version: 'v1beta', auth });
}

async function runReport(propertyId, options = {}) {
  const client = getClient();

  const endDate = options.endDate || 'today';
  const startDate = options.startDate || '28daysAgo';

  const request = {
    property: `properties/${propertyId}`,
    requestBody: {
      dateRanges: [{ startDate, endDate }],
      dimensions: options.dimensions || [{ name: 'pagePath' }],
      metrics: options.metrics || [
        { name: 'screenPageViews' },
        { name: 'sessions' },
        { name: 'bounceRate' },
        { name: 'averageSessionDuration' },
      ],
      limit: options.limit || 50,
      orderBys: options.orderBys || [
        { metric: { metricName: 'screenPageViews' }, desc: true },
      ],
    },
  };

  logger.debug(`Analytics report: property=${propertyId} ${startDate} → ${endDate}`);

  const response = await client.properties.runReport(request);

  const headers = {
    dimensions: (response.data.dimensionHeaders || []).map((h) => h.name),
    metrics: (response.data.metricHeaders || []).map((h) => h.name),
  };

  const rows = (response.data.rows || []).map((row) => {
    const obj = {};
    (row.dimensionValues || []).forEach((v, i) => {
      obj[headers.dimensions[i]] = v.value;
    });
    (row.metricValues || []).forEach((v, i) => {
      obj[headers.metrics[i]] = parseFloat(v.value);
    });
    return obj;
  });

  return {
    rows,
    rowCount: response.data.rowCount || 0,
    totals: response.data.totals,
  };
}

async function getTopPages(propertyId, limit = 20) {
  return runReport(propertyId, {
    dimensions: [{ name: 'pagePath' }],
    metrics: [
      { name: 'screenPageViews' },
      { name: 'sessions' },
      { name: 'bounceRate' },
    ],
    limit,
  });
}

async function getTrafficSources(propertyId, limit = 20) {
  return runReport(propertyId, {
    dimensions: [{ name: 'sessionSource' }, { name: 'sessionMedium' }],
    metrics: [
      { name: 'sessions' },
      { name: 'screenPageViews' },
    ],
    limit,
  });
}

async function getOrganicKeywords(propertyId, limit = 20) {
  return runReport(propertyId, {
    dimensions: [{ name: 'sessionSource' }, { name: 'landingPage' }],
    metrics: [
      { name: 'sessions' },
      { name: 'screenPageViews' },
      { name: 'bounceRate' },
    ],
    limit,
    dimensionFilter: {
      filter: {
        fieldName: 'sessionMedium',
        stringFilter: { value: 'organic' },
      },
    },
  });
}

module.exports = {
  runReport,
  getTopPages,
  getTrafficSources,
  getOrganicKeywords,
};
