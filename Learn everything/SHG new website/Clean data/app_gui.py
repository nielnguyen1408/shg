# app_gui.py
import os, tkinter as tk
from tkinter import filedialog, messagebox
import traceback
import vn_clean_and_split4_v2 as worker

def main():
    root = tk.Tk(); root.withdraw()
    try:
        file_paths = filedialog.askopenfilenames(
            title="Chọn file Excel để xử lý",
            filetypes=[("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")]
        )
        if not file_paths:
            messagebox.showinfo("Thông báo", "Bạn chưa chọn file nào."); return

        created = []
        for p in file_paths:
            folder = os.path.dirname(p)
            old_cwd = os.getcwd()
            try:
                os.chdir(folder)             # đổi CWD về thư mục chứa file
                worker.process_files([p])    # giữ logic cũ nếu hàm nhận list
                # Nếu bạn biết tên file output, có thể tự cộng vào `created` ở đây
            finally:
                os.chdir(old_cwd)

        messagebox.showinfo("Hoàn tất", "Đã xử lý xong tất cả các file!\n(Kiểm tra cùng thư mục với file nguồn)")

    except Exception as e:
        messagebox.showerror("Lỗi", f"{e}\n\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
