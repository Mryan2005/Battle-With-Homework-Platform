import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
import sys  # 新增导入

import pyautogui
import keyboard

# 新增：Windows API 相关定义
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    # 定义 Windows API 常量
    WM_INPUTLANGCHANGEREQUEST = 0x0050
    # 美式键盘布局标识符
    HKL_EN_US = 0x04090409

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01  # 调整停顿时间以适应按键模拟


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("自动输入工具")
        self.root.geometry("560x360")

        self.status_var = tk.StringVar(
            value="从剪贴板获取内容，点击按钮或按快捷键后 2 秒输入。"
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
            root, text="开始自动输入（2 秒后）", command=self.on_start
        )
        self.btn.pack(pady=10)

        # 移除旧的 Tkinter 快捷键绑定
        # self.HOTKEY_TAG = "HOTKEY"
        # self._install_hotkey_priority()

        # 新增：设置全局快捷键
        self._setup_global_hotkey()

        # 可选：按钮文本显示快捷键提示
        self.btn.configure(text="开始自动输入（2 秒后） [Ctrl+Alt+V]")

        self.pending_text = ""
        self.countdown_left = 0  # 新增：用于倒计时
        self.after_id = None  # 用于存储 after 任务 ID
        self.paste_thread = None  # 用于存储输入线程
        self.stop_event = threading.Event()  # 用于中断线程的信号

        # 新增：确保程序关闭时注销快捷键
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # 移除旧的 Tkinter 快捷键安装方法
    # def _install_hotkey_priority(self): ...

    # 新增：Windows 平台下的 API 辅助函数
    def _get_foreground_window_pid(self):
        if sys.platform != 'win32':
            return None, None
        hwnd = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return tid, hwnd

    def _get_current_keyboard_layout(self):
        if sys.platform != 'win32':
            return None
        tid, _ = self._get_foreground_window_pid()
        if not tid:
            return None
        return user32.GetKeyboardLayout(tid)

    def _switch_keyboard_layout(self, layout_hkl):
        if sys.platform != 'win32':
            return
        _, hwnd = self._get_foreground_window_pid()
        if not hwnd:
            return
        user32.PostMessageA(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, layout_hkl)
        time.sleep(0.1)  # 等待布局切换生效

    # 新增：设置全局快捷键
    def _setup_global_hotkey(self):
        try:
            # suppress=True 会阻止此快捷键事件被其他程序捕获
            keyboard.add_hotkey(
                "ctrl+alt+v", self._on_global_hotkey, suppress=True
            )
            # 添加诊断信息
            print("全局快捷键 Ctrl+Alt+V 已注册。")
            # 给予 keyboard 库后台线程一点时间来设置钩子
            time.sleep(0.01)
        except Exception as e:
            # 如果注册失败（例如在某些环境下），则显示错误
            print(f"注册全局快捷键失败: {e}")
            messagebox.showwarning("警告", f"注册全局快捷键失败: {e}\n\n快捷键功能可能无法使用。")

    # 新增：全局快捷键的回调
    def _on_global_hotkey(self):
        # 添加诊断信息
        print("全局快捷键 Ctrl+Alt+V 被触发！")
        # 检查按钮状态，如果正在操作，则中断它
        if self.btn["state"] == "disabled":
            print("操作正在进行中，发送中断信号。")
            self.root.after(0, self._stop_current_operation)
        else:
            # 从非 GUI 线程安全地调用 GUI 更新
            self.root.after(0, self.on_start)

    def on_start(self):
        # 改为：从剪贴板读取，不再读取多行文本框
        content = self._get_clipboard_text()
        if not content:
            self.status_var.set("剪贴板为空或无法读取。")
            try:
                self.root.bell()
            except Exception:
                pass
            return

        self.pending_text = content
        self.btn.config(state="disabled")
        self.countdown_left = 2  # 设置 2 秒倒计时
        self.status_var.set("即将开始：2 秒后自动输入剪贴板内容。请将光标放到目标位置…")
        # 最小化窗口，方便切换到目标输入处
        try:
            self.root.iconify()
        except Exception:
            pass
        # 恢复倒计时逻辑
        self.after_id = self.root.after(1000, self._tick)

    # 新增：读取剪贴板文本
    def _get_clipboard_text(self) -> str:
        try:
            txt = self.root.clipboard_get()
            return txt if isinstance(txt, str) and txt else ""
        except Exception:
            return ""

    # 新增：恢复 _tick 方法用于倒计时
    def _tick(self):
        self.countdown_left -= 1
        if self.countdown_left <= 0:
            self.status_var.set("正在输入…")
            self.after_id = self.root.after(50, self._perform_paste)
            return
        self.status_var.set(
            f"即将开始：{self.countdown_left} 秒后自动输入剪贴板内容。请将光标放到目标位置…"
        )
        self.after_id = self.root.after(1000, self._tick)

    def _perform_paste(self):
        self.stop_event.clear()  # 清除上一次的中断信号
        self.paste_thread = threading.Thread(target=self._threaded_paste, daemon=True)
        self.paste_thread.start()

    # 移除旧的 _process_text_for_typing 方法
    # def _process_text_for_typing(self, text: str) -> str: ...

    # 新增：在单独线程中执行输入，避免阻塞 GUI
    def _threaded_paste(self):
        original_layout = None
        try:
            # 仅在 Windows 平台下切换输入法
            if sys.platform == 'win32':
                original_layout = self._get_current_keyboard_layout()
                if original_layout and original_layout != HKL_EN_US:
                    print(f"当前输入法: {hex(original_layout)}，切换到美式键盘...")
                    self._switch_keyboard_layout(HKL_EN_US)

            lines = self.pending_text.replace("\r\n", "\n").replace("\r", "\n").split('\n')
            current_indent = 0

            for i, line in enumerate(lines):
                if self.stop_event.is_set():
                    print("输入被中断。")
                    self.root.after(0, self.status_var.set, "操作已中断。")
                    return

                # 计算目标缩进
                target_indent = 0
                for char in line:
                    if char == '\t':
                        target_indent += 1
                    else:
                        break

                line_content = line[target_indent:]

                # 调整缩进
                indent_diff = target_indent - current_indent
                if indent_diff > 0:
                    for _ in range(indent_diff):
                        pyautogui.press('tab')
                elif indent_diff < 0:
                    for _ in range(abs(indent_diff)):
                        pyautogui.hotkey('shift', 'tab')

                current_indent = target_indent

                # 输入行内容
                if line_content:
                    pyautogui.write(line_content)

                # 如果不是最后一行，则换行
                if i < len(lines) - 1:
                    pyautogui.press('enter')

            # 只有在未被中断时才显示完成
            if not self.stop_event.is_set():
                self.root.after(0, self.status_var.set, "已完成输入。")
        except Exception as e:
            self.root.after(
                0, messagebox.showerror, "错误", f"自动输入失败：{e}"
            )
            self.root.after(0, self.status_var.set, "自动输入失败。")
        finally:
            # 恢复原始输入法
            if sys.platform == 'win32' and original_layout and original_layout != HKL_EN_US:
                print(f"恢复原始输入法: {hex(original_layout)}")
                self._switch_keyboard_layout(original_layout)

            # 恢复按钮与窗口（在主线程中执行）
            if not self.stop_event.is_set():
                self.root.after(0, self._reset_ui)

    # 新增：停止当前操作
    def _stop_current_operation(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.stop_event.set()  # 设置中断信号
        self._reset_ui()
        self.status_var.set("操作已中断。准备就绪。")

    # 新增：重置 UI 状态
    def _reset_ui(self):
        try:
            if self.root.state() == "iconic":
                self.root.deiconify()
        except Exception:
            pass
        self.btn.config(state="normal")

    # 新增：处理窗口关闭事件
    def on_closing(self):
        self._stop_current_operation()  # 确保退出前停止所有活动
        try:
            keyboard.unhook_all()  # 移除所有快捷键钩子
        except Exception as e:
            print(f"注销快捷键时出错: {e}")
        self.root.destroy()


if __name__ == "__main__":
    # 添加运行提示
    print("正在启动应用... 如果全局快捷键无效，请尝试以管理员权限运行此脚本。")
    root = tk.Tk()
    app = App(root)
    root.mainloop()
