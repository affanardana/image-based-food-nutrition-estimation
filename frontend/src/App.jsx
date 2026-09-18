import { useEffect, useState } from "react";
import UploadScreen from "./components/UploadScreen.jsx";
import LabelScreen from "./components/LabelScreen.jsx";
import ResultScreen from "./components/ResultScreen.jsx";
import HistoryScreen from "./components/HistoryScreen.jsx";
import { onSlowRequestsChange } from "./api.js";

export default function App() {
  const [meal, setMeal] = useState(null);
  const [view, setView] = useState("upload");
  const [labelMode, setLabelMode] = useState("create");
  const [serverWaking, setServerWaking] = useState(false);

  useEffect(() => onSlowRequestsChange(setServerWaking), []);

  const startNewAnalysis = () => {
    setMeal(null);
    setView("upload");
  };

  return (
    <div className="min-h-screen bg-stone-100 text-stone-800">
      <header className="flex items-center justify-between bg-emerald-800 px-4 py-4 text-white">
        <h1 className="text-xl font-bold">Food Nutrition Estimation</h1>
        <nav className="flex gap-2">
          <button
            onClick={startNewAnalysis}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              view === "upload"
                ? "bg-emerald-700 font-medium"
                : "hover:bg-emerald-700"
            }`}
          >
            Analyze
          </button>
          <button
            onClick={() => setView("history")}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              view === "history"
                ? "bg-emerald-700 font-medium"
                : "hover:bg-emerald-700"
            }`}
          >
            History
          </button>
        </nav>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6">
        {serverWaking && (
          <div className="mb-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Waking up the demo server — the first request after a pause can
            take up to a minute.
          </div>
        )}

        {view === "upload" && (
          <UploadScreen
            onAnalyzed={(analyzed) => {
              setMeal(analyzed);
              setLabelMode("create");
              setView("label");
            }}
          />
        )}

        {view === "history" && (
          <HistoryScreen
            onOpen={(stored) => {
              setMeal(stored);
              setView("result");
            }}
            onBack={startNewAnalysis}
          />
        )}

        {view === "label" && meal && (
          <LabelScreen
            meal={meal}
            mode={labelMode}
            onLabeled={(updated) => {
              setMeal(updated);
              setView("result");
            }}
            onMealUpdated={setMeal}
            onBack={() =>
              labelMode === "edit" ? setView("result") : startNewAnalysis()
            }
          />
        )}

        {view === "result" && meal && (
          <ResultScreen
            meal={meal}
            onUpdated={setMeal}
            onEditLabels={() => {
              setLabelMode("edit");
              setView("label");
            }}
            onDeleted={() => {
              setMeal(null);
              setView("history");
            }}
            onNewAnalysis={startNewAnalysis}
          />
        )}
      </main>
    </div>
  );
}
