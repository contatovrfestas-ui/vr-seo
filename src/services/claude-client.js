'use strict';

const Anthropic = require('@anthropic-ai/sdk');
const configManager = require('./config-manager');
const logger = require('./logger');

class ClaudeClient {
  constructor() {
    this._client = null;
  }

  _getClient() {
    if (!this._client) {
      const apiKey = configManager.get('ANTHROPIC_API_KEY');
      if (!apiKey) {
        throw new Error(
          'ANTHROPIC_API_KEY not set. Run: vr-seo config set ANTHROPIC_API_KEY sk-ant-...'
        );
      }
      this._client = new Anthropic({ apiKey });
    }
    return this._client;
  }

  async chat(systemPrompt, userMessage, options = {}) {
    const client = this._getClient();
    const model = options.model || configManager.get('anthropic.model');
    const maxTokens = options.maxTokens || configManager.get('anthropic.maxTokens');

    logger.debug(`Claude request: model=${model}, maxTokens=${maxTokens}`);

    const messages = Array.isArray(userMessage)
      ? userMessage
      : [{ role: 'user', content: userMessage }];

    const response = await client.messages.create({
      model,
      max_tokens: maxTokens,
      system: systemPrompt,
      messages,
    });

    const text = response.content
      .filter((block) => block.type === 'text')
      .map((block) => block.text)
      .join('\n');

    logger.debug(`Claude response: ${text.length} chars, stop=${response.stop_reason}`);

    return {
      text,
      usage: response.usage,
      stopReason: response.stop_reason,
    };
  }

  async generateContent(template, variables) {
    const prompt = Object.entries(variables).reduce(
      (tpl, [key, val]) => tpl.replace(new RegExp(`{{${key}}}`, 'g'), val),
      template
    );
    return this.chat(
      'You are an expert SEO content strategist and writer. Produce high-quality, optimized content.',
      prompt
    );
  }

  async analyze(systemPrompt, data) {
    return this.chat(systemPrompt, typeof data === 'string' ? data : JSON.stringify(data, null, 2));
  }
}

module.exports = new ClaudeClient();
