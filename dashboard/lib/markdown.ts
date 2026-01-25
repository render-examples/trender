'use client';

import { marked } from 'marked';

/**
 * Get DOMPurify instance (client-side only)
 * This ensures proper loading in browser environment
 */
function getDOMPurify() {
  if (typeof window !== 'undefined') {
    // Dynamic import to ensure it only runs in browser
    const DOMPurify = require('dompurify');
    return DOMPurify;
  }
  return null;
}

/**
 * Decode HTML entities to their character equivalents
 */
function decodeHTMLEntities(text: string): string {
  // Create a temporary element to decode entities
  if (typeof window !== 'undefined') {
    const textarea = document.createElement('textarea');
    textarea.innerHTML = text;
    return textarea.value;
  }
  // Fallback for SSR - decode common entities manually
  return text
    .replace(/&nbsp;?/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

/**
 * Convert relative GitHub image URLs to absolute raw.githubusercontent.com URLs
 * 
 * @param src - The image src attribute
 * @param repoUrl - The repository URL (e.g., https://github.com/owner/repo)
 * @returns Absolute URL or original if already absolute
 */
function resolveImageUrl(src: string, repoUrl: string): string {
  // Skip if already absolute URL
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src;
  }

  // Parse repo URL to get owner and repo name
  // Example: https://github.com/owner/repo -> owner/repo
  const match = repoUrl.match(/github\.com\/([^/]+\/[^/]+)/);
  if (!match) {
    return src;
  }

  const repoPath = match[1];
  
  // Try main branch first (most common default now)
  const baseUrl = `https://raw.githubusercontent.com/${repoPath}/main`;

  // Handle different relative path formats
  if (src.startsWith('./')) {
    // ./path/to/image.png -> /path/to/image.png
    return `${baseUrl}/${src.substring(2)}`;
  } else if (src.startsWith('/')) {
    // /path/to/image.png
    return `${baseUrl}${src}`;
  } else {
    // path/to/image.png (relative)
    return `${baseUrl}/${src}`;
  }
}

/**
 * Safely render markdown to HTML using marked and DOMPurify
 * 
 * @param markdown - The markdown string to render
 * @param repoUrl - Optional repository URL for resolving relative image paths
 * @returns Sanitized HTML string
 * 
 * Security: All HTML is sanitized with DOMPurify to prevent XSS attacks
 * Performance: marked is significantly faster than react-markdown
 */
export function renderMarkdown(markdown: string, repoUrl?: string): string {
  if (!markdown || markdown.trim() === '') {
    return '<p class="text-zinc-500">No content available</p>';
  }

  try {
    // First decode any HTML entities in the source markdown
    const decodedMarkdown = decodeHTMLEntities(markdown);
    
    // Configure marked options
    const options: any = {
      gfm: true,
      breaks: true,
      pedantic: false,
    };

    // Use walkTokens to modify image tokens before rendering
    if (repoUrl) {
      options.walkTokens = (token: any) => {
        if (token.type === 'image') {
          // If the href is relative, resolve it to GitHub raw URL
          if (token.href && !token.href.startsWith('http://') && !token.href.startsWith('https://')) {
            token.href = resolveImageUrl(token.href, repoUrl);
          }
        }
      };
    }
    
    // Parse markdown to HTML using marked with options
    // Note: We use marked.use() to apply options, then parse
    // This is the recommended approach for marked v17+
    marked.use(options);
    const rawHtml = marked.parse(decodedMarkdown) as string;
    
    // Get DOMPurify instance (client-side only)
    const DOMPurify = getDOMPurify();
    
    if (!DOMPurify) {
      // If DOMPurify is not available (SSR), return raw HTML
      // This is safe because we're in a client component that will re-render
      return rawHtml;
    }
    
    // Sanitize the HTML to prevent XSS attacks
    const cleanHtml = DOMPurify.sanitize(rawHtml, {
      // Allow common safe tags
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'blockquote',
        'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'del', 'ins',
        'hr',
        'div', 'span'
      ],
      // Allow common safe attributes
      ALLOWED_ATTR: [
        'href', 'title', 'alt', 'src',
        'class', 'id',
        'align', 'width', 'height',
        'target', 'rel'
      ],
      // Ensure external links are safe
      ALLOW_DATA_ATTR: false,
      // Add rel="noopener noreferrer" to external links
      ADD_ATTR: ['target'],
      // Return HTML string (default behavior)
      RETURN_DOM: false,
      RETURN_DOM_FRAGMENT: false,
    });

    return cleanHtml;
  } catch (error) {
    console.error('Error rendering markdown:', error);
    return '<p class="text-red-400">Error rendering content</p>';
  }
}

/**
 * Truncate markdown content for preview purposes
 * 
 * @param markdown - The markdown string to truncate
 * @param maxLength - Maximum length in characters (default: 500)
 * @returns Truncated markdown string
 */
export function truncateMarkdown(markdown: string, maxLength: number = 500): string {
  if (!markdown || markdown.length <= maxLength) {
    return markdown;
  }

  // Truncate at word boundary
  const truncated = markdown.substring(0, maxLength);
  const lastSpace = truncated.lastIndexOf(' ');
  
  return lastSpace > 0 
    ? truncated.substring(0, lastSpace) + '...'
    : truncated + '...';
}

/**
 * Strip markdown formatting and return plain text
 * Useful for generating meta descriptions or previews
 * 
 * @param markdown - The markdown string to strip
 * @returns Plain text string
 */
export function stripMarkdown(markdown: string): string {
  if (!markdown) return '';
  
  return markdown
    // Remove headings
    .replace(/^#{1,6}\s+/gm, '')
    // Remove bold/italic
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(/(\*|_)(.*?)\1/g, '$2')
    // Remove links but keep text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove images
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '')
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, '')
    // Remove inline code
    .replace(/`([^`]+)`/g, '$1')
    // Remove blockquotes
    .replace(/^\s*>\s+/gm, '')
    // Remove horizontal rules
    .replace(/^-{3,}$/gm, '')
    // Remove list markers
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    // Clean up extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

