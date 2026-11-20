//! Tauri entry. Starts the backend before the window opens, exposes a single
//! `get_session` command so the webview can learn the port and token, and
//! stops the backend when the app exits. Add new commands to the
//! `generate_handler!` list; the webview has no other way into Rust.

mod sidecar;

use sidecar::{Backend, Session};
use tauri::{Manager, RunEvent, State};

// A "command" is a Rust function the webview can call with invoke("get_session").
#[tauri::command]
fn get_session(backend: State<'_, Backend>) -> Session {
    backend.session.clone()
}

pub fn run() {
    let backend = Backend::start();

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(backend) // makes `Backend` available to commands as State
        .invoke_handler(tauri::generate_handler![get_session])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                app.state::<Backend>().stop();
            }
        });
}
