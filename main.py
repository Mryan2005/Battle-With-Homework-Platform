import tkinter as tk
from tkinter import ttk, messagebox

import pyautogui

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("三秒后自动输入")
        self.root.geometry("560x360")

        self.status_var = tk.StringVar(
            value="在下面输入要自动输入的文本，点击按钮后 3 秒内把光标放到目标位置。"
        )
        status = ttk.Label(root, textvariable=self.status_var, anchor="w")
        status.pack(fill="x", padx=10, pady=(10, 4))

        frame = ttk.Frame(root)
        frame.pack(fill="both", expand=True, padx=10, pady=4)

        self.text = tk.Text(frame, wrap="word", height=10, undo=True)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=yscroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        self.btn = ttk.Button(
            root, text="开始自动输入（3 秒后）", command=self.on_start
        )
        self.btn.pack(pady=10)

        self.pending_text = ""
        self.countdown_left = 0

    def on_start(self):
        content = self.text.get("1.0", "end-1c")
        if not content.strip():
            self.status_var.set("请输入要自动输入的内容。")
            return

        self.pending_text = content
        self.btn.config(state="disabled")
        self.countdown_left = 3
        self.status_var.set("即将开始：3 秒后自动输入。请将光标放到目标位置…")
        # 最小化窗口，方便切换到目标输入处
        try:
            self.root.iconify()
        except Exception:
            pass
        self.root.after(1000, self._tick)

    def _tick(self):
        # 修正倒计时：精确等待满 3 秒后再开始输入
        self.countdown_left -= 1
        if self.countdown_left <= 0:
            self.status_var.set("正在输入…")
            self.root.after(50, self._perform_paste)
            return
        self.status_var.set(
            f"即将开始：{self.countdown_left} 秒后自动输入。请将光标放到目标位置…"
        )
        self.root.after(1000, self._tick)

    def _perform_paste(self):
        try:
            # 直接逐字输入，不使用剪贴板或粘贴快捷键；保留多行换行
            txt = self.pending_text.replace("\r\n", "\n").replace("\r", "\n")
            pyautogui.write(txt, interval=0.005)
            self.status_var.set("已完成输入。")
        except Exception as e:
            messagebox.showerror("错误", f"自动输入失败：{e}")
            self.status_var.set("自动输入失败。")
        finally:
            # 恢复按钮与窗口
            try:
                self.root.deiconify()
            except Exception:
                pass
            self.btn.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
