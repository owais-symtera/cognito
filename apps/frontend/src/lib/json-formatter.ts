/**
 * Format JSON data for human-readable display
 */

export function formatJSON(data: any, indent: number = 0): string {
  // Handle stringified JSON
  if (typeof data === 'string') {
    try {
      data = JSON.parse(data);
    } catch {
      return data; // Return as-is if not valid JSON
    }
  }

  if (data === null || data === undefined) {
    return 'null';
  }

  // Primitive types
  if (typeof data !== 'object') {
    return String(data);
  }

  const indentStr = '  '.repeat(indent);
  const lines: string[] = [];

  if (Array.isArray(data)) {
    // Handle arrays
    if (data.length === 0) {
      return '[]';
    }

    data.forEach((item, index) => {
      if (typeof item === 'object' && item !== null) {
        // For objects in arrays, show numbered items
        lines.push(`${indentStr}${index + 1}.`);
        lines.push(formatJSON(item, indent + 1));
      } else {
        // For simple values, show as bullet list
        lines.push(`${indentStr}• ${formatJSON(item, 0)}`);
      }
    });
  } else {
    // Handle objects
    const entries = Object.entries(data);

    if (entries.length === 0) {
      return '{}';
    }

    entries.forEach(([key, value]) => {
      if (typeof value === 'object' && value !== null) {
        lines.push(`${indentStr}${key}:`);
        lines.push(formatJSON(value, indent + 1));
      } else {
        lines.push(`${indentStr}${key}: ${formatJSON(value, 0)}`);
      }
    });
  }

  return lines.join('\n');
}

/**
 * Format JSON for compact inline display
 */
export function formatJSONInline(data: any): string {
  if (data === null || data === undefined) {
    return 'null';
  }

  if (typeof data !== 'object') {
    return String(data);
  }

  if (Array.isArray(data)) {
    if (data.length === 0) return '[]';
    if (data.length <= 3) {
      return `[${data.map(v => formatJSONInline(v)).join(', ')}]`;
    }
    return `[${data.length} items]`;
  }

  const entries = Object.entries(data);

  if (entries.length === 0) return '{}';

  if (entries.length <= 3) {
    return entries.map(([k, v]) => `${k}: ${formatJSONInline(v)}`).join(', ');
  }

  return `{${entries.length} keys}`;
}
