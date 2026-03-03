'use strict';

function formatAuditReport(data) {
  return JSON.stringify(
    {
      type: 'audit-report',
      url: data.url,
      date: new Date().toISOString(),
      score: data.score,
      summary: data.summary,
      issues: data.issues || [],
      cwv: data.cwv || null,
      recommendations: data.recommendations,
      pages: data.pages || [],
    },
    null,
    2
  );
}

function formatContentOutput(data) {
  return JSON.stringify(
    {
      type: 'content-output',
      contentType: data.type,
      title: data.title,
      keywords: data.keywords || [],
      language: data.language,
      tone: data.tone,
      content: data.content,
      generatedAt: new Date().toISOString(),
    },
    null,
    2
  );
}

module.exports = { formatAuditReport, formatContentOutput };
