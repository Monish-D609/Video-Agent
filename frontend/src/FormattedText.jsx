// Turns the plain-text LLM output (headings like "OVERVIEW:", "- bullets", "1. items") into clean HTML.

function inline(text) {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .map((part, i) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={i}>{part.slice(2, -2)}</strong>
      ) : (
        part
      ),
    );
}

// "task | Owner: X | Deadline: Y"  ->  task, then the rest as muted details
function Item({ text }) {
  const [main, ...rest] = text.split(/\s\|\s/);
  return (
    <li>
      {inline(main)}
      {rest.length > 0 && <span className="meta">{rest.join("  ·  ")}</span>}
    </li>
  );
}

function parse(text) {
  const blocks = [];
  let list = null;
  const flush = () => {
    if (list) blocks.push({ type: "ul", items: list });
    list = null;
  };
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) {
      flush();
      continue;
    }
    let m;
    if ((m = line.match(/^#{2,4}\s+(.*)$/))) {
      flush();
      blocks.push({ type: "h3", text: m[1] });
    } else if ((m = line.match(/^([A-Z][A-Z &/]+):\s*(.*)$/))) {
      flush();
      blocks.push(
        m[2]
          ? { type: "field", label: m[1], text: m[2] }
          : { type: "h2", text: m[1] },
      );
    } else if ((m = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/))) {
      if (!list) list = [];
      list.push(m[1]);
    } else {
      flush();
      blocks.push({ type: "p", text: line });
    }
  }
  flush();
  return blocks;
}

export default function FormattedText({ text }) {
  if (!text) return <p className="muted">Nothing here.</p>;
  return (
    <div className="prose">
      {parse(text).map((b, i) => {
        switch (b.type) {
          case "h2":
            return <h2 key={i}>{b.text.toLowerCase()}</h2>;
          case "h3":
            return <h3 key={i}>{b.text}</h3>;
          case "field":
            return (
              <p key={i} className="field">
                <span>{b.label.toLowerCase()}</span> {inline(b.text)}
              </p>
            );
          case "ul":
            return (
              <ul key={i}>
                {b.items.map((t, j) => (
                  <Item key={j} text={t} />
                ))}
              </ul>
            );
          default:
            return <p key={i}>{inline(b.text)}</p>;
        }
      })}
    </div>
  );
}
