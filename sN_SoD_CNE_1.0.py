import tkinter as tk
from tkinter import filedialog, messagebox
import json
import threading
from collections import defaultdict
import re
import time

# Custom collapsible section widget
class CollapsibleCategory(tk.Frame):
    def __init__(self, master, title):
        super().__init__(master, bg=master["bg"])
        self.is_expanded = False
        self.content = tk.Frame(self, bg=master["bg"])
        self.btn = tk.Button(
            self,
            text=f"> {title}",
            font=("Segoe UI", 11, "bold"),
            bg="#333", fg="#eee",
            relief="flat",
            command=self.toggle
        )
        self.btn.pack(fill="x", pady=2)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        symbol = "v" if self.is_expanded else ">"
        self.btn.config(text=f"{symbol} {self.btn.cget('text')[2:]}")
        if self.is_expanded:
            self.content.pack(fill="x")
        else:
            self.content.pack_forget()

    def add(self, widget):
        widget.pack(in_=self.content, fill="x", padx=12, pady=4)

# Main app logic
class CitEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("superNug's Shadows of Doubt CIT Names Editor")
        self.root.configure(bg="#1e1e1e")
        self.root.geometry("1000x900")  # Double height
        self.entries = []
        self.data = None

        # Dark theme color scheme
        self.bg = "#1e1e1e"
        self.fg = "#f0f0f0"
        self.ebg = "#2e2e2e"
        self.bbg = "#444"

        # City label (shows animated city name)
        self.city_label = tk.Label(root, text="", font=("Consolas", 20, "bold"),
                                   fg="#00ffaa", bg=self.bg)
        self.city_label.pack(pady=10)

        # Progress bar container
        self.progress_frame = tk.Frame(root, bg=self.bg)
        self.progress_frame.pack(pady=4, fill="x", padx=20)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = tk.Canvas(self.progress_frame, height=28, bg="#222", bd=0, highlightthickness=0)
        self.progress_bar.pack(fill="x")
        self.progress_rect = self.progress_bar.create_rectangle(0, 0, 0, 28, fill="#00ffaa", width=0)
        self.progress_text = self.progress_bar.create_text(10, 14, anchor='w', text="Loading...", fill="#222")

        # Control buttons
        button_frame = tk.Frame(root, bg=self.bg)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Load .CIT File", font=("Segoe UI", 10, "bold"),
                  command=self.threaded_load_file, bg=self.bbg, fg=self.fg,
                  relief="flat", padx=10, pady=5).pack(side="left", padx=10)
        self.save_btn = tk.Button(button_frame, text="Save Changes", font=("Segoe UI", 10, "bold"),
                                  command=self.save_file, state=tk.DISABLED,
                                  bg=self.bbg, fg=self.fg, relief="flat", padx=10, pady=5)
        self.save_btn.pack(side="left", padx=10)

        # Scrollable entry canvas
        self.canvas = tk.Canvas(root, bg=self.bg, highlightthickness=0, bd=0)
        self.scroll_y = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.frame = tk.Frame(self.canvas, bg=self.bg)
        self.cframe = self.canvas.create_window((0, 0), window=self.frame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        self.scroll_y.pack(side="right", fill="y")
        self.frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        root.bind("<Configure>", self.on_root_resize)

        # Ignore list for name comparisons
        self.ignore_words = [
            "laboratories", "labs", "clinic", "store", "market",
            "hardware", "bakery", "grill", "canteen"
        ]

    # Run file loader in thread to avoid UI freeze
    def threaded_load_file(self):
        threading.Thread(target=self.load_file).start()

    # Load and parse .CIT JSON file
    def load_file(self):
        fp = filedialog.askopenfilename(filetypes=[("CIT files", "*.cit")])
        if not fp: return
        self.update_progress(0, "Loading file...")

        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                self.data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load JSON:\n{e}")
            return

        self.file_path = fp
        city_name = self.data.get("cityName", "Unknown")
        self.animate_city_name(city_name)
        self.update_progress(10, "Parsing data...")
        self.populate_fields()
        self.update_progress(100, "Done")
        self.save_btn.config(state=tk.NORMAL)

    # Visually animate loading text by revealing city name
    def animate_city_name(self, name):
        self.city_label.config(text="")
        for i in range(len(name) + 1):
            self.city_label.config(text=name[:i])
            self.progress_bar.itemconfig(self.progress_text, text=f"Loading: {name[:i]}")
            self.root.update()
            time.sleep(0.05)  # typing delay effect

    # Update progress bar width and text
    def update_progress(self, percent, text):
        w = self.progress_bar.winfo_width()
        self.progress_bar.coords(self.progress_rect, 0, 0, (percent / 100) * w, 28)
        self.progress_bar.itemconfig(self.progress_text, text=f"{text} ({percent:.0f}%)")
        self.root.update_idletasks()

    # Create an editable entry field with label
    def add_entry(self, parent, label, current_value, references):
        f = tk.Frame(parent, bg=self.bg)
        tk.Label(f, text=label, fg="#bbb", bg=self.bg, width=25,
                 anchor='w', font=("Segoe UI", 10, "bold")).pack(side='left')
        e = tk.Entry(f, width=60, bg=self.ebg, fg=self.fg, insertbackground=self.fg,
                     font=("Consolas", 10), relief="flat", highlightthickness=1, highlightcolor="#444")
        e.insert(0, current_value)
        e.pack(side='left', fill="x", expand=True, padx=6)
        self.entries.append((e, references))
        parent.add(f)

    # Scan and populate categories and entries from loaded data
    def populate_fields(self):
        for w in self.frame.winfo_children(): w.destroy()
        self.entries.clear()

        city_cat = self.add_cat("City")
        self.add_entry(city_cat, "City Name", self.data.get("cityName", ""), [(self.data, "cityName")])

        dist_cat = self.add_cat("Districts")
        self.add_unique_name_entries(self.data.get("districts", []), dist_cat, "District")

        street_cat = self.add_cat("Streets")
        self.add_unique_name_entries(self.data.get("streets", []), street_cat, "Street")

        keywords = [
            #"market", "store", "deli", "butcher", "bakery", "pawn", "electronics",
            #"diner", "cafe", "restaurant", "grill", "pub", "bar", "sync clinic", "pharmacy", "hospital", 
            #"repair", "laundromat", "tailors", "arcade", "nightclub", "gym", "studio", "museum", "gallery", 
            #"office", "factory", "\'s", "labs", "laboratory", "networks", "systems", "hotel", "black market", 
            #"weapons dealer", "launderette", "management", "loan shark", "casino", "gambling den",
            #"chemical plant"
        ]
        ignore_terms = [
            #"null", "backroom", "storeroom", "floor", "rooftop", "bathroom", "kitchen", 
            #"diner diner", "bargains", "supermarket", "sync sync", "dining room",
            #"ballroom", "control room", "reception", "pharmacy pharmacy", "bar bar", 
            #"sync sync", "marketing executive", "black trader", "black doctor", 
            #"break room", "utility cupboard", "living room", "bedroom", "hallway", 
            #"unknown", "study", "lobby", "penthouse", "basement", "officer", "manager",
            #"owner", "shower room"
        ]

        found_by_type = defaultdict(lambda: defaultdict(list))

        def normalize_name(name):
            name = name.replace("\'S", "\'s")
            words = name.lower().split()
            cleaned = [w for w in words if w not in self.ignore_words and w not in ignore_terms]
            return " ".join(cleaned).strip().title()

        def scan(obj):
            if isinstance(obj, dict):
                name = obj.get("name", "")
                lname = name.lower()
                for keyword in keywords:
                    if keyword in lname and not any(ig in lname for ig in ignore_terms):
                        base = normalize_name(name)
                        if base:
                            found_by_type[keyword][base].append((obj, "name"))
                        break
                for v in obj.values():
                    scan(v)
            elif isinstance(obj, list):
                for item in obj:
                    scan(item)

        scan(self.data)

        for keyword, base_dict in found_by_type.items():
            cat = self.add_cat(keyword.capitalize())
            for i, (base_name, refs) in enumerate(base_dict.items(), 1):
                self.add_entry(cat, f"{keyword.capitalize()} {i}", base_name, refs)

    # Collect unique names from lists
    def add_unique_name_entries(self, objects, parent_cat, label_prefix):
        name_map = defaultdict(list)
        for obj in objects:
            name = obj.get("name", "")
            if name:
                name_map[name].append((obj, "name"))
        for i, (name, refs) in enumerate(name_map.items(), 1):
            self.add_entry(parent_cat, f"{label_prefix} {i}", name, refs)

    # Add a collapsible category
    def add_cat(self, label):
        c = CollapsibleCategory(self.frame, label)
        c.pack(fill="x", padx=10, pady=5)
        return c

    # Save modified entries back to file
    def save_file(self):
        for entry, refs in self.entries:
            new_name = entry.get()
            for obj, key in refs:
                obj[key] = new_name
        nf = filedialog.asksaveasfilename(defaultextension=".cit", filetypes=[("CIT files", "*.cit")])
        if nf:
            with open(nf, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            messagebox.showinfo("Success", "File saved!")

    # Update scroll region
    def on_frame_configure(self, e): self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    def on_canvas_configure(self, e): self.canvas.itemconfig(self.cframe, width=e.width)
    def on_root_resize(self, e): self.canvas.configure(scrollregion=self.canvas.bbox("all"))

# Launch the app
if __name__ == "__main__":
    root = tk.Tk()
    app = CitEditorApp(root)
    root.mainloop()
