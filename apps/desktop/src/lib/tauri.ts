// Thin wrapper around `@tauri-apps/api` that no-ops in plain browser preview.
//
// The UI is also served via `vite dev` (no Tauri runtime) for quick iteration
// and in CI smoke tests. Calling `invoke` outside Tauri throws, so we detect
// the runtime once and short-circuit.

const isTauri =
  typeof window !== "undefined" && Object.prototype.hasOwnProperty.call(window, "__TAURI_INTERNALS__");

export function isTauriRuntime(): boolean {
  return isTauri;
}

/**
 * Invoke a Rust command. Returns `null` outside Tauri so callers can stay
 * declarative without sprinkling environment checks everywhere.
 */
export async function invokeCommand<T = void>(
  name: string,
  args?: Record<string, unknown>,
): Promise<T | null> {
  if (!isTauri) return null;
  const { invoke } = await import("@tauri-apps/api/core");
  return (await invoke(name, args)) as T;
}

/**
 * Subscribe to a Tauri event. Returns an unlisten function; outside Tauri it
 * resolves to a no-op so cleanup logic can stay symmetrical.
 */
export async function listenEvent<T>(name: string, handler: (payload: T) => void): Promise<() => void> {
  if (!isTauri) return () => {};
  const { listen } = await import("@tauri-apps/api/event");
  const unlisten = await listen<T>(name, (event) => handler(event.payload));
  return unlisten;
}
