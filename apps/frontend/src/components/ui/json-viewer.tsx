"use client";

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface JSONViewerProps {
  data: any;
  defaultExpanded?: boolean;
  maxHeight?: string;
  showCopyButton?: boolean;
}

export function JSONViewer({
  data,
  defaultExpanded = true,
  maxHeight = "400px",
  showCopyButton = true
}: JSONViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Handle null, undefined, or empty data
  if (data === null || data === undefined) {
    return <span className="text-muted-foreground italic">null</span>;
  }

  // Handle primitive types
  if (typeof data !== 'object') {
    return <PrimitiveValue value={data} />;
  }

  // Handle arrays and objects
  return (
    <div className="relative">
      {showCopyButton && (
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 h-8 w-8 p-0"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-500" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </Button>
      )}
      <div
        className="rounded-md border bg-muted/50 p-4 font-mono text-sm overflow-auto"
        style={{ maxHeight }}
      >
        <JSONNode data={data} defaultExpanded={defaultExpanded} />
      </div>
    </div>
  );
}

interface JSONNodeProps {
  data: any;
  keyName?: string;
  defaultExpanded?: boolean;
  level?: number;
}

function JSONNode({ data, keyName, defaultExpanded = true, level = 0 }: JSONNodeProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Primitive values
  if (data === null || data === undefined || typeof data !== 'object') {
    return (
      <div className="flex gap-2">
        {keyName && <span className="text-blue-600 dark:text-blue-400">{keyName}:</span>}
        <PrimitiveValue value={data} />
      </div>
    );
  }

  const isArray = Array.isArray(data);
  const entries = isArray ? data : Object.entries(data);
  const isEmpty = entries.length === 0;
  const indent = level * 16;

  return (
    <div style={{ marginLeft: level > 0 ? `${indent}px` : 0 }}>
      <div className="flex items-center gap-1 cursor-pointer hover:bg-muted/50 rounded px-1 -mx-1" onClick={() => setIsExpanded(!isExpanded)}>
        {!isEmpty && (
          isExpanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
          )
        )}
        {isEmpty && <span className="w-3" />}

        {keyName && (
          <span className="text-blue-600 dark:text-blue-400">{keyName}:</span>
        )}

        <span className="text-muted-foreground">
          {isArray ? '[' : '{'}
          {!isExpanded && !isEmpty && (
            <span className="text-xs ml-1">
              {isArray ? `${entries.length} items` : `${entries.length} keys`}
            </span>
          )}
          {!isExpanded && (isArray ? ']' : '}')}
        </span>
      </div>

      {isExpanded && (
        <>
          <div className="border-l-2 border-muted-foreground/20 ml-1">
            {isArray ? (
              // Array items
              entries.map((item: any, index: number) => (
                <div key={index} className="ml-2">
                  <JSONNode
                    data={item}
                    keyName={`[${index}]`}
                    defaultExpanded={defaultExpanded}
                    level={level + 1}
                  />
                </div>
              ))
            ) : (
              // Object entries
              entries.map(([key, value]: [string, any]) => (
                <div key={key} className="ml-2">
                  <JSONNode
                    data={value}
                    keyName={key}
                    defaultExpanded={defaultExpanded}
                    level={level + 1}
                  />
                </div>
              ))
            )}
          </div>
          <span className="text-muted-foreground">{isArray ? ']' : '}'}</span>
        </>
      )}
    </div>
  );
}

function PrimitiveValue({ value }: { value: any }) {
  if (value === null || value === undefined) {
    return <span className="text-orange-500 dark:text-orange-400">null</span>;
  }

  if (typeof value === 'boolean') {
    return <span className="text-purple-600 dark:text-purple-400">{String(value)}</span>;
  }

  if (typeof value === 'number') {
    return <span className="text-green-600 dark:text-green-400">{value}</span>;
  }

  if (typeof value === 'string') {
    // Check if it's a URL
    if (value.match(/^https?:\/\//)) {
      return (
        <a
          href={value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 dark:text-blue-400 underline hover:text-blue-600"
        >
          "{value}"
        </a>
      );
    }

    // Check if it's a date-like string
    if (value.match(/^\d{4}-\d{2}-\d{2}/) || value.includes('T') && value.includes('Z')) {
      return (
        <span className="text-amber-600 dark:text-amber-400" title={new Date(value).toLocaleString()}>
          "{value}"
        </span>
      );
    }

    return <span className="text-red-600 dark:text-red-400">"{value}"</span>;
  }

  return <span className="text-muted-foreground">{String(value)}</span>;
}

// Compact inline JSON viewer for small data
export function JSONInline({ data }: { data: any }) {
  if (data === null || data === undefined) {
    return <span className="text-muted-foreground italic">null</span>;
  }

  if (typeof data !== 'object') {
    return <PrimitiveValue value={data} />;
  }

  const isArray = Array.isArray(data);
  const entries = isArray ? data : Object.entries(data);

  if (entries.length === 0) {
    return <span className="text-muted-foreground">{isArray ? '[]' : '{}'}</span>;
  }

  if (isArray && entries.length <= 3) {
    return (
      <span className="text-muted-foreground">
        [
        {entries.map((item: any, i: number) => (
          <React.Fragment key={i}>
            <PrimitiveValue value={item} />
            {i < entries.length - 1 && ', '}
          </React.Fragment>
        ))}
        ]
      </span>
    );
  }

  if (!isArray && entries.length <= 2) {
    return (
      <span className="text-muted-foreground">
        {'{'}
        {entries.map(([key, value]: [string, any], i: number) => (
          <React.Fragment key={key}>
            <span className="text-blue-600 dark:text-blue-400">{key}</span>
            : <PrimitiveValue value={value} />
            {i < entries.length - 1 && ', '}
          </React.Fragment>
        ))}
        {'}'}
      </span>
    );
  }

  return (
    <span className="text-muted-foreground text-xs">
      {isArray ? `[${entries.length} items]` : `{${entries.length} keys}`}
    </span>
  );
}
