import { useEffect, useState } from "react";
import {
  assetUrl,
  deleteMeal,
  getMeal,
  listMeals,
  renameMeal,
} from "../api.js";

/** Meals fetched per page; the API caps limit at 100. */
const PAGE_SIZE = 20;

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function format(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(1);
}

export default function HistoryScreen({ onOpen, onBack }) {
  const [entries, setEntries] = useState([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [renamingId, setRenamingId] = useState(null);
  const [renameValue, setRenameValue] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const meals = await listMeals(PAGE_SIZE, 0);
        if (!active) return;
        setEntries(meals);
        // A short page means this was the last one.
        setHasMore(meals.length === PAGE_SIZE);
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const loadMore = async () => {
    setLoadingMore(true);
    setError(null);
    try {
      const next = await listMeals(PAGE_SIZE, entries.length);
      setEntries((prev) => [...prev, ...next]);
      setHasMore(next.length === PAGE_SIZE);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingMore(false);
    }
  };

  const open = async (mealId) => {
    setBusyId(mealId);
    setError(null);
    try {
      onOpen(await getMeal(mealId));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (mealId) => {
    if (!window.confirm("Delete this meal and its crops?")) return;
    setBusyId(mealId);
    setError(null);
    try {
      await deleteMeal(mealId);
      setEntries((prev) => prev.filter((entry) => entry.meal_id !== mealId));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const startRename = (entry) => {
    setRenamingId(entry.meal_id);
    setRenameValue(entry.name ?? "");
    setError(null);
  };

  const cancelRename = () => {
    setRenamingId(null);
    setRenameValue("");
  };

  const saveRename = async (mealId) => {
    setBusyId(mealId);
    setError(null);
    try {
      const updated = await renameMeal(mealId, renameValue.trim());
      setEntries((prev) =>
        prev.map((entry) =>
          entry.meal_id === mealId ? { ...entry, name: updated.name } : entry
        )
      );
      cancelRename();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          Meal history
          <span className="ml-2 text-sm font-normal text-stone-500">
            {entries.length} shown
            {hasMore ? " · more available" : ""}
          </span>
        </h2>
        <button
          onClick={onBack}
          className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-200"
        >
          ← New analysis
        </button>
      </div>

      {loading && (
        <p className="rounded-xl bg-white p-4 text-sm text-stone-500 shadow">
          Loading…
        </p>
      )}

      {!loading && entries.length === 0 && (
        <p className="rounded-xl bg-white p-4 text-sm text-stone-500 shadow">
          No saved meals yet. Analyze an image and it will appear here.
        </p>
      )}

      <div className="space-y-3">
        {entries.map((entry) => (
          <div key={entry.meal_id} className="rounded-xl bg-white p-3 shadow">
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-stone-200">
                {entry.image_url && (
                  <img
                    src={assetUrl(entry.image_url)}
                    alt={entry.name || entry.meal_id}
                    className="h-full w-full object-cover"
                  />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">
                  {entry.name || (
                    <span className="text-stone-400">Untitled meal</span>
                  )}
                </div>
                <div className="text-sm text-stone-600">
                  {formatDate(entry.created_at)}
                </div>
                <div className="truncate font-mono text-xs text-stone-400">
                  {entry.meal_id}
                </div>
                <div className="text-xs text-stone-500">
                  {entry.food_item_count} food item(s) · {entry.segment_count}{" "}
                  crop(s) · {entry.state}
                </div>
              </div>

              <div className="shrink-0 text-right">
                <div className="text-lg font-semibold text-emerald-800">
                  {format(entry.total_calories_kcal)}
                </div>
                <div className="text-xs text-stone-500">kcal</div>
              </div>

              <div className="flex shrink-0 flex-col gap-2">
                <button
                  onClick={() => open(entry.meal_id)}
                  disabled={busyId === entry.meal_id}
                  className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm text-white disabled:opacity-50 hover:bg-emerald-800"
                >
                  Open
                </button>
                <div className="flex gap-2">
                  <button
                    onClick={() => startRename(entry)}
                    disabled={busyId === entry.meal_id}
                    className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm disabled:opacity-50 hover:bg-stone-200"
                  >
                    Rename
                  </button>
                  <button
                    onClick={() => remove(entry.meal_id)}
                    disabled={busyId === entry.meal_id}
                    className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-700 disabled:opacity-50 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>

            {renamingId === entry.meal_id && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  saveRename(entry.meal_id);
                }}
                className="mt-3 flex items-center gap-2 border-t border-stone-200 pt-3"
              >
                <input
                  autoFocus
                  value={renameValue}
                  maxLength={120}
                  placeholder="Name this meal, e.g. Lunch with the team"
                  onChange={(e) => setRenameValue(e.target.value)}
                  className="flex-1 rounded-lg border border-stone-300 px-3 py-1.5 text-sm"
                />
                <button
                  type="submit"
                  disabled={busyId === entry.meal_id}
                  className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm text-white disabled:opacity-50 hover:bg-emerald-800"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={cancelRename}
                  className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-200"
                >
                  Cancel
                </button>
              </form>
            )}
          </div>
        ))}
      </div>

      {hasMore && (
        <button
          onClick={loadMore}
          disabled={loadingMore}
          className="w-full rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-sm font-medium disabled:opacity-50 hover:bg-stone-200"
        >
          {loadingMore ? "Loading…" : `Load ${PAGE_SIZE} more`}
        </button>
      )}

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
