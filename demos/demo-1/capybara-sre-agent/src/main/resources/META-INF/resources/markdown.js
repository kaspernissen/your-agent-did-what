/*
 * The model writes its incident reports in markdown, so the console has to render it.
 *
 * This is deliberately not a general markdown implementation. It covers what the agent
 * actually emits — measured from live responses: headings, bold, italic, inline code,
 * fenced code, bullet and numbered lists, horizontal rules and blockquotes. No tables,
 * no links, no nesting. If the model starts emitting something else, add it here.
 *
 * Everything is HTML-escaped before any markup is introduced, so model output can never
 * inject markup into the page.
 */
(function (global) {
  'use strict';

  const escapeHtml = (s) =>
    String(s).replace(/[&<>]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[c]));

  /*
   * Inline spans, applied to already-escaped text.
   *
   * Code spans are lifted out first and put back last, so that `**` inside a code span
   * stays literal instead of turning into <strong>.
   */
  function inline(escaped) {
    const code = [];
    // NUL as the sentinel: it cannot appear in the model's text, so a placeholder can
    // never collide with the prose around it.
    const NUL = '\u0000';
    let s = escaped.replace(/`([^`]+)`/g, (_, c) => NUL + (code.push(c) - 1) + NUL);

    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
         .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');

    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${code[i]}</code>`);
  }

  /* Block structure. One pass, one open block at a time — the model does not nest. */
  function renderMarkdown(src) {
    const out = [];
    let open = null;          // 'ul' | 'ol' | 'blockquote' | 'p'
    let buffer = [];          // paragraph and blockquote lines, joined on close
    let fence = null;         // lines collected inside a ``` block

    const close = () => {
      if (open === 'p' || open === 'blockquote') {
        const body = inline(buffer.join(' '));
        out.push(open === 'p' ? `<p>${body}</p>` : `<blockquote>${body}</blockquote>`);
      } else if (open) {
        out.push(`</${open}>`);
      }
      open = null;
      buffer = [];
    };

    const openBlock = (kind) => {
      if (open !== kind) { close(); open = kind; if (kind === 'ul' || kind === 'ol') out.push(`<${kind}>`); }
    };

    for (const line of escapeHtml(src).split('\n')) {
      if (/^\s*```/.test(line)) {
        if (fence) { out.push(`<pre><code>${fence.join('\n')}</code></pre>`); fence = null; }
        else { close(); fence = []; }
        continue;
      }
      if (fence) { fence.push(line); continue; }

      let m;
      if (!line.trim()) {
        close();
      } else if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {   // before the bullet rule
        close();
        out.push('<hr>');
      } else if ((m = line.match(/^(#{1,6})\s+(.*)$/))) {
        close();
        const level = Math.min(m[1].length + 1, 6);             // ## in the answer is an h3 on the page
        out.push(`<h${level}>${inline(m[2])}</h${level}>`);
      } else if ((m = line.match(/^\s*[-*+]\s+(.*)$/))) {
        openBlock('ul');
        out.push(`<li>${inline(m[1])}</li>`);
      } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
        openBlock('ol');
        out.push(`<li>${inline(m[1])}</li>`);
        // escapeHtml already ran, so a quote marker arrives as &gt;
      } else if ((m = line.match(/^\s*&gt;\s?(.*)$/))) {
        openBlock('blockquote');
        buffer.push(m[1]);
      } else {
        openBlock('p');
        buffer.push(line.trim());
      }
    }
    close();
    if (fence) out.push(`<pre><code>${fence.join('\n')}</code></pre>`);   // unterminated fence

    return out.join('');
  }

  /* For one-line prose that should not become a paragraph — the judge's explanations. */
  const renderInline = (src) => inline(escapeHtml(src));

  global.md = {renderMarkdown, renderInline};
})(window);
