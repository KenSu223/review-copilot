import { useEffect, useState } from "react";
import { Library } from "./library/Library";
import { Workspace } from "./workspace/Workspace";

const readRoute = () => window.location.hash.match(/^#\/paper\/([\w-]+)/)?.[1] ?? null;

export default function App() {
  const [paperId, setPaperId] = useState<string | null>(readRoute);

  useEffect(() => {
    const onHash = () => setPaperId(readRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (paperId) return <Workspace paperId={paperId} onBack={() => (window.location.hash = "")} />;
  return <Library onOpen={(id) => (window.location.hash = `#/paper/${id}`)} />;
}
