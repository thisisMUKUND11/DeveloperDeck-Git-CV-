// Module-level UI memory. Survives client-side navigation (the module stays
// loaded), but resets on a full page refresh (the module is re-evaluated) —
// so the typed username sticks while you move between pages, and clears when
// you refresh to start a new one.
export const formMemory = { username: "" };
