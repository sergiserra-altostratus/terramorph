/**
 * Simple line-based diff utility using Longest Common Subsequence (LCS).
 * Produces a side-by-side diff result with line states for highlighting.
 */

export type LineState = "unchanged" | "added" | "removed" | "padding";

export interface DiffLine {
  text: string;
  state: LineState;
  lineNumber: number | null;
}

export interface DiffResult {
  left: DiffLine[];
  right: DiffLine[];
  hasChanges: boolean;
}

/**
 * Compute a line-based diff between original and fixed content.
 * Uses LCS to align lines and identify additions/removals.
 */
export function computeDiff(original: string, fixed: string): DiffResult {
  const originalLines = original.split("\n");
  const fixedLines = fixed.split("\n");

  // Compute LCS table
  const lcs = computeLCS(originalLines, fixedLines);

  // Build diff from LCS
  const left: DiffLine[] = [];
  const right: DiffLine[] = [];
  let hasChanges = false;

  let i = originalLines.length;
  let j = fixedLines.length;

  // Trace back through the LCS table
  const actions: Array<{ type: "match" | "remove" | "add"; oi: number; fi: number }> = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && originalLines[i - 1].trimEnd() === fixedLines[j - 1].trimEnd()) {
      actions.unshift({ type: "match", oi: i - 1, fi: j - 1 });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || lcs[i][j - 1] >= lcs[i - 1][j])) {
      actions.unshift({ type: "add", oi: -1, fi: j - 1 });
      j--;
    } else if (i > 0) {
      actions.unshift({ type: "remove", oi: i - 1, fi: -1 });
      i--;
    }
  }

  // Convert actions to diff lines
  let leftLineNum = 0;
  let rightLineNum = 0;

  for (const action of actions) {
    if (action.type === "match") {
      leftLineNum++;
      rightLineNum++;
      left.push({ text: originalLines[action.oi], state: "unchanged", lineNumber: leftLineNum });
      right.push({ text: fixedLines[action.fi], state: "unchanged", lineNumber: rightLineNum });
    } else if (action.type === "remove") {
      leftLineNum++;
      left.push({ text: originalLines[action.oi], state: "removed", lineNumber: leftLineNum });
      right.push({ text: "", state: "padding", lineNumber: null });
      hasChanges = true;
    } else if (action.type === "add") {
      rightLineNum++;
      left.push({ text: "", state: "padding", lineNumber: null });
      right.push({ text: fixedLines[action.fi], state: "added", lineNumber: rightLineNum });
      hasChanges = true;
    }
  }

  return { left, right, hasChanges };
}

/**
 * Compute the LCS table (dynamic programming).
 */
function computeLCS(a: string[], b: string[]): number[][] {
  const m = a.length;
  const n = b.length;
  const table: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1].trimEnd() === b[j - 1].trimEnd()) {
        table[i][j] = table[i - 1][j - 1] + 1;
      } else {
        table[i][j] = Math.max(table[i - 1][j], table[i][j - 1]);
      }
    }
  }

  return table;
}
