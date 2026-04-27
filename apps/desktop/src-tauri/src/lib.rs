/// Tauri shell for the Desktop AI Companion.
///
/// M3 introduces the second "presence" window: a small, transparent,
/// always-on-top sprite that the user can position freely. The chat-panel
/// window stays the primary surface; the presence window forwards user
/// intent (clicks, drag) and listens for `emotion-changed` events emitted
/// from the chat side.
use tauri::{AppHandle, Emitter, Manager};

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            ping,
            show_main,
            set_presence_visible,
            emit_emotion,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn ping() -> &'static str {
    "pong"
}

/// Bring the main chat window to the foreground. Called from the presence
/// window when the user clicks the sprite.
#[tauri::command]
fn show_main(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Toggle the presence window's visibility. Persistence of the preference
/// itself lives in the frontend (localStorage); this command is the
/// imperative knob that flips OS-level state.
#[tauri::command]
fn set_presence_visible(app: AppHandle, visible: bool) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("presence") {
        if visible {
            window.show().map_err(|e| e.to_string())?;
        } else {
            window.hide().map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

/// Broadcast an emotion-state change so the presence window's sprite can
/// update. Payload is a string ("neutral" | "happy" | "thinking" |
/// "listening" | "sad"); the frontend type-asserts it.
#[tauri::command]
fn emit_emotion(app: AppHandle, state: String) -> Result<(), String> {
    app.emit("emotion-changed", state).map_err(|e| e.to_string())?;
    Ok(())
}
