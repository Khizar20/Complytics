import React from 'react';

const UiTestingRecommendations = ({ content }) => {
  if (!content) {
    return <div className="text-sm text-muted-foreground">No recommendations available.</div>;
  }

  // Process markdown content and convert to React elements
  const processMarkdown = (text) => {
    if (!text) return [];

    const elements = [];
    const lines = text.split('\n');
    let currentIndex = 0;
    let inCodeBlock = false;
    let codeBlockContent = [];
    let codeBlockLang = 'text';
    let inOrderedList = false;
    let orderedListItems = [];
    let inUnorderedList = false;
    let unorderedListItems = [];

    const flushOrderedList = () => {
      if (orderedListItems.length > 0) {
        elements.push(
          <ol key={`ol-${currentIndex++}`} className="list-decimal list-inside space-y-2 mb-4 ml-4">
            {orderedListItems.map((item, idx) => (
              <li key={idx} className="text-sm text-foreground leading-relaxed">
                {item}
              </li>
            ))}
          </ol>
        );
        orderedListItems = [];
        inOrderedList = false;
      }
    };

    const flushUnorderedList = () => {
      if (unorderedListItems.length > 0) {
        elements.push(
          <ul key={`ul-${currentIndex++}`} className="list-disc list-inside space-y-2 mb-4 ml-4">
            {unorderedListItems.map((item, idx) => (
              <li key={idx} className="text-sm text-foreground leading-relaxed">
                {item}
              </li>
            ))}
          </ul>
        );
        unorderedListItems = [];
        inUnorderedList = false;
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Handle code blocks
      if (trimmed.startsWith('```')) {
        if (inCodeBlock) {
          // End code block
          const codeContent = codeBlockContent.join('\n');
          elements.push(
            <div key={`code-${currentIndex++}`} className="my-4">
              <div className="bg-gray-900 dark:bg-gray-800 rounded-lg overflow-hidden border border-gray-700 dark:border-gray-600">
                {codeBlockLang !== 'text' && (
                  <div className="px-4 py-2 bg-gray-800 dark:bg-gray-900 border-b border-gray-700 dark:border-gray-600">
                    <span className="text-xs font-semibold text-gray-400 uppercase">{codeBlockLang}</span>
                  </div>
                )}
                <pre className="p-4 overflow-x-auto">
                  <code className={`language-${codeBlockLang} text-sm text-gray-100 font-mono leading-relaxed`}>
                    {codeContent}
                  </code>
                </pre>
              </div>
            </div>
          );
          codeBlockContent = [];
          codeBlockLang = 'text';
          inCodeBlock = false;
        } else {
          // Start code block
          flushOrderedList();
          flushUnorderedList();
          const langMatch = trimmed.match(/^```(\w+)?/);
          codeBlockLang = langMatch && langMatch[1] ? langMatch[1] : 'text';
          inCodeBlock = true;
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        continue;
      }

      // Handle horizontal rules
      if (trimmed === '---' || trimmed.match(/^-{3,}$/)) {
        flushOrderedList();
        flushUnorderedList();
        elements.push(
          <hr key={`hr-${currentIndex++}`} className="my-6 border-t border-border opacity-50" />
        );
        continue;
      }

      // Handle empty lines
      if (!trimmed) {
        flushOrderedList();
        flushUnorderedList();
        elements.push(<br key={`br-${currentIndex++}`} />);
        continue;
      }

      // Handle markdown headings
      if (trimmed.startsWith('## ')) {
        flushOrderedList();
        flushUnorderedList();
        const headingText = trimmed.substring(3).trim();
        elements.push(
          <h2 key={`h2-${currentIndex++}`} className="text-xl font-bold text-foreground mt-6 mb-4 first:mt-0">
            {processInlineMarkdown(headingText)}
          </h2>
        );
        continue;
      }

      if (trimmed.startsWith('### ')) {
        flushOrderedList();
        flushUnorderedList();
        const headingText = trimmed.substring(4).trim();
        elements.push(
          <h3 key={`h3-${currentIndex++}`} className="text-lg font-semibold text-foreground mt-5 mb-3">
            {processInlineMarkdown(headingText)}
          </h3>
        );
        continue;
      }

      if (trimmed.startsWith('#### ')) {
        flushOrderedList();
        flushUnorderedList();
        const headingText = trimmed.substring(5).trim();
        elements.push(
          <h4 key={`h4-${currentIndex++}`} className="text-base font-semibold text-foreground mt-4 mb-2">
            {processInlineMarkdown(headingText)}
          </h4>
        );
        continue;
      }

      // Handle ordered list items (1., 2., etc.) - also handle cases with **bold** at start
      const orderedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
      if (orderedMatch) {
        flushUnorderedList();
        inOrderedList = true;
        const itemContent = orderedMatch[2].trim();
        orderedListItems.push(processInlineMarkdown(itemContent));
        continue;
      }

      // Handle unordered list items (-, *, •)
      if (trimmed.match(/^[-*•]\s+(.+)$/)) {
        flushOrderedList();
        inUnorderedList = true;
        const itemText = trimmed.replace(/^[-*•]\s+/, '');
        unorderedListItems.push(processInlineMarkdown(itemText));
        continue;
      }

      // Regular paragraph
      flushOrderedList();
      flushUnorderedList();

      // Check if line contains inline code or bold text
      const processedLine = processInlineMarkdown(trimmed);
      
      elements.push(
        <p key={`p-${currentIndex++}`} className="text-sm text-foreground leading-relaxed mb-3">
          {processedLine}
        </p>
      );
    }

    // Flush any remaining lists
    flushOrderedList();
    flushUnorderedList();

    return elements;
  };

  // Process inline markdown (bold, italic, code, links)
  const processInlineMarkdown = (text) => {
    if (!text) return text;

    const parts = [];
    let currentIndex = 0;
    let remaining = text;

    // Process inline code blocks first (backticks)
    const codeRegex = /`([^`]+)`/g;
    let codeMatch;
    let lastIndex = 0;

    while ((codeMatch = codeRegex.exec(text)) !== null) {
      // Add text before code
      if (codeMatch.index > lastIndex) {
        const beforeText = text.substring(lastIndex, codeMatch.index);
        parts.push(...processBoldAndItalic(beforeText));
      }
      
      // Add code
      parts.push(
        <code key={`inline-code-${currentIndex++}`} className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-xs font-mono text-foreground border border-gray-300 dark:border-gray-600">
          {codeMatch[1]}
        </code>
      );
      
      lastIndex = codeRegex.lastIndex;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      const afterText = text.substring(lastIndex);
      parts.push(...processBoldAndItalic(afterText));
    }

    // If no code blocks found, process bold/italic
    if (parts.length === 0) {
      return processBoldAndItalic(text);
    }

    return parts;
  };

  // Process bold (**text**) and italic (*text*)
  const processBoldAndItalic = (text) => {
    if (!text) return [text];

    const parts = [];
    let remaining = text;
    let keyIndex = 0;

    // Process bold (**text**)
    const boldRegex = /\*\*([^*]+?)\*\*/g;
    let lastIndex = 0;
    let boldMatch;

    while ((boldMatch = boldRegex.exec(text)) !== null) {
      // Add text before bold
      if (boldMatch.index > lastIndex) {
        const beforeText = text.substring(lastIndex, boldMatch.index);
        parts.push(...processItalic(beforeText, keyIndex));
        keyIndex += beforeText.split('*').length;
      }
      
      // Add bold text
      const boldContent = processItalic(boldMatch[1], keyIndex);
      parts.push(
        <strong key={`bold-${keyIndex++}`} className="font-semibold text-foreground">
          {boldContent}
        </strong>
      );
      
      lastIndex = boldRegex.lastIndex;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      const afterText = text.substring(lastIndex);
      parts.push(...processItalic(afterText, keyIndex));
    }

    // If no bold found, process italic
    if (parts.length === 0) {
      return processItalic(text, 0);
    }

    return parts;
  };

  // Process italic (*text*)
  const processItalic = (text, startKey = 0) => {
    if (!text) return [text];

    const parts = [];
    const italicRegex = /(?<!\*)\*([^*\n]+?)\*(?!\*)/g;
    let lastIndex = 0;
    let italicMatch;
    let keyIndex = startKey;

    while ((italicMatch = italicRegex.exec(text)) !== null) {
      // Add text before italic
      if (italicMatch.index > lastIndex) {
        parts.push(text.substring(lastIndex, italicMatch.index));
      }
      
      // Add italic text
      parts.push(
        <em key={`italic-${keyIndex++}`} className="italic text-foreground">
          {italicMatch[1]}
        </em>
      );
      
      lastIndex = italicRegex.lastIndex;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : [text];
  };

  const elements = processMarkdown(content);

  return (
    <div className="space-y-2">
      {elements}
    </div>
  );
};

export default UiTestingRecommendations;

