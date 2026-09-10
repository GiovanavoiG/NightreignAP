from . import NightreignTestBase


class TestDefault(NightreignTestBase):
    options = {"starting_nightfarer": "wylder", "remembrance_locks": "progressive"}

    def test_tricephalos_open_at_start(self):
        self.assertTrue(self.can_reach_region("Expedition: Tricephalos"))
        self.assertFalse(self.can_reach_region("Expedition: Gaping Jaw"))

    def test_expedition_access(self):
        self.collect_by_name("Expedition Access: Gaping Jaw")
        self.assertTrue(self.can_reach_region("Expedition: Gaping Jaw"))

    def test_night_aspect_requires_seven(self):
        self.collect_all_but(["Expedition Access: Fissure in the Fog", "Fissure in the Fog Cleared"])
        self.assertFalse(self.can_reach_region("Expedition: Night Aspect"))
        self.collect_by_name("Expedition Access: Fissure in the Fog")
        self.multiworld.state.sweep_for_advancements()
        self.assertTrue(self.can_reach_region("Expedition: Night Aspect"))

    def test_remembrance_progressive(self):
        loc = "Remembrance: Wylder - Chapter 3"
        items = self.get_items_by_name("Progressive Remembrance: Wylder")
        self.collect(items[:2])
        self.assertFalse(self.can_reach_location(loc))
        self.collect(items[2])
        self.assertTrue(self.can_reach_location(loc))

    def test_other_nightfarer_locked(self):
        self.assertFalse(self.can_reach_location("Remembrance: Guardian - Chapter 1"))


class TestDlcEverything(NightreignTestBase):
    options = {"dlc_forsaken_hollows": True, "deep_of_night_checks": True, "per_run_checks": True, "run_challenge_pool": "extended", "goal": "all_nightlords"}


class TestNoLocks(NightreignTestBase):
    options = {"expedition_locks": False, "nightfarer_shuffle": False, "remembrance_locks": "none",
               "shifting_earth_locks": False, "vessel_checks": False}


class TestRemembranceKeys(NightreignTestBase):
    options = {"starting_nightfarer": "wylder", "remembrance_locks": "key"}

    def test_key_unlocks_all_chapters(self):
        self.assertFalse(self.can_reach_location("Remembrance: Wylder - Chapter 1"))
        self.collect_by_name("Remembrance Key: Wylder")
        self.assertTrue(self.can_reach_location("Remembrance: Wylder - Chapter 1"))
        self.assertTrue(self.can_reach_location("Remembrance: Wylder - Chapter 9"))
