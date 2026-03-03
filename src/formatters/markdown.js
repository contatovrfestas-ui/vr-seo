'use strict';

function formatAuditReport(data) {
  const lines = [];
  lines.push(`# SEO Audit Report`);
  lines.push(`**URL:** ${data.url}`);
  lines.push(`**Date:** ${new Date().toISOString().slice(0, 10)}`);
  lines.push('');

  if (data.summary) {
    lines.push('## Summary');
    lines.push(data.summary);
    lines.push('');
  }

  if (data.score !== undefined) {
    lines.push(`**Overall Score:** ${data.score}/100`);
    lines.push('');
  }

  if (data.issues && data.issues.length > 0) {
    lines.push('## Issues Found');
    lines.push('');
    for (const issue of data.issues) {
      const icon = issue.severity === 'critical' ? '🔴' : issue.severity === 'warning' ? '🟡' : '🟢';
      lines.push(`### ${icon} ${issue.title}`);
      lines.push(`**Severity:** ${issue.severity}`);
      if (issue.description) lines.push(issue.description);
      if (issue.recommendation) lines.push(`**Recommendation:** ${issue.recommendation}`);
      lines.push('');
    }
  }

  if (data.cwv) {
    lines.push('## Core Web Vitals');
    lines.push(`- **LCP:** ${data.cwv.lcp || 'N/A'}`);
    lines.push(`- **FID:** ${data.cwv.fid || 'N/A'}`);
    lines.push(`- **CLS:** ${data.cwv.cls || 'N/A'}`);
    lines.push('');
  }

  if (data.recommendations) {
    lines.push('## Recommendations');
    lines.push(data.recommendations);
    lines.push('');
  }

  return lines.join('\n');
}

function formatContentOutput(data) {
  const lines = [];
  lines.push(`# ${data.title || 'Generated Content'}`);
  lines.push(`**Type:** ${data.type}`);
  lines.push(`**Keywords:** ${(data.keywords || []).join(', ')}`);
  lines.push(`**Generated:** ${new Date().toISOString().slice(0, 10)}`);
  lines.push('');
  lines.push('---');
  lines.push('');
  lines.push(data.content);
  return lines.join('\n');
}

module.exports = { formatAuditReport, formatContentOutput };
