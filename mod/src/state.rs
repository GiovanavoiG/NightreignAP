//! Shared state between the AP task, the game poller and the overlay.
use crate::config::Config;
use once_cell::sync::OnceCell;
use parking_lot::Mutex;
use std::collections::{BTreeSet, HashMap, VecDeque};

#[derive(Debug, Clone, Default)]
pub struct SlotData {
    pub goal: i64,
    pub include_dlc: bool,
    pub expedition_locks: bool,
    pub nightfarer_shuffle: bool,
    pub remembrance_locks: i64,
    pub shifting_earth_locks: bool,
    pub death_link: bool,
    pub starting_nightfarer: String,
    /// AP location id -> game event flag id (0 = unknown / not yet reversed)
    pub location_flags: HashMap<i64, u32>,
}

#[derive(Debug, Default)]
pub struct Shared {
    pub config: Config,
    pub connected: bool,
    pub status: String,
    pub slot_data: SlotData,
    pub missing_locations: BTreeSet<i64>,
    pub checked_locations: BTreeSet<i64>,
    /// Item ids received from the server, in order. `applied` counts how many have been granted.
    pub items_received: Vec<i64>,
    pub applied: usize,
    pub pending_checks: VecDeque<i64>,
    pub pending_death: bool,
    pub goal_reached: bool,
    pub goal_sent: bool,
    pub log: VecDeque<String>,
    pub item_names: HashMap<i64, String>,
    pub location_names: HashMap<i64, String>,
}

static SHARED: OnceCell<Mutex<Shared>> = OnceCell::new();

pub fn init(config: Config) {
    let _ = SHARED.set(Mutex::new(Shared { config, status: "disconnected".into(), ..Default::default() }));
}

pub fn shared() -> &'static Mutex<Shared> {
    SHARED.get().expect("state not initialised")
}

pub fn push_log(msg: impl Into<String>) {
    let mut s = shared().lock();
    s.log.push_back(msg.into());
    while s.log.len() > 200 { s.log.pop_front(); }
}
