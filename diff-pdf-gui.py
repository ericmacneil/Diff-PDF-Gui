import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import sys
import shutil
import threading
import time

# --- Import tkinterdnd2 for Drag and Drop ---
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

# --- Configuration ---
try:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        SCRIPT_DIR = sys._MEIPASS
    else:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
except Exception:
    SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
    
DIFF_PDF_DIR = os.path.join(SCRIPT_DIR, 'diff-pdf-bin')
DIFF_PDF_COMMAND = os.path.join(DIFF_PDF_DIR, 'diff-pdf.exe')

class DiffPDFApp:
    def __init__(self, master):
        self.master = master
        master.title("Diff-PDF GUI Wrapper")
        master.geometry("600x500")
        master.resizable(False, False)

        # File path variables
        self.file_a_path = tk.StringVar()
        self.file_b_path = tk.StringVar()
        
        # Checkbox variable (Default to True)
        self.check_3d_var = tk.BooleanVar(value=True)

        # Apply style
        self.style = ttk.Style()
        self.style.theme_use('vista') 
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Segoe UI', 10))
        self.style.configure('TCheckbutton', background='#f0f0f0', font=('Segoe UI', 10))
        
        self.style.configure('Accent.TButton', background='#9B84D3', foreground='black', font=('Segoe UI', 12, 'bold'))
        self.style.map('Accent.TButton', 
                       background=[('active', '#8C74C2'), ('pressed', '#7E65B1')],
                       foreground=[('active', 'black'), ('pressed', 'black')])

        # Main Frame
        main_frame = ttk.Frame(master, padding="30 20 30 20")
        main_frame.pack(expand=True, fill='both')

        # Title
        title_label = ttk.Label(main_frame, text="PDF & 3D Difference Finder", 
                                font=('Segoe UI', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 25), sticky='w')

        # --- File 1 Drop Zone ---
        self.create_drop_zone(main_frame, "File 1 (Original):", self.file_a_path, 1)

        # --- File 2 Drop Zone ---
        self.create_drop_zone(main_frame, "File 2 (Comparison):", self.file_b_path, 2)

        # --- 3D Checkbox ---
        self.check_3d = ttk.Checkbutton(main_frame, 
                                        text="Auto-diff matching .STEP files (requires 'diff3d' & 'build123d')", 
                                        variable=self.check_3d_var,
                                        onvalue=True, offvalue=False)
        self.check_3d.grid(row=3, column=0, pady=(15, 5), sticky='w')

        # --- Run Button ---
        self.run_button = ttk.Button(main_frame, text="COMPARE FILES", command=self.run_diff, 
                                     style='Accent.TButton', width=25)
        self.run_button.grid(row=4, column=0, pady=(20, 5))

        # --- Status Label ---
        self.status_label = ttk.Label(main_frame, text="Ready. Drag files above.", foreground='#666', font=('Segoe UI', 10))
        self.status_label.grid(row=5, column=0, pady=(5, 0))

        # Grid weight
        main_frame.grid_columnconfigure(0, weight=1)

    def create_drop_zone(self, parent, title, path_var, row_idx):
        container = ttk.Frame(parent)
        container.grid(row=row_idx, column=0, sticky='ew', pady=10)
        container.grid_columnconfigure(0, weight=1)

        ttk.Label(container, text=title, font=('Segoe UI', 10, 'bold'), foreground="#333").grid(row=0, column=0, sticky='w', padx=2, pady=(0, 5))

        bg_normal = "#E8EAF6"
        bg_hover = "#D1C4E9"
        bg_selected = "#E0F2F1"
        fg_normal = "#5C6BC0"
        fg_selected = "#00695C"

        drop_zone = tk.Label(container, 
                             text="☁  Drag & Drop PDF Here", 
                             bg=bg_normal, 
                             fg=fg_normal,
                             font=('Segoe UI', 11),
                             relief="groove", 
                             borderwidth=2,
                             height=3,
                             cursor="hand2")
        drop_zone.grid(row=1, column=0, sticky='ew')

        def update_ui(*args):
            path = path_var.get()
            if path:
                filename = os.path.basename(path)
                if len(filename) > 50: filename = filename[:47] + "..."
                drop_zone.config(text=f"📄  {filename}", bg=bg_selected, fg=fg_selected, font=('Segoe UI', 11, 'bold'))
                self.status_label.config(text="Ready to compare.", foreground='#666', font=('Segoe UI', 10))
            else:
                drop_zone.config(text="☁  Drag & Drop PDF Here", bg=bg_normal, fg=fg_normal, font=('Segoe UI', 11))

        path_var.trace_add("write", update_ui)

        def on_click(event):
            self.select_file(path_var)
        drop_zone.bind("<Button-1>", on_click)

        if TkinterDnD:
            drop_zone.drop_target_register(DND_FILES)
            def on_drop(event):
                files = self.master.tk.splitlist(event.data)
                if files: path_var.set(files[0])
            
            def on_enter(event):
                if not path_var.get(): drop_zone.config(bg=bg_hover)

            def on_leave(event):
                if not path_var.get(): drop_zone.config(bg=bg_normal)

            drop_zone.dnd_bind('<<Drop>>', on_drop)
            drop_zone.dnd_bind('<<DragEnter>>', on_enter)
            drop_zone.dnd_bind('<<DragLeave>>', on_leave)

    def select_file(self, path_var):
        filepath = filedialog.askopenfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Select a PDF File"
        )
        if filepath: path_var.set(filepath)

    def find_step_file(self, pdf_path):
        if not pdf_path: return None
        base_path = os.path.splitext(pdf_path)[0]
        for ext in ['.step', '.stp', '.STEP', '.STP']:
            candidate = base_path + ext
            if os.path.exists(candidate):
                return candidate
        return None

    def run_diff(self):
        file_a = self.file_a_path.get()
        file_b = self.file_b_path.get()

        if not file_a or not file_b:
            self.status_label.config(text="⚠️ Please select both PDF files first.", foreground='red')
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save the Difference PDF as...",
            initialfile="diff_result.pdf"
        )

        if not output_path:
            self.status_label.config(text="Save cancelled.", foreground='#666')
            return

        self.status_label.config(text="Processing...", foreground='#9B84D3', font=('Segoe UI', 10, 'italic'))
        self.master.update() 

        # 1. PDF Diff
        pdf_success = False
        command = [
            DIFF_PDF_COMMAND,
            f'--output-diff={os.path.normpath(output_path)}', 
            os.path.normpath(file_b), 
            os.path.normpath(file_a)
        ]
        
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=False, cwd=DIFF_PDF_DIR, 
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if result.returncode in [0, 1]:
                pdf_success = True
            else:
                error_msg = result.stderr or result.stdout or "Unknown Error"
                if result.returncode in [2, 3] or "Error opening" in error_msg:
                     messagebox.showerror("Blocked", f"Could not write PDF.\nPlease whitelist 'pdf-diff-gui.exe'.\n\nDetails: {error_msg}")
                else:
                     print(f"PDF Diff Failed: {error_msg}")
        except Exception as e:
            print(f"PDF Execution Exception: {e}")

        # 2. 3D STEP Diff (Auto-Screenshot Script)
        if self.check_3d_var.get():
            step_a = self.find_step_file(file_a)
            step_b = self.find_step_file(file_b)
            
            if step_a and step_b:
                save_dir = os.path.dirname(output_path)
                target_image_name = os.path.splitext(os.path.basename(output_path))[0] + ".png"
                target_image_path = os.path.join(save_dir, target_image_name)

                # Check simple existence first
                diff3d_ok = False
                try:
                     # Check imports
                     subprocess.run([sys.executable, "-c", "import diff3d; import pyvista; import build123d"], 
                                    check=True, capture_output=True, 
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                     diff3d_ok = True
                except Exception:
                     diff3d_ok = False

                if diff3d_ok:
                    # Simplified instructions
                    # REMOVED: Pop-up instruction to make workflow faster
                    
                    # The magic script that patches PyVista behavior
                    viewer_script = f"""
import sys
import os
import pyvista as pv
import vtk
import diff3d

# Force interactive mode
pv.global_theme.interactive = True

file_a = r"{step_a}"
file_b = r"{step_b}"
save_name = "screenshot.png"

# --- MONKEY PATCH: Intercept show() to add callbacks ---
OriginalShow = pv.Plotter.show

def patched_show(self, *args, **kwargs):
    # Define the screenshot function
    def auto_capture(*_):
        try:
            # Take screenshot (blocking=False helps performance)
            self.screenshot(save_name, return_img=False)
            print("Captured.")
        except:
            pass

    # 1. Add Observer for Mouse Release (EndInteractionEvent)
    if hasattr(self, 'iren') and self.iren:
        self.iren.add_observer(vtk.vtkCommand.EndInteractionEvent, auto_capture)

    # 2. Capture immediately on load (after a tiny delay to ensure render)
    # We use a timer event to fire once after 500ms
    def initial_shot(step_id):
        auto_capture()
        # We don't need to repeat, but PyVista timers are often repeating. 
        # We just let it run or could clear it. 
        # For simplicity, one-shot call at startup is usually enough via simple call if render window is ready.
    
    # Attempt immediate capture (might be black if too early)
    # Better: Render once then capture
    try:
        self.render()
        auto_capture()
    except:
        pass

    return OriginalShow(self, *args, **kwargs)

pv.Plotter.show = patched_show
# -------------------------------------------------------

print("Launching diff3d viewer...")
try:
    diff3d.from_files(file_a, file_b)
except Exception as e:
    print(f"Error in 3D viewer: {{e}}")
"""
                    def run_3d_process():
                        try:
                            default_screenshot = os.path.join(save_dir, "screenshot.png")
                            if os.path.exists(default_screenshot):
                                os.remove(default_screenshot)

                            # Run the python script in the save_dir so screenshot.png appears there
                            subprocess.run([sys.executable, "-c", viewer_script], 
                                           cwd=save_dir,
                                           creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                            
                            # Rename final result
                            if os.path.exists(default_screenshot):
                                if os.path.exists(target_image_path):
                                    os.remove(target_image_path)
                                os.rename(default_screenshot, target_image_path)
                                
                                self.master.after(0, lambda: self.status_label.config(
                                    text=f"✔ PDF & 3D Image Saved.", foreground='green'))
                            else:
                                self.master.after(0, lambda: self.status_label.config(
                                    text=f"✔ PDF Saved (3D: No capture).", foreground='green'))
                                
                        except Exception as e:
                            print(f"3D Process Error: {e}")

                    threading.Thread(target=run_3d_process, daemon=True).start()
                    self.status_label.config(text="3D View Open... Rotate to Auto-Save...", foreground='#9B84D3')
                    return 

                else:
                    messagebox.showwarning("Missing Library", "3D diff requested but libraries not found.\nPlease run: pip install diff3d build123d pyvista")

        if pdf_success:
            self.status_label.config(text=f"✔ PDF Saved.", foreground='green', font=('Segoe UI', 10, 'bold'))
        else:
            self.status_label.config(text=f"✘ PDF Failed.", foreground='red', font=('Segoe UI', 10, 'bold'))

def main():
    if TkinterDnD:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = DiffPDFApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
