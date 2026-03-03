'use strict';

const winston = require('winston');
const configManager = require('./config-manager');

const logger = winston.createLogger({
  level: configManager.get('log.level') || 'info',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.printf(({ timestamp, level, message, stack }) => {
      const msg = `${timestamp} [${level.toUpperCase()}] ${message}`;
      return stack ? `${msg}\n${stack}` : msg;
    })
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(({ timestamp, level, message, stack }) => {
          const msg = `${timestamp} [${level}] ${message}`;
          return stack ? `${msg}\n${stack}` : msg;
        })
      ),
    }),
  ],
});

module.exports = logger;
