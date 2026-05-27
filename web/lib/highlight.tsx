import React from "react";

const COLORS = {
  comment: "text-slate-500 italic",
  string: "text-emerald-300",
  number: "text-amber-300",
  keyword: "text-fuchsia-300",
  ident: "text-sky-300",
  punct: "text-slate-400",
  flag: "text-amber-200",
};

type Token = { className: string; value: string };

const KEYWORDS: Record<string, RegExp> = {
  python:
    /\b(import|from|as|def|return|if|else|elif|for|while|in|not|and|or|True|False|None|class|with|try|except|finally|raise|await|async|yield|lambda|print)\b/,
  javascript:
    /\b(const|let|var|function|return|if|else|for|while|in|of|await|async|true|false|null|undefined|new|class|import|from|export|default|try|catch|finally|throw)\b/,
};

const STRINGS_RE = /(["'`])((?:\\.|(?!\1).)*)\1/;
const NUM_RE = /\b\d+(?:\.\d+)?\b/;
const COMMENT_PY = /#[^\n]*/;
const COMMENT_JS = /\/\/[^\n]*/;
const URL_RE = /https?:\/\/[^\s"']+/;

function tokenizeShell(line: string): Token[] {
  // Highlights `curl`, flags like `-H`, URLs, and quoted strings.
  const tokens: Token[] = [];
  let rest = line;
  while (rest.length > 0) {
    const cmd = rest.match(/^(\$\s?|>\s|#\s)/);
    if (cmd) {
      tokens.push({ className: COLORS.comment, value: cmd[0] });
      rest = rest.slice(cmd[0].length);
      continue;
    }
    const kw = rest.match(/^(curl|http|GET|POST|PUT|DELETE|PATCH|export)\b/);
    if (kw) {
      tokens.push({ className: COLORS.keyword, value: kw[0] });
      rest = rest.slice(kw[0].length);
      continue;
    }
    const flag = rest.match(/^-{1,2}[A-Za-z][A-Za-z0-9-]*/);
    if (flag) {
      tokens.push({ className: COLORS.flag, value: flag[0] });
      rest = rest.slice(flag[0].length);
      continue;
    }
    const url = rest.match(URL_RE);
    if (url && url.index === 0) {
      tokens.push({ className: COLORS.string, value: url[0] });
      rest = rest.slice(url[0].length);
      continue;
    }
    const str = rest.match(STRINGS_RE);
    if (str && str.index === 0) {
      tokens.push({ className: COLORS.string, value: str[0] });
      rest = rest.slice(str[0].length);
      continue;
    }
    tokens.push({ className: "text-slate-200", value: rest[0] });
    rest = rest.slice(1);
  }
  return tokens;
}

function tokenizeGeneric(
  line: string,
  keywordsRe: RegExp,
  commentRe: RegExp,
): Token[] {
  const tokens: Token[] = [];
  let rest = line;

  const commentMatch = rest.match(commentRe);
  if (commentMatch && commentMatch.index !== undefined) {
    const before = rest.slice(0, commentMatch.index);
    tokens.push(...tokenizeNoComment(before, keywordsRe));
    tokens.push({ className: COLORS.comment, value: commentMatch[0] });
    return tokens;
  }
  return tokenizeNoComment(rest, keywordsRe);
}

function tokenizeNoComment(line: string, keywordsRe: RegExp): Token[] {
  const tokens: Token[] = [];
  let rest = line;
  while (rest.length > 0) {
    const str = rest.match(STRINGS_RE);
    if (str && str.index === 0) {
      tokens.push({ className: COLORS.string, value: str[0] });
      rest = rest.slice(str[0].length);
      continue;
    }
    const kw = rest.match(keywordsRe);
    if (kw && kw.index === 0) {
      tokens.push({ className: COLORS.keyword, value: kw[0] });
      rest = rest.slice(kw[0].length);
      continue;
    }
    const num = rest.match(NUM_RE);
    if (num && num.index === 0) {
      tokens.push({ className: COLORS.number, value: num[0] });
      rest = rest.slice(num[0].length);
      continue;
    }
    const ident = rest.match(/^[A-Za-z_][A-Za-z0-9_]*/);
    if (ident && ident.index === 0) {
      tokens.push({ className: COLORS.ident, value: ident[0] });
      rest = rest.slice(ident[0].length);
      continue;
    }
    if (/[{}()[\],.:;=+\-*/<>!?|&]/.test(rest[0])) {
      tokens.push({ className: COLORS.punct, value: rest[0] });
      rest = rest.slice(1);
      continue;
    }
    tokens.push({ className: "text-slate-200", value: rest[0] });
    rest = rest.slice(1);
  }
  return tokens;
}

function tokenizeJson(line: string): Token[] {
  const tokens: Token[] = [];
  let rest = line;
  while (rest.length > 0) {
    const str = rest.match(/^"((?:\\.|[^"\\])*)"(\s*:)?/);
    if (str) {
      const isKey = !!str[2];
      tokens.push({
        className: isKey ? COLORS.ident : COLORS.string,
        value: `"${str[1]}"`,
      });
      if (isKey) tokens.push({ className: COLORS.punct, value: str[2]! });
      rest = rest.slice(str[0].length);
      continue;
    }
    const num = rest.match(/^-?\d+(?:\.\d+)?/);
    if (num) {
      tokens.push({ className: COLORS.number, value: num[0] });
      rest = rest.slice(num[0].length);
      continue;
    }
    const lit = rest.match(/^(true|false|null)\b/);
    if (lit) {
      tokens.push({ className: COLORS.keyword, value: lit[0] });
      rest = rest.slice(lit[0].length);
      continue;
    }
    if (/[{}\[\],:]/.test(rest[0])) {
      tokens.push({ className: COLORS.punct, value: rest[0] });
      rest = rest.slice(1);
      continue;
    }
    tokens.push({ className: "text-slate-200", value: rest[0] });
    rest = rest.slice(1);
  }
  return tokens;
}

export type Language = "shell" | "python" | "javascript" | "json";

export function highlight(code: string, language: Language): React.ReactNode {
  const lines = code.split("\n");
  return lines.map((line, i) => {
    let tokens: Token[];
    switch (language) {
      case "shell":
        tokens = tokenizeShell(line);
        break;
      case "python":
        tokens = tokenizeGeneric(line, KEYWORDS.python, COMMENT_PY);
        break;
      case "javascript":
        tokens = tokenizeGeneric(line, KEYWORDS.javascript, COMMENT_JS);
        break;
      case "json":
        tokens = tokenizeJson(line);
        break;
      default:
        tokens = [{ className: "text-slate-200", value: line }];
    }
    return (
      <div key={i} className="whitespace-pre">
        {tokens.length === 0 ? (
          <span>&nbsp;</span>
        ) : (
          tokens.map((t, j) => (
            <span key={j} className={t.className}>
              {t.value}
            </span>
          ))
        )}
      </div>
    );
  });
}
