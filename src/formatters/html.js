'use strict';

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatAuditReport(data) {
  const issuesHtml = (data.issues || [])
    .map((issue) => {
      const color = issue.severity === 'critical' ? '#e74c3c' : issue.severity === 'warning' ? '#f39c12' : '#27ae60';
      return `<div class="issue" style="border-left: 4px solid ${color}; padding: 10px; margin: 10px 0;">
        <h3>${escapeHtml(issue.title)}</h3>
        <span style="color: ${color}; font-weight: bold;">${escapeHtml(issue.severity)}</span>
        ${issue.description ? `<p>${escapeHtml(issue.description)}</p>` : ''}
        ${issue.recommendation ? `<p><strong>Recommendation:</strong> ${escapeHtml(issue.recommendation)}</p>` : ''}
      </div>`;
    })
    .join('\n');

  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>SEO Audit Report - ${escapeHtml(data.url)}</title>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
    h1 { color: #2c3e50; }
    .score { font-size: 2em; font-weight: bold; color: #2c3e50; }
  </style>
</head>
<body>
  <h1>SEO Audit Report</h1>
  <p><strong>URL:</strong> ${escapeHtml(data.url)}</p>
  <p><strong>Date:</strong> ${new Date().toISOString().slice(0, 10)}</p>
  ${data.score !== undefined ? `<p class="score">Score: ${data.score}/100</p>` : ''}
  ${data.summary ? `<h2>Summary</h2><p>${escapeHtml(data.summary)}</p>` : ''}
  <h2>Issues</h2>
  ${issuesHtml || '<p>No issues found.</p>'}
  ${data.recommendations ? `<h2>Recommendations</h2><p>${escapeHtml(data.recommendations)}</p>` : ''}
</body>
</html>`;
}

function formatContentOutput(data) {
  return `<!DOCTYPE html>
<html lang="${data.language || 'pt-BR'}">
<head>
  <meta charset="UTF-8">
  <title>${escapeHtml(data.title || 'Generated Content')}</title>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
  </style>
</head>
<body>
  <h1>${escapeHtml(data.title || 'Generated Content')}</h1>
  <p><em>Type: ${escapeHtml(data.type)} | Keywords: ${escapeHtml((data.keywords || []).join(', '))}</em></p>
  <hr>
  <div>${data.content}</div>
</body>
</html>`;
}

module.exports = { formatAuditReport, formatContentOutput };
