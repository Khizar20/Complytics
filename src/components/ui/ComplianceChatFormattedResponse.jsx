import React from 'react';
import { Box, Typography, useTheme } from '@mui/material';

const ComplianceChatFormattedResponse = ({ content, textColor }) => {
  const theme = useTheme();
  const effectiveTextColor = textColor || theme.palette.text.primary;
  const isDarkMode = theme.palette.mode === 'dark';

  if (!content) return null;

  // Process markdown and HTML content
  const processContent = (text) => {
    if (!text) return text;

    // Step 1: Convert HTML tables first (protect them before any other processing)
    const htmlTablePlaceholders = [];
    let htmlTableIndex = 0;
    // Match HTML tables (including multiline with whitespace)
    const htmlTableRegex = /<table[\s\S]*?<\/table>/gi;
    text = text.replace(htmlTableRegex, (match) => {
      const placeholder = `__HTML_TABLE_${htmlTableIndex}__`;
      // Clean up whitespace around table tags but preserve table structure
      const cleanedTable = match.replace(/>\s+</g, '><').trim();
      htmlTablePlaceholders[htmlTableIndex] = cleanedTable;
      htmlTableIndex++;
      return placeholder;
    });

    // Step 2: Convert markdown code blocks (protect them)
    const codeBlockPlaceholders = [];
    let codeBlockIndex = 0;
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      const placeholder = `__CODE_BLOCK_${codeBlockIndex}__`;
      codeBlockPlaceholders[codeBlockIndex] = `<pre class="code-block" data-lang="${lang || 'text'}"><code>${code.trim()}</code></pre>`;
      codeBlockIndex++;
      return placeholder;
    });

    // Step 3: Convert markdown tables (protect them)
    const tablePlaceholders = [];
    let tableIndex = 0;
    const tableRegex = /(\|.+\|\s*\n\|[-\s|:]+\|\s*\n(?:\|.+\|\s*\n?)+)/g;
    text = text.replace(tableRegex, (match) => {
      const placeholder = `__TABLE_${tableIndex}__`;
      tablePlaceholders[tableIndex] = convertMarkdownTables(match);
      tableIndex++;
      return placeholder;
    });

    // Step 3: Convert markdown headings to HTML
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    text = text.replace(/^##### (.*$)/gim, '<h5>$1</h5>');
    text = text.replace(/^###### (.*$)/gim, '<h6>$1</h6>');
    text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Step 4: Convert markdown bold (**text**)
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Step 5: Convert markdown italic (*text*)
    text = text.replace(/\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>');

    // Step 6: Convert markdown inline code (`code`)
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Step 7: Convert markdown bullet lists (* or -)
    text = convertMarkdownBulletLists(text);

    // Step 8: Convert markdown numbered lists (1. 2. 3.)
    text = convertMarkdownNumberedLists(text);

    // Step 9: Process line by line to separate block elements from text
    const lines = text.split('\n');
    const blocks = [];
    let currentTextLines = [];
    
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();
      
      // Check if this line is a block element
      const isHeader = /^<h[1-6]>/.test(trimmed);
      const isListTag = /^<(ul|ol|li)>/.test(trimmed) || /<\/(ul|ol|li)>$/.test(trimmed);
      const isHtmlTablePlaceholder = /^__HTML_TABLE_\d+__$/.test(trimmed);
      const isTablePlaceholder = /^__TABLE_\d+__$/.test(trimmed);
      const isCodePlaceholder = /^__CODE_BLOCK_\d+__$/.test(trimmed);
      
      if (isHeader) {
        // Save current text block (trim trailing empty lines)
        if (currentTextLines.length > 0) {
          // Remove trailing empty lines
          while (currentTextLines.length > 0 && currentTextLines[currentTextLines.length - 1].trim() === '') {
            currentTextLines.pop();
          }
          const textContent = currentTextLines.join('\n').trim();
          if (textContent) {
            blocks.push({ type: 'text', content: textContent });
          }
          currentTextLines = [];
        }
        blocks.push({ type: 'header', content: trimmed });
      } else if (isHtmlTablePlaceholder) {
        // Save current text block (trim trailing empty lines)
        if (currentTextLines.length > 0) {
          // Remove trailing empty lines
          while (currentTextLines.length > 0 && currentTextLines[currentTextLines.length - 1].trim() === '') {
            currentTextLines.pop();
          }
          const textContent = currentTextLines.join('\n').trim();
          if (textContent) {
            blocks.push({ type: 'text', content: textContent });
          }
          currentTextLines = [];
        }
        const tableId = parseInt(trimmed.match(/\d+/)[0]);
        blocks.push({ type: 'table', content: htmlTablePlaceholders[tableId] || trimmed });
      } else if (isTablePlaceholder) {
        // Save current text block (trim trailing empty lines)
        if (currentTextLines.length > 0) {
          // Remove trailing empty lines
          while (currentTextLines.length > 0 && currentTextLines[currentTextLines.length - 1].trim() === '') {
            currentTextLines.pop();
          }
          const textContent = currentTextLines.join('\n').trim();
          if (textContent) {
            blocks.push({ type: 'text', content: textContent });
          }
          currentTextLines = [];
        }
        const tableId = parseInt(trimmed.match(/\d+/)[0]);
        blocks.push({ type: 'table', content: tablePlaceholders[tableId] || trimmed });
      } else if (isCodePlaceholder) {
        // Save current text block (trim trailing empty lines)
        if (currentTextLines.length > 0) {
          // Remove trailing empty lines
          while (currentTextLines.length > 0 && currentTextLines[currentTextLines.length - 1].trim() === '') {
            currentTextLines.pop();
          }
          const textContent = currentTextLines.join('\n').trim();
          if (textContent) {
            blocks.push({ type: 'text', content: textContent });
          }
          currentTextLines = [];
        }
        const codeId = parseInt(trimmed.match(/\d+/)[0]);
        blocks.push({ type: 'code', content: codeBlockPlaceholders[codeId] || trimmed });
      } else if (isListTag) {
        // Collect list lines until list ends
        const listLines = [];
        let listDepth = 0;
        
        while (i < lines.length) {
          const currentLine = lines[i];
          const currentTrimmed = currentLine.trim();
          
          if (/^<(ul|ol)>/.test(currentTrimmed)) {
            listDepth++;
            listLines.push(currentTrimmed);
          } else if (/<\/(ul|ol)>$/.test(currentTrimmed)) {
            listDepth--;
            listLines.push(currentTrimmed);
            if (listDepth === 0) {
              i++;
              break;
            }
          } else if (/^<li>/.test(currentTrimmed) || /<\/li>$/.test(currentTrimmed)) {
            listLines.push(currentTrimmed);
          } else if (currentTrimmed === '' && listDepth > 0) {
            // Empty line within list - preserve it
            listLines.push('');
          } else {
            break;
          }
          i++;
        }
        
        // Save current text block
        if (currentTextLines.length > 0) {
          const textContent = currentTextLines.join('\n').trim();
          if (textContent) {
            blocks.push({ type: 'text', content: textContent });
          }
          currentTextLines = [];
        }
        
        blocks.push({ type: 'list', content: listLines.join('\n') });
        continue; // Skip increment since we already incremented in the loop
      } else if (trimmed === '') {
        // Empty line - only add if we have text content (to preserve spacing between paragraphs)
        // Don't add empty lines before/after block elements
        if (currentTextLines.length > 0) {
          currentTextLines.push(line);
        }
        // Otherwise, skip empty lines that appear before block elements
      } else {
        // Regular text line
        currentTextLines.push(line);
      }
      
      i++;
    }
    
    // Add remaining text block
    if (currentTextLines.length > 0) {
      const textContent = currentTextLines.join('\n').trim();
      if (textContent) {
        blocks.push({ type: 'text', content: textContent });
      }
    }

    // Step 10: Process blocks - wrap only text blocks in paragraphs
    const processedBlocks = blocks.map((block) => {
      if (block.type === 'text') {
        // Split text by double newlines for paragraphs
        const paragraphs = block.content.split(/\n\n+/).filter(p => p.trim());
        
        if (paragraphs.length === 0) return '';
        
        // Process each paragraph
        const processedParagraphs = paragraphs.map(para => {
          // Convert single newlines to <br> within paragraphs
          para = para.replace(/\n/g, '<br>');
          return `<p>${para.trim()}</p>`;
        });
        
        return processedParagraphs.join('');
      } else {
        // Headers, lists, tables, code blocks - return as-is
        return block.content;
      }
    });

    return processedBlocks.join('\n');
  };

  // Convert markdown tables to HTML
  const convertMarkdownTables = (text) => {
    const tableRegex = /(\|.+\|\s*\n\|[-\s|:]+\|\s*\n(?:\|.+\|\s*\n?)+)/g;
    
    return text.replace(tableRegex, (match) => {
      const lines = match.trim().split('\n')
        .map(line => line.trim())
        .filter(line => line && line.length > 0);
      
      if (lines.length < 2) return match;
      
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
          return true;
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
      let htmlTable = '<table class="compliance-table"><thead><tr>';
      headerRow.forEach(header => {
        htmlTable += `<th>${processInlineMarkdown(header)}</th>`;
      });
      htmlTable += '</tr></thead><tbody>';
      
      dataRows.forEach(row => {
        htmlTable += '<tr>';
        row.forEach(cell => {
          htmlTable += `<td>${processInlineMarkdown(cell || '&nbsp;')}</td>`;
        });
        htmlTable += '</tr>';
      });
      
      htmlTable += '</tbody></table>';
      return htmlTable;
    });
  };

  // Process inline markdown within table cells
  const processInlineMarkdown = (text) => {
    if (!text) return text;
    // Process bold, italic, and code within cells
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>');
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    return text;
  };

  // Convert markdown bullet lists
  const convertMarkdownBulletLists = (text) => {
    // Handle both * and - as bullet markers
    const lines = text.split('\n');
    const processedLines = [];
    let inList = false;
    let listItems = [];
    let listLevel = 0;

    lines.forEach((line, index) => {
      // Match bullet points with optional indentation
      const bulletMatch = line.match(/^(\s*)([-*])\s+(.+)$/);
      
      if (bulletMatch) {
        const [, indent, marker, content] = bulletMatch;
        const level = Math.floor(indent.length / 2);
        
        // If we're starting a new list or changing levels
        if (!inList || level !== listLevel) {
          // Close previous list if exists
          if (inList && listItems.length > 0) {
            processedLines.push(`<ul>${listItems.join('')}</ul>`);
          }
          
          // Start new list
          listLevel = level;
          listItems = [];
          inList = true;
        }
        
        // Process content for nested formatting
        const processedContent = processInlineMarkdown(content);
        listItems.push(`<li>${processedContent}</li>`);
      } else {
        // Not a bullet point
        if (inList && listItems.length > 0) {
          // Close the list
          processedLines.push(`<ul>${listItems.join('')}</ul>`);
          listItems = [];
          inList = false;
          listLevel = 0;
        }
        processedLines.push(line);
      }
    });

    // Close any remaining list
    if (inList && listItems.length > 0) {
      processedLines.push(`<ul>${listItems.join('')}</ul>`);
    }

    return processedLines.join('\n');
  };

  // Convert markdown numbered lists
  const convertMarkdownNumberedLists = (text) => {
    const lines = text.split('\n');
    const processedLines = [];
    let inList = false;
    let listItems = [];
    let listLevel = 0;

    lines.forEach((line) => {
      // Match numbered items with optional indentation
      const numberedMatch = line.match(/^(\s*)(\d+)\.\s+(.+)$/);
      
      if (numberedMatch) {
        const [, indent, number, content] = numberedMatch;
        const level = Math.floor(indent.length / 2);
        
          // If we're starting a new list or changing levels
          if (!inList || level !== listLevel) {
            // Close previous list if exists
            if (inList && listItems.length > 0) {
              processedLines.push(`<ol>${listItems.join('')}</ol>`);
            }
            
            // Start new list
            listLevel = level;
            listItems = [];
            inList = true;
          }
        
        // Process content for nested formatting
        const processedContent = processInlineMarkdown(content);
        listItems.push(`<li>${processedContent}</li>`);
      } else {
        // Not a numbered item
        if (inList && listItems.length > 0) {
          // Close the list
          processedLines.push(`<ol>${listItems.join('')}</ol>`);
          listItems = [];
          inList = false;
          listLevel = 0;
        }
        processedLines.push(line);
      }
    });

    // Close any remaining list
    if (inList && listItems.length > 0) {
      processedLines.push(`<ol>${listItems.join('')}</ol>`);
    }

    return processedLines.join('\n');
  };

  // Process the content
  const processedContent = processContent(content);

  // Extract code blocks for special handling
  const renderWithCodeBlocks = (html) => {
    const parts = [];
    let lastIndex = 0;
    const codeBlockRegex = /<pre class="code-block" data-lang="([^"]*)"><code>([\s\S]*?)<\/code><\/pre>/g;
    let match;

    while ((match = codeBlockRegex.exec(html)) !== null) {
      // Add content before code block
      if (match.index > lastIndex) {
        parts.push({
          type: 'html',
          content: html.substring(lastIndex, match.index)
        });
      }

      // Add code block
      parts.push({
        type: 'code',
        language: match[1] || 'text',
        content: match[2]
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining content
    if (lastIndex < html.length) {
      parts.push({
        type: 'html',
        content: html.substring(lastIndex)
      });
    }

    return parts.length > 0 ? parts : [{ type: 'html', content: html }];
  };

  const contentParts = renderWithCodeBlocks(processedContent);

  return (
    <Box
      sx={{
        width: '100%',
        color: effectiveTextColor,
        fontFamily: 'DM Sans, sans-serif',
        lineHeight: 1.7,
        '& h1': {
          fontSize: '1.75rem',
          fontWeight: 700,
          marginTop: '1.5rem',
          marginBottom: '1rem',
          color: theme.palette.text.primary,
          borderBottom: `2px solid ${theme.palette.divider}`,
          paddingBottom: '0.5rem'
        },
        '& h2': {
          fontSize: '1.5rem',
          fontWeight: 600,
          marginTop: '1.25rem',
          marginBottom: '0.75rem',
          color: theme.palette.text.primary
        },
        '& h3': {
          fontSize: '1.25rem',
          fontWeight: 600,
          marginTop: '1rem',
          marginBottom: '0.5rem',
          color: theme.palette.text.primary
        },
        '& h4': {
          fontSize: '1.1rem',
          fontWeight: 600,
          marginTop: '0.75rem',
          marginBottom: '0.5rem',
          color: theme.palette.text.primary
        },
        '& h5, & h6': {
          fontSize: '1rem',
          fontWeight: 600,
          marginTop: '0.5rem',
          marginBottom: '0.5rem',
          color: theme.palette.text.primary
        },
        '& p': {
          marginTop: '0.75rem',
          marginBottom: '0.75rem',
          '&:first-of-type': {
            marginTop: 0
          },
          '&:last-of-type': {
            marginBottom: 0
          }
        },
        '& ul, & ol': {
          marginTop: '0.5rem',
          marginBottom: '0.75rem',
          paddingLeft: '1.5rem',
          '& li': {
            marginTop: '0.25rem',
            marginBottom: '0.25rem',
            '& ul, & ol': {
              marginTop: '0.25rem',
              marginBottom: '0.25rem'
            }
          }
        },
        '& ul': {
          listStyleType: 'disc',
          '& ul': {
            listStyleType: 'circle',
            '& ul': {
              listStyleType: 'square'
            }
          }
        },
        '& ol': {
          listStyleType: 'decimal',
          '& ol': {
            listStyleType: 'lower-alpha',
            '& ol': {
              listStyleType: 'lower-roman'
            }
          }
        },
        '& strong': {
          fontWeight: 600,
          color: theme.palette.text.primary
        },
        '& em': {
          fontStyle: 'italic'
        },
        '& code': {
          backgroundColor: isDarkMode 
            ? 'rgba(255, 255, 255, 0.1)' 
            : 'rgba(0, 0, 0, 0.05)',
          padding: '0.125rem 0.25rem',
          borderRadius: '0.25rem',
          fontSize: '0.9em',
          fontFamily: 'Monaco, Consolas, "Courier New", monospace',
          color: theme.palette.primary.main
        },
        '& pre': {
          backgroundColor: isDarkMode ? '#1e1e1e' : '#f5f5f5',
          padding: '1rem',
          borderRadius: '0.5rem',
          overflow: 'auto',
          marginTop: '1rem',
          marginBottom: '1rem',
          border: `1px solid ${theme.palette.divider}`,
          '& code': {
            backgroundColor: 'transparent',
            padding: 0,
            color: 'inherit'
          }
        },
        '& table.compliance-table': {
          width: '100%',
          borderCollapse: 'collapse',
          marginTop: '1rem',
          marginBottom: '1rem',
          fontSize: '0.9rem',
          '& th': {
            backgroundColor: theme.palette.mode === 'dark' 
              ? 'rgba(255, 255, 255, 0.1)' 
              : 'rgba(0, 0, 0, 0.05)',
            fontWeight: 600,
            padding: '0.75rem',
            textAlign: 'left',
            borderBottom: `2px solid ${theme.palette.divider}`,
            color: theme.palette.text.primary
          },
          '& td': {
            padding: '0.75rem',
            borderBottom: `1px solid ${theme.palette.divider}`,
            '&:last-child': {
              borderBottom: 'none'
            }
          },
          '& tr:hover': {
            backgroundColor: theme.palette.mode === 'dark' 
              ? 'rgba(255, 255, 255, 0.05)' 
              : 'rgba(0, 0, 0, 0.02)'
          }
        },
        '& span[style*="color:#008000"]': {
          color: '#008000 !important',
          fontWeight: 500
        },
        '& span[style*="color:green"]': {
          color: '#008000 !important',
          fontWeight: 500
        },
        '& a': {
          color: theme.palette.primary.main,
          textDecoration: 'none',
          '&:hover': {
            textDecoration: 'underline'
          }
        },
        '& hr': {
          border: 'none',
          borderTop: `1px solid ${theme.palette.divider}`,
          margin: '1.5rem 0'
        }
      }}
    >
      {contentParts.map((part, index) => {
        if (part.type === 'code') {
          return (
            <Box
              key={index}
              component="pre"
              sx={{
                backgroundColor: isDarkMode ? '#1e1e1e' : '#f5f5f5',
                padding: '1rem',
                borderRadius: '0.5rem',
                overflow: 'auto',
                marginTop: '1rem',
                marginBottom: '1rem',
                border: `1px solid ${theme.palette.divider}`,
                fontSize: '0.875rem',
                fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                lineHeight: 1.6,
                color: effectiveTextColor,
                '& code': {
                  backgroundColor: 'transparent',
                  padding: 0,
                  color: 'inherit',
                  fontFamily: 'inherit'
                }
              }}
            >
              <code>{part.content}</code>
            </Box>
          );
        } else {
          return (
            <Box
              key={index}
              dangerouslySetInnerHTML={{ __html: part.content }}
            />
          );
        }
      })}
    </Box>
  );
};

export default ComplianceChatFormattedResponse;

