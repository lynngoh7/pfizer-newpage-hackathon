/**
 * Single wide input, browser-style. Handles both keyword search and plain
 * English questions; the backend decides which (step 3/4). Controlled input,
 * submits only trimmed non-empty text.
 */
import { FormEvent, useState } from "react";

interface Props {
  onSubmit: (query: string) => void;
}

export default function SearchBar({ onSubmit }: Props) {
  const [value, setValue] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault(); // stop the browser reloading the page on submit
    const q = value.trim();
    if (q) onSubmit(q);
  }

  return (
    <form className="searchbar" onSubmit={submit} role="search">
      <input
        type="search"
        placeholder="Search your notes or ask a question…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        autoFocus
        aria-label="Search or ask"
      />
    </form>
  );
}
