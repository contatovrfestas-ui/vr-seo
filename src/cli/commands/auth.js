'use strict';

const { Command } = require('commander');
const colors = require('ansi-colors');
const ora = require('ora');
const logger = require('../../services/logger');

function createAuthCommand() {
  const auth = new Command('auth')
    .description('Manage authentication');

  const google = auth
    .command('google')
    .description('Google API authentication');

  google
    .command('login')
    .description('Authenticate with Google (OAuth2)')
    .action(async () => {
      const spinner = ora('Starting Google authentication...').start();
      try {
        const googleAuth = require('../../integrations/google/auth');
        const url = await googleAuth.getAuthUrl();

        spinner.info('Opening browser for authentication...');
        console.log('');
        console.log(colors.cyan('If the browser does not open, visit this URL:'));
        console.log(colors.underline(url));
        console.log('');

        const tokens = await googleAuth.authenticate();
        spinner.succeed('Google authentication successful!');
        console.log(colors.green('Tokens saved. You can now use Google Search Console and Analytics.'));
      } catch (err) {
        spinner.fail(`Authentication failed: ${err.message}`);
        logger.error(err);
        process.exitCode = 1;
      }
    });

  google
    .command('status')
    .description('Check Google authentication status')
    .action(async () => {
      try {
        const googleAuth = require('../../integrations/google/auth');
        const status = googleAuth.getStatus();

        if (status.authenticated) {
          console.log(colors.green('Google: Authenticated'));
          console.log(colors.gray(`  Token expires: ${status.expiresAt || 'unknown'}`));
        } else {
          console.log(colors.yellow('Google: Not authenticated'));
          console.log(colors.gray('  Run: vr-seo auth google login'));
        }
      } catch (err) {
        console.error(colors.red(`Error: ${err.message}`));
        process.exitCode = 1;
      }
    });

  google
    .command('revoke')
    .description('Revoke Google authentication')
    .action(async () => {
      try {
        const googleAuth = require('../../integrations/google/auth');
        await googleAuth.revoke();
        console.log(colors.green('Google tokens revoked.'));
      } catch (err) {
        console.error(colors.red(`Error: ${err.message}`));
        process.exitCode = 1;
      }
    });

  return auth;
}

module.exports = createAuthCommand;
