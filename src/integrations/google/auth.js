'use strict';

const { google } = require('googleapis');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');
const configManager = require('../../services/config-manager');
const logger = require('../../services/logger');

const TOKEN_FILE = 'google-tokens.json';

function getTokenPath() {
  return path.join(configManager.getConfigDir(), TOKEN_FILE);
}

function createOAuth2Client() {
  const clientId = configManager.get('GOOGLE_CLIENT_ID');
  const clientSecret = configManager.get('GOOGLE_CLIENT_SECRET');
  const redirectUri = configManager.get('google.redirectUri');

  if (!clientId || !clientSecret) {
    throw new Error(
      'Google OAuth2 credentials not set. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.'
    );
  }

  return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
}

function getAuthUrl() {
  const client = createOAuth2Client();
  const scopes = configManager.get('google.scopes');

  return client.generateAuthUrl({
    access_type: 'offline',
    scope: scopes,
    prompt: 'consent',
  });
}

async function authenticate() {
  const client = createOAuth2Client();
  const port = configManager.get('google.callbackPort') || 3456;
  const authUrl = getAuthUrl();

  // Try to open browser
  try {
    const open = require('open');
    await open(authUrl);
  } catch {
    logger.info('Could not open browser automatically.');
  }

  // Start local server to receive callback
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      try {
        const url = new URL(req.url, `http://localhost:${port}`);
        const code = url.searchParams.get('code');

        if (!code) {
          res.writeHead(400);
          res.end('No authorization code received.');
          return;
        }

        const { tokens } = await client.getToken(code);
        client.setCredentials(tokens);

        // Save tokens
        saveTokens(tokens);

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end('<h1>Authentication successful!</h1><p>You can close this window.</p>');

        server.close();
        resolve(tokens);
      } catch (err) {
        res.writeHead(500);
        res.end(`Authentication error: ${err.message}`);
        server.close();
        reject(err);
      }
    });

    server.listen(port, () => {
      logger.info(`OAuth callback server listening on port ${port}`);
    });

    server.on('error', reject);

    // Timeout after 5 minutes
    setTimeout(() => {
      server.close();
      reject(new Error('Authentication timed out (5 minutes)'));
    }, 5 * 60 * 1000);
  });
}

function saveTokens(tokens) {
  const tokenPath = getTokenPath();
  fs.writeFileSync(tokenPath, JSON.stringify(tokens, null, 2));
  logger.info(`Tokens saved to ${tokenPath}`);
}

function loadTokens() {
  const tokenPath = getTokenPath();
  if (!fs.existsSync(tokenPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(tokenPath, 'utf-8'));
  } catch {
    return null;
  }
}

function getAuthenticatedClient() {
  const tokens = loadTokens();
  if (!tokens) {
    throw new Error('Not authenticated. Run: vr-seo auth google login');
  }

  const client = createOAuth2Client();
  client.setCredentials(tokens);

  // Auto-refresh expired tokens
  client.on('tokens', (newTokens) => {
    const merged = { ...tokens, ...newTokens };
    saveTokens(merged);
    logger.debug('Tokens refreshed and saved');
  });

  return client;
}

function getStatus() {
  const tokens = loadTokens();
  if (!tokens) {
    return { authenticated: false };
  }
  return {
    authenticated: true,
    expiresAt: tokens.expiry_date ? new Date(tokens.expiry_date).toISOString() : null,
    hasRefreshToken: !!tokens.refresh_token,
  };
}

async function revoke() {
  const tokens = loadTokens();
  if (!tokens) {
    logger.info('No tokens to revoke.');
    return;
  }

  try {
    const client = createOAuth2Client();
    if (tokens.access_token) {
      await client.revokeToken(tokens.access_token);
    }
  } catch (err) {
    logger.warn(`Token revocation request failed: ${err.message}`);
  }

  const tokenPath = getTokenPath();
  if (fs.existsSync(tokenPath)) {
    fs.unlinkSync(tokenPath);
  }
  logger.info('Tokens revoked and deleted.');
}

module.exports = {
  getAuthUrl,
  authenticate,
  getAuthenticatedClient,
  getStatus,
  revoke,
};
