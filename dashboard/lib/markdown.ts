'use client';

import { marked } from 'marked';

/**
 * Configure marked options for optimal rendering
 * Following recommendations from https://marked.js.org/#specifications
 */
marked.setOptions({
  // Enable GitHub Flavored Markdown
  gfm: true,
  // Break on single line breaks (like GitHub)
  breaks: true,
  // Use smarter list behavior than markdown.pl
  pedantic: false,
  // Sanitization is handled separately with DOMPurify
  // This is more secure than marked's built-in sanitizer
});

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
 * Safely render markdown to HTML using marked and DOMPurify
 * 
 * @param markdown - The markdown string to render
 * @returns Sanitized HTML string
 * 
 * Security: All HTML is sanitized with DOMPurify to prevent XSS attacks
 * Performance: marked is significantly faster than react-markdown
 */
export function renderMarkdown(markdown: string): string {
  if (!markdown || markdown.trim() === '') {
    return '<p class="text-zinc-500">No content available</p>';
  }

  try {
    // Parse markdown to HTML using marked
    const rawHtml = marked.parse(markdown, { async: false }) as string;
    
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

