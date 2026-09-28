// Tiny zustand-style external store helper
// Avoids depending on zustand while giving a useSyncExternalStore-friendly API.

import { useEffect, useState } from "react";

export function create<T>(getInitial: () => T) {
  let state: T = getInitial();
  const listeners = new Set<(s: T) => void>();

  function setState(next: T | ((prev: T) => T)): void {
    state = typeof next === "function" ? (next as (p: T) => T)(state) : next;
    listeners.forEach((l) => l(state));
  }

  function getState(): T {
    return state;
  }

  function subscribe(l: (s: T) => void): () => void {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  }

  function useStore(): T {
    const [s, setS] = useState<T>(state);
    useEffect(() => subscribe(setS), []);
    return s;
  }

  return { setState, getState, subscribe, useStore };
}
