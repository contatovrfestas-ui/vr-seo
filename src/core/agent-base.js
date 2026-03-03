'use strict';

const { EventEmitter } = require('events');
const logger = require('../services/logger');

class AgentBase extends EventEmitter {
  constructor(name) {
    super();
    this.name = name;
    this.startTime = null;
    this.endTime = null;
  }

  async run(params) {
    this.startTime = Date.now();
    this.emit('start', { agent: this.name, params });
    logger.info(`[${this.name}] Starting...`);

    try {
      this.validate(params);
      const result = await this.execute(params);
      this.endTime = Date.now();

      const duration = this.endTime - this.startTime;
      logger.info(`[${this.name}] Completed in ${duration}ms`);
      this.emit('complete', { agent: this.name, result, duration });

      return result;
    } catch (error) {
      this.endTime = Date.now();
      logger.error(`[${this.name}] Error: ${error.message}`);
      this.emit('error', { agent: this.name, error });
      throw error;
    }
  }

  validate(_params) {
    // Override in subclass
  }

  async execute(_params) {
    throw new Error(`${this.name}: execute() must be implemented`);
  }

  getCapabilities() {
    return {
      name: this.name,
      capabilities: [],
    };
  }

  getDuration() {
    if (!this.startTime || !this.endTime) return null;
    return this.endTime - this.startTime;
  }
}

module.exports = AgentBase;
