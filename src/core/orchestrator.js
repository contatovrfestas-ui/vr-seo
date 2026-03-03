'use strict';

const { EventEmitter } = require('events');
const AuditAgent = require('../agents/audit');
const ContentAgent = require('../agents/content');
const claudeClient = require('../services/claude-client');
const { saveOutput, generateFilename } = require('../utils/file-io');
const { formatAuditReport } = require('../formatters/markdown');
const { formatContentOutput } = require('../formatters/markdown');
const jsonFormatter = require('../formatters/json');
const logger = require('../services/logger');

class Orchestrator extends EventEmitter {
  constructor() {
    super();
    this.auditAgent = new AuditAgent();
    this.contentAgent = new ContentAgent();
  }

  async run(params) {
    const { url, full, depth, maxPages, language } = params;
    const outputFiles = [];

    // Phase 1: Audit
    this.emit('phase', { phase: '1/4', description: 'Running SEO audit...' });

    const auditResult = await this.auditAgent.run({
      url,
      depth: depth || 2,
      maxPages: maxPages || 50,
    });

    // Save audit report
    const auditMd = saveOutput(
      formatAuditReport(auditResult),
      generateFilename('pipeline-audit', 'md'),
      'pipeline'
    );
    const auditJson = saveOutput(
      jsonFormatter.formatAuditReport(auditResult),
      generateFilename('pipeline-audit', 'json'),
      'pipeline'
    );
    outputFiles.push(auditMd, auditJson);

    if (!full) {
      return { audit: auditResult, content: [], outputFiles };
    }

    // Phase 2: Analyze with AI
    this.emit('phase', { phase: '2/4', description: 'Analyzing audit results with AI...' });

    const analysisResponse = await claudeClient.analyze(
      `You are an expert SEO strategist. Based on the audit results below, create a content plan to improve the site's SEO.
       Return a JSON array of content items to create.
       Each item should have: type (blog|landing-page), topic, keywords (array), priority (high|medium|low).
       Focus on the most impactful improvements. Return 3-5 items maximum.
       Language: ${language || 'pt-BR'}`,
      {
        url,
        score: auditResult.score,
        issues: auditResult.issues.slice(0, 20),
        recommendations: auditResult.recommendations,
      }
    );

    let contentPlan;
    try {
      const jsonMatch = analysisResponse.text.match(/\[[\s\S]*\]/);
      contentPlan = jsonMatch ? JSON.parse(jsonMatch[0]) : [];
    } catch {
      logger.warn('Could not parse content plan. Using default suggestions.');
      contentPlan = [
        {
          type: 'blog',
          topic: `SEO improvements for ${url}`,
          keywords: ['seo', 'optimization'],
          priority: 'high',
        },
      ];
    }

    // Save content plan
    const planFile = saveOutput(
      JSON.stringify(contentPlan, null, 2),
      generateFilename('content-plan', 'json'),
      'pipeline'
    );
    outputFiles.push(planFile);

    // Phase 3: Generate content
    this.emit('phase', { phase: '3/4', description: `Generating ${contentPlan.length} content pieces...` });

    const contentResults = [];
    for (let i = 0; i < contentPlan.length; i++) {
      const item = contentPlan[i];
      this.emit('progress', { message: `Generating content ${i + 1}/${contentPlan.length}: ${item.topic}` });

      try {
        const result = await this.contentAgent.run({
          type: item.type || 'blog',
          topic: item.topic,
          keywords: item.keywords || [],
          tone: 'professional',
          language: language || 'pt-BR',
        });

        contentResults.push(result);

        const contentMd = saveOutput(
          formatContentOutput(result),
          generateFilename(`pipeline-${result.type}`, 'md'),
          'pipeline'
        );
        outputFiles.push(contentMd);
      } catch (err) {
        logger.warn(`Failed to generate content for "${item.topic}": ${err.message}`);
      }
    }

    // Phase 4: Summary
    this.emit('phase', { phase: '4/4', description: 'Creating summary report...' });

    const summary = {
      url,
      auditScore: auditResult.score,
      issuesFound: auditResult.issues.length,
      contentGenerated: contentResults.length,
      contentPlan,
      timestamp: new Date().toISOString(),
    };

    const summaryFile = saveOutput(
      JSON.stringify(summary, null, 2),
      generateFilename('pipeline-summary', 'json'),
      'pipeline'
    );
    outputFiles.push(summaryFile);

    return {
      audit: auditResult,
      contentPlan,
      content: contentResults,
      summary,
      outputFiles,
    };
  }
}

module.exports = Orchestrator;
