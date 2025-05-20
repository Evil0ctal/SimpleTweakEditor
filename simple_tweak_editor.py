import os
import subprocess
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox


class DebPackageGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("iOS .deb Tweak Unpacker/Repacker")

        # Buttons for Unpack and Repack actions
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Unpack .deb File", command=self.unpack_deb).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Repack Folder to .deb", command=self.repack_folder).pack(side=tk.LEFT, padx=5)

        # Logging text area with scrollbar
        log_frame = tk.Frame(root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text = tk.Text(log_frame, height=15, width=80)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.insert(tk.END, "Ready.\n")
        self.log_text.configure(state=tk.NORMAL)

    def log(self, message):
        """Append a message to the log text area."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.NORMAL)

    def unpack_deb(self):
        """Handle the Unpack button action: select a .deb and unpack it."""
        deb_path = filedialog.askopenfilename(
            title="Select a .deb package to unpack",
            filetypes=[("Debian Package", "*.deb"), ("All Files", "*.*")]
        )
        if not deb_path:
            return  # user canceled dialog
        output_dir = filedialog.askdirectory(title="Select output directory for unpacking")
        if not output_dir:
            return  # canceled

        # Prepare target directory for unpacking (folder named after the .deb file)
        deb_name = os.path.splitext(os.path.basename(deb_path))[0]
        target_dir = os.path.join(output_dir, deb_name)
        if os.path.isdir(target_dir):
            # Ask for confirmation to overwrite existing folder
            if not messagebox.askyesno(
                    "Overwrite Directory",
                    f"The directory '{target_dir}' already exists.\nDelete its contents and unpack again?"
            ):
                self.log(f"Unpack canceled: directory '{target_dir}' already exists.")
                return
            # Remove the existing directory
            try:
                shutil.rmtree(target_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove existing directory:\n{e}")
                self.log(f"Error: could not remove directory '{target_dir}': {e}")
                return
        os.makedirs(target_dir, exist_ok=True)

        # Run dpkg-deb commands to unpack
        self.log(f"Unpacking '{os.path.basename(deb_path)}' to folder: {target_dir}")
        try:
            # Extract file system content
            result1 = subprocess.run(["dpkg-deb", "-x", deb_path, target_dir],
                                     capture_output=True, text=True)
            # Extract control files into DEBIAN/
            os.makedirs(os.path.join(target_dir, "DEBIAN"), exist_ok=True)
            result2 = subprocess.run(["dpkg-deb", "-e", deb_path, os.path.join(target_dir, "DEBIAN")],
                                     capture_output=True, text=True)
        except FileNotFoundError:
            messagebox.showerror("dpkg-deb not found",
                                 "The 'dpkg-deb' tool is not installed or not in PATH.\nPlease install dpkg (Debian package tools) to use this feature.")
            self.log("Error: dpkg-deb tool not found. Install 'dpkg' package (e.g. via Homebrew) to enable unpacking.")
            return

        # Check for errors in extraction
        if result1.returncode != 0 or result2.returncode != 0:
            self.log(f"Error: Failed to unpack '{os.path.basename(deb_path)}'")
            if result1.stdout: self.log(result1.stdout.strip())
            if result1.stderr: self.log(result1.stderr.strip())
            if result2.stdout: self.log(result2.stdout.strip())
            if result2.stderr: self.log(result2.stderr.strip())
            messagebox.showerror("Unpack Failed",
                                 f"Could not unpack '{os.path.basename(deb_path)}'. Please see log for details.")
            return

        # Log any output or warnings from dpkg-deb
        if result1.stdout: self.log(result1.stdout.strip())
        if result1.stderr: self.log(result1.stderr.strip())
        if result2.stdout: self.log(result2.stdout.strip())
        if result2.stderr: self.log(result2.stderr.strip())
        self.log(f"Successfully unpacked to: {target_dir}")
        messagebox.showinfo("Unpack Complete",
                            f"Successfully unpacked '{os.path.basename(deb_path)}' to:\n{target_dir}")

    def repack_folder(self):
        """Handle the Repack button action: select a folder and repack it into a .deb."""
        folder_path = filedialog.askdirectory(title="Select folder to repack (must contain DEBIAN/control)")
        if not folder_path:
            return  # canceled
        control_path = os.path.join(folder_path, "DEBIAN", "control")
        if not os.path.isfile(control_path):
            messagebox.showerror("Invalid Folder",
                                 "The selected folder is not a valid package directory (missing DEBIAN/control).")
            self.log(f"Repack canceled: '{folder_path}' has no DEBIAN/control file.")
            return

        # Ask user for output .deb file path
        default_name = os.path.basename(folder_path.rstrip("/")) or "package"
        if not default_name.lower().endswith(".deb"):
            default_name += ".deb"
        out_path = filedialog.asksaveasfilename(
            title="Save repacked .deb as",
            defaultextension=".deb",
            initialfile=default_name,
            filetypes=[("Debian Package", "*.deb"), ("All Files", "*.*")]
        )
        if not out_path:
            return  # canceled
        if os.path.exists(out_path):
            # Confirm overwrite of existing file
            if not messagebox.askyesno("Overwrite File", f"The file '{out_path}' already exists. Overwrite it?"):
                self.log(f"Repack canceled: file '{out_path}' already exists.")
                return

        # Read control file content
        try:
            with open(control_path, "r") as cf:
                control_content = cf.read()
        except Exception as e:
            messagebox.showerror("Error", f"Could not read control file:\n{e}")
            self.log(f"Error: unable to read '{control_path}': {e}")
            return

        # Popup window to review/edit control file
        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit control file before repacking")
        edit_win.geometry("500x400")
        tk.Label(edit_win, text="Review or edit DEBIAN/control metadata:").pack(anchor="w", padx=5, pady=2)
        text_area = tk.Text(edit_win)
        text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        text_area.insert("1.0", control_content)
        # Scrollbar for the text area
        scroll = tk.Scrollbar(edit_win, command=text_area.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text_area.configure(yscrollcommand=scroll.set)

        # Frame for buttons in the popup
        btn_frame = tk.Frame(edit_win)
        btn_frame.pack(pady=5)

        def do_repack():
            # Save edited control content back to file
            new_content = text_area.get("1.0", "end-1c")
            try:
                with open(control_path, "w") as cf:
                    cf.write(new_content)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to write control file:\n{e}")
                self.log(f"Error: could not write to '{control_path}': {e}")
                return  # do not destroy window, allow retry
            edit_win.destroy()
            # Set permissions for control, postinst, and prerm scripts to 755
            debian_dir = os.path.join(folder_path, "DEBIAN")
            for script in ["control", "postinst", "prerm"]:
                script_path = os.path.join(debian_dir, script)
                if os.path.exists(script_path):
                    os.chmod(script_path, 0o755)
                    self.log(f"Set 755 permissions for {script_path}")
            # Run dpkg-deb to build the package
            self.log(f"Repacking folder '{folder_path}' into '{os.path.basename(out_path)}'...")
            try:
                build_cmd = ["dpkg-deb", "-Zgzip", "-z9", "-b", folder_path, out_path]
                result = subprocess.run(build_cmd, capture_output=True, text=True)
            except FileNotFoundError:
                messagebox.showerror("dpkg-deb not found",
                                     "The 'dpkg-deb' tool is not installed or not in PATH.\nPlease install it to create .deb packages.")
                self.log("Error: dpkg-deb tool not found. Cannot repack folder.")
                return

            if result.returncode != 0:
                self.log(f"Error: Failed to create package '{os.path.basename(out_path)}'")
                if result.stdout: self.log(result.stdout.strip())
                if result.stderr: self.log(result.stderr.strip())
                messagebox.showerror("Repack Failed", "Package creation failed. See log for details.")
            else:
                # Log any output or warnings
                if result.stdout: self.log(result.stdout.strip())
                if result.stderr: self.log(result.stderr.strip())
                self.log(f"Successfully created package: {out_path}")
                messagebox.showinfo("Repack Complete", f"Successfully created .deb package:\n{out_path}")

        def cancel_repack():
            self.log("Repack canceled by user.")
            edit_win.destroy()

        tk.Button(btn_frame, text="Cancel", command=cancel_repack).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Save & Repack", command=do_repack).pack(side=tk.RIGHT, padx=5)

        # Make the popup modal
        edit_win.transient(self.root)
        edit_win.grab_set()
        self.root.wait_window(edit_win)


# Initialize and start the Tkinter event loop
if __name__ == "__main__":
    root = tk.Tk()
    app = DebPackageGUI(root)
    root.mainloop()
