import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from queue import Empty, Queue


VIDEO_TYPES = (
    ("Video files", "*.mp4 *.mkv *.mov *.avi *.wmv *.m4v *.webm"),
    ("All files", "*.*"),
)


def find_ffmpeg() -> str | None:
    executable = shutil.which("ffmpeg")
    if executable:
        return executable

    links = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links"
    candidate = links / "ffmpeg.exe"
    if candidate.is_file():
        return str(candidate)

    winget_packages = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_packages.exists():
        for candidate in winget_packages.rglob("ffmpeg.exe"):
            return str(candidate)

    for package_dir in (Path.home() / "scoop", Path("C:/ffmpeg"), Path("C:/tools")):
        if package_dir.exists():
            for candidate in package_dir.rglob("ffmpeg.exe"):
                return str(candidate)
    return None


class VideoCompressorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Video Compressor")
        self.geometry("980x680")
        self.minsize(820, 560)
        self.configure(bg="#111827")

        self.ffmpeg = find_ffmpeg()
        self.files: list[Path] = []
        self.queue: Queue[tuple[str, object]] = Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background="#111827", foreground="#f9fafb", font=("Segoe UI", 10))
        style.configure("Surface.TFrame", background="#1f2937")
        style.configure("Card.TFrame", background="#1f2937")
        style.configure("Title.TLabel", background="#111827", foreground="#f9fafb", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background="#111827", foreground="#9ca3af", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#1f2937", foreground="#e5e7eb", font=("Segoe UI", 11, "bold"))
        style.configure("Field.TLabel", background="#1f2937", foreground="#9ca3af", font=("Segoe UI", 9))
        style.configure("Status.TLabel", background="#111827", foreground="#34d399", font=("Segoe UI", 9, "bold"))
        style.configure("StatusOff.TLabel", background="#111827", foreground="#f87171", font=("Segoe UI", 9, "bold"))

        style.configure(
            "TButton",
            background="#374151",
            foreground="#f9fafb",
            borderwidth=0,
            padding=(14, 8),
            focusthickness=0,
        )
        style.map("TButton", background=[("active", "#4b5563"), ("disabled", "#374151")])
        style.configure(
            "Primary.TButton",
            background="#2563eb",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=(18, 10),
        )
        style.map("Primary.TButton", background=[("active", "#3b82f6"), ("disabled", "#1e40af")])

        style.configure(
            "TCombobox",
            fieldbackground="#111827",
            background="#374151",
            foreground="#f9fafb",
            selectbackground="#111827",
            selectforeground="#f9fafb",
            arrowcolor="#f9fafb",
            borderwidth=0,
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#111827"), ("disabled", "#1f2937")],
            foreground=[("readonly", "#f9fafb"), ("disabled", "#9ca3af")],
            selectbackground=[("readonly", "#111827")],
            selectforeground=[("readonly", "#f9fafb")],
        )
        style.configure("TSpinbox", fieldbackground="#111827", background="#374151", foreground="#f9fafb", padding=6)
        style.configure("TRadiobutton", background="#1f2937", foreground="#d1d5db")
        style.configure("Horizontal.TProgressbar", troughcolor="#374151", background="#3b82f6", borderwidth=0)
        style.configure(
            "Source.Treeview",
            background="#111827",
            fieldbackground="#111827",
            foreground="#e5e7eb",
            rowheight=30,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Source.Treeview.Heading",
            background="#1f2937",
            foreground="#9ca3af",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Source.Treeview",
            background=[("selected", "#2563eb")],
            foreground=[("selected", "#ffffff")],
        )
        style.map("Source.Treeview.Heading", background=[("active", "#374151")])

        main = ttk.Frame(self, padding=24)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="Video Compressor", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Batch video compression with FFmpeg", style="Subtitle.TLabel").pack(anchor="w")

        status = "FFmpeg ready" if self.ffmpeg else "FFmpeg not found"
        status_style = "Status.TLabel" if self.ffmpeg else "StatusOff.TLabel"
        ttk.Label(header, text=status, style=status_style).place(relx=1.0, y=8, anchor="ne")

        content = ttk.Frame(main)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=7)
        content.columnconfigure(1, weight=3, minsize=250)
        content.rowconfigure(0, weight=1)

        files_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        files_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        files_card.rowconfigure(1, weight=1)

        ttk.Label(files_card, text="Source Videos", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(files_card, text="+ Add Videos", command=self.select_files).grid(row=0, column=1, sticky="e")
        files_card.columnconfigure(0, weight=1)

        source_table = ttk.Frame(files_card, style="Card.TFrame")
        source_table.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(12, 10))
        source_table.rowconfigure(0, weight=1)
        source_table.columnconfigure(0, weight=1)
        self.file_list = ttk.Treeview(
            source_table,
            columns=("video", "size"),
            show="headings",
            selectmode="extended",
            style="Source.Treeview",
        )
        self.file_list.heading("video", text="VIDEO", anchor="w")
        self.file_list.heading("size", text="SIZE", anchor="e")
        self.file_list.column("video", anchor="w", width=360, minwidth=160, stretch=True)
        self.file_list.column("size", anchor="e", width=100, minwidth=80, stretch=False)
        file_scrollbar = ttk.Scrollbar(source_table, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=file_scrollbar.set)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        file_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Button(files_card, text="Clear Selection", command=self.clear_files).grid(row=2, column=1, sticky="e")

        settings_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        settings_card.grid(row=0, column=1, sticky="nsew")
        ttk.Label(settings_card, text="Compression Settings", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )

        ttk.Label(settings_card, text="Codec", style="Field.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(settings_card, text="Quality (CRF)", style="Field.TLabel").grid(row=1, column=1, sticky="w")
        self.codec = tk.StringVar(value="h264")
        ttk.Combobox(settings_card, textvariable=self.codec, values=("h264", "h265"), state="readonly").grid(
            row=2, column=0, sticky="ew", padx=(0, 8)
        )
        self.crf = tk.IntVar(value=24)
        ttk.Spinbox(settings_card, from_=18, to=35, textvariable=self.crf).grid(row=2, column=1, sticky="ew")

        ttk.Label(settings_card, text="Preset", style="Field.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        ttk.Label(settings_card, text="Max Resolution", style="Field.TLabel").grid(row=3, column=1, sticky="w", pady=(12, 0))
        self.preset = tk.StringVar(value="medium")
        ttk.Combobox(
            settings_card,
            textvariable=self.preset,
            values=("ultrafast", "fast", "medium", "slow"),
            state="readonly",
        ).grid(row=4, column=0, sticky="ew", padx=(0, 8))
        self.max_height = tk.StringVar(value="1080")
        ttk.Combobox(
            settings_card,
            textvariable=self.max_height,
            values=("Original", "2160", "1080", "720", "480"),
            state="readonly",
        ).grid(row=4, column=1, sticky="ew")

        ttk.Label(settings_card, text="Output", style="Field.TLabel").grid(row=5, column=0, sticky="w", pady=(16, 6))
        self.output_mode = tk.StringVar(value="compressed")
        ttk.Radiobutton(
            settings_card, text="Compressed subfolder", variable=self.output_mode, value="compressed"
        ).grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(
            settings_card, text="Beside original files", variable=self.output_mode, value="source"
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 12))

        settings_card.columnconfigure(0, weight=1)
        settings_card.columnconfigure(1, weight=1)

        self.compress_button = ttk.Button(settings_card, text="Compress Videos", style="Primary.TButton", command=self.start_compression)
        self.compress_button.grid(row=8, column=0, columnspan=2, sticky="ew")

        footer = ttk.Frame(main)
        footer.pack(fill="x", pady=(14, 0))
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))

        results_card = ttk.Frame(footer, style="Card.TFrame", padding=12)
        results_card.pack(fill="x", pady=(0, 8))
        results_card.columnconfigure(0, weight=1)
        ttk.Label(results_card, text="Compressed Videos  ·  Original → Compressed", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(results_card, text="Open Selected", command=self.open_selected_result).grid(
            row=0, column=1, sticky="e"
        )
        self.results_list = tk.Listbox(
            results_card,
            height=3,
            background="#111827",
            foreground="#d1d5db",
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#374151",
            highlightcolor="#2563eb",
            activestyle="none",
            font=("Segoe UI", 9),
        )
        self.results_list.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.results_list.bind("<Double-Button-1>", lambda _event: self.open_selected_result())
        self.result_paths: list[Path] = []

        self.log = tk.Text(
            footer,
            height=4,
            state="disabled",
            background="#111827",
            foreground="#d1d5db",
            insertbackground="#d1d5db",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#374151",
            font=("Consolas", 9),
        )
        self.log.pack(fill="x")

    def select_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Select videos", filetypes=VIDEO_TYPES)
        for filename in selected:
            path = Path(filename)
            if path not in self.files:
                self.files.append(path)
                self.file_list.insert("", "end", values=(path.name, self._format_size(path.stat().st_size)))

    def clear_files(self) -> None:
        self.files.clear()
        self.file_list.delete(*self.file_list.get_children())

    def open_selected_result(self) -> None:
        selection = self.results_list.curselection()
        if not selection:
            messagebox.showinfo("Select a video", "Select a compressed video to open.")
            return

        path = self.result_paths[selection[0]]
        try:
            os.startfile(str(path))
        except OSError as exc:
            messagebox.showerror("Could not open video", f"Could not open {path}:\n{exc}")

    def start_compression(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.files:
            messagebox.showwarning("No files", "Select one or more videos first.")
            return
        if not self.ffmpeg:
            messagebox.showerror("FFmpeg missing", "FFmpeg was not found. Install FFmpeg and restart this app.")
            return

        self.compress_button.configure(state="disabled")
        self.progress.configure(value=0)
        self._log("Starting compression...")
        self.worker = threading.Thread(target=self._compress_files, daemon=True)
        self.worker.start()

    def _compress_files(self) -> None:
        total = len(self.files)
        completed = 0
        for source in list(self.files):
            if self.output_mode.get() == "compressed":
                destination_dir = source.parent / "compressed"
            else:
                destination_dir = source.parent
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / f"{source.stem}_{self.codec.get()}_{self.crf.get()}.mp4"

            command = [
                self.ffmpeg or "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-map",
                "0",
                "-map_metadata",
                "0",
                "-c:v",
                "libx264" if self.codec.get() == "h264" else "libx265",
                "-crf",
                str(self.crf.get()),
                "-preset",
                self.preset.get(),
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                "-pix_fmt",
                "yuv420p",
                "-progress",
                "pipe:1",
                "-nostats",
            ]

            resolution = self.max_height.get()
            if resolution != "Original":
                command.extend(["-vf", f"scale=-2:'min({resolution},ih)'"])
            command.append(str(destination))

            self.queue.put(("log", f"Compressing: {source.name}\n"))
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                assert process.stdout is not None
                for line in process.stdout:
                    if line.startswith("out_time_ms="):
                        try:
                            elapsed_ms = int(line.strip().split("=", 1)[1])
                            file_progress = min(100, elapsed_ms / 10000)
                            self.queue.put(("file_progress", file_progress))
                        except ValueError:
                            pass
                    elif line.startswith("progress=end"):
                        self.queue.put(("file_progress", 100))
                process.wait()
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, command)

                before = source.stat().st_size
                after = destination.stat().st_size
                saved = (1 - after / before) * 100 if before else 0
                self.queue.put(("result", (destination, before, after, saved)))
                self.queue.put(
                    (
                        "log",
                        f"Done: {source.name} | {self._format_size(before)} -> "
                        f"{self._format_size(after)} ({saved:.1f}% smaller)\n",
                    )
                )
            except Exception as exc:
                self.queue.put(("log", f"Failed: {source.name}: {exc}\n"))

            completed += 1
            self.queue.put(("total_progress", completed / total * 100))
        self.queue.put(("done", None))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, value = self.queue.get_nowait()
                if kind == "log":
                    self._log(str(value))
                elif kind == "file_progress":
                    pass
                elif kind == "total_progress":
                    self.progress.configure(value=float(value))
                elif kind == "result":
                    path, original_size, compressed_size, saved = value
                    self.result_paths.append(path)
                    self.results_list.insert(
                        "end",
                        f"{path.name}  |  {self._format_size(original_size)} -> "
                        f"{self._format_size(compressed_size)}  |  {saved:.1f}% smaller",
                    )
        except Empty:
            pass

        if self.queue.empty() and self.worker and not self.worker.is_alive():
            if self.compress_button["state"] == "disabled":
                self.compress_button.configure(state="normal")
        self.after(100, self._poll_queue)

    def _log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message)
        self.log.see("end")
        self.log.configure(state="disabled")

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} TB"


if __name__ == "__main__":
    app = VideoCompressorApp()
    app.mainloop()
