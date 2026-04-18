"use client";

/** GitHub-flavored-markdown renderer for assistant messages, styled to match
 *  the chat bubble without pulling in @tailwindcss/typography. */

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

const components: Components = {
  p: ({ children, ...props }) => (
    <p className="mb-2 last:mb-0 leading-relaxed" {...props}>
      {children}
    </p>
  ),
  h1: ({ children, ...props }) => (
    <h1 className="text-base font-semibold mt-3 mb-2 first:mt-0" {...props}>
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 className="text-sm font-semibold mt-3 mb-2 first:mt-0" {...props}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 className="text-sm font-semibold mt-2 mb-1 first:mt-0" {...props}>
      {children}
    </h3>
  ),
  ul: ({ children, ...props }) => (
    <ul className="list-disc pl-5 mb-2 space-y-1" {...props}>
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol className="list-decimal pl-5 mb-2 space-y-1" {...props}>
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li className="leading-relaxed" {...props}>
      {children}
    </li>
  ),
  strong: ({ children, ...props }) => (
    <strong className="font-semibold" {...props}>
      {children}
    </strong>
  ),
  em: ({ children, ...props }) => (
    <em className="italic" {...props}>
      {children}
    </em>
  ),
  a: ({ children, href, ...props }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="text-primary underline underline-offset-2 hover:no-underline"
      {...props}
    >
      {children}
    </a>
  ),
  blockquote: ({ children, ...props }) => (
    <blockquote
      className="border-l-2 border-border pl-3 italic text-muted-foreground my-2"
      {...props}
    >
      {children}
    </blockquote>
  ),
  code: ({ className, children, ...props }) => {
    const isBlock = /language-/.test(className || "");
    if (isBlock) {
      return (
        <code
          className={cn(
            "block rounded-md bg-background/70 border border-border/60 px-3 py-2 text-xs font-mono overflow-x-auto whitespace-pre",
            className
          )}
          {...props}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        className="rounded bg-background/70 border border-border/60 px-1 py-0.5 text-[0.85em] font-mono"
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ children, ...props }) => (
    <pre className="my-2" {...props}>
      {children}
    </pre>
  ),
  table: ({ children, ...props }) => (
    <div className="my-2 overflow-x-auto">
      <table className="w-full text-xs border border-border/60 rounded-md" {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="bg-background/60" {...props}>
      {children}
    </thead>
  ),
  th: ({ children, ...props }) => (
    <th
      className="px-2 py-1 text-left font-semibold border-b border-border/60"
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td className="px-2 py-1 border-b border-border/30 align-top" {...props}>
      {children}
    </td>
  ),
  hr: () => <hr className="my-3 border-border/60" />,
};

export function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
