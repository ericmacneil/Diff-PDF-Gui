import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import sys

# --- Import tkinterdnd2 for Drag and Drop ---
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

# --- Configuration ---
# Determine SCRIPT_DIR robustly for use as CWD in subprocess call
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
        # Height adjusted
        master.geometry("600x450")
        master.resizable(False, False)

        # File path variables
        self.file_a_path = tk.StringVar()
        self.file_b_path = tk.StringVar()

        # Apply style
        self.style = ttk.Style()
        self.style.theme_use('vista') 
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Segoe UI', 10))
        
        # Custom Button Style (Purple)
        self.style.configure('Accent.TButton', background='#9B84D3', foreground='black', font=('Segoe UI', 12, 'bold'))
        self.style.map('Accent.TButton', 
                       background=[('active', '#8C74C2'), ('pressed', '#7E65B1')],
                       foreground=[('active', 'black'), ('pressed', 'black')])

        # Main Frame
        main_frame = ttk.Frame(master, padding="30 20 30 20")
        main_frame.pack(expand=True, fill='both')

        # Title
        title_label = ttk.Label(main_frame, text="PDF Difference Finder", 
                                font=('Segoe UI', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 25), sticky='w')

        # --- File 1 Drop Zone ---
        self.create_drop_zone(main_frame, "File 1 (Original):", self.file_a_path, 1)

        # --- File 2 Drop Zone ---
        self.create_drop_zone(main_frame, "File 2 (Comparison):", self.file_b_path, 2)

        # --- Run Button ---
        # Simplified text, slightly wider/taller look
        self.run_button = ttk.Button(main_frame, text="COMPARE PDFs", command=self.run_diff, 
                                     style='Accent.TButton', width=25)
        self.run_button.grid(row=3, column=0, pady=(30, 5))

        # --- Status Label ---
        # This will now act as the primary feedback mechanism
        self.status_label = ttk.Label(main_frame, text="Ready. Drag files above.", foreground='#666', font=('Segoe UI', 10))
        self.status_label.grid(row=4, column=0, pady=(5, 0))

        # Grid weight
        main_frame.grid_columnconfigure(0, weight=1)


    def create_drop_zone(self, parent, title, path_var, row_idx):
        """Creates a stylized drag-and-drop zone."""
        
        # Container
        container = ttk.Frame(parent)
        container.grid(row=row_idx, column=0, sticky='ew', pady=10)
        container.grid_columnconfigure(0, weight=1)

        # Label
        ttk.Label(container, text=title, font=('Segoe UI', 10, 'bold'), foreground="#333").grid(row=0, column=0, sticky='w', padx=2, pady=(0, 5))

        # Drop Zone Widget
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

        # -- Visual Update Logic --
        def update_ui(*args):
            path = path_var.get()
            if path:
                filename = os.path.basename(path)
                if len(filename) > 50: filename = filename[:47] + "..."
                drop_zone.config(text=f"📄  {filename}", bg=bg_selected, fg=fg_selected, font=('Segoe UI', 11, 'bold'))
                # Reset status label when a new file is added
                self.status_label.config(text="Ready to compare.", foreground='#666', font=('Segoe UI', 10))
            else:
                drop_zone.config(text="☁  Drag & Drop PDF Here", bg=bg_normal, fg=fg_normal, font=('Segoe UI', 11))

        path_var.trace_add("write", update_ui)

        # -- Click to Browse --
        def on_click(event):
            self.select_file(path_var)
        drop_zone.bind("<Button-1>", on_click)

        # -- Drag and Drop Events --
        if TkinterDnD:
            drop_zone.drop_target_register(DND_FILES)

            def on_drop(event):
                files = self.master.tk.splitlist(event.data)
                if files:
                    path_var.set(files[0])
            
            def on_enter(event):
                if not path_var.get():
                    drop_zone.config(bg=bg_hover)

            def on_leave(event):
                if not path_var.get():
                    drop_zone.config(bg=bg_normal)

            drop_zone.dnd_bind('<<Drop>>', on_drop)
            drop_zone.dnd_bind('<<DragEnter>>', on_enter)
            drop_zone.dnd_bind('<<DragLeave>>', on_leave)

    def select_file(self, path_var):
        filepath = filedialog.askopenfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Select a PDF File"
        )
        if filepath:
            path_var.set(filepath)

    def run_diff(self):
        file_a = self.file_a_path.get()
        file_b = self.file_b_path.get()

        if not file_a or not file_b:
            # Small animation or red text on status for missing files
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

        # Arg order swapped: New(Red), Old(Blue)
        command = [
            DIFF_PDF_COMMAND,
            f'--output-diff={os.path.normpath(output_path)}', 
            os.path.normpath(file_b), 
            os.path.normpath(file_a)
        ]
        
        print(f"Executing command: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                cwd=DIFF_PDF_DIR, 
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            if result.returncode in [0, 1]:
                status_text = "IDENTICAL" if result.returncode == 0 else "DIFFERENCES FOUND"
                # Update status label instead of popup
                self.status_label.config(
                    text=f"✔ Success! Files are {status_text}.", 
                    foreground='green',
                    font=('Segoe UI', 10, 'bold')
                )
            else: 
                error_msg = result.stderr or result.stdout or "Unknown Error"
                if result.returncode in [2, 3] or "Error opening" in error_msg:
                     # Keep popup for critical security block as it needs detail
                     messagebox.showerror("Blocked", f"Could not write file.\nPlease whitelist 'pdf-diff-gui.exe' in Windows Security.\n\nDetails: {error_msg}")
                     self.status_label.config(text="✘ Blocked by Security Software.", foreground='red', font=('Segoe UI', 10, 'bold'))
                else:
                     self.status_label.config(text=f"✘ Failed (Code {result.returncode}).", foreground='red', font=('Segoe UI', 10, 'bold'))
                     print(error_msg)

        except Exception as e:
            self.status_label.config(text="✘ Execution Error.", foreground='red')
            messagebox.showerror("Error", f"Execution failed: {e}")

def main():
    if TkinterDnD:
        root = TkinterDnD.Tk()
    else:
        messagebox.showwarning("Library Missing", "tkinterdnd2 not found. Drag & drop disabled.")
        root = tk.Tk()
    app = DiffPDFApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()