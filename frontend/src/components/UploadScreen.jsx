import { useState } from "react";
import { analyzeMeal } from "../api.js";

export default function UploadScreen({ onAnalyzed }) {
  const [file, setFile] = useState(null);
  const [suggest, setSuggest] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const meal = await analyzeMeal(file, suggest);
      onAnalyzed(meal);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl">
      <h2 className="mb-4 text-lg font-semibold">Analyze a meal</h2>
      <form
        onSubmit={submit}
        className="space-y-4 rounded-xl bg-white p-6 shadow"
      >
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Meal image</span>
          <input
            type="file"
            accept="image/jpeg,image/png"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-stone-600 file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-700 file:px-4 file:py-2 file:text-white hover:file:bg-emerald-800"
          />
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={suggest}
            onChange={(e) => setSuggest(e.target.checked)}
            className="h-4 w-4"
          />
          Suggest labels (catalog-as-prompts)
        </label>

        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={!file || loading}
          className="w-full rounded-lg bg-emerald-700 px-4 py-2 font-medium text-white disabled:opacity-50 hover:bg-emerald-800"
        >
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </form>
    </div>
  );
}
