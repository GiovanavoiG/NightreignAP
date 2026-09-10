//! Game-side integration. Everything that touches nightreign.exe memory lives here.
//!
//! `fromsoftware-rs`'s `nightreign` crate currently ships param bindings only; the runtime
//! singletons (`CSEventFlagMan`, `GameDataMan`, `WorldChrMan`) are declared in `singletons.rs`
//! as thin structs over the FD4 singleton finder from `fromsoftware-shared`, using the Elden Ring
//! layouts as the starting hypothesis. Each offset is tagged TODO(RE) until verified with the
//! Hexinton CE table / Ghidra on the current patch.
pub mod flags;
pub mod grant;
pub mod locks;
pub mod singletons;

use crate::state::{push_log, shared};
use std::thread;
use std::time::Duration;

pub fn init() -> Result<(), String> {
    singletons::init()?;
    locks::install_hooks()?;
    Ok(())
}

/// Polls event flags for new checks and applies received items, on a background thread.
/// Anything that must run on the game thread is queued through `locks::run_on_game_thread`.
pub fn spawn_poller() {
    thread::spawn(|| {
        let interval = Duration::from_millis(shared().lock().config.behaviour.poll_interval_ms.max(100));
        loop {
            thread::sleep(interval);
            let connected = shared().lock().connected;
            if !connected || !singletons::in_game() { continue; }

            // 1) checks
            let candidates: Vec<(i64, u32)> = {
                let s = shared().lock();
                s.missing_locations.iter().filter_map(|id| s.slot_data.location_flags.get(id).map(|f| (*id, *f)))
                    .filter(|(_, f)| *f != 0).collect()
            };
            for (id, flag) in candidates {
                if flags::is_set(flag) {
                    let mut s = shared().lock();
                    if s.missing_locations.remove(&id) {
                        s.pending_checks.push_back(id);
                        let name = s.location_names.get(&id).cloned().unwrap_or_else(|| id.to_string());
                        drop(s);
                        push_log(format!("check: {name}"));
                    }
                }
            }
            // Goal
            {
                let mut s = shared().lock();
                if !s.goal_reached && flags::goal_reached(&s.slot_data) { s.goal_reached = true; }
            }

            // 2) items
            loop {
                let next = {
                    let s = shared().lock();
                    if s.applied < s.items_received.len() { Some(s.items_received[s.applied]) } else { None }
                };
                let Some(item) = next else { break };
                match grant::apply(item) {
                    Ok(()) => {
                        let mut s = shared().lock();
                        s.applied += 1;
                        let name = s.item_names.get(&item).cloned().unwrap_or_else(|| item.to_string());
                        let toasts = s.config.behaviour.toasts;
                        drop(s);
                        push_log(format!("received: {name}"));
                        if toasts { crate::overlay::toast(format!("Received {name}")); }
                    }
                    Err(grant::GrantError::NotNow) => break,   // e.g. mid-expedition; retry later
                    Err(grant::GrantError::Unknown(e)) => {
                        push_log(format!("cannot grant {item}: {e}"));
                        shared().lock().applied += 1;
                    }
                }
            }

            // 3) locks (cheap; re-evaluated every tick so they follow item receipt)
            locks::refresh();

            // 4) death detection for DeathLink
            if shared().lock().slot_data.death_link && singletons::player_just_died() {
                shared().lock().pending_death = true;
            }
        }
    });
}
