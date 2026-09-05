import { NavLink, Route, Routes } from "react-router-dom";
import Catalog from "./pages/Catalog";
import Playground from "./pages/Playground";
import Scoreboard from "./pages/Scoreboard";

function Tab({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
          isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Query Decomposer Arena</h1>
            <p className="text-xs text-muted">
              Break one query into sub-queries + a dependency DAG — nine methods, side by side,
              scored by an LLM judge.
            </p>
          </div>
          <nav className="flex gap-1">
            <Tab to="/" label="Catalog" />
            <Tab to="/playground" label="Playground" />
            <Tab to="/scoreboard" label="Scoreboard" />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Catalog />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/scoreboard" element={<Scoreboard />} />
        </Routes>
      </main>
    </div>
  );
}
