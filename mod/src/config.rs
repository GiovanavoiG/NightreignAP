use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub server: String,
    pub slot: String,
    #[serde(default)]
    pub password: String,
    #[serde(default)]
    pub overlay: Overlay,
    #[serde(default)]
    pub behaviour: Behaviour,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Overlay {
    pub toggle_key: String,
}
impl Default for Overlay {
    fn default() -> Self { Self { toggle_key: "F9".into() } }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Behaviour {
    pub poll_interval_ms: u64,
    pub toasts: bool,
}
impl Default for Behaviour {
    fn default() -> Self { Self { poll_interval_ms: 500, toasts: true } }
}

impl Default for Config {
    fn default() -> Self {
        Self { server: "archipelago.gg:38281".into(), slot: String::new(), password: String::new(),
               overlay: Overlay::default(), behaviour: Behaviour::default() }
    }
}

pub fn mod_dir() -> PathBuf {
    // The DLL lives next to archipelago.toml inside the me3 mod folder.
    use windows::Win32::System::LibraryLoader::{GetModuleFileNameW, GetModuleHandleExW,
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT};
    use windows::core::PCWSTR;
    unsafe {
        let mut hmod = Default::default();
        let _ = GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                   PCWSTR(mod_dir as *const () as *const u16), &mut hmod);
        let mut buf = [0u16; 1024];
        let n = GetModuleFileNameW(hmod, &mut buf) as usize;
        let path = String::from_utf16_lossy(&buf[..n]);
        PathBuf::from(path).parent().map(|p| p.to_path_buf()).unwrap_or_default()
    }
}

pub fn load() -> Config {
    let path = mod_dir().join("archipelago.toml");
    match std::fs::read_to_string(&path) {
        Ok(s) => toml::from_str(&s).unwrap_or_else(|e| { tracing::warn!("bad archipelago.toml: {e}"); Config::default() }),
        Err(_) => Config::default(),
    }
}

pub fn save(cfg: &Config) {
    if let Ok(s) = toml::to_string_pretty(cfg) {
        let _ = std::fs::write(mod_dir().join("archipelago.toml"), s);
    }
}

pub fn init_logging() {
    let appender = tracing_appender::rolling::never(mod_dir(), "nightreign-archipelago.log");
    let (nb, guard) = tracing_appender::non_blocking(appender);
    std::mem::forget(guard);
    let _ = tracing_subscriber::fmt().with_writer(nb).with_ansi(false).try_init();
}
