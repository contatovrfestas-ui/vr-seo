'use strict';

const AgentBase = require('../../core/agent-base');
const blogGenerator = require('./blog-generator');
const landingPageGenerator = require('./landing-page-generator');
const institutionalGenerator = require('./institutional-generator');
const metaTagsGenerator = require('./meta-tags-generator');
const schemaGenerator = require('./schema-generator');

const GENERATORS = {
  blog: blogGenerator,
  'landing-page': landingPageGenerator,
  institutional: institutionalGenerator,
  'meta-tags': metaTagsGenerator,
  schema: schemaGenerator,
};

class ContentAgent extends AgentBase {
  constructor() {
    super('ContentAgent');
  }

  validate(params) {
    if (!params.type) {
      throw new Error('Content type is required (blog, landing-page, institutional, meta-tags, schema)');
    }
    if (!GENERATORS[params.type]) {
      throw new Error(`Unknown content type: ${params.type}. Available: ${Object.keys(GENERATORS).join(', ')}`);
    }
  }

  async execute(params) {
    const generator = GENERATORS[params.type];
    return generator.generate(params);
  }

  getCapabilities() {
    return {
      name: this.name,
      capabilities: Object.keys(GENERATORS).map((type) => ({
        type,
        description: `Generate ${type} content`,
      })),
    };
  }
}

module.exports = ContentAgent;
