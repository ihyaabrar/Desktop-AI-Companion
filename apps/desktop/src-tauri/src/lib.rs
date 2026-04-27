/// Tauri shell for the Desktop AI Companion.
///
/// In M0 this is intentionally minimal: it just hosts the React WebView. The
/// always-on-top transparent window, sprite IPC, and global hotkeys arrive in
/// M3 (Desktop Presence). Sidecar spawning currently relies on the developer
/// running `uv run uvicorn …` manually; auto-spawn lands alongside the Tauri
/// installer work.
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![ping])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn ping() -> &'static str {
    "pong"
}
