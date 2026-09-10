//! Archipelago client for Elden Ring: Nightreign.
//!
//! Loaded as a native DLL by Mod Engine 3. Responsibilities:
//!  * connect to an Archipelago server (archipelago_rs)
//!  * detect checks by reading `CSEventFlagMan` flags on a timer (`game::flags`)
//!  * grant items by calling the game's item-give routine and by setting flags (`game::grant`)
//!  * enforce expedition / Nightfarer / Shifting Earth locks (`game::locks`)
//!  * draw an ImGui overlay (hudhook) for connection settings and item log (`overlay`)
//!
//! Layout mirrors fswap/from-software-archipelago-clients so this can later become
//! `crates/nr-archipelago` in that workspace.

#![allow(clippy::missing_safety_doc)]

mod ap;
mod config;
mod game;
mod overlay;
mod state;

use std::thread;
use windows::Win32::Foundation::{BOOL, HINSTANCE, TRUE};
use windows::Win32::System::SystemServices::{DLL_PROCESS_ATTACH, DLL_PROCESS_DETACH};

#[no_mangle]
#[allow(non_snake_case)]
pub unsafe extern "system" fn DllMain(_hinst: HINSTANCE, reason: u32, _reserved: *mut ()) -> BOOL {
    match reason {
        DLL_PROCESS_ATTACH => {
            thread::spawn(|| {
                config::init_logging();
                tracing::info!("nightreign-archipelago {} starting", env!("CARGO_PKG_VERSION"));
                let cfg = config::load();
                state::init(cfg);
                if let Err(e) = game::init() {
                    tracing::error!("game init failed: {e}");
                }
                overlay::install();
                ap::spawn_client();
                game::spawn_poller();
            });
        }
        DLL_PROCESS_DETACH => {
            ap::shutdown();
        }
        _ => {}
    }
    TRUE
}
