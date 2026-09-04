#!/usr/bin/env python3
"""Local contract visualization app. Run: python3 visualizer.py"""
import json, os, tkinter as tk
from tkinter import ttk, messagebox

TEXT_DIR = "contract_text"
GT_FILE = "contract_ground_truth"

# Load ground truth
print("Loading ground truth...")
gt = {}
with open(GT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        gt[d["contract_id"]] = d["gold"]

# List available contracts
contracts = sorted([c for c in os.listdir(TEXT_DIR) if c.endswith(".txt")])
contracts = [c[:-4] for c in contracts if c[:-4] in gt]
print(f"Contracts loaded: {len(contracts)}")

# Generate distinct colors for categories
all_cats = sorted({cat for d in gt.values() for cat in d})
category_colors = {}
# Simple hue spread
import colorsys
n = len(all_cats)
for i, cat in enumerate(all_cats):
    hue = i / max(n, 1)
    # avoid too light colors: use saturation ~0.7, value ~0.85
    r, g, b = colorsys.hsv_to_rgb(hue, 0.7, 0.85)
    hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    category_colors[cat] = hex_color

class App:
    def __init__(self, root):
        self.root = root
        root.title("Contract Visualization")
        root.geometry("1400x1000")

        # Left panel
        left = tk.Frame(root, width=350)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="Contracts (510)", font=("Segoe UI", 12, "bold")).pack(pady=5)
        search_frame = tk.Frame(left)
        search_frame.pack(fill="x", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_contracts)
        tk.Entry(search_frame, textvariable=self.search_var).pack(fill="x")

        self.listbox = tk.Listbox(left, exportselection=False, width=40, font=("Segoe UI", 9))
        self.listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        scrollbar = tk.Scrollbar(left, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.all_contracts = contracts[:]
        self.display_contracts = contracts[:]
        self.listbox.insert(0, *self.display_contracts)
        # Select first
        self.listbox.selection_set(0)
        self.listbox.event_generate("<<ListboxSelect>>")

        # Right area
        right = tk.Frame(root)
        right.pack(side="left", fill="both", expand=True)

        # Header
        header = tk.Frame(right)
        header.pack(fill="x", padx=10, pady=5)
        self.title_label = tk.Label(header, text="", font=("Segoe UI", 14, "bold"), anchor="w")
        self.title_label.pack(side="left")
        self.info_label = tk.Label(header, text="", font=("Segoe UI", 10), anchor="e", fg="#555555")
        self.info_label.pack(side="right")

        # Categories frame
        cat_frame = tk.LabelFrame(right, text="Present Categories", font=("Segoe UI", 10, "bold"))
        cat_frame.pack(fill="x", padx=10, pady=5)
        self.cat_inner = tk.Frame(cat_frame)
        self.cat_inner.pack(fill="both", expand=True, padx=5, pady=5)

        # Text area
        text_frame = tk.LabelFrame(right, text="Contract Text", font=("Segoe UI", 10, "bold"))
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.text = tk.Text(text_frame, wrap="none", font=("Consolas", 10), background="#fdfdfd", undo=True)
        self.text.pack(side="left", fill="both", expand=True)
        text_scroll_y = tk.Scrollbar(text_frame, command=self.text.yview)
        text_scroll_y.pack(side="right", fill="y")
        text_scroll_x = tk.Scrollbar(text_frame, orient="horizontal", command=self.text.xview)
        text_scroll_x.pack(side="bottom", fill="x")
        self.text.config(yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set)

        # Tags setup (will be created per selection)
        self.current_tags = []

    def filter_contracts(self, *args):
        term = self.search_var.get().lower()
        self.display_contracts = [c for c in self.all_contracts if term in c.lower()]
        self.listbox.delete(0, tk.END)
        if self.display_contracts:
            self.listbox.insert(0, *self.display_contracts)
            self.listbox.selection_set(0)
            self.listbox.event_generate("<<ListboxSelect>>")
        else:
            self.title_label.config(text="No matches")
            self.info_label.config(text="")
            self.text.delete("1.0", tk.END)
            for w in self.cat_inner.winfo_children():
                w.destroy()

    def on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        contract_id = self.listbox.get(sel[0])
        self.load_contract(contract_id)

    def load_contract(self, contract_id):
        # Clear previous tags
        for tag in self.current_tags:
            try:
                self.text.tag_delete(tag)
            except tk.TclError:
                pass
        self.current_tags = []
        # Load text
        path = os.path.join(TEXT_DIR, contract_id + ".txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read {path}: {e}")
            return
        # Update text widget
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)
        # Get gold
        gold = gt.get(contract_id, {})
        present = [(cat, info) for cat, info in gold.items() if not info.get("is_impossible", True)]
        present.sort(key=lambda x: x[0])
        # Build category labels
        for w in self.cat_inner.winfo_children():
            w.destroy()
        for idx, (cat, info) in enumerate(present):
            color = category_colors.get(cat, "#aaaaaa")
            # Small colored box + label
            frame = tk.Frame(self.cat_inner, bd=1, relief="solid", bg=color)
            frame.grid(row=0, column=idx, padx=2, pady=2, sticky="nw")
            label = tk.Label(frame, text=f"{cat}\n{len(info.get('spans', []))} spans", bg=color,
                             fg="white" if int(color[1:3], 16) < 128 else "black",
                             font=("Segoe UI", 7), wraplength=120, justify="center")
            label.pack(padx=2, pady=2)
        self.cat_inner.update_idletasks()

        # Highlight spans
        for cat, info in present:
            tag_name = f"tag_{cat}"
            # sanitize tag name
            tag_name = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in tag_name)
            # Ensure unique
            tag_name = tag_name[:40]
            # Make unique per selection by adding contract id? Not needed if deleted each time.
            self.current_tags.append(tag_name)
            color = category_colors.get(cat, "#aaaaaa")
            self.text.tag_config(tag_name, background=color, foreground="black", font=("Consolas", 10, "bold"))
            spans = info.get("spans", [])
            for span in spans:
                if isinstance(span, list) and len(span) == 2:
                    s, e = span
                elif isinstance(span, (list, tuple)) and len(span) == 2:
                    s, e = span[0], span[1]
                else:
                    continue
                # Apply tag
                try:
                    start_idx = f"1.0 + {int(s)} chars"
                    end_idx = f"1.0 + {int(e)} chars"
                    self.text.tag_add(tag_name, start_idx, end_idx)
                except Exception as ex:
                    # Some spans may extend beyond text due to encoding differences; skip
                    pass

        # Update title
        n_present = len(present)
        total_spans = sum(len(info.get("spans", [])) for _, info in present)
        self.title_label.config(text=f"{contract_id}")
        self.info_label.config(text=f"{n_present} categories  |  {total_spans} highlights  |  {len(text):,} chars")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
