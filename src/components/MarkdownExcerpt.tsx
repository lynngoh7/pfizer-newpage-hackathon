import type { ReactNode } from "react";

type ListKind = "bullet" | "task" | "ordered";

type ListItem = {
  text: string;
  checked?: boolean;
};

type Block =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "quote"; text: string }
  | { kind: "code"; text: string }
  | { kind: "rule" }
  | { kind: "list"; listKind: ListKind; start?: number; items: ListItem[] };

function getListItem(line: string): (ListItem & { listKind: ListKind; start?: number }) | null {
  const task = /^\s{0,3}[-*+]\s+\[([ xX])\]\s*(.*)$/.exec(line);
  if (task) return { listKind: "task", text: task[2], checked: task[1].toLowerCase() === "x" };

  const bullet = /^\s{0,3}[-*+]\s+(.*)$/.exec(line);
  if (bullet) return { listKind: "bullet", text: bullet[1] };

  const ordered = /^\s{0,3}(\d+)[.)]\s+(.*)$/.exec(line);
  if (ordered) return { listKind: "ordered", start: Number(ordered[1]), text: ordered[2] };

  return null;
}

function isBlockStart(line: string): boolean {
  return (
    /^\s{0,3}(?:#{1,6}\s+|>\s?|```)/.test(line) ||
    getListItem(line) !== null ||
    /^\s{0,3}(?:-{3,}|_{3,}|\*{3,})\s*$/.test(line)
  );
}

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (/^\s{0,3}```/.test(line)) {
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !/^\s{0,3}```/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push({ kind: "code", text: code.join("\n") });
      continue;
    }

    const heading = /^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$/.exec(line);
    if (heading) {
      blocks.push({ kind: "heading", text: heading[1] });
      index += 1;
      continue;
    }

    if (/^\s{0,3}(?:-{3,}|_{3,}|\*{3,})\s*$/.test(line)) {
      blocks.push({ kind: "rule" });
      index += 1;
      continue;
    }

    const listItem = getListItem(line);
    if (listItem) {
      const items: ListItem[] = [];
      const listKind = listItem.listKind;
      const start = listItem.start;
      while (index < lines.length) {
        const next = getListItem(lines[index]);
        if (!next || next.listKind !== listKind) break;
        items.push({ text: next.text, checked: next.checked });
        index += 1;
      }
      blocks.push({ kind: "list", listKind, start, items });
      continue;
    }

    const quote = /^\s{0,3}>\s?(.*)$/.exec(line);
    if (quote) {
      const quotedLines: string[] = [];
      while (index < lines.length) {
        const next = /^\s{0,3}>\s?(.*)$/.exec(lines[index]);
        if (!next) break;
        quotedLines.push(next[1].trim());
        index += 1;
      }
      blocks.push({ kind: "quote", text: quotedLines.join(" ") });
      continue;
    }

    const paragraph = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines[index])) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
  }

  return blocks;
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const pattern =
    /!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|_[^_\n]+_/g;
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let part = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${part++}`;
    const image = /^!\[([^\]]*)\]\(([^)]+)\)$/.exec(token);
    const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);

    if (image) {
      nodes.push(
        <span className="markdown-image" key={key}>
          Image: {image[1] || "attachment"}
        </span>,
      );
    } else if (link) {
      // Keep note links as text so excerpts never trigger outbound navigation.
      nodes.push(
        <span className="markdown-link" key={key}>
          {renderInline(link[1], key)}
        </span>,
        <span className="markdown-link-target" key={`${key}-target`}>
          {" "}({link[2]})
        </span>,
      );
    } else if (token.startsWith("`")) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("**") || token.startsWith("__")) {
      nodes.push(<strong key={key}>{renderInline(token.slice(2, -2), key)}</strong>);
    } else {
      nodes.push(<em key={key}>{renderInline(token.slice(1, -1), key)}</em>);
    }
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export default function MarkdownExcerpt({ text }: { text: string }) {
  return (
    <div className="markdown-excerpt">
      {parseBlocks(text).map((block, blockIndex) => {
        const key = `block-${blockIndex}`;
        if (block.kind === "heading") {
          return <h4 className="markdown-heading" key={key}>{renderInline(block.text, key)}</h4>;
        }
        if (block.kind === "paragraph") {
          return <p className="markdown-paragraph" key={key}>{renderInline(block.text, key)}</p>;
        }
        if (block.kind === "quote") {
          return (
            <blockquote className="markdown-quote" key={key}>
              <p>{renderInline(block.text, key)}</p>
            </blockquote>
          );
        }
        if (block.kind === "code") {
          return (
            <pre className="markdown-code" key={key}>
              <code>{block.text}</code>
            </pre>
          );
        }
        if (block.kind === "rule") return <hr className="markdown-rule" key={key} />;

        const items = block.items.map((item, itemIndex) => (
          <li className={block.listKind === "task" ? "markdown-task" : undefined} key={`${key}-${itemIndex}`}>
            {block.listKind === "task" && (
              <input
                type="checkbox"
                checked={item.checked ?? false}
                disabled
                aria-label={item.checked ? "Completed task" : "Incomplete task"}
              />
            )}
            <span>{renderInline(item.text, `${key}-${itemIndex}`)}</span>
          </li>
        ));
        if (block.listKind === "ordered") {
          return <ol className="markdown-list" key={key} start={block.start}>{items}</ol>;
        }
        return (
          <ul className={block.listKind === "task" ? "markdown-list markdown-task-list" : "markdown-list"} key={key}>
            {items}
          </ul>
        );
      })}
    </div>
  );
}
