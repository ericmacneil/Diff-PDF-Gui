import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import shutil
import threading
import time
import difflib
import re # Added for revision number parsing

# --- CONFIGURATION & SETUP ---

# 1. Determine Application Directory (Robust for EXE and Script)
if getattr(sys, 'frozen', False):
    # Running as PyInstaller EXE
    APP_DIR = os.path.dirname(sys.executable)
    if hasattr(sys, '_MEIPASS'):
        SCRIPT_DIR = sys._MEIPASS # Internal temp dir for bundled files
    else:
        SCRIPT_DIR = APP_DIR
else:
    # Running as Python Script
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    SCRIPT_DIR = APP_DIR

DIFF_PDF_DIR = os.path.join(SCRIPT_DIR, 'diff-pdf-bin')
DIFF_PDF_COMMAND = os.path.join(DIFF_PDF_DIR, 'diff-pdf.exe')

# 2. Debug Logging
def log_debug(msg):
    try:
        log_path = os.path.join(APP_DIR, "debug_args.txt")
        with open(log_path, "a") as f:
            f.write(f"{msg}\n")
    except:
        pass

log_debug(f"STARTUP ARGS: {sys.argv}")

# --- Import tkinterdnd2 ---
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None


# --- 3D VIEWER LOGIC (Run in subprocess) ---
def run_3d_viewer_mode(file_a, file_b, save_dir):
    try:
        log_debug("Starting 3D Viewer Mode...")
        import pyvista as pv
        import vtk
        import diff3d

        pv.global_theme.interactive = True
        target_image_name = "screenshot.png"
        
        # Monkey Patch show() for auto-screenshot
        OriginalShow = pv.Plotter.show

        def patched_show(self, *args, **kwargs):
            def auto_capture(*_):
                try:
                    self.screenshot(target_image_name, return_img=False)
                except:
                    pass

            if hasattr(self, 'iren') and self.iren:
                self.iren.add_observer(vtk.vtkCommand.EndInteractionEvent, auto_capture)

            try:
                self.render()
                auto_capture()
            except:
                pass

            return OriginalShow(self, *args, **kwargs)

        pv.Plotter.show = patched_show

        os.chdir(save_dir)
        
        if os.path.exists(target_image_name):
            os.remove(target_image_name)

        log_debug(f"Diffing: {file_a} vs {file_b}")
        diff3d.from_files(file_a, file_b)
        
    except Exception as e:
        log_debug(f"3D CRASH: {e}")
        with open(os.path.join(save_dir, "diff3d_error.log"), "w") as f:
            f.write(f"Error running 3D viewer: {str(e)}")
        sys.exit(1)

