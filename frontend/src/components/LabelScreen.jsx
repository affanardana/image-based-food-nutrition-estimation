import { useMemo, useState } from "react";
import {
  assetUrl,
  discardSegments,
  labelMeal,
  replaceLabels,
  searchFoods,
} from "../api.js";
import FoodSearch from "./FoodSearch.jsx";

function CropImage({ url, alt }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="flex h-32 items-center justify-center bg-stone-200 px-2 text-center text-xs text-stone-500">
        crop file not available
        <br />
        (mock provider)
      </div>
    );
  }
  return (
    <img
      src={url}
      alt={alt}
      onError={() => setFailed(true)}
      className="h-32 w-full object-cover"
    />
  );
}

export default function LabelScreen({
  meal,
  mode = "create",
  onLabeled,
  onMealUpdated,
  onBack,
}) {
  const isEditing = mode === "edit";
  const [selected, setSelected] = useState(() => new Set());
  // Editing starts from the meal's current labeling so the user can
  // change part of it instead of relabeling every crop.
  const [assignments, setAssignments] = useState(() =>
    (meal.food_items ?? [])
      .filter((item) => item.canonical_food)
      .map((item) => ({
        canonical_food_id: item.canonical_food.id,
        name: item.canonical_food.name,
        segment_ids: item.segment_ids,
      }))
  );
  const [mealName, setMealName] = useState(meal.name ?? "");
  // The overlay positions are percentages of the source image, so the
  // image's real size is needed. Only the analyze response carries
  // `image`; meals loaded from elsewhere (history, after a discard)
  // measure the image once it loads.
  const [imageSize, setImageSize] = useState(() =>
    meal.image?.width && meal.image?.height
      ? { width: meal.image.width, height: meal.image.height }
      : null
  );
  const [discarding, setDiscarding] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  /** segment id → food name, for the card badges and the image overlays. */
  const foodBySegment = useMemo(() => {
    const map = new Map();
    for (const assignment of assignments) {
      for (const id of assignment.segment_ids) map.set(id, assignment.name);
    }
    return map;
  }, [assignments]);

  /** Selected crops grouped by their predicted label. */
  const selectedSuggestions = useMemo(() => {
    const groups = new Map();
    for (const segment of meal.segments) {
      if (!selected.has(segment.id) || !segment.suggestion) continue;
      const label = segment.suggestion.label;
      groups.set(label, [...(groups.get(label) ?? []), segment.id]);
    }
    return [...groups.entries()];
  }, [meal.segments, selected]);

  const unassignedCount = meal.segments.length - foodBySegment.size;

  const deselect = (segmentIds) => {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const id of segmentIds) next.delete(id);
      return next;
    });
  };

  const toggle = (segmentId) => {
    if (foodBySegment.has(segmentId)) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(segmentId)) next.delete(segmentId);
      else next.add(segmentId);
      return next;
    });
  };

  const clearSelection = () => setSelected(new Set());

  /**
   * Assign an explicit set of segments to a food.
   *
   * Takes the ids as an argument rather than reading the selection
   * state: callers that just set the selection (the prediction buttons)
   * would otherwise assign the *previous* selection.
   */
  const assignSegments = (segmentIds, food) => {
    if (segmentIds.length === 0) return;
    setAssignments((prev) => {
      const existing = prev.find((a) => a.canonical_food_id === food.id);
      if (existing) {
        const merged = new Set([...existing.segment_ids, ...segmentIds]);
        return prev.map((a) =>
          a.canonical_food_id === food.id
            ? { ...a, segment_ids: [...merged] }
            : a
        );
      }
      return [
        ...prev,
        {
          canonical_food_id: food.id,
          name: food.name,
          segment_ids: [...segmentIds],
        },
      ];
    });
  };

  /** Accept the prediction for a group of crops without searching. */
  const acceptPrediction = async (segmentIds, label) => {
    setError(null);
    try {
      const results = await searchFoods(label, 1);
      const food = results[0] ?? { id: label, name: label };
      assignSegments(segmentIds, food);
      deselect(segmentIds);
    } catch {
      setError(`Could not resolve “${label}” — search for the food.`);
    }
  };

  const assignSelected = (food) => {
    assignSegments([...selected], food);
    clearSelection();
  };

  const removeAssignment = (index) => {
    setAssignments((prev) => prev.filter((_, i) => i !== index));
  };

  const discard = async (segmentIds) => {
    if (segmentIds.length === 0) return;
    const what =
      segmentIds.length === 1
        ? segmentIds[0]
        : `${segmentIds.length} crops`;
    if (
      !window.confirm(
        `Discard ${what}? Use this for bad segmentations or foods missing from the catalog. Their crop images are deleted.`
      )
    ) {
      return;
    }
    setDiscarding(true);
    setError(null);
    try {
      const updated = await discardSegments(meal.meal_id, segmentIds);
      const dropped = new Set(segmentIds);
      setAssignments((prev) =>
        prev
          .map((assignment) => ({
            ...assignment,
            segment_ids: assignment.segment_ids.filter(
              (id) => !dropped.has(id)
            ),
          }))
          .filter((assignment) => assignment.segment_ids.length > 0)
      );
      deselect(segmentIds);
      onMealUpdated?.(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setDiscarding(false);
    }
  };

  const submit = async () => {
    if (assignments.length === 0) return;
    setSubmitting(true);
    setError(null);
    const payload = assignments.map((a) => ({
      canonical_food_id: a.canonical_food_id,
      segment_ids: a.segment_ids,
    }));
    try {
      // The name travels with the labels so it cannot be forgotten.
      const updated = isEditing
        ? await replaceLabels(meal.meal_id, payload, mealName.trim())
        : await labelMeal(meal.meal_id, payload, mealName.trim());
      onLabeled(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const imgWidth = imageSize?.width;
  const imgHeight = imageSize?.height;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {isEditing ? "Edit the labeled crops" : "Label the crops"}
          <span className="ml-2 text-sm font-normal text-stone-500">
            meal {meal.meal_id}
          </span>
        </h2>
        <button
          onClick={onBack}
          className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-200"
        >
          {isEditing ? "← Back to result" : "← New image"}
        </button>
      </div>

      {/* No separate save step: the name is submitted with the labels. */}
      <div className="flex items-center gap-2 rounded-xl bg-white p-3 shadow">
        <label
          htmlFor="meal-name"
          className="shrink-0 text-sm text-stone-600"
        >
          Meal name
        </label>
        <input
          id="meal-name"
          value={mealName}
          maxLength={120}
          placeholder="Untitled meal"
          onChange={(e) => setMealName(e.target.value)}
          className="flex-1 rounded-lg border border-stone-300 px-3 py-1.5 text-sm"
        />
      </div>

      {!isEditing && (
        <ol className="space-y-1 rounded-xl bg-sky-50 px-4 py-3 text-sm text-sky-900">
          <li>
            <b>1.</b> Click every crop that shows the same food.
          </li>
          <li>
            <b>2.</b> Accept the prediction, or search for the food yourself.
          </li>
          <li>
            <b>3.</b> Discard bad crops, then save.
          </li>
        </ol>
      )}

      {/* Source image with segment overlays */}
      {meal.image_url && imgWidth && imgHeight && (
        <div className="rounded-xl bg-white p-4 shadow">
          <div className="relative mx-auto w-fit">
            <img
              src={assetUrl(meal.image_url)}
              alt="Meal"
              onLoad={(event) =>
                setImageSize({
                  width: event.target.naturalWidth,
                  height: event.target.naturalHeight,
                })
              }
              className="mx-auto block max-h-96 max-w-full"
            />
            {meal.segments.map((segment) => (
              <div
                key={segment.id}
                onClick={() => toggle(segment.id)}
                className={`absolute border-2 ${
                  foodBySegment.has(segment.id)
                    ? "cursor-default border-emerald-500 bg-emerald-300/20"
                    : selected.has(segment.id)
                      ? "cursor-pointer border-amber-500 bg-amber-300/30"
                      : "cursor-pointer border-sky-400 bg-sky-300/10"
                }`}
                style={{
                  left: `${(segment.bbox.x / imgWidth) * 100}%`,
                  top: `${(segment.bbox.y / imgHeight) * 100}%`,
                  width: `${(segment.bbox.width / imgWidth) * 100}%`,
                  height: `${(segment.bbox.height / imgHeight) * 100}%`,
                }}
                title={
                  foodBySegment.has(segment.id)
                    ? `${segment.id} — labeled ${foodBySegment.get(segment.id)}`
                    : `${segment.id} — click to select`
                }
              />
            ))}
          </div>
          <p className="mt-2 text-center text-xs text-stone-500">
            <span className="text-sky-600">Blue</span> = not labeled ·{" "}
            <span className="text-amber-600">Amber</span> = selected ·{" "}
            <span className="text-emerald-600">Green</span> = labeled
          </p>
        </div>
      )}

      {/* Selection + predictions + food picker */}
      <div className="rounded-xl bg-white p-4 shadow">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-medium">
            {selected.size > 0
              ? `${selected.size} crop(s) selected`
              : "Select crops"}
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => discard([...selected])}
              disabled={selected.size === 0 || discarding}
              className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-700 disabled:opacity-40 hover:bg-red-50"
            >
              {discarding ? "Discarding…" : "Discard selected"}
            </button>
            <button
              onClick={clearSelection}
              disabled={selected.size === 0}
              className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-stone-200"
            >
              Clear selection
            </button>
          </div>
        </div>

        {selectedSuggestions.length > 0 && (
          <div className="mb-3 space-y-2 rounded-lg bg-sky-50 p-3">
            <p className="text-xs font-medium text-sky-900">
              Accept prediction:
            </p>
            <div className="flex flex-wrap gap-2">
              {selectedSuggestions.map(([label, ids]) => (
                <button
                  key={label}
                  onClick={() => acceptPrediction(ids, label)}
                  className="rounded-lg bg-sky-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-800"
                >
                  Label {ids.length} crop(s) as {label}
                </button>
              ))}
            </div>
          </div>
        )}

        <FoodSearch
          onPick={assignSelected}
          disabled={selected.size === 0}
          hint={
            selected.size > 0 ? "Or search for the food…" : "Select crops first"
          }
        />
        <p className="mt-2 text-xs text-stone-500">
          Unlabeled crops are not counted.
        </p>
      </div>

      {/* Crop cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {meal.segments.map((segment) => {
          const foodName = foodBySegment.get(segment.id);
          const isSelected = selected.has(segment.id);
          return (
            <div
              key={segment.id}
              onClick={() => toggle(segment.id)}
              className={`overflow-hidden rounded-xl bg-white shadow transition ${
                isSelected
                  ? "ring-2 ring-amber-500"
                  : foodName
                    ? "ring-2 ring-emerald-500 opacity-80"
                    : "cursor-pointer ring-1 ring-stone-200 hover:ring-sky-400"
              }`}
            >
              <CropImage url={assetUrl(segment.crop_url)} alt={segment.id} />
              <div className="space-y-2 p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-stone-500">
                    {segment.id}
                  </span>
                  {foodName ? (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800">
                      {foodName}
                    </span>
                  ) : isSelected ? (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800">
                      selected
                    </span>
                  ) : (
                    <span className="text-stone-400">tap to select</span>
                  )}
                </div>

                {segment.suggestion && !foodName && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      acceptPrediction([segment.id], segment.suggestion.label);
                    }}
                    className="w-full rounded-lg bg-sky-100 px-2 py-1.5 text-xs font-medium text-sky-800 hover:bg-sky-200"
                  >
                    Label as {segment.suggestion.label} (
                    {Math.round(segment.suggestion.confidence * 100)}%)
                  </button>
                )}

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    discard([segment.id]);
                  }}
                  disabled={discarding}
                  title="For bad segmentations or foods missing from the catalog"
                  className="w-full rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 disabled:opacity-50 hover:bg-red-50"
                >
                  Discard
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Assignments */}
      <div className="rounded-xl bg-white p-4 shadow">
        <h3 className="mb-2 font-medium">
          Foods in this meal
          {assignments.length > 0 && (
            <span className="ml-2 text-sm font-normal text-stone-500">
              {assignments.length}
            </span>
          )}
        </h3>

        {assignments.length === 0 && (
          <p className="text-sm text-stone-500">Nothing labeled yet.</p>
        )}

        <ul className="space-y-1">
          {assignments.map((assignment, index) => (
            <li
              key={`${assignment.canonical_food_id}-${index}`}
              className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm"
            >
              <span>
                <span className="font-medium">{assignment.name}</span>
                <span className="ml-2 text-xs text-stone-500">
                  {assignment.segment_ids.length} crop(s):{" "}
                  <span className="font-mono">
                    {assignment.segment_ids.join(", ")}
                  </span>
                </span>
              </span>
              <button
                onClick={() => removeAssignment(index)}
                className="text-xs text-red-600 hover:underline"
              >
                remove
              </button>
            </li>
          ))}
        </ul>

        {unassignedCount > 0 && assignments.length > 0 && (
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {unassignedCount} crop(s) unlabeled — not counted.
          </p>
        )}

        {error && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          onClick={submit}
          disabled={assignments.length === 0 || submitting}
          className="mt-4 w-full rounded-lg bg-emerald-700 px-4 py-2 font-medium text-white disabled:opacity-50 hover:bg-emerald-800"
        >
          {submitting
            ? "Calculating nutrition…"
            : isEditing
              ? "Save changes"
              : "Save and calculate nutrition"}
        </button>
      </div>
    </div>
  );
}
