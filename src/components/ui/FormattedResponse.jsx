import React from 'react';
import { Box, Typography, useTheme } from '@mui/material';
import { buildApiUrl } from '@/lib/api';

const FormattedResponse = ({ content, textColor }) => {
  const theme = useTheme();
  const effectiveTextColor = textColor || theme.palette.text.primary;

  // Check if content is HTML (contains HTML tags)
  const isHTML = (text) => {
    if (!text) return false;
    // Check for common HTML tags
    return /<\/?[a-z][\s\S]*>/i.test(text);
  };

  // Convert markdown tables to HTML
  const convertMarkdownTablesToHTML = (text) => {
    if (!text) return text;
    
    // Match markdown tables: header row | separator row | data rows
    const tableRegex = /(\|.+\|\s*\n\|[-\s|:]+\|\s*\n(?:\|.+\|\s*\n?)+)/g;
    
    return text.replace(tableRegex, (match) => {
      const lines = match.trim().split('\n')
        .map(line => line.trim())
        .filter(line => line && line.length > 0);
      
      if (lines.length < 2) return match; // Need at least header and separator
      
      // Parse header row
      const headerLine = lines[0].replace(/^\||\|$/g, '').trim();
      const headerRow = headerLine
        .split('|')
        .map(cell => cell.trim())
        .filter(cell => cell.length > 0);
      
      if (headerRow.length === 0) return match;
      
      // Identify separator row
      const separatorRow = lines[1] || '';
      const isSeparatorRow = /^[\|\s\-:]+$/.test(separatorRow.trim());
      let dataStartIndex = isSeparatorRow ? 2 : 1;
      
      // Parse data rows
      const dataRows = lines.slice(dataStartIndex)
        .filter(row => {
          const trimmed = row.trim();
          if (!trimmed || !trimmed.includes('|')) return false;
          if (/^[\|\s\-:]+$/.test(trimmed)) return false;
          const dashCount = (trimmed.match(/-/g) || []).length;
          const totalLength = trimmed.length;
          const isMostlyDashes = totalLength > 50 && dashCount / totalLength > 0.7;
          return !isMostlyDashes;
        })
        .map(row => {
          const cleanRow = row.replace(/^\||\|$/g, '').trim();
          const cells = cleanRow.split('|').map(cell => cell.trim());
          while (cells.length < headerRow.length) {
            cells.push('');
          }
          return cells.slice(0, headerRow.length);
        })
        .filter(row => row.some(cell => cell && cell.trim().length > 0));
      
      // Convert to HTML table
      let htmlTable = '<table><thead><tr>';
      headerRow.forEach(header => {
        htmlTable += `<th>${header}</th>`;
      });
      htmlTable += '</tr></thead><tbody>';
      
      dataRows.forEach(row => {
        htmlTable += '<tr>';
        row.forEach(cell => {
          htmlTable += `<td>${cell || '&nbsp;'}</td>`;
        });
        htmlTable += '</tr>';
      });
      
      htmlTable += '</tbody></table>';
      return htmlTable;
    });
  };

  // Convert numbered paragraphs to HTML ordered lists
  const convertNumberedParagraphsToLists = (html) => {
    if (!html) return html;
    
    // First, extract numbered items from paragraph tags and convert them to plain lines
    // This helps with detection later
    html = html.replace(/<p>(\d+)\.\s+(.+?)<\/p>/g, (match, num, content) => {
      return `${num}. ${content}`;
    });
    
    // Process line by line to handle numbered items that appear on separate lines
    const lines = html.split('\n');
    const processedLines = [];
    let inNumberedList = false;
    let listItems = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      
      // Check if line starts with a numbered item (e.g., "1. ", "2. ", etc.)
      // This handles both plain text and HTML content
      const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
      
      if (numberedMatch && !trimmed.includes('<ol') && !trimmed.includes('</ol') && !trimmed.includes('<li')) {
        // Start a new list if not already in one
        if (!inNumberedList) {
          inNumberedList = true;
          listItems = [];
        }
        // Extract the content after the number
        const content = numberedMatch[2];
        // Clean up any HTML tags but preserve content (like <strong>, <span>, etc.)
        const cleanContent = content.trim();
        listItems.push(cleanContent);
      } else {
        // If we were in a numbered list, close it
        if (inNumberedList && listItems.length > 0) {
          const listHTML = '<ol>' + listItems.map(item => `<li>${item}</li>`).join('\n') + '</ol>';
          processedLines.push(listHTML);
          inNumberedList = false;
          listItems = [];
        }
        // Add the current line
        processedLines.push(line);
      }
    }
    
    // Close any remaining list
    if (inNumberedList && listItems.length > 0) {
      const listHTML = '<ol>' + listItems.map(item => `<li>${item}</li>`).join('\n') + '</ol>';
      processedLines.push(listHTML);
    }
    
    let result = processedLines.join('\n');
    
    // Also handle cases where numbered items appear in the same paragraph (multiple items in one <p> tag)
    result = result.replace(/<p>((?:\d+\.\s+[^<]+(?:\s+\d+\.\s+[^<]+){1,}))<\/p>/g, (match, content) => {
      // Skip if this is already inside a list
      if (match.includes('<ol') || match.includes('</ol')) {
        return match;
      }
      // Split by number pattern (look for "number. " pattern)
      const items = content.split(/(?=\d+\.\s+)/).filter(item => item.trim());
      if (items.length >= 2) {
        // Convert to ordered list
        const listItems = items.map(item => {
          const cleaned = item.replace(/^\d+\.\s+/, '').trim();
          return `<li>${cleaned}</li>`;
        }).join('\n');
        return `<ol>${listItems}</ol>`;
      }
      return match;
    });
    
    return result;
  };

  // Basic HTML sanitization - remove script tags and dangerous attributes
  const sanitizeHTML = (html) => {
    if (!html) return '';
    
    // Remove script tags and their content
    html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    
    // Remove event handlers (onclick, onerror, etc.)
    html = html.replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '');
    
    // Remove javascript: protocol
    html = html.replace(/javascript:/gi, '');
    
    // Remove iframe tags
    html = html.replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '');
    
    return html;
  };

  // Extract and preserve code blocks before processing
  // Also strips HTML code blocks (```html ... ```) and extracts the HTML directly
  const extractCodeBlocks = (text) => {
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
    const codeBlocks = [];
    let codeBlockIndex = 0;
    
    const processedText = text.replace(codeBlockRegex, (match, lang, code) => {
      const langLower = (lang || 'text').toLowerCase();
      const cleanCode = code.trim();
      
      // If it's an HTML code block, extract the HTML content directly (don't treat as code block)
      if (langLower === 'html' && /<[a-z][\s\S]*>/i.test(cleanCode)) {
        // Return the HTML content directly, removing the code block wrapper
        return cleanCode;
      }
      
      // For other code blocks, preserve them
      const placeholder = `__CODE_BLOCK_${codeBlockIndex}__`;
      codeBlocks.push({ placeholder, lang: langLower, code: cleanCode });
      codeBlockIndex++;
      return placeholder;
    });
    
    return { processedText, codeBlocks };
  };

  const renderCodeBlock = (code, lang = 'text') => {
    // Escape HTML in code
    const escapedCode = code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');

    return (
      <Box
        sx={{
          my: 2,
          borderRadius: 1,
          overflow: 'hidden',
          border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
          backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.02)'
        }}
      >
        {lang !== 'text' && (
          <Box
            sx={{
              px: 2,
              py: 0.5,
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              color: theme.palette.text.secondary,
              backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
              borderBottom: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`
            }}
          >
            {lang}
          </Box>
        )}
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 2,
            fontSize: '0.875rem',
            fontFamily: 'Monaco, Consolas, "Courier New", monospace',
            lineHeight: 1.6,
            overflowX: 'auto',
            color: effectiveTextColor,
            backgroundColor: 'transparent'
          }}
        >
          <code dangerouslySetInnerHTML={{ __html: escapedCode }} />
        </Box>
      </Box>
    );
  };

  // Convert markdown headings (standalone **Heading** on its own line) to HTML headings
  const convertMarkdownHeadings = (html) => {
    if (!html) return html;
    
    const lines = html.split('\n');
    const processedLines = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      
      // Check if line is a standalone bold heading (e.g., "**Regulatory Requirements**")
      // This should be on its own line with no other content
      const headingMatch = trimmed.match(/^\*\*([^*]+?)\*\*$/);
      
      if (headingMatch) {
        // Convert to h2 heading
        processedLines.push(`<h2>${headingMatch[1]}</h2>`);
      } else {
        processedLines.push(line);
      }
    }
    
    return processedLines.join('\n');
  };

  // Convert markdown bold/italic within HTML content
  const convertMarkdownInHTML = (html) => {
    if (!html) return html;
    
    // Convert markdown bold (**text**) to <strong>text</strong>
    // But skip if it's already a heading or inside HTML tags
    html = html.replace(/\*\*([^*]+?)\*\*/g, (match, content) => {
      // If this is already inside a heading tag, don't convert
      if (match.includes('<h2>') || match.includes('</h2>') || match.includes('<h3>') || match.includes('</h3>')) {
        return match;
      }
      return `<strong>${content}</strong>`;
    });
    
    // Convert markdown italic (*text*) to <em>text</em>
    // But only if it's not already part of **text** (bold) - check for single asterisks not preceded/followed by asterisks
    // Also skip if it's a bullet point (starts with * and space)
    html = html.replace(/(?<!\*)\*([^*\n]+?)\*(?!\*)/g, (match, content) => {
      // Skip if this looks like a bullet point (starts with * and space at line start)
      if (match.match(/^\*\s/)) {
        return match;
      }
      return `<em>${content}</em>`;
    });
    
    return html;
  };

  const renderHTMLContent = (htmlContent) => {
    // Extract code blocks first
    const { processedText, codeBlocks } = extractCodeBlocks(htmlContent);
    
    // Convert markdown headings first (standalone **Heading** to <h2>)
    let textWithHeadings = convertMarkdownHeadings(processedText);
    
    // Convert markdown bold/italic within HTML content (but preserve headings)
    let textWithMarkdown = convertMarkdownInHTML(textWithHeadings);
    
    // Convert markdown tables to HTML if present
    let textWithTables = convertMarkdownTablesToHTML(textWithMarkdown);
    
    // Convert numbered paragraphs to HTML lists (fallback for improperly formatted lists)
    let textWithLists = convertNumberedParagraphsToLists(textWithTables);
    
    // Sanitize HTML
    let sanitizedHTML = sanitizeHTML(textWithLists);
    
    // Replace code block placeholders with rendered components
    const parts = sanitizedHTML.split(/(__CODE_BLOCK_\d+__)/);
    const elements = [];
    
    parts.forEach((part, index) => {
      const codeBlockMatch = part.match(/__CODE_BLOCK_(\d+)__/);
      if (codeBlockMatch) {
        const blockIndex = parseInt(codeBlockMatch[1]);
        const block = codeBlocks[blockIndex];
        if (block) {
          elements.push(
            <Box key={`code-${index}`}>
              {renderCodeBlock(block.code, block.lang)}
            </Box>
          );
        }
      } else if (part.trim()) {
        // Render HTML content
        elements.push(
          <Box
            key={`html-${index}`}
            sx={{
              '& h2': {
                fontFamily: 'Montserrat, sans-serif',
                fontWeight: 600,
                fontSize: '1.5rem',
                color: effectiveTextColor,
                marginTop: 3,
                marginBottom: 2,
                lineHeight: 1.3
              },
              '& h3': {
                fontFamily: 'Montserrat, sans-serif',
                fontWeight: 600,
                fontSize: '1.25rem',
                color: effectiveTextColor,
                marginTop: 2,
                marginBottom: 1.5,
                lineHeight: 1.3
              },
              '& h4': {
                fontFamily: 'Montserrat, sans-serif',
                fontWeight: 600,
                fontSize: '1.1rem',
                color: effectiveTextColor,
                marginTop: 1.5,
                marginBottom: 1,
                lineHeight: 1.3
              },
              '& p': {
                fontFamily: 'DM Sans, sans-serif',
                fontSize: '0.95rem',
                lineHeight: 1.6,
                color: effectiveTextColor,
                marginBottom: 1.5
              },
              '& ul, & ol': {
                fontFamily: 'DM Sans, sans-serif',
                fontSize: '0.95rem',
                lineHeight: 1.6,
                color: effectiveTextColor,
                marginBottom: 1.5,
                paddingLeft: 3
              },
              '& li': {
                marginBottom: 0.5,
                '& p': {
                  marginBottom: 0.5
                }
              },
              '& table': {
                width: '100%',
                borderCollapse: 'collapse',
                marginTop: 2,
                marginBottom: 2,
                borderRadius: 2,
                overflow: 'hidden',
                border: `2px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)'}`,
                boxShadow: theme.palette.mode === 'dark' 
                  ? '0 4px 6px rgba(0,0,0,0.3)' 
                  : '0 2px 4px rgba(0,0,0,0.1)'
              },
              '& thead': {
                backgroundColor: theme.palette.mode === 'dark' 
                  ? 'rgba(255,255,255,0.05)' 
                  : 'rgba(0,0,0,0.02)'
              },
              '& th': {
                fontFamily: 'DM Sans, sans-serif',
                fontWeight: 600,
                fontSize: '0.875rem',
                color: effectiveTextColor,
                padding: '12px 16px',
                textAlign: 'left',
                border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
                borderBottom: `2px solid ${theme.palette.divider}`
              },
              '& tbody tr': {
                '&:nth-of-type(odd)': {
                  backgroundColor: theme.palette.mode === 'dark' 
                    ? 'rgba(255,255,255,0.02)' 
                    : 'rgba(0,0,0,0.01)'
                },
                '&:hover': {
                  backgroundColor: theme.palette.mode === 'dark' 
                    ? 'rgba(255,255,255,0.05)' 
                    : 'rgba(0,0,0,0.03)'
                }
              },
              '& td': {
                fontFamily: 'DM Sans, sans-serif',
                fontSize: '0.875rem',
                color: effectiveTextColor,
                padding: '12px 16px',
                border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
                borderBottom: `1px solid ${theme.palette.divider}`,
                wordBreak: 'break-word'
              },
              '& strong': {
                fontWeight: 600,
                color: effectiveTextColor
              },
              '& em': {
                fontStyle: 'italic',
                color: textColor ? effectiveTextColor : theme.palette.text.secondary
              },
              '& a': {
                color: theme.palette.primary.main,
                textDecoration: 'none',
                borderBottom: `1px solid ${theme.palette.primary.main}`,
                paddingBottom: 1,
                '&:hover': {
                  opacity: 0.8
                }
              },
              '& span[style*="color:#008000"], & span[style*="color: #008000"]': {
                backgroundColor: 'rgba(0, 128, 0, 0.1)',
                padding: '2px 4px',
                borderRadius: '3px',
                fontWeight: 500,
                color: '#008000 !important'
              },
              '& code': {
                fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                fontSize: '0.875rem',
                backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.05)',
                padding: '2px 6px',
                borderRadius: '4px',
                border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`
              }
            }}
            dangerouslySetInnerHTML={{ __html: part }}
          />
        );
      }
    });
    
    return elements;
  };

  // Convert markdown to HTML for rendering
  const convertMarkdownToHTML = (text) => {
    if (!text) return '';
    
    let html = text;
    
    // Convert markdown tables first (before other processing)
    html = convertMarkdownTablesToHTML(html);
    
    // Split by lines to process line-by-line
    const lines = html.split('\n');
    const processedLines = [];
    let inUnorderedList = false;
    let inOrderedList = false;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      
      // Skip empty lines
      if (!trimmed) {
        if (inUnorderedList) {
          processedLines.push('</ul>');
          inUnorderedList = false;
        }
        if (inOrderedList) {
          processedLines.push('</ol>');
          inOrderedList = false;
        }
        processedLines.push('');
        continue;
      }
      
      // Skip if already HTML
      if (trimmed.startsWith('<')) {
        if (inUnorderedList) {
          processedLines.push('</ul>');
          inUnorderedList = false;
        }
        if (inOrderedList) {
          processedLines.push('</ol>');
          inOrderedList = false;
        }
        processedLines.push(line);
        continue;
      }
      
      // Convert markdown headings
      if (trimmed.match(/^###\s+/)) {
        if (inUnorderedList) {
          processedLines.push('</ul>');
          inUnorderedList = false;
        }
        if (inOrderedList) {
          processedLines.push('</ol>');
          inOrderedList = false;
        }
        processedLines.push(`<h3>${trimmed.replace(/^###\s+/, '')}</h3>`);
        continue;
      }
      if (trimmed.match(/^##\s+/)) {
        if (inUnorderedList) {
          processedLines.push('</ul>');
          inUnorderedList = false;
        }
        if (inOrderedList) {
          processedLines.push('</ol>');
          inOrderedList = false;
        }
        processedLines.push(`<h2>${trimmed.replace(/^##\s+/, '')}</h2>`);
        continue;
      }
      if (trimmed.match(/^#\s+/)) {
        if (inUnorderedList) {
          processedLines.push('</ul>');
          inUnorderedList = false;
        }
        if (inOrderedList) {
          processedLines.push('</ol>');
          inOrderedList = false;
        }
        processedLines.push(`<h2>${trimmed.replace(/^#\s+/, '')}</h2>`);
        continue;
      }
      
      // Convert numbered list items (e.g., "1. ", "2. ", etc.)
      if (trimmed.match(/^\d+\.\s+/)) {
        // Close unordered list if open
        if (inUnorderedList) {
          processedLines.push('</ul>');
          inUnorderedList = false;
        }
        // Start ordered list if not already open
        if (!inOrderedList) {
          processedLines.push('<ol>');
          inOrderedList = true;
        }
        const listContent = trimmed.replace(/^\d+\.\s+/, '');
        // Convert inline markdown in list items
        const processedContent = listContent
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.+?)\*/g, '<em>$1</em>');
        processedLines.push(`<li>${processedContent}</li>`);
        continue;
      }
      
      // Convert markdown unordered list items (bullet points)
      if (trimmed.match(/^[\*\-]\s+/)) {
        // Close ordered list if open
        if (inOrderedList) {
          processedLines.push('</ol>');
          inOrderedList = false;
        }
        // Start unordered list if not already open
        if (!inUnorderedList) {
          processedLines.push('<ul>');
          inUnorderedList = true;
        }
        const listContent = trimmed.replace(/^[\*\-]\s+/, '');
        // Convert inline markdown in list items
        const processedContent = listContent
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.+?)\*/g, '<em>$1</em>');
        processedLines.push(`<li>${processedContent}</li>`);
        continue;
      }
      
      // Regular paragraph - close any open lists
      if (inUnorderedList) {
        processedLines.push('</ul>');
        inUnorderedList = false;
      }
      if (inOrderedList) {
        processedLines.push('</ol>');
        inOrderedList = false;
      }
      
      // Convert inline markdown
      let processedLine = trimmed
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>');
      
      processedLines.push(`<p>${processedLine}</p>`);
    }
    
    // Close any open lists
    if (inUnorderedList) {
      processedLines.push('</ul>');
    }
    if (inOrderedList) {
      processedLines.push('</ol>');
    }
    
    return processedLines.join('\n');
  };

  if (!content) return null;

  // Check if content is HTML or contains markdown tables
  const hasMarkdownTable = /(\|.+\|\s*\n\|[-\s|:]+\|\s*\n(?:\|.+\|\s*\n?)+)/.test(content);
  
  if (isHTML(content) || hasMarkdownTable) {
    // Convert markdown to HTML if needed
    const htmlContent = isHTML(content) ? content : convertMarkdownToHTML(content);
    return (
      <Box sx={{ width: '100%' }}>
        {renderHTMLContent(htmlContent)}
      </Box>
    );
  }

  // Fallback to plain text
  return (
    <Box sx={{ width: '100%' }}>
      <Typography
        variant="body1"
        sx={{
          fontFamily: 'DM Sans, sans-serif',
          lineHeight: 1.6,
          fontSize: '0.95rem',
          whiteSpace: 'pre-wrap',
          color: effectiveTextColor
        }}
      >
        {content}
      </Typography>
    </Box>
  );
};

export default FormattedResponse;
