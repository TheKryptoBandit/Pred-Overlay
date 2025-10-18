# ui.py
import tkinter as tk
from tkinter import ttk, font
import json
import os
import requests
from PIL import Image, ImageTk
import io
import shutil
import sys

API_BASE_URL = "https://omeda.city"

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

BUILDS_FILE = os.path.join(application_path, "predecessor_builds_v2.json")
CACHE_FOLDER = os.path.join(application_path, "app_cache")
IMAGE_CACHE_FOLDER = os.path.join(CACHE_FOLDER, "images")
HEROES_JSON_FILE = os.path.join(CACHE_FOLDER, "heroes.json")
ITEMS_JSON_FILE = os.path.join(CACHE_FOLDER, "items.json")

LANES = ['Carry', 'Support', 'Midlane', 'Offlane', 'Jungle']
MAX_BUILD_ITEMS = 6
BG_COLOR = "#111827"
FG_COLOR = "#F9FAFB"
ACCENT_COLOR = "#3B82F6"
FRAME_COLOR = "#1F2937"
TRANSPARENT_COLOR = "#010101"
RARITY_COLORS = {"Common": "#9CA3AF", "Uncommon": "#22C55E", "Rare": "#3B82F6", "Epic": "#A855F7", "Legendary": "#F97316", "Default": "#4B5563"}

