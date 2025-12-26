/**
 * Proxy Helper Module
 * 
 * Shields generated apps from reverse proxy complexity.
 * Apps can use standard absolute paths - this module handles the rest.
 * 
 * Usage:
 *   Backend: const { redirect, sendFile } = require('./utils/proxy-helper');
 *   Frontend: Include via <script src="/utils/proxy-helper.js"></script>
 */

const path = require('path');

/**
 * Smart redirect that works with or without reverse proxy.
 * Always use absolute paths in your code: redirect(res, '/dashboard')
 * 
 * @param {Object} res - Express response object
 * @param {string} targetPath - Target path (e.g., '/dashboard', '/login?error=invalid')
 */
function redirect(res, targetPath) {
  // Ensure path starts with /
  const absolutePath = targetPath.startsWith('/') ? targetPath : `/${targetPath}`;
  res.redirect(absolutePath);
}

/**
 * Smart sendFile that calculates correct path depth automatically.
 * Use relative paths from project root: sendFile(res, 'public/login.html')
 * 
 * @param {Object} res - Express response object
 * @param {string} filePath - File path relative to project root (e.g., 'public/login.html')
 */
function sendFile(res, filePath) {
  // Calculate how many directories up from current file to project root
  const currentDir = __dirname;
  const projectRoot = process.cwd();
  
  // Count directory depth
  const currentParts = currentDir.split(path.sep).filter(p => p);
  const rootParts = projectRoot.split(path.sep).filter(p => p);
  const depth = currentParts.length - rootParts.length;
  
  // Build path with correct number of '..'
  const upDirs = depth > 0 ? Array(depth).fill('..') : [];
  const fullPath = path.join(__dirname, ...upDirs, filePath);
  
  res.sendFile(fullPath);
}

/**
 * Frontend helper script (inject into HTML pages)
 * Provides ProxyHelper.fetch() and ProxyHelper.url() for client-side code
 */
const clientScript = `
<script>
/**
 * ProxyHelper - Client-side utilities for proxy-safe requests
 * 
 * Usage:
 *   ProxyHelper.fetch('/api/user')  // Works with or without proxy
 *   ProxyHelper.url('/dashboard')   // Returns proxy-safe URL
 */
const ProxyHelper = {
  /**
   * Proxy-safe fetch wrapper
   * Use absolute paths: ProxyHelper.fetch('/api/user')
   */
  fetch(url, options) {
    // Convert absolute to relative for proxy compatibility
    const relativeUrl = url.startsWith('/') ? url.slice(1) : url;
    return fetch(relativeUrl, options);
  },
  
  /**
   * Convert absolute path to proxy-safe relative path
   * Use for dynamic URL construction
   */
  url(path) {
    return path.startsWith('/') ? path.slice(1) : path;
  }
};
</script>
`;

module.exports = {
  redirect,
  sendFile,
  clientScript
};
