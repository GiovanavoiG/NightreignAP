//! ImGui overlay via hudhook: connection form, status, item/check log, toasts.
use crate::state::{push_log, shared};
use hudhook::imgui::{Condition, Ui};
use hudhook::{ImguiRenderLoop, Hudhook};
use hudhook::hooks::dx12::ImguiDx12Hooks;
use parking_lot::Mutex;
use std::collections::VecDeque;
use std::time::{Duration, Instant};

static TOASTS: Mutex<VecDeque<(String, Instant)>> = Mutex::new(VecDeque::new());

pub fn toast(text: String) {
    TOASTS.lock().push_back((text, Instant::now()));
}

struct Overlay {
    visible: bool,
    server: String,
    slot: String,
    password: String,
}

impl ImguiRenderLoop for Overlay {
    fn initialize<'a>(&'a mut self, _ctx: &mut hudhook::imgui::Context, _r: &'a mut dyn hudhook::RenderContext) {
        let cfg = shared().lock().config.clone();
        self.server = cfg.server; self.slot = cfg.slot; self.password = cfg.password;
    }

    fn render(&mut self, ui: &mut Ui) {
        if ui.is_key_pressed(hudhook::imgui::Key::F9) { self.visible = !self.visible; }

        // Toasts (always drawn)
        {
            let mut t = TOASTS.lock();
            while t.front().map(|(_, at)| at.elapsed() > Duration::from_secs(4)).unwrap_or(false) { t.pop_front(); }
            let mut y = 40.0;
            for (text, _) in t.iter() {
                ui.window(format!("##toast{y}")).position([30.0, y], Condition::Always).no_decoration().bg_alpha(0.6)
                    .always_auto_resize(true).build(|| ui.text(text));
                y += 34.0;
            }
        }
        if !self.visible { return; }

        ui.window("Archipelago").size([460.0, 420.0], Condition::FirstUseEver).build(|| {
            let status = shared().lock().status.clone();
            ui.text(format!("Status: {status}"));
            ui.separator();
            ui.input_text("Server", &mut self.server).build();
            ui.input_text("Slot", &mut self.slot).build();
            ui.input_text("Password", &mut self.password).password(true).build();
            if ui.button("Connect") {
                {
                    let mut s = shared().lock();
                    s.config.server = self.server.clone();
                    s.config.slot = self.slot.clone();
                    s.config.password = self.password.clone();
                    crate::config::save(&s.config);
                }
                crate::ap::request_reconnect();
                push_log("reconnecting...");
            }
            ui.same_line();
            if ui.button("Resync items") { shared().lock().applied = 0; }
            ui.separator();
            let (checked, missing, items, applied) = {
                let s = shared().lock();
                (s.checked_locations.len(), s.missing_locations.len(), s.items_received.len(), s.applied)
            };
            ui.text(format!("Checks: {checked} done / {missing} remaining    Items: {applied}/{items} applied"));
            ui.separator();
            ui.child_window("log").build(|| {
                for line in shared().lock().log.iter().rev() { ui.text_wrapped(line); }
            });
        });
    }
}

pub fn install() {
    let overlay = Overlay { visible: true, server: String::new(), slot: String::new(), password: String::new() };
    if let Err(e) = Hudhook::builder().with::<ImguiDx12Hooks>(overlay).build().apply() {
        tracing::error!("hudhook failed: {e:?}");
    }
}
