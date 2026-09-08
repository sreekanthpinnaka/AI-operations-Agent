import React from 'react';

interface FormattedMessageProps {
  content: string;
}

export const FormattedMessage: React.FC<FormattedMessageProps> = ({ content }) => {
  if (!content) return null;

  // Split lines into structured markdown blocks: headers, lists, code blocks, tables, paragraphs
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockLines: string[] = [];
  let codeLanguage = '';

  const renderInline = (text: string): React.ReactNode => {
    // Bold: **text**
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return <strong key={idx} style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code
            key={idx}
            style={{
              background: '#f1f5f9',
              color: '#4338ca',
              padding: '0.15rem 0.4rem',
              borderRadius: '4px',
              border: '1px solid #e2e8f0',
              fontSize: '0.85em',
              fontFamily: 'var(--font-mono)',
              fontWeight: 500,
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Handle code blocks
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <div
            key={`code-${i}`}
            style={{
              background: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              padding: '0.85rem 1rem',
              margin: '0.85rem 0',
              overflowX: 'auto',
              boxShadow: 'var(--shadow-xs)',
            }}
          >
            {codeLanguage && (
              <div
                style={{
                  fontSize: '0.7rem',
                  fontFamily: 'var(--font-mono)',
                  color: '#94a3b8',
                  textTransform: 'uppercase',
                  marginBottom: '0.35rem',
                  letterSpacing: '0.05em',
                  fontWeight: 600,
                }}
              >
                {codeLanguage}
              </div>
            )}
            <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#38bdf8', lineHeight: 1.5 }}>
              {codeBlockLines.join('\n')}
            </pre>
          </div>
        );
        inCodeBlock = false;
        codeBlockLines = [];
        codeLanguage = '';
      } else {
        inCodeBlock = true;
        codeLanguage = line.trim().slice(3).trim();
        codeBlockLines = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Headers: ### or ## or #
    if (line.startsWith('### ')) {
      elements.push(
        <h4
          key={`h4-${i}`}
          style={{
            fontSize: '0.95rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginTop: '1.25rem',
            marginBottom: '0.45rem',
          }}
        >
          {renderInline(line.slice(4))}
        </h4>
      );
      continue;
    }

    if (line.startsWith('## ') || line.startsWith('# ')) {
      const text = line.replace(/^#+\s*/, '');
      elements.push(
        <h3
          key={`h3-${i}`}
          style={{
            fontSize: '1.05rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginTop: '1.4rem',
            marginBottom: '0.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '0.35rem',
          }}
        >
          {renderInline(text)}
        </h3>
      );
      continue;
    }

    // Bullet points: - or *
    if (/^\s*[-*•]\s+/.test(line)) {
      const bulletText = line.replace(/^\s*[-*•]\s+/, '');
      elements.push(
        <div
          key={`bullet-${i}`}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.5rem',
            marginTop: '0.3rem',
            marginBottom: '0.3rem',
            paddingLeft: '0.5rem',
            color: 'var(--text-secondary)',
          }}
        >
          <span style={{ color: 'var(--accent-blue)', fontSize: '1rem', lineHeight: '1.4' }}>•</span>
          <span style={{ flex: 1, lineHeight: 1.6 }}>{renderInline(bulletText)}</span>
        </div>
      );
      continue;
    }

    // Numbered lists: 1. or 2.
    const numMatch = line.match(/^\s*(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(
        <div
          key={`num-${i}`}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.5rem',
            marginTop: '0.35rem',
            marginBottom: '0.35rem',
            paddingLeft: '0.5rem',
            color: 'var(--text-secondary)',
          }}
        >
          <span
            style={{
              color: 'var(--accent-blue)',
              fontWeight: 700,
              fontSize: '0.8rem',
              minWidth: '1.2rem',
              lineHeight: '1.5',
            }}
          >
            {numMatch[1]}.
          </span>
          <span style={{ flex: 1, lineHeight: 1.6 }}>{renderInline(numMatch[2])}</span>
        </div>
      );
      continue;
    }

    // Empty line / spacing
    if (!line.trim()) {
      elements.push(<div key={`space-${i}`} style={{ height: '0.65rem' }} />);
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={`p-${i}`} style={{ margin: '0.4rem 0', lineHeight: 1.65, color: 'var(--text-secondary)' }}>
        {renderInline(line)}
      </p>
    );
  }

  return <div className="formatted-message-container">{elements}</div>;
};
