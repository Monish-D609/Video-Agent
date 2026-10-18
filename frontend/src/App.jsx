import { useEffect, useState } from "react";
import Home from "./Home.jsx";
import Job from "./Job.jsx";

// The open video lives in the URL (#/v/<id>), so refresh and the back button just work.
const parse = () => {
  const m = window.location.hash.match(/^#\/v\/([\w-]+)$/);
  return m ? m[1] : null;
};

export default function App() {
  const [id, setId] = useState(parse);

  useEffect(() => {
    const onHash = () => setId(parse());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const open = (next) => {
    window.location.hash = next ? `/v/${next}` : "/";
  };

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={() => open(null)}>
          <span className="logo">▶</span> Video Agent
        </button>
        {id && (
          <button className="btn ghost" onClick={() => open(null)}>
            New video
          </button>
        )}
      </header>
      <main className="container">
        {id ? (
          <Job key={id} id={id} onHome={() => open(null)} />
        ) : (
          <Home onOpen={open} />
        )}
      </main>
    </div>
  );
}
