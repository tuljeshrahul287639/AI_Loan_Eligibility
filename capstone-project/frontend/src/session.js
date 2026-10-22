import { useEffect, useState } from "react";
import { getSession } from "./api.js";

// Returns the current login session ({ token, username, full_name, role }) or null, and updates when it changes.
export function useSession() {
  const [session, setSession] = useState(getSession);

  useEffect(() => {
    const update = () => setSession(getSession());
    window.addEventListener("session-changed", update);
    return () => window.removeEventListener("session-changed", update);
  }, []);

  return session;
}
