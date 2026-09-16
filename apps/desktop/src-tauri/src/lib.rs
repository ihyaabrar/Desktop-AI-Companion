/// Tauri shell for the Desktop AI Companion.
///
/// M3 introduces the second "presence" window: a small, transparent,
/// always-on-top sprite that the user can position freely. The chat-panel
/// window stays the primary surface; the presence window forwards user
/// intent (clicks, drag) and listens for `emotion-changed` events emitted
/// from the chat side.
use std::{
    io::{self, Read, Write},
    net::{SocketAddr, TcpStream},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::{Duration, Instant},
};

use tauri::{AppHandle, Emitter, Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

const SIDECAR_HOST: &str = "127.0.0.1";
const SIDECAR_PORT: u16 = 8765;
const SIDECAR_STARTUP_TIMEOUT: Duration = Duration::from_secs(15);
const SIDECAR_POLL_INTERVAL: Duration = Duration::from_millis(200);

/// The child is present only when this app launched it. A manually started
/// sidecar is reused and deliberately left alone at shutdown.
#[derive(Clone, Default)]
struct SidecarState(Arc<Mutex<Option<SidecarChild>>>);

enum SidecarChild {
    Development(Child),
    Bundled(CommandChild),
}

pub fn run() {
    let app = tauri::Builder::default()
        .manage(SidecarState::default())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let state = app.state::<SidecarState>();
            start_sidecar(&app.handle(), &state)
                .map_err(|error| -> Box<dyn std::error::Error> { Box::new(error) })?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ping,
            show_main,
            set_presence_visible,
            emit_emotion,
        ])
        .build(tauri::generate_context!())
        .expect("error while building Tauri application");

    app.run(|app_handle, event| {
        // `ExitRequested` can be cancelled by another lifecycle handler. Wait
        // for `Exit` so we never terminate the sidecar while the app remains open.
        if matches!(event, RunEvent::Exit) {
            let state = app_handle.state::<SidecarState>();
            stop_sidecar(&state);
        }
    });
}

/// Starts the development sidecar and waits until its HTTP health endpoint is
/// responsive. If the user already launched one on the configured port, reuse
/// it instead of creating a competing process.
fn start_sidecar(app: &AppHandle, state: &SidecarState) -> io::Result<()> {
    if sidecar_is_healthy() {
        log::info!("reusing an existing Companion sidecar on port {SIDECAR_PORT}");
        return Ok(());
    }

    let child = if cfg!(debug_assertions) {
        start_development_sidecar()?
    } else {
        start_bundled_sidecar(app)?
    };
    *state.0.lock().expect("sidecar state lock poisoned") = Some(child);
    wait_for_sidecar(state)
}

fn start_development_sidecar() -> io::Result<SidecarChild> {
    let sidecar_dir = source_sidecar_dir();
    if !sidecar_dir.is_dir() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("Companion sidecar source was not found at {}", sidecar_dir.display()),
        ));
    }

    let port = SIDECAR_PORT.to_string();
    let child = Command::new("uv")
        .args([
            "run",
            "uvicorn",
            "companion.main:app",
            "--host",
            SIDECAR_HOST,
            "--port",
            &port,
        ])
        .current_dir(&sidecar_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| {
            io::Error::new(
                error.kind(),
                format!("could not start the sidecar with `uv`: {error}. Install uv and run `uv sync` in apps/sidecar"),
            )
        })?;

    Ok(SidecarChild::Development(child))
}

fn start_bundled_sidecar(app: &AppHandle) -> io::Result<SidecarChild> {
    let port = SIDECAR_PORT.to_string();
    let (_, child) = app
        .shell()
        .sidecar("companion-sidecar")
        .map_err(|error| io::Error::other(format!("could not find bundled sidecar: {error}")))?
        .args(["--host", SIDECAR_HOST, "--port", &port])
        .spawn()
        .map_err(|error| io::Error::other(format!("could not start bundled sidecar: {error}")))?;
    Ok(SidecarChild::Bundled(child))
}

fn source_sidecar_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .expect("src-tauri should be nested in apps/desktop")
        .join("sidecar")
}

fn wait_for_sidecar(state: &SidecarState) -> io::Result<()> {
    let deadline = Instant::now() + SIDECAR_STARTUP_TIMEOUT;
    while Instant::now() < deadline {
        if sidecar_is_healthy() {
            log::info!("Companion sidecar is ready on port {SIDECAR_PORT}");
            return Ok(());
        }

        if let Some(SidecarChild::Development(child)) =
            state.0.lock().expect("sidecar state lock poisoned").as_mut()
        {
            if let Some(status) = child.try_wait()? {
                return Err(io::Error::other(format!(
                    "Companion sidecar exited during startup with status {status}"
                )));
            }
        }
        thread::sleep(SIDECAR_POLL_INTERVAL);
    }

    stop_sidecar(state);
    Err(io::Error::new(
        io::ErrorKind::TimedOut,
        "Companion sidecar did not become healthy within 15 seconds",
    ))
}

fn sidecar_is_healthy() -> bool {
    let address = SocketAddr::from(([127, 0, 0, 1], SIDECAR_PORT));
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(250)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));
    if stream
        .write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .is_err()
    {
        return false;
    }

    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok() && response.starts_with("HTTP/1.1 200")
}

fn stop_sidecar(state: &SidecarState) {
    let mut child = state.0.lock().expect("sidecar state lock poisoned").take();
    if let Some(child) = child.as_mut() {
        let result = match child {
            SidecarChild::Development(child) => {
                let result = child.kill();
                let _ = child.wait();
                result
            }
            SidecarChild::Bundled(child) => child.kill(),
        };
        if let Err(error) = result {
            // The process may already have exited, which needs no recovery.
            log::debug!("could not stop Companion sidecar: {error}");
        }
    }
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
