/* eslint-disable no-useless-escape */
/**
 * Formats text with numbered/lettered lists into proper HTML lists
 * Handles both line-starting lists and inline lists within sentences
 */
export function formatSummaryText(text: string): string {
  if (!text) return text;

  let result = text;

  result = result.replace(
    /(.*?[:.]\s*)((?:\d+\)\s*[^]*?(?=\s+\d+\)|\.(?:\s|$)))+)/g,
    (match, intro, listSection) => {
      const parts = listSection.split(/(?=\s*\d+\))/);
      const items = parts.filter((part: string) =>
        /^\s*\d+\)/.test(part.trim())
      );

      if (items.length > 1) {
        const listItems = items
          .map((item: string) => {
            const content = item.replace(/^\s*\d+\)\s*/, "").trim();
            const cleanContent = content.replace(/\.\s*$/, "");
            return `  <li>${cleanContent}</li>`;
          })
          .join("\n");

        return `${intro.trim()}\n<ol>\n${listItems}\n</ol>`;
      }

      return match;
    }
  );

  result = result.replace(
    /(.*?[:.]\s*)((?:[a-zA-Z]\)\s*[^]*?(?=\s+[a-zA-Z]\)|\.(?:\s|$)))+)/g,
    (match, intro, listSection) => {
      const parts = listSection.split(/(?=\s*[a-zA-Z]\))/);
      const items = parts.filter((part: string) =>
        /^\s*[a-zA-Z]\)/.test(part.trim())
      );

      if (items.length > 1) {
        const listItems = items
          .map((item: string) => {
            const content = item.replace(/^\s*[a-zA-Z]\)\s*/, "").trim();
            const cleanContent = content.replace(/\.\s*$/, "");
            return `  <li>${cleanContent}</li>`;
          })
          .join("\n");

        return `${intro.trim()}\n<ul>\n${listItems}\n</ul>`;
      }

      return match;
    }
  );

  // Handle traditional line-by-line lists
  const lines = result.split("\n");
  const finalResult: string[] = [];
  let currentList: { type: "ol" | "ul"; items: string[] } | null = null;
  let pendingText: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Skip lines that are already HTML lists
    if (line.match(/^<\/?[ou]l>$/) || line.match(/^\s*<li>/)) {
      if (currentList) {
        const listTag = currentList.type;
        const listItems = currentList.items
          .map((item) => `  <li>${item}</li>`)
          .join("\n");
        finalResult.push(`<${listTag}>\n${listItems}\n</${listTag}>`);
        currentList = null;
      }

      if (pendingText.length > 0) {
        finalResult.push(...pendingText);
        pendingText = [];
      }
      finalResult.push(line);
      continue;
    }

    // Check if line starts with list markers (traditional format)
    const numberedMatch = line.match(/^(\d+)[\.\)]\s*(.+)$/);
    const letteredMatch = line.match(/^([a-zA-Z])[\.\)]\s*(.+)$/);

    if (numberedMatch || letteredMatch) {
      if (pendingText.length > 0 && !currentList) {
        finalResult.push(...pendingText);
        pendingText = [];
      }

      const content = (numberedMatch || letteredMatch)![2];
      const isNumbered = !!numberedMatch;

      if (
        !currentList ||
        (isNumbered && currentList.type === "ul") ||
        (!isNumbered && currentList.type === "ol")
      ) {
        if (currentList) {
          const listTag = currentList.type;
          const listItems = currentList.items
            .map((item) => `  <li>${item}</li>`)
            .join("\n");
          finalResult.push(`<${listTag}>\n${listItems}\n</${listTag}>`);
        }

        currentList = {
          type: isNumbered ? "ol" : "ul",
          items: [content],
        };
      } else {
        currentList.items.push(content);
      }
    } else {
      if (currentList) {
        const listTag = currentList.type;
        const listItems = currentList.items
          .map((item) => `  <li>${item}</li>`)
          .join("\n");
        finalResult.push(`<${listTag}>\n${listItems}\n</${listTag}>`);
        currentList = null;
      }

      if (line) {
        pendingText.push(line);
      } else if (pendingText.length > 0) {
        finalResult.push(...pendingText, "");
        pendingText = [];
      }
    }
  }

  // Handle remaining content
  if (currentList) {
    const listTag = currentList.type;
    const listItems = currentList.items
      .map((item) => `  <li>${item}</li>`)
      .join("\n");
    finalResult.push(`<${listTag}>\n${listItems}\n</${listTag}>`);
  }

  if (pendingText.length > 0) {
    finalResult.push(...pendingText);
  }

  return finalResult.join("\n");
}

/**
 * Example usage:
 *
 * Input:
 * "Next week demand forecast shows stable trends. Critical actions needed: 1) Immediate raw material orders for pork_loins (703kg) 2) Address expiry risks for bread_loaf inventory 3) Priority production of sausages_1kg (658 units). Current raw material stock is adequate."
 *
 * Output:
 * "Next week demand forecast shows stable trends. Critical actions needed:
 * <ol>
 *   <li>Immediate raw material orders for pork_loins (703kg)</li>
 *   <li>Address expiry risks for bread_loaf inventory</li>
 *   <li>Priority production of sausages_1kg (658 units)</li>
 * </ol>
 * Current raw material stock is adequate."
 */
