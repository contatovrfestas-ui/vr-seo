'use strict';

module.exports = {
  anthropic: {
    model: 'claude-sonnet-4-20250514',
    maxTokens: 4096,
  },
  google: {
    redirectUri: 'http://localhost:3456/callback',
    scopes: [
      'https://www.googleapis.com/auth/webmasters.readonly',
      'https://www.googleapis.com/auth/analytics.readonly',
    ],
    tokenPath: null, // set at runtime to ~/.vr-seo/google-tokens.json
    callbackPort: 3456,
  },
  crawler: {
    maxDepth: 2,
    maxPages: 50,
    timeout: 10000,
    userAgent: 'VR-SEO-Bot/1.0',
    concurrency: 5,
  },
  content: {
    defaultLanguage: 'pt-BR',
    defaultTone: 'professional',
  },
  output: {
    dir: './output',
    formats: ['markdown', 'json'],
  },
  log: {
    level: 'info',
  },
};
