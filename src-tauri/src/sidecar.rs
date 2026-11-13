//! Spawns and supervises the Python backend.
//!
//! The launcher (this process) is the only party that knows the session token:
//! it generates it, hands it to the backend via environment variable, and hands
//! it to the webview via the `get_session` command. The backend binds to
//! 127.0.0.1 only and rejects any request without the token.

use rand::RngCore;
use serde::Serialize;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

#[derive(Clone, Serialize)]
pub struct Session {
    pub port: u16,
    pub token: String,
}

pub struct Backend {
    pub session: Session,
    child: Mutex<Option<Child>>,
}

fn random_token() -> String {
    let mut bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|a| a.port())
        .expect("could not find a free localhost port")
}

/// Locate the packaged PyInstaller binary next to the app executable.
fn packaged_binary() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;
    let name = if cfg!(windows) { "notes-backend.exe" } else { "notes-backend" };
    let candidate = dir.join(name);
    candidate.exists().then_some(candidate)
}

/// Build the command for the backend. Packaged binary if present; otherwise,
/// in debug builds only, run the Python sources directly for development.
fn backend_command() -> Option<Command> {
    if let Some(bin) = packaged_binary() {
        return Some(Command::new(bin));
    }
    if cfg!(debug_assertions) {
        let backend_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../backend");
        let venv_python = backend_dir.join(".venv/bin/python");
        let python = if venv_python.exists() {
            venv_python
        } else {
            PathBuf::from("python3")
        };
        let mut cmd = Command::new(python);
        cmd.arg("-m").arg("app.main").current_dir(backend_dir);
        return Some(cmd);
    }
    None
}

impl Backend {
    pub fn start() -> Self {
        let session = Session { port: free_port(), token: random_token() };
        let child = backend_command().and_then(|mut cmd| {
            cmd.env("NOTES_SESSION_TOKEN", &session.token)
                .env("NOTES_PORT", session.port.to_string())
                .stdin(Stdio::null())
                .stdout(Stdio::inherit())
                .stderr(Stdio::inherit());
            match cmd.spawn() {
                Ok(c) => Some(c),
                Err(e) => {
                    eprintln!("failed to start backend: {e}");
                    None
                }
            }
        });
        if child.is_none() {
            eprintln!("backend not started; the UI will show the engine as offline");
        }
        Backend { session, child: Mutex::new(child) }
    }

    pub fn stop(&self) {
        if let Some(mut c) = self.child.lock().unwrap().take() {
            let _ = c.kill();
            let _ = c.wait();
        }
    }
}

impl Drop for Backend {
    fn drop(&mut self) {
        self.stop();
    }
}
