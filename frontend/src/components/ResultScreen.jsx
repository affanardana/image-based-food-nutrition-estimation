import { useState } from "react";
import { assetUrl, deleteMeal, updateMeal } from "../api.js";

function format(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(1);
}

export default function ResultScreen({
  meal,
  onUpdated,
  onEditLabels,
  onDeleted,
  onNewAnalysis,
}) {
  const [weights, setWeights] = useState({});
  const [savingId, setSavingId] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);

  const saveWeight = async (item) => {
    const value = Number.parseFloat(weights[item.id]);
    if (Number.isNaN(value) || value <= 0) {
      setError("Enter a positive weight in grams.");
      return;
    }
    setSavingId(item.id);
    setError(null);
    try {
      const updated = await updateMeal(meal.meal_id, [
        { id: item.id, estimated_weight_g: value },
      ]);
      onUpdated(updated);
      setWeights((prev) => ({ ...prev, [item.id]: undefined }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingId(null);
    }
  };

  const remove = async () => {
    if (!window.confirm("Delete this meal?")) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteMeal(meal.meal_id);
      onDeleted();
    } catch (err) {
      setError(err.message);
      setDeleting(false);
    }
  };

  const summary = meal.summary ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">Nutrition result</h2>
          <p className="truncate text-sm text-stone-600">
            {meal.name || "Untitled meal"}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            onClick={onEditLabels}
            className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-200"
          >
            Edit labels
          </button>
          <button
            onClick={onNewAnalysis}
            className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-200"
          >
            New analysis
          </button>
          <button
            onClick={remove}
            disabled={deleting}
            className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            {deleting ? "Deleting…" : "Delete meal"}
          </button>
        </div>
      </div>

      {/* The analyzed photo */}
      {meal.image_url && (
        <div className="rounded-xl bg-white p-4 shadow">
          <img
            src={assetUrl(meal.image_url)}
            alt={meal.name || "Meal"}
            className="mx-auto block max-h-72 max-w-full rounded-lg"
          />
        </div>
      )}

      {/* Summary card */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ["Calories", summary.total_calories_kcal, "kcal"],
          ["Protein", summary.total_protein_g, "g"],
          ["Fat", summary.total_fat_g, "g"],
          ["Carbs", summary.total_carbohydrates_g, "g"],
        ].map(([label, value, unit]) => (
          <div key={label} className="rounded-xl bg-emerald-700 p-4 text-white shadow">
            <div className="text-sm opacity-80">{label}</div>
            <div className="text-2xl font-bold">
              {format(value)} <span className="text-sm font-normal">{unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Food items */}
      <div className="space-y-3">
        {meal.food_items.length === 0 && (
          <p className="rounded-xl bg-white p-4 text-sm text-stone-500 shadow">
            No food items yet — go back and label the segments.
          </p>
        )}
        {meal.food_items.map((item) => (
          <div key={item.id} className="rounded-xl bg-white p-4 shadow">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-medium">
                {item.canonical_food?.name ?? "Unknown food"}
              </h3>
              <span className="font-mono text-xs text-stone-400">
                {item.segment_ids.length} crop(s)
              </span>
            </div>

            <div className="mb-3 grid grid-cols-2 gap-2 text-sm text-stone-600 md:grid-cols-4">
              <div>
                Volume: <b>{format(item.measurement?.estimated_volume_cm3)} cm³</b>
              </div>
              <div>
                Weight: <b>{format(item.measurement?.estimated_weight_g)} g</b>
              </div>
              <div>
                Calories: <b>{format(item.nutrition?.calories_kcal)} kcal</b>
              </div>
              <div>
                Protein: <b>{format(item.nutrition?.protein_g)} g</b>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                saveWeight(item);
              }}
              className="flex items-center gap-2"
            >
              <label className="text-sm text-stone-600">
                Correct weight (g):
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={weights[item.id] ?? ""}
                  placeholder={String(item.measurement?.estimated_weight_g ?? "")}
                  onChange={(e) =>
                    setWeights((prev) => ({ ...prev, [item.id]: e.target.value }))
                  }
                  className="ml-2 w-24 rounded-lg border border-stone-300 px-2 py-1 text-sm"
                />
              </label>
              <button
                type="submit"
                disabled={savingId === item.id}
                className="rounded-lg bg-stone-700 px-3 py-1 text-sm text-white disabled:opacity-50 hover:bg-stone-800"
              >
                {savingId === item.id ? "Saving…" : "Save"}
              </button>
            </form>
          </div>
        ))}
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
