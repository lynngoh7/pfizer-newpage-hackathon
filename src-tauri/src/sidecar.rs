//! Spawns and supervises the Python backend.
//!
//! The launcher (this process) is the only party that knows the session token:
//! it generates it, hands it to the backend via environment variable, and hands
//! it to the webview via the `get_session` command. The backend binds to
//! 127.0.0.1 only and rejects any request without the token.

use rand::RngCore;
use serde::Serialize;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::time::Duration;
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

/// 32 random bytes as hex (64 chars). New every launch, never saved.
fn random_token() -> String {
    let mut bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

/// Ask the OS for an unused localhost port (port 0 = "any free one"), then
/// release it for the backend to bind. A random port avoids clashes with
/// other apps and with a second copy of this one.
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
        #[cfg_attr(not(windows), allow(unused_mut))]
        let mut cmd = Command::new(bin);
        // The backend is a console program; without this flag Windows opens
        // an empty terminal window next to the app.
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }
        return Some(cmd);
    }
    if cfg!(debug_assertions) {
        let backend_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../backend");
        let venv_python = if cfg!(windows) {
            backend_dir.join(".venv/Scripts/python.exe")
        } else {
            backend_dir.join(".venv/bin/python")
        };
        let python = if venv_python.exists() {
            venv_python
        } else {
            PathBuf::from(if cfg!(windows) { "python" } else { "python3" })
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
                // `tauri dev` loads the UI from the Vite server, so the backend
                // must accept that origin. Release builds never set this.
                .env("NOTES_DEV", if cfg!(debug_assertions) { "1" } else { "0" })
                .stdin(Stdio::null())
                // Backend logs appear in the same terminal as `tauri dev`.
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

    /// Ask the backend to unload the Ollama model before it is killed, so the
    /// model keeps no context after quit (One Rule: no copies). Plain HTTP on
    /// 127.0.0.1 with the session token; best effort, 5 s at most.
    fn unload_model(&self) {
        let addr = SocketAddr::from(([127, 0, 0, 1], self.session.port));
        let Ok(mut s) = TcpStream::connect_timeout(&addr, Duration::from_secs(1)) else { return };
        let _ = s.set_read_timeout(Some(Duration::from_secs(5)));
        let req = format!(
            "POST /api/engine/unload HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer {}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
            self.session.token
        );
        if s.write_all(req.as_bytes()).is_ok() {
            let _ = s.read(&mut [0u8; 256]); // wait for the reply, ignore it
        }
    }

    pub fn stop(&self) {
        if let Some(mut c) = self.child.lock().unwrap().take() {
            self.unload_model();
            terminate(&mut c);
        }
    }
}

/// Stop the backend and wait for it. The packaged backend is a PyInstaller
/// one-file binary: a launcher process plus the real Python child. SIGKILL on
/// the launcher orphans the child (it keeps running after quit), so send
/// SIGTERM first, which the launcher forwards to the child and then cleans up
/// its unpacked temp folder. SIGKILL only if it is still alive after 3 s.
/// Windows has no SIGTERM, and killing only the launcher orphans the child,
/// so kill the whole process tree with taskkill /T.
fn terminate(c: &mut Child) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let _ = Command::new("taskkill")
            .args(["/PID", &c.id().to_string(), "/T", "/F"])
            .creation_flags(0x0800_0000) // CREATE_NO_WINDOW
            .status();
    }
    #[cfg(unix)]
    {
        // SAFETY: plain kill(2) on our own child's pid.
        unsafe { libc::kill(c.id() as libc::pid_t, libc::SIGTERM) };
        for _ in 0..30 {
            if let Ok(Some(_)) = c.try_wait() {
                return;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
    }
    let _ = c.kill();
    let _ = c.wait();
}

// Safety net: if the app exits without the Exit event, still kill the backend.
impl Drop for Backend {
    fn drop(&mut self) {
        self.stop();
    }
}