# --- GUI LOGIC ---
class DiffPDFApp:
    def __init__(self, master):
        self.master = master
        master.title("Diff-PDF GUI Wrapper")
        master.geometry("600x600")
        master.resizable(False, False)

        self.file_a_path = tk.StringVar()
        self.file_b_path = tk.StringVar()
        self.check_3d_var = tk.BooleanVar(value=True)
        self.check_autofill_var = tk.BooleanVar(value=True)
        
        self.is_internal_update = False 

        self.style = ttk.Style()
        self.style.theme_use('vista') 
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Segoe UI', 10))
        self.style.configure('TCheckbutton', background='#f0f0f0', font=('Segoe UI', 10))
        self.style.configure('Accent.TButton', background='#9B84D3', foreground='black', font=('Segoe UI', 12, 'bold'))
        self.style.map('Accent.TButton', 
                       background=[('active', '#8C74C2'), ('pressed', '#7E65B1')],
                       foreground=[('active', 'black'), ('pressed', 'black')])

        self.style.configure('Control.TButton', font=('Segoe UI', 10))

        main_frame = ttk.Frame(master, padding="30 20 30 20")
        main_frame.pack(expand=True, fill='both')

        title_label = ttk.Label(main_frame, text="PDF & 3D Difference Finder", font=('Segoe UI', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20), sticky='w')

        # --- Row 1: File A (Original) ---
        self.drop_zone_a = self.create_drop_zone(main_frame, "File 1 (Original):", self.file_a_path, 1)

        # --- Row 2: Controls ---
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=2, column=0, pady=5, sticky='ew')
        
        # Swap Button
        self.swap_btn = ttk.Button(controls_frame, text="⇅ Swap", command=self.swap_files, style='Control.TButton', width=8)
        self.swap_btn.pack(side='left', padx=(0, 10))
        
        # Clear Button
        self.clear_btn = ttk.Button(controls_frame, text="✖ Clear", command=self.clear_files, style='Control.TButton', width=8)
        self.clear_btn.pack(side='left', padx=(0, 20))

        # Auto-fill Checkbox
        self.check_autofill = ttk.Checkbutton(controls_frame, 
                                              text="Auto-fill revision pair", 
                                              variable=self.check_autofill_var,
                                              onvalue=True, offvalue=False)
        self.check_autofill.pack(side='left')

        # --- Row 3: File B (Comparison) ---
        self.drop_zone_b = self.create_drop_zone(main_frame, "File 2 (Comparison):", self.file_b_path, 3)

        # --- Row 4: 3D Checkbox ---
        self.check_3d = ttk.Checkbutton(main_frame, text="Auto-diff matching .STEP files (requires 'diff3d' & 'build123d')", 
                                        variable=self.check_3d_var, onvalue=True, offvalue=False)
        self.check_3d.grid(row=4, column=0, pady=(15, 5), sticky='w')

        # --- Row 5: Run Button ---
        self.run_button = ttk.Button(main_frame, text="COMPARE FILES", command=self.run_diff, style='Accent.TButton', width=25)
        self.run_button.grid(row=5, column=0, pady=(20, 5))

        # --- Row 6: Status ---
        self.status_label = ttk.Label(main_frame, text="Ready. Drag files above.", foreground='#666', font=('Segoe UI', 10))
        self.status_label.grid(row=6, column=0, pady=(5, 0))

        main_frame.grid_columnconfigure(0, weight=1)

        # Attach listeners
        # When A changes -> Try to fill B (Next Revision)
        self.file_a_path.trace_add("write", lambda *args: self.on_path_change(self.file_a_path, self.file_b_path, self.drop_zone_b, mode="next"))
        # When B changes -> Try to fill A (Previous Revision)
        self.file_b_path.trace_add("write", lambda *args: self.on_path_change(self.file_b_path, self.file_a_path, self.drop_zone_a, mode="prev"))

    def swap_files(self):
        self.is_internal_update = True 
        val_a = self.file_a_path.get()
        val_b = self.file_b_path.get()
        self.file_a_path.set(val_b)
        self.file_b_path.set(val_a)
        self.is_internal_update = False
        self.status_label.config(text="Files swapped.", foreground='#333')

        # Retry auto-fill after swap if one side is empty
        # If A has file and B is empty, treat A as base and find NEXT revision for B
        if self.file_a_path.get() and not self.file_b_path.get():
            self.on_path_change(self.file_a_path, self.file_b_path, self.drop_zone_b, mode="next")
        # If B has file and A is empty, treat B as base and find PREV revision for A
        elif self.file_b_path.get() and not self.file_a_path.get():
            self.on_path_change(self.file_b_path, self.file_a_path, self.drop_zone_a, mode="prev")

    def clear_files(self):
        self.is_internal_update = True
        self.file_a_path.set("")
        self.file_b_path.set("")
        self.is_internal_update = False
        # Reset drop zones visual state
        self.drop_zone_a.config(text="☁  Drag & Drop PDF Here", bg="#E8EAF6", fg="#5C6BC0", font=('Segoe UI', 11))
        self.drop_zone_b.config(text="☁  Drag & Drop PDF Here", bg="#E8EAF6", fg="#5C6BC0", font=('Segoe UI', 11))
        self.status_label.config(text="Cleared.", foreground='#333')

    def extract_revision(self, filename):
        """Finds a revision number in a filename. Returns (prefix, separator, number, suffix)."""
        # Priority 1: Explicit 'Rev' or 'v' (greedy start ensures we find the LAST instance)
        # matches "Part_Rev1_..." -> "Part_", "Rev", "1", "_..."
        match = re.search(r'(.*)(Rev|v)(\d+)(.*)', filename, re.IGNORECASE)
        if match:
            return match.groups()
            
        # Priority 2: Underscore or Hyphen separator (greedy start)
        # matches "Part-02" -> "Part", "-", "02", ""
        match = re.search(r'(.*)(_|-)(\d+)(.*)', filename, re.IGNORECASE)
        if match:
            return match.groups()
            
        return None

    def on_path_change(self, changed_var, target_var, target_widget, mode="next"):
        """
        Auto-fills the target path based on revision logic.
        mode="next": Looks for revision > current (For File 1 -> File 2)
        mode="prev": Looks for revision < current (For File 2 -> File 1)
        """
        if not self.check_autofill_var.get() or self.is_internal_update:
            return

        current_path = changed_var.get()
        if not current_path or not os.path.exists(current_path):
            return

        if target_var.get():
            return

        try:
            directory = os.path.dirname(current_path)
            filename = os.path.basename(current_path)
            name_no_ext, ext = os.path.splitext(filename)

            candidates = [f for f in os.listdir(directory) if f.lower().endswith(ext.lower()) and f != filename]
            
            best_match_file = None
            
            # 1. Try smart revision matching first
            rev_info = self.extract_revision(name_no_ext)
            
            if rev_info:
                prefix, sep, num_str, suffix = rev_info
                try:
                    current_rev = int(num_str)
                    
                    valid_candidates = []
                    for cand in candidates:
                        cand_name = os.path.splitext(cand)[0]
                        cand_rev_info = self.extract_revision(cand_name)
                        if cand_rev_info:
                            c_prefix, c_sep, c_num_str, c_suffix = cand_rev_info
                            # Check prefix matches (ignoring the revision number part)
                            if c_prefix.lower() == prefix.lower(): 
                                try:
                                    c_rev = int(c_num_str)
                                    valid_candidates.append((c_rev, cand))
                                except:
                                    pass

                    valid_candidates.sort(key=lambda x: x[0])
                    
                    if mode == "next":
                        # Find smallest revision > current_rev
                        potential = [x for x in valid_candidates if x[0] > current_rev]
                        if potential: best_match_file = potential[0][1]
                            
                    elif mode == "prev":
                        # Find largest revision < current_rev
                        potential = [x for x in valid_candidates if x[0] < current_rev]
                        if potential: best_match_file = potential[-1][1]

                except Exception as e:
                    print(f"Revision parse error: {e}")

            # 2. Fallback only if NO revision info was found in source (avoids matching wrong revs)
            if not best_match_file and candidates and not rev_info:
                matches = difflib.get_close_matches(filename, candidates, n=1, cutoff=0.6)
                if matches:
                    best_match_file = matches[0]

            if best_match_file:
                match_path = os.path.join(directory, best_match_file)
                self.is_internal_update = True 
                target_var.set(match_path)
                self.is_internal_update = False
                self.status_label.config(text=f"Auto-filled: {best_match_file}", foreground='#00695C')
                # Reset visual state
                target_widget.config(bg="#E0F2F1", fg="#00695C") # Greenish for success
            else:
                target_widget.config(bg="#FFEBEE", fg="#D32F2F", text="✘ No matching revision found")
                self.status_label.config(text="No matching pair found for auto-fill.", foreground='#D32F2F')

        except Exception as e:
            print(f"Autofill error: {e}")

    def create_drop_zone(self, parent, title, path_var, row_idx):
        container = ttk.Frame(parent)
        container.grid(row=row_idx, column=0, sticky='ew', pady=10)
        container.grid_columnconfigure(0, weight=1)
        ttk.Label(container, text=title, font=('Segoe UI', 10, 'bold'), foreground="#333").grid(row=0, column=0, sticky='w', padx=2, pady=(0, 5))
        
        bg_normal, bg_hover, bg_selected = "#E8EAF6", "#D1C4E9", "#E0F2F1"
        fg_normal, fg_selected = "#5C6BC0", "#00695C"

        drop_zone = tk.Label(container, text="☁  Drag & Drop PDF Here", bg=bg_normal, fg=fg_normal, 
                             font=('Segoe UI', 11), relief="groove", borderwidth=2, height=3, cursor="hand2")
        drop_zone.grid(row=1, column=0, sticky='ew')

        def update_ui(*args):
            path = path_var.get()
            if path:
                filename = os.path.basename(path)
                if len(filename) > 50: filename = filename[:47] + "..."
                drop_zone.config(text=f"📄  {filename}", bg=bg_selected, fg=fg_selected, font=('Segoe UI', 11, 'bold'))
                if not self.is_internal_update:
                    self.status_label.config(text="Ready to compare.", foreground='#666', font=('Segoe UI', 10))
            else:
                drop_zone.config(text="☁  Drag & Drop PDF Here", bg=bg_normal, fg=fg_normal, font=('Segoe UI', 11))
        
        path_var.trace_add("write", update_ui)
        drop_zone.bind("<Button-1>", lambda e: self.select_file(path_var))

        if TkinterDnD:
            drop_zone.drop_target_register(DND_FILES)
            drop_zone.dnd_bind('<<Drop>>', lambda e: path_var.set(self.master.tk.splitlist(e.data)[0]) if self.master.tk.splitlist(e.data) else None)
            drop_zone.dnd_bind('<<DragEnter>>', lambda e: drop_zone.config(bg=bg_hover) if not path_var.get() else None)
            drop_zone.dnd_bind('<<DragLeave>>', lambda e: drop_zone.config(bg=bg_normal) if not path_var.get() else None)
        
        return drop_zone

    def select_file(self, path_var):
        filepath = filedialog.askopenfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if filepath: path_var.set(filepath)

    def find_step_file(self, pdf_path):
        if not pdf_path: return None
        base_path = os.path.splitext(pdf_path)[0]
        for ext in ['.step', '.stp', '.STEP', '.STP']:
            if os.path.exists(base_path + ext): return base_path + ext
        return None

    def run_diff(self):
        file_a, file_b = self.file_a_path.get(), self.file_b_path.get()
        if not file_a or not file_b:
            self.status_label.config(text="⚠️ Please select both PDF files first.", foreground='red')
            return
        
        default_name = "diff_result.pdf"
        if file_b:
            try:
                base_name = os.path.splitext(os.path.basename(file_b))[0]
                default_name = f"{base_name}-Redline.pdf"
            except:
                pass

        output_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], initialfile=default_name)
        if not output_path: return

        self.status_label.config(text="Processing...", foreground='#9B84D3', font=('Segoe UI', 10, 'italic'))
        self.master.update()

        # 1. PDF Diff
        pdf_success = False
        try:
            cmd = [DIFF_PDF_COMMAND, f'--output-diff={os.path.normpath(output_path)}', os.path.normpath(file_b), os.path.normpath(file_a)]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=DIFF_PDF_DIR, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            if res.returncode in [0, 1]: pdf_success = True
            elif res.returncode in [2, 3] or "Error opening" in res.stderr:
                messagebox.showerror("Blocked", f"Could not write PDF.\nPlease whitelist 'pdf-diff-gui.exe'.\n\nDetails: {res.stderr}")
        except Exception as e: print(f"PDF Error: {e}")

        # 2. 3D Diff
        step_msg = ""
        if self.check_3d_var.get():
            step_a, step_b = self.find_step_file(file_a), self.find_step_file(file_b)
            if step_a and step_b:
                save_dir = os.path.dirname(output_path)
                target_img = os.path.join(save_dir, os.path.splitext(os.path.basename(output_path))[0] + ".png")
                
                # Check libraries
                try:
                    subprocess.run([sys.executable, "-c", "import diff3d, pyvista, build123d"], check=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                    diff3d_ok = True
                except: diff3d_ok = False

                if diff3d_ok:
                    def run_3d():
                        try:
                            # Use a strict flag --run-3d-viewer
                            if getattr(sys, 'frozen', False):
                                cmd = [sys.executable, "--run-3d-viewer", step_a, step_b, save_dir]
                            else:
                                cmd = [sys.executable, os.path.abspath(__file__), "--run-3d-viewer", step_a, step_b, save_dir]
                            
                            subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                            
                            default_ss = os.path.join(save_dir, "screenshot.png")
                            if os.path.exists(default_ss):
                                if os.path.exists(target_img): os.remove(target_img)
                                os.rename(default_ss, target_img)
                                self.master.after(0, lambda: self.status_label.config(text=f"✔ PDF & 3D Image Saved.", foreground='green'))
                            else:
                                self.master.after(0, lambda: self.status_label.config(text=f"✔ PDF Saved (3D: No capture).", foreground='green'))
                        except Exception as e: print(f"3D Error: {e}")

                    threading.Thread(target=run_3d, daemon=True).start()
                    self.status_label.config(text="3D View Open... Rotate to Auto-Save...", foreground='#9B84D3')
                    return
                else: messagebox.showwarning("Missing Library", "Please run: pip install diff3d build123d pyvista")

        if pdf_success: self.status_label.config(text=f"✔ PDF Saved.", foreground='green', font=('Segoe UI', 10, 'bold'))
        else: self.status_label.config(text=f"✘ PDF Failed.", foreground='red', font=('Segoe UI', 10, 'bold'))

def main():
    # --- INTERNAL DISPATCHER (Strict Flag Check) ---
    if "--run-3d-viewer" in sys.argv:
        try:
            log_debug("Found 3D flag. Entering 3D logic.")
            idx = sys.argv.index("--run-3d-viewer")
            # Validate we have enough arguments
            if len(sys.argv) > idx + 3:
                file_a = sys.argv[idx + 1]
                file_b = sys.argv[idx + 2]
                save_dir = sys.argv[idx + 3]
                run_3d_viewer_mode(file_a, file_b, save_dir)
            else:
                log_debug(f"ERROR: Not enough args after flag. Args: {sys.argv}")

        except Exception as e:
            log_debug(f"DISPATCH ERROR: {e}")
        
        sys.exit(0) 

    # --- GUI MODE ---
    if TkinterDnD: root = TkinterDnD.Tk()
    else: root = tk.Tk()
    app = DiffPDFApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
