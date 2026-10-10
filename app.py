"""Windows desktop prompt assistant. Standard-library runtime, local Ollama."""
import json
import queue
import shutil
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.request import Request, urlopen
from host import BridgeHost\nfrom offline_planner import generate_offline_plan
from remote_script.AbletonPromptBridge.protocol import SCHEMA, validate_plan

OLLAMA = "http://127.0.0.1:11434/api/chat"


def asset_path(relative):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / relative


def generate_plan(prompt, snapshot, model):
    payload = {"model": model, "stream": False, "format": "json", "options": {"temperature": 0.1},
               "messages": [{"role": "system", "content": "You are a careful Ableton assistant. " + SCHEMA},
                            {"role": "user", "content": json.dumps({"live_state": snapshot["state"], "request": prompt}, ensure_ascii=False)}]}
    request = Request(OLLAMA, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=180) as response:
        data = json.loads(response.read().decode("utf-8"))
    return validate_plan(json.loads(data["message"]["content"]))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ableton Control · Prompt Assistant")
        self.geometry("900x740")
        self.minsize(740, 620)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.messages = queue.Queue()
        self.plan = None
        self.expected_revision = None
        self.busy = False
        self.running = False
        try:
            self.host = BridgeHost()
        except OSError as exc:
            messagebox.showerror("Start fehlgeschlagen", "Port 8765 ist belegt. Schließe eine zweite Instanz der App.\n\n" + str(exc))
            self.destroy()
            raise SystemExit(1)

        style = ttk.Style(self)
        if "clam" in style.theme_names(): style.theme_use("clam")
        style.configure("TButton", padding=8)
        main = ttk.Frame(self, padding=22)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Ableton per Prompt", font=("Helvetica", 23, "bold")).pack(anchor="w")
        ttk.Label(main, text="Auftrag eingeben → Vorschlag prüfen → in Live ausführen", font=("Segoe UI", 11)).pack(anchor="w", pady=(4, 12))
        row = ttk.Frame(main)
        row.pack(fill="x")
        self.connection = ttk.Label(row, text="Ableton nicht verbunden")
        self.connection.pack(side="left")
        ttk.Button(row, text="Ableton-Brücke installieren", command=self.install).pack(side="right")
        settings = ttk.Frame(main)
        settings.pack(fill="x", pady=12)
        ttk.Label(settings, text="Ollama-Modell:").pack(side="left")
        self.model = ttk.Entry(settings, width=24)
        self.model.insert(0, "offline" if sys.platform == "darwin" else "qwen2.5:7b")
        self.model.pack(side="left", padx=8)
        ttk.Label(settings, text="Offline (Mac) oder Ollama · kein Cloud-API-Schlüssel").pack(side="left")
        self.prompt = tk.Text(main, height=5, wrap="word", font=("Segoe UI", 11))
        self.prompt.pack(fill="x")
        self.prompt.insert("1.0", "Erstelle eine MIDI-Spur namens Bass und setze das Tempo auf 118 BPM.")
        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=12)
        self.plan_button = ttk.Button(buttons, text="Vorschlag erstellen", command=self.plan_request)
        self.plan_button.pack(side="left")
        self.execute_button = ttk.Button(buttons, text="In Live ausführen", state="disabled", command=self.execute)
        self.execute_button.pack(side="left", padx=10)
        ttk.Label(main, text="Vorschlag und genaue Aktionen", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.preview = tk.Text(main, height=13, wrap="word", font=("Menlo", 10), state="disabled")
        self.preview.pack(fill="both", expand=True, pady=6)
        ttk.Label(main, text="Unterstützt: Spuren, Tempo, Solo/Mute/Arm, Lautstärke, MIDI-Clips und Parameter vorhandener Geräte.", wraplength=800).pack(anchor="w", pady=8)
        self.status = ttk.Label(main, text="Installiere die Brücke und wähle sie in Live unter Bedienoberfläche/Control Surface aus.", wraplength=800)
        self.status.pack(anchor="w")
        self.after(250, self.poll)

    def install(self):
        messagebox.showinfo("User Library wählen", "Wähle den User-Library-Ordner, den Live unter Einstellungen → Library anzeigt. Die Brücke wird nach Remote Scripts/AbletonPromptBridge kopiert.")
        folder = filedialog.askdirectory(title="Ableton User Library auswählen")
        if not folder: return
        target = Path(folder) / "Remote Scripts" / "AbletonPromptBridge"
        if target.exists() and not messagebox.askyesno("Brücke aktualisieren", "AbletonPromptBridge existiert bereits. Die zugehörigen Python-Dateien ersetzen?"):
            return
        try:
            target.mkdir(parents=True, exist_ok=True)
            source = asset_path("remote_script/AbletonPromptBridge")
            for file in source.glob("*.py"):
                shutil.copy2(file, target / file.name)
            messagebox.showinfo("Brücke installiert", "Live neu starten. Einstellungen → MIDI → Bedienoberfläche: AbletonPromptBridge. Eingang und Ausgang auf None/Keine lassen. Diese Desktop-App geöffnet lassen.")
        except OSError as exc:
            messagebox.showerror("Installation fehlgeschlagen", str(exc))

    def plan_request(self):
        snap = self.host.current()
        if not snap:
            messagebox.showinfo("Ableton fehlt", "Starte Live und aktiviere AbletonPromptBridge als Bedienoberfläche.")
            return
        prompt = self.prompt.get("1.0", "end").strip()
        model = self.model.get().strip()
        if not prompt or not model: return
        self.plan = None
        self.busy = True
        self.plan_button.configure(state="disabled")
        self.execute_button.configure(state="disabled")
        self.status.configure(text="Lokale KI erstellt den Vorschlag …")
        threading.Thread(target=self.worker, args=(prompt, snap, model), daemon=True).start()

    def worker(self, prompt, snap, model):
        try:
            plan = generate_plan(prompt, snap, model)
            self.messages.put(("plan", plan, snap["revision"]))
        except Exception as exc:
            self.messages.put(("error", str(exc), None))

    def execute(self):
        if not self.plan or self.running: return
        try:
            self.host.submit(self.plan, self.expected_revision)
            self.running = True
            self.execute_button.configure(state="disabled")
            self.plan_button.configure(state="disabled")
            self.status.configure(text="Auftrag an Ableton übergeben — warte auf Ausführungsbestätigung …")
        except (ValueError, queue.Full) as exc:
            self.execute_button.configure(state="disabled")
            messagebox.showerror("Auftrag nicht gesendet", str(exc))

    def poll(self):
        snap = self.host.current()
        if snap:
            self.connection.configure(text="Ableton verbunden · %s BPM · %s Spuren" % (snap["state"]["tempo"], len(snap["state"]["tracks"])))
        else:
            self.connection.configure(text="Ableton nicht verbunden")
        while not self.messages.empty():
            kind, value, rev = self.messages.get_nowait()
            self.busy = False
            self.plan_button.configure(state="normal")
            if kind == "plan":
                self.plan, self.expected_revision = value, rev
                self.preview.configure(state="normal")
                self.preview.delete("1.0", "end")
                self.preview.insert("1.0", value["summary"] + "\n\n" + json.dumps(value["actions"], indent=2, ensure_ascii=False))
                self.preview.configure(state="disabled")
                self.execute_button.configure(state="normal" if value["actions"] else "disabled")
                self.status.configure(text="Prüfe die Aktionen. Der Klick auf 'In Live ausführen' bestätigt genau diesen Vorschlag.")
            else:
                self.status.configure(text="Vorschlag fehlgeschlagen")
                messagebox.showerror("KI nicht verfügbar / ungültiger Plan", "Prüfe Ollama und das Modell. Befehl: ollama pull " + self.model.get() + "\n\n" + value)
        while not self.host.events.empty():
            result = self.host.events.get_nowait()["result"]
            self.running = False
            self.plan = None
            self.plan_button.configure(state="normal")
            self.execute_button.configure(state="disabled")
            if result["ok"]:
                self.status.configure(text="Ableton bestätigt: %s Aktionen ausgeführt." % result["completed"])
            else:
                self.status.configure(text="Ableton meldet einen Fehler")
                messagebox.showerror("Ableton-Ausführung", "%s\n\n%s Aktionen vollständig abgeschlossen. Eventuelle Teiländerungen in Live mit Undo prüfen." % (result.get("error"), result.get("completed", 0)))
        self.after(250, self.poll)

    def close(self):
        self.host.close()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
