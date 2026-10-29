import { useEffect, useState } from "react";
import { api } from "./lib/api";
import { Library } from "./library/Library";
import { Onboarding } from "./onboarding/Onboarding";
import { Workspace } from "./workspace/Workspace";

const readRoute = () => {
  const h = window.location.hash;
  if (h.startsWith("#/profile")) return { view: "profile" as const, paperId: null };
  const pid = h.match(/^#\/paper\/([\w-]+)/)?.[1] ?? null;
  return { view: pid ? ("paper" as const) : ("library" as const), paperId: pid };
};

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [hasProfile, setHasProfile] = useState<boolean | null>(null);

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    api.getProfile().then(({ profile }) => setHasProfile(!!profile.level));
  }, [route.view]);

  if (hasProfile === null) return null;
  if (!hasProfile) return <Onboarding onDone={() => setHasProfile(true)} />;
  if (route.view === "profile") return <Onboarding editing onDone={() => (window.location.hash = "")} />;
  if (route.view === "paper" && route.paperId)
    return <Workspace paperId={route.paperId} onBack={() => (window.location.hash = "")} />;
  return <Library onOpen={(id) => (window.location.hash = `#/paper/${id}`)} />;
}
