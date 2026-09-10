//! Archipelago network task (archipelago_rs).
//!
//! The exact `archipelago_rs` API surface changes between minor versions; this module isolates it.
//! Pinned in Cargo.toml to the same version the DS3 4.x client uses so the calls below match its usage.
use crate::state::{push_log, shared};
use once_cell::sync::OnceCell;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;
use tokio::runtime::Runtime;

pub const GAME: &str = "Elden Ring Nightreign";
pub const BASE_ID: i64 = 2_622_380_000;

static RUNTIME: OnceCell<Runtime> = OnceCell::new();
static STOP: AtomicBool = AtomicBool::new(false);
static RECONNECT: AtomicBool = AtomicBool::new(false);

/// Called by the overlay after the user edits server/slot.
pub fn request_reconnect() { RECONNECT.store(true, Ordering::SeqCst); }

pub fn shutdown() { STOP.store(true, Ordering::SeqCst); }

pub fn spawn_client() {
    let rt = RUNTIME.get_or_init(|| tokio::runtime::Builder::new_multi_thread().worker_threads(2).enable_all().build().unwrap());
    rt.spawn(async {
        loop {
            if STOP.load(Ordering::SeqCst) { break; }
            let cfg = shared().lock().config.clone();
            if cfg.slot.is_empty() {
                tokio::time::sleep(Duration::from_secs(1)).await;
                if RECONNECT.swap(false, Ordering::SeqCst) { continue; }
                continue;
            }
            match session(&cfg.server, &cfg.slot, &cfg.password).await {
                Ok(()) => push_log("disconnected"),
                Err(e) => { push_log(format!("connection error: {e}")); }
            }
            {
                let mut s = shared().lock();
                s.connected = false;
                s.status = "disconnected".into();
            }
            // wait for reconnect request or retry after a delay
            for _ in 0..50 {
                if RECONNECT.swap(false, Ordering::SeqCst) || STOP.load(Ordering::SeqCst) { break; }
                tokio::time::sleep(Duration::from_millis(100)).await;
            }
        }
    });
}

async fn session(server: &str, slot: &str, password: &str) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use archipelago_rs::client::ArchipelagoClient;
    use archipelago_rs::protocol::{ClientStatus, ServerMessage};

    let url = if server.starts_with("ws") { server.to_string() } else { format!("wss://{server}") };
    { let mut s = shared().lock(); s.status = format!("connecting to {url}"); }

    let mut client = match ArchipelagoClient::new(&url).await {
        Ok(c) => c,
        Err(_) => ArchipelagoClient::new(&url.replacen("wss://", "ws://", 1)).await?,
    };

    // Cache data package names for the overlay / toasts.
    if let Some(dp) = client.data_package() {
        if let Some(game) = dp.games.get(GAME) {
            let mut s = shared().lock();
            s.item_names = game.item_name_to_id.iter().map(|(n, id)| (*id, n.clone())).collect();
            s.location_names = game.location_name_to_id.iter().map(|(n, id)| (*id, n.clone())).collect();
        }
    }

    let pw = if password.is_empty() { None } else { Some(password) };
    let connected = client.connect(GAME, slot, pw, Some(0b111), vec!["AP".into()]).await?;

    {
        let mut s = shared().lock();
        s.connected = true;
        s.status = format!("connected as {slot}");
        s.missing_locations = connected.missing_locations.iter().copied().collect();
        s.checked_locations = connected.checked_locations.iter().copied().collect();
        s.slot_data = parse_slot_data(&connected.slot_data);
        s.applied = 0;
        s.items_received.clear();
        if s.slot_data.death_link {
            let _ = client.update_tags(vec!["AP".into(), "DeathLink".into()]);
        }
    }
    push_log(format!("connected to {url} as {slot}"));

    loop {
        if STOP.load(Ordering::SeqCst) || RECONNECT.load(Ordering::SeqCst) { return Ok(()); }

        // Outgoing: checks, goal, deathlink
        let (checks, goal, death) = {
            let mut s = shared().lock();
            let checks: Vec<i64> = s.pending_checks.drain(..).collect();
            let goal = s.goal_reached && !s.goal_sent;
            if goal { s.goal_sent = true; }
            let death = s.pending_death && s.slot_data.death_link;
            s.pending_death = false;
            (checks, goal, death)
        };
        if !checks.is_empty() {
            client.location_checks(checks.clone()).await?;
            let mut s = shared().lock();
            for c in checks { s.checked_locations.insert(c); s.missing_locations.remove(&c); }
        }
        if goal { client.status_update(ClientStatus::ClientGoal).await?; push_log("goal sent"); }
        if death {
            let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)?.as_secs_f64();
            let data = serde_json::json!({"time": now, "source": slot, "cause": format!("{slot} fell to the Night")});
            client.bounce(None, None, Some(vec!["DeathLink".into()]), data).await?;
        }

        // Incoming
        match tokio::time::timeout(Duration::from_millis(200), client.recv()).await {
            Ok(Ok(Some(msg))) => handle(msg),
            Ok(Ok(None)) => return Ok(()),
            Ok(Err(e)) => return Err(e.into()),
            Err(_) => {}
        }
    }
}

fn handle(msg: archipelago_rs::protocol::ServerMessage) {
    use archipelago_rs::protocol::ServerMessage;
    match msg {
        ServerMessage::ReceivedItems(ri) => {
            let mut s = shared().lock();
            if ri.index == 0 { s.items_received.clear(); s.applied = 0; }
            for it in ri.items { s.items_received.push(it.item); }
        }
        ServerMessage::Bounced(b) => {
            if b.tags.iter().any(|t| t == "DeathLink") {
                let mut s = shared().lock();
                if s.slot_data.death_link { crate::game::grant::queue_death(&mut s); }
            }
        }
        ServerMessage::PrintJSON(p) => {
            let text: String = p.data.iter().map(|d| d.text.clone()).collect();
            push_log(text);
        }
        ServerMessage::RoomUpdate(ru) => {
            if let Some(checked) = ru.checked_locations {
                let mut s = shared().lock();
                for c in checked { s.checked_locations.insert(c); s.missing_locations.remove(&c); }
            }
        }
        _ => {}
    }
}

fn parse_slot_data(v: &serde_json::Value) -> crate::state::SlotData {
    let g = |k: &str| v.get(k).and_then(|x| x.as_i64()).unwrap_or(0);
    let b = |k: &str| g(k) != 0;
    let mut sd = crate::state::SlotData {
        goal: g("goal"),
        include_dlc: b("dlc_forsaken_hollows"),
        expedition_locks: b("expedition_locks"),
        nightfarer_shuffle: b("nightfarer_shuffle"),
        remembrance_locks: g("remembrance_locks"),
        shifting_earth_locks: b("shifting_earth_locks"),
        death_link: b("death_link"),
        starting_nightfarer: v.get("starting_nightfarer").and_then(|x| x.as_str()).unwrap_or("").to_string(),
        location_flags: Default::default(),
    };
    if let Some(obj) = v.get("location_flags").and_then(|x| x.as_object()) {
        for (k, val) in obj {
            if let (Ok(id), Some(flag)) = (k.parse::<i64>(), val.as_u64()) { sd.location_flags.insert(id, flag as u32); }
        }
    }
    sd
}
