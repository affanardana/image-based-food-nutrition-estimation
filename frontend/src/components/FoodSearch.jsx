import { useEffect, useRef, useState } from "react";
import { searchFoods } from "../api.js";

const DEBOUNCE_MS = 200;
const MAX_RESULTS = 8;

/**
 * Food picker with autocomplete.
 *
 * Suggestions appear as the user types, in a dropdown anchored to the
 * input. The list closes when a food is picked, when the input is
 * cleared, when clicking outside, and on Escape.
 */
export default function FoodSearch({ onPick, disabled, hint }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const containerRef = useRef(null);
  const latestQuery = useRef("");

  useEffect(() => {
    const keyword = query.trim();
    latestQuery.current = keyword;

    if (keyword.length === 0) {
      setResults([]);
      setOpen(false);
      setSearching(false);
      return;
    }

    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        const found = await searchFoods(keyword, MAX_RESULTS);
        // Ignore responses that arrived after the query moved on.
        if (latestQuery.current !== keyword) return;
        setResults(found);
        setHighlight(0);
        setOpen(true);
      } catch {
        if (latestQuery.current === keyword) {
          setResults([]);
          setOpen(true);
        }
      } finally {
        if (latestQuery.current === keyword) setSearching(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onDocumentMouseDown = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocumentMouseDown);
    return () =>
      document.removeEventListener("mousedown", onDocumentMouseDown);
  }, []);

  const pick = (food) => {
    onPick(food);
    setQuery("");
    setResults([]);
    setOpen(false);
  };

  const onKeyDown = (event) => {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (!open || results.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlight((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight(
        (index) => (index - 1 + results.length) % results.length
      );
    } else if (event.key === "Enter") {
      event.preventDefault();
      pick(results[highlight]);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        value={query}
        disabled={disabled}
        placeholder={hint ?? "Search food (e.g. sate)"}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => {
          if (results.length > 0) setOpen(true);
        }}
        onKeyDown={onKeyDown}
        autoComplete="off"
        className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm disabled:bg-stone-100 disabled:opacity-50"
      />

      {open && (
        <ul className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-stone-200 bg-white py-1 shadow-lg">
          {searching && results.length === 0 && (
            <li className="px-3 py-2 text-xs text-stone-400">Searching…</li>
          )}
          {!searching && results.length === 0 && (
            <li className="px-3 py-2 text-sm text-stone-500">
              No food matches “{query.trim()}”.
            </li>
          )}
          {results.map((food, index) => (
            <li key={food.id}>
              <button
                type="button"
                onMouseEnter={() => setHighlight(index)}
                onClick={() => pick(food)}
                className={`flex w-full items-baseline justify-between px-3 py-2 text-left text-sm ${
                  index === highlight ? "bg-emerald-50" : "hover:bg-stone-50"
                }`}
              >
                <span className="font-medium">{food.name}</span>
                <span className="ml-2 font-mono text-xs text-stone-400">
                  {food.id}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
