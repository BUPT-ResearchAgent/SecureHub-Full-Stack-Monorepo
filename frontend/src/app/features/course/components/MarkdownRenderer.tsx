// Status: partial-real
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter';
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash';
import javascript from 'react-syntax-highlighter/dist/esm/languages/prism/javascript';
import json from 'react-syntax-highlighter/dist/esm/languages/prism/json';
import python from 'react-syntax-highlighter/dist/esm/languages/prism/python';
import sql from 'react-syntax-highlighter/dist/esm/languages/prism/sql';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

const supportedLanguages = new Set(['sql', 'python', 'javascript', 'bash', 'shell', 'json', 'text']);

SyntaxHighlighter.registerLanguage('bash', bash);
SyntaxHighlighter.registerLanguage('shell', bash);
SyntaxHighlighter.registerLanguage('javascript', javascript);
SyntaxHighlighter.registerLanguage('json', json);
SyntaxHighlighter.registerLanguage('python', python);
SyntaxHighlighter.registerLanguage('sql', sql);

const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className ?? '');
    const rawLanguage = match?.[1]?.toLowerCase();
    const language = rawLanguage && supportedLanguages.has(rawLanguage) ? rawLanguage : 'text';
    const text = String(children).replace(/\n$/, '');

    if (match) {
      return (
        <SyntaxHighlighter
          language={language}
          style={oneLight}
          customStyle={{ margin: 0, borderRadius: '0.5rem', fontSize: 13 }}
          PreTag="div"
        >
          {text}
        </SyntaxHighlighter>
      );
    }

    return (
      <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[0.85em] text-slate-800" {...props}>
        {children}
      </code>
    );
  },
  table({ children }) {
    return (
      <div className="my-4 overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">{children}</table>
      </div>
    );
  },
  th({ children }) {
    return <th className="bg-slate-50 px-3 py-2 text-left text-xs font-semibold text-slate-600">{children}</th>;
  },
  td({ children }) {
    return <td className="border-t border-slate-100 px-3 py-2 align-top text-sm text-slate-700">{children}</td>;
  },
};

export function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none prose-slate prose-headings:text-slate-900 prose-a:text-brand-blue-600 prose-code:before:content-none prose-code:after:content-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