class DataHandler:
    def __init__(self):
        self.heroes = []
        self.items = []
        self.base_crests = []
        self.crest_evolution_map = {}
        self.image_cache = {}
        os.makedirs(IMAGE_CACHE_FOLDER, exist_ok=True)
        self.fetch_game_data()

    def fetch_game_data(self):
        api_heroes, api_items = None, None
        if os.path.exists(HEROES_JSON_FILE) and os.path.exists(ITEMS_JSON_FILE):
            try:
                with open(HEROES_JSON_FILE, 'r', encoding='utf-8') as f: api_heroes = json.load(f)
                with open(ITEMS_JSON_FILE, 'r', encoding='utf-8') as f: api_items = json.load(f)
            except json.JSONDecodeError: api_heroes, api_items = None, None
        if not api_heroes or not api_items:
            try:
                heroes_res = requests.get(f"{API_BASE_URL}/heroes.json")
                items_res = requests.get(f"{API_BASE_URL}/items.json")
                heroes_res.raise_for_status(); items_res.raise_for_status()
                api_heroes, api_items = heroes_res.json(), items_res.json()
                with open(HEROES_JSON_FILE, 'w', encoding='utf-8') as f: json.dump(api_heroes, f)
                with open(ITEMS_JSON_FILE, 'w', encoding='utf-8') as f: json.dump(api_items, f)
            except requests.RequestException as e: print(f"FATAL ERROR: Could not fetch game data: {e}.")
        self.heroes = sorted([{'id': h['name'].lower(), 'name': h['display_name'], 'icon': h['image']} for h in api_heroes], key=lambda x: x['name'])
        all_items_full_data = [i for i in api_items if i.get('display_name')]
        crests_full_data = [item for item in all_items_full_data if item.get('slot_type') == 'Crest']
        EXCLUDED_SLOT_TYPES = ["Crest", "Trinket", "Consumable", "Potion", "Active"]
        EXCLUDED_RARITIES = ["Common", "Uncommon", "Rare"]
        self.items = [i for i in all_items_full_data if i.get('slot_type') not in EXCLUDED_SLOT_TYPES and i.get('rarity') not in EXCLUDED_RARITIES]
        self.items = [{'id': i['name'].lower(), 'name': i['display_name'], 'icon': i['image'], 'hero_class': i.get('hero_class'), 'rarity': i.get('rarity')} for i in self.items]
        self.base_crests, self.crest_evolution_map = [], {}
        crest_map_by_internal_name = {c['name']: c for c in crests_full_data}
        all_children_internal_names = set()
        for crest in crests_full_data:
            for req in crest.get('requirements', []):
                if req in crest_map_by_internal_name:
                    if req not in self.crest_evolution_map: self.crest_evolution_map[req] = []
                    self.crest_evolution_map[req].append({'id': crest['name'].lower(), 'name': crest['display_name'], 'icon': crest['image'], 'internal_name': crest['name']})
                    all_children_internal_names.add(crest['name'])
        for crest in crests_full_data:
            if crest['name'] not in all_children_internal_names:
                self.base_crests.append({'id': crest['name'].lower(), 'name': crest['display_name'], 'icon': crest['image'], 'internal_name': crest['name']})
        self.base_crests.sort(key=lambda x: x['name'])

    def get_image(self, path, size):
        if not path: return self.get_placeholder(size)
        if (path, size) in self.image_cache: return self.image_cache.get((path, size))
        local_path = os.path.join(IMAGE_CACHE_FOLDER, path.lstrip('/'))
        if os.path.exists(local_path):
            try:
                img = Image.open(local_path).resize(size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_cache[(path, size)] = photo
                return photo
            except Exception: pass
        try:
            url = f"{API_BASE_URL}{path}"
            response = requests.get(url, stream=True)
            response.raise_for_status()
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f: shutil.copyfileobj(response.raw, f)
            img = Image.open(local_path).resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_cache[(path, size)] = photo
            return photo
        except requests.RequestException: return self.get_placeholder(size)

    def get_placeholder(self, size):
        if ('placeholder', size) in self.image_cache: return self.image_cache.get(('placeholder', size))
        img = Image.new('RGBA', size, (50, 50, 50, 200))
        photo = ImageTk.PhotoImage(img)
        self.image_cache[('placeholder', size)] = photo
        return photo

class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, bg=kwargs.get('bg'), highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=kwargs.get('bg'))
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        def _on_mousewheel(event): canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
class App(tk.Tk):
    def __init__(self, data_handler):
        super().__init__()
        self.data = data_handler
        self.title("Predecessor Overlay Control Panel")
        self.geometry("1000x800+100+100")
        self.overrideredirect(True) 
        self.wm_attributes("-topmost", True)
        self.config(bg=TRANSPARENT_COLOR)
        self.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.all_builds = self.load_builds()
        self.active_build, self.selected_hero, self.is_editing = None, None, False
        self.offset_x, self.offset_y = 0, 0
        self.main_frame = None
        self.display_expanded_view()
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)

    def on_click(self, event): self.offset_x, self.offset_y = event.x, event.y
    def on_drag(self, event): self.geometry(f"+{self.winfo_x() + event.x - self.offset_x}+{self.winfo_y() + event.y - self.offset_y}")
    def clear_main_frame(self):
        if self.main_frame: self.main_frame.destroy()
    def display_collapsed_view(self):
        self.clear_main_frame()
        self.geometry("550x80")
        self.main_frame = tk.Frame(self, bg=TRANSPARENT_COLOR, padx=8, pady=8)
        self.main_frame.pack(fill="both", expand=True)
        hero_icon = self.data.get_image(self.selected_hero['icon'], (64, 64))
        hero_icon_label = tk.Label(self.main_frame, image=hero_icon, bg=TRANSPARENT_COLOR); hero_icon_label.image = hero_icon
        hero_icon_label.pack(side="left")
        for item in self.active_build.get('items', []):
            item_icon = self.data.get_image(item['icon'], (48, 48))
            item_label = tk.Label(self.main_frame, image=item_icon, bg=TRANSPARENT_COLOR); item_label.image = item_icon
            item_label.pack(side="left", padx=2)
        if self.active_build.get('crest'):
            tk.Frame(self.main_frame, bg="gray", width=2, height=48).pack(side="left", padx=5)
            crest_icon = self.data.get_image(self.active_build['crest']['icon'], (48, 48))
            crest_label = tk.Label(self.main_frame, image=crest_icon, bg=TRANSPARENT_COLOR); crest_label.image = crest_icon
            crest_label.pack(side="left", padx=1)
        expand_btn = tk.Button(self.main_frame, text="EXPAND", bg=ACCENT_COLOR, fg=FG_COLOR, bd=0, command=self.display_expanded_view)
        expand_btn.pack(side="right", padx=10)
        
    def display_expanded_view(self):
        self.active_build, self.is_editing = None, False
        self.clear_main_frame()
        self.geometry("1000x800")
        self.main_frame = tk.Frame(self, bg=BG_COLOR); self.main_frame.pack(fill="both", expand=True)
        title_bar = tk.Frame(self.main_frame, bg=FRAME_COLOR); title_bar.pack(fill="x")
        tk.Label(title_bar, text="Predecessor Build Overlay", bg=FRAME_COLOR, fg=FG_COLOR).pack(side="left", padx=10)
        tk.Button(title_bar, text="X", bg="red", fg=FG_COLOR, bd=0, command=self.destroy).pack(side="right")
        content_frame = tk.Frame(self.main_frame, bg=BG_COLOR); content_frame.pack(fill="both", expand=True)
        self.hero_list_container = tk.Frame(content_frame, bg=BG_COLOR, width=192)
        self.hero_list_container.pack(side="left", fill="y", padx=5, pady=5); self.hero_list_container.pack_propagate(False)
        self.build_view_frame = tk.Frame(content_frame, bg=BG_COLOR); self.build_view_frame.pack(side="left", fill="both", expand=True)
        self.populate_hero_list()
        self.draw_build_area()
    
    def populate_hero_list(self):
        for widget in self.hero_list_container.winfo_children(): widget.destroy()
        scroll_area = ScrollableFrame(self.hero_list_container, bg=BG_COLOR)
        scroll_area.pack(fill="both", expand=True)
        for i, hero in enumerate(self.data.heroes):
            icon = self.data.get_image(hero['icon'], (64, 64))
            btn = tk.Button(scroll_area.scrollable_frame, image=icon, bg=FRAME_COLOR, relief=tk.RAISED, bd=1, command=lambda h=hero: self.select_hero(h))
            btn.image = icon
            btn.grid(row=i // 2, column=i % 2, padx=2, pady=2)
        
    def select_hero(self, hero): self.selected_hero, self.is_editing = hero, False; self.draw_build_area()
    def draw_build_area(self):
        for widget in self.build_view_frame.winfo_children(): widget.destroy()
        if not self.selected_hero: tk.Label(self.build_view_frame, text="Select a hero to begin...", font=("Segoe UI", 24), bg=BG_COLOR, fg=FG_COLOR).pack(expand=True); return
        if self.is_editing: self.draw_build_editor()
        else: self.draw_build_viewer()
            
    def draw_build_viewer(self):
        header = tk.Frame(self.build_view_frame, bg=BG_COLOR); header.pack(fill="x", pady=10)
        hero_icon = self.data.get_image(self.selected_hero['icon'], (80, 80)); hero_label = tk.Label(header, image=hero_icon, bg=BG_COLOR); hero_label.image = hero_icon; hero_label.pack(side="left", padx=10)
        tk.Label(header, text=f"{self.selected_hero['name']}'s Builds", font=("Segoe UI", 20, "bold"), bg=BG_COLOR, fg=FG_COLOR).pack(side="left")
        tk.Button(self.build_view_frame, text="Create New Build", bg=ACCENT_COLOR, fg=FG_COLOR, bd=0, command=lambda: self.enter_edit_mode()).pack(fill="x", padx=10, pady=10)
        build_list_scroll_area = ScrollableFrame(self.build_view_frame, bg=BG_COLOR); build_list_scroll_area.pack(fill="both", expand=True, padx=10)
        hero_builds = self.all_builds.get(self.selected_hero['id'], [])
        builds_by_lane = {lane: [b for b in hero_builds if b['lane'] == lane] for lane in LANES}
        for lane in LANES:
            if builds_by_lane.get(lane):
                tk.Label(build_list_scroll_area.scrollable_frame, text=lane, font=("Segoe UI", 14, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).pack(anchor="w", padx=10)
                for build in builds_by_lane[lane]:
                    build_frame = tk.Frame(build_list_scroll_area.scrollable_frame, bg=FRAME_COLOR, pady=5); build_frame.pack(fill="x", padx=10, pady=2)
                    top_frame = tk.Frame(build_frame, bg=FRAME_COLOR); top_frame.pack(fill="x", padx=10)
                    tk.Label(top_frame, text=build['name'], font=("Segoe UI", 12, "bold"), bg=FRAME_COLOR, fg=FG_COLOR).pack(side="left")
                    tk.Button(top_frame, text="Delete", bg="red", fg=FG_COLOR, bd=0, command=lambda b=build: self.delete_build(b)).pack(side="right")
                    tk.Button(top_frame, text="Edit", bg="orange", fg=FG_COLOR, bd=0, command=lambda b=build: self.enter_edit_mode(b)).pack(side="right", padx=5)
                    display_frame = tk.Frame(build_frame, bg=FRAME_COLOR); display_frame.pack()
                    btn = tk.Button(display_frame, text="SELECT", bg=BG_COLOR, fg=FG_COLOR, bd=0, command=lambda b=build: self.select_active_build(b)); btn.pack(side="left", padx=(0, 5))
                    for item in build.get('items', []):
                        item_icon = self.data.get_image(item['icon'], (40, 40)); item_label = tk.Label(display_frame, image=item_icon, bg=FRAME_COLOR); item_label.image = item_icon; item_label.pack(side="left")
                    if build.get('crest'):
                        tk.Frame(display_frame, bg="gray", width=2, height=30).pack(side="left", padx=5)
                        crest_icon = self.data.get_image(build['crest']['icon'], (40, 40)); crest_label = tk.Label(display_frame, image=crest_icon, bg=FRAME_COLOR); crest_label.image = crest_icon; crest_label.pack(side="left")

    def enter_edit_mode(self, build=None): self.is_editing = build or True; self.draw_build_area()
    def draw_build_editor(self):
        build_data = self.is_editing if isinstance(self.is_editing, dict) else {'id': f"build-{self.selected_hero['id']}-{len(self.all_builds.get(self.selected_hero['id'], []))}", 'name': 'New Build', 'lane': LANES[0], 'items': [], 'crest': None}
        editor_frame = tk.Frame(self.build_view_frame, bg=BG_COLOR); editor_frame.pack(fill="both", expand=True)
        top_frame = tk.Frame(editor_frame, bg=BG_COLOR); top_frame.pack(fill="x")
        tk.Label(top_frame, text=f"Editing for {self.selected_hero['name']}", font=("Segoe UI", 16), bg=BG_COLOR, fg=FG_COLOR).pack()
        controls_frame = tk.Frame(top_frame, bg=BG_COLOR); controls_frame.pack(pady=5)
        tk.Label(controls_frame, text="Name:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left"); name_var = tk.StringVar(value=build_data['name']); tk.Entry(controls_frame, textvariable=name_var).pack(side="left")
        tk.Label(controls_frame, text="Lane:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left", padx=5); lane_var = tk.StringVar(value=build_data['lane']); ttk.Combobox(controls_frame, textvariable=lane_var, values=LANES, state="readonly").pack(side="left")
        current_build_frame = tk.Frame(top_frame, bg=BG_COLOR); current_build_frame.pack(pady=10)
        tk.Label(current_build_frame, text="Items", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, pady=(0, 5)); current_items_frame = tk.Frame(current_build_frame, bg=FRAME_COLOR, padx=5, pady=5); current_items_frame.grid(row=1, column=0)
        tk.Label(current_build_frame, text="Crest", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=1, pady=(0, 5), padx=(10, 0)); current_crest_frame = tk.Frame(current_build_frame, bg=FRAME_COLOR, padx=5, pady=5); current_crest_frame.grid(row=1, column=1, padx=(10, 0))
        action_frame = tk.Frame(editor_frame, bg=BG_COLOR); action_frame.pack(side="bottom", pady=10)
        tk.Button(action_frame, text="Cancel", command=lambda: self.select_hero(self.selected_hero)).pack(side="left")
        tk.Button(action_frame, text="Save", bg="green", fg=FG_COLOR, command=lambda: self.save_build(build_data, name_var.get(), lane_var.get())).pack(side="left")
        lists_container = tk.Frame(editor_frame, bg=BG_COLOR); lists_container.pack(fill="both", expand=True)
        def update_displays():
            for w in current_items_frame.winfo_children(): w.destroy()
            for i, item in enumerate(build_data['items']):
                icon = self.data.get_image(item['icon'], (48, 48)); btn = tk.Button(current_items_frame, image=icon, bg=BG_COLOR, command=lambda idx=i: remove_item(idx)); btn.image = icon; btn.pack(side="left")
            for _ in range(MAX_BUILD_ITEMS - len(build_data['items'])): tk.Frame(current_items_frame, bg=BG_COLOR, width=52, height=52).pack(side="left", padx=2)
            for w in current_crest_frame.winfo_children(): w.destroy()
            if build_data.get('crest'):
                icon = self.data.get_image(build_data['crest']['icon'], (48, 48)); btn = tk.Button(current_crest_frame, image=icon, bg=BG_COLOR, command=lambda: select_crest(None)); btn.image = icon; btn.pack(side="left")
            else: tk.Frame(current_crest_frame, bg=BG_COLOR, width=52, height=52).pack(side="left", padx=2)
        def add_item(item):
            if len(build_data['items']) < MAX_BUILD_ITEMS: build_data['items'].append(item); update_displays()
        def remove_item(index): build_data['items'].pop(index); update_displays()
        def select_crest(crest): build_data['crest'] = crest; update_displays()
        update_displays()
        tk.Label(lists_container, text="Available Items", bg=BG_COLOR, fg=FG_COLOR).pack()
        item_scroll_container = ScrollableFrame(lists_container, bg=BG_COLOR); item_scroll_container.pack(fill="both", expand=True, pady=5)
        items_by_class, class_order = {}, ['Marksman', 'Fighter', 'Tank', 'Mage', 'Support']
        for item in self.data.items:
            hero_class = item.get('hero_class') or "General"
            if hero_class not in items_by_class: items_by_class[hero_class] = []
            items_by_class[hero_class].append(item)
            if hero_class not in class_order: class_order.append(hero_class)
        for hero_class in class_order:
            if hero_class in items_by_class:
                tk.Label(item_scroll_container.scrollable_frame, text=hero_class, font=("Segoe UI", 10, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).pack(anchor="w", padx=5, pady=(10, 2))
                class_frame = tk.Frame(item_scroll_container.scrollable_frame, bg=BG_COLOR); class_frame.pack(fill="x")
                items_in_class = sorted(items_by_class[hero_class], key=lambda x: x['name'])
                for i, item in enumerate(items_in_class):
                    icon = self.data.get_image(item['icon'], (48, 48))
                    border_color = RARITY_COLORS.get(item.get('rarity'), RARITY_COLORS["Default"])
                    border_frame = tk.Frame(class_frame, bg=border_color)
                    btn = tk.Button(border_frame, image=icon, bg=FRAME_COLOR, bd=0, command=lambda it=item: add_item(it)); btn.image = icon; btn.pack(padx=2, pady=2)
                    border_frame.grid(row=i // 14, column=i % 14, padx=1, pady=1)
        tk.Label(lists_container, text="Crests", bg=BG_COLOR, fg=FG_COLOR).pack(); crest_scroll_container = ScrollableFrame(lists_container, bg=BG_COLOR, height=250); crest_scroll_container.pack(fill="x", pady=5)
        tk.Label(crest_scroll_container.scrollable_frame, text="1. Select Base Crest", bg=BG_COLOR, fg=FG_COLOR).pack(); base_crest_frame = tk.Frame(crest_scroll_container.scrollable_frame, bg=BG_COLOR); base_crest_frame.pack()
        tk.Label(crest_scroll_container.scrollable_frame, text="2. Select Evolution", bg=BG_COLOR, fg=FG_COLOR).pack(); evolved_crest_frame = tk.Frame(crest_scroll_container.scrollable_frame, bg=BG_COLOR); evolved_crest_frame.pack(pady=2)
        tk.Label(crest_scroll_container.scrollable_frame, text="3. Select Legendary", bg=BG_COLOR, fg=FG_COLOR).pack(); legendary_crest_frame = tk.Frame(crest_scroll_container.scrollable_frame, bg=BG_COLOR); legendary_crest_frame.pack(pady=2)
        base_crest_frame.image_refs, evolved_crest_frame.image_refs, legendary_crest_frame.image_refs = [], [], []
        def show_legendary_evolutions(stage1_crest):
            select_crest(stage1_crest)
            for w in legendary_crest_frame.winfo_children(): w.destroy()
            legendary_crest_frame.image_refs.clear()
            for evo in self.data.crest_evolution_map.get(stage1_crest['internal_name'], []):
                icon = self.data.get_image(evo['icon'], (48, 48)); legendary_crest_frame.image_refs.append(icon); btn = tk.Button(legendary_crest_frame, image=icon, bg=FRAME_COLOR, command=lambda c=evo: select_crest(c)); btn.pack(side="left", padx=2)
        def show_stage1_evolution(base_crest):
            select_crest(base_crest)
            for w in evolved_crest_frame.winfo_children(): w.destroy()
            evolved_crest_frame.image_refs.clear()
            for w in legendary_crest_frame.winfo_children(): w.destroy()
            legendary_crest_frame.image_refs.clear()
            for evo in self.data.crest_evolution_map.get(base_crest['internal_name'], []):
                icon = self.data.get_image(evo['icon'], (48, 48)); evolved_crest_frame.image_refs.append(icon); btn = tk.Button(evolved_crest_frame, image=icon, bg=FRAME_COLOR, command=lambda c=evo: show_legendary_evolutions(c)); btn.pack(side="left", padx=2)
        for crest in self.data.base_crests:
            icon = self.data.get_image(crest['icon'], (48, 48)); base_crest_frame.image_refs.append(icon); btn = tk.Button(base_crest_frame, image=icon, bg=BG_COLOR, command=lambda c=crest: show_stage1_evolution(c)); btn.pack(side="left", padx=2)

    def save_build(self, build_data, name, lane):
        build_data['name'], build_data['lane'] = name, lane
        hero_id = self.selected_hero['id']
        if hero_id not in self.all_builds: self.all_builds[hero_id] = []
        builds, found = self.all_builds[hero_id], False
        for i, b in enumerate(builds):
            if b['id'] == build_data['id']: builds[i], found = build_data, True; break
        if not found: builds.append(build_data)
        with open(BUILDS_FILE, 'w') as f: json.dump(self.all_builds, f, indent=2)
        self.select_hero(self.selected_hero)

    def delete_build(self, build_to_delete):
        hero_id = self.selected_hero['id']
        if hero_id in self.all_builds: self.all_builds[hero_id] = [b for b in self.all_builds[hero_id] if b['id'] != build_to_delete['id']]
        with open(BUILDS_FILE, 'w') as f: json.dump(self.all_builds, f, indent=2)
        self.draw_build_area()

    def select_active_build(self, build):
        self.active_build = build
        payload = {"hero": {"name": self.selected_hero['name'], "icon": f"{API_BASE_URL}{self.selected_hero['icon']}"}, "items": [{"icon": f"{API_BASE_URL}{item['icon']}"} for item in build.get('items', [])], "crest": {"icon": f"{API_BASE_URL}{build.get('crest')['icon']}"} if build.get('crest') else None}
        try:
            response = requests.post("http://127.0.0.1:5000/api/set_build", json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending build to server: {e}")
        self.display_collapsed_view()

    def load_builds(self):
        if os.path.exists(BUILDS_FILE):
            try:
                with open(BUILDS_FILE, 'r') as f: return json.load(f)
            except json.JSONDecodeError: return {}
        return {}

def run_ui():
    """Initializes and runs the Tkinter application."""
    data = DataHandler()
    app = App(data)
    app.mainloop()

if __name__ == '__main__':
    run_ui()