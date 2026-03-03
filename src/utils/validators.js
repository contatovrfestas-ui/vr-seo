'use strict';

function isValidUrl(str) {
  try {
    const url = new URL(str);
    return ['http:', 'https:'].includes(url.protocol);
  } catch {
    return false;
  }
}

function isValidKeywords(str) {
  if (!str || typeof str !== 'string') return false;
  const keywords = str.split(',').map((k) => k.trim()).filter(Boolean);
  return keywords.length > 0;
}

function parseKeywords(str) {
  if (!str) return [];
  return str.split(',').map((k) => k.trim()).filter(Boolean);
}

function isValidSchemaType(type) {
  const valid = ['Organization', 'Article', 'FAQ', 'Product', 'LocalBusiness', 'WebSite', 'BreadcrumbList'];
  return valid.includes(type);
}

function isValidTone(tone) {
  const valid = ['professional', 'casual', 'technical', 'friendly', 'persuasive'];
  return valid.includes(tone);
}

function isValidLanguage(lang) {
  return /^[a-z]{2}(-[A-Z]{2})?$/.test(lang);
}

module.exports = {
  isValidUrl,
  isValidKeywords,
  parseKeywords,
  isValidSchemaType,
  isValidTone,
  isValidLanguage,
};
