#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimpleTweakEditor - iOS越狱插件简易修改工具
"""

import os
import sys
import shutil
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path


class SimpleTweakEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("SimpleTweakEditor - iOS越狱插件简易修改工具")
        self.root.geometry("600x400")

        # 设置变量
        self.deb_path = tk.StringVar()
        self.extract_path = tk.StringVar()
        self.output_path = tk.StringVar()

        # 创建界面
        self.create_widgets()

        # 设置日志区域
        self.log_area = tk.Text(self.root, height=10, wrap=tk.WORD)
        self.log_area.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        # 添加滚动条
        scrollbar = tk.Scrollbar(self.root, command=self.log_area.yview)
        scrollbar.grid(row=5, column=3, sticky="ns")
        self.log_area.config(yscrollcommand=scrollbar.set)

        # 设置网格权重
        self.root.grid_rowconfigure(5, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

    def create_widgets(self):
        # 第一行: 选择deb文件
        ttk.Label(self.root, text="选择DEB文件:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ttk.Entry(self.root, textvariable=self.deb_path, width=50).grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        ttk.Button(self.root, text="浏览...", command=self.browse_deb).grid(row=0, column=2, padx=5, pady=10)

        # 第二行: 解包路径
        ttk.Label(self.root, text="解包路径:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ttk.Entry(self.root, textvariable=self.extract_path, width=50).grid(row=1, column=1, padx=5, pady=10,
                                                                            sticky="ew")
        ttk.Button(self.root, text="浏览...", command=self.browse_extract).grid(row=1, column=2, padx=5, pady=10)

        # 第三行: 解包按钮
        ttk.Button(self.root, text="解包DEB文件", command=self.extract_deb).grid(row=2, column=0, columnspan=3, padx=10,
                                                                                 pady=10)

        # 第四行: 输出deb路径
        ttk.Label(self.root, text="输出DEB路径:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        ttk.Entry(self.root, textvariable=self.output_path, width=50).grid(row=3, column=1, padx=5, pady=10,
                                                                           sticky="ew")
        ttk.Button(self.root, text="浏览...", command=self.browse_output).grid(row=3, column=2, padx=5, pady=10)

        # 第五行: 重新打包按钮
        ttk.Button(self.root, text="重新打包为DEB文件", command=self.repack_deb).grid(row=4, column=0, columnspan=3,
                                                                                      padx=10, pady=10)

    def log(self, message):
        """向日志区域添加消息"""
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.root.update()

    def browse_deb(self):
        """浏览选择deb文件"""
        filename = filedialog.askopenfilename(
            title="选择DEB文件",
            filetypes=[("DEB文件", "*.deb"), ("所有文件", "*.*")]
        )
        if filename:
            self.deb_path.set(filename)
            # 自动设置默认的解包路径
            default_extract = os.path.join(os.path.dirname(filename),
                                           os.path.basename(filename).replace('.deb', '_extracted'))
            self.extract_path.set(default_extract)
            # 设置默认输出路径
            default_output = os.path.join(os.path.dirname(filename),
                                          os.path.basename(filename).replace('.deb', '_modified.deb'))
            self.output_path.set(default_output)

    def browse_extract(self):
        """浏览选择解包路径"""
        directory = filedialog.askdirectory(title="选择解包目录")
        if directory:
            self.extract_path.set(directory)

    def browse_output(self):
        """浏览选择输出deb文件路径"""
        filename = filedialog.asksaveasfilename(
            title="保存DEB文件",
            filetypes=[("DEB文件", "*.deb")],
            defaultextension=".deb"
        )
        if filename:
            self.output_path.set(filename)

    def extract_deb(self):
        """解包deb文件"""
        deb_file = self.deb_path.get()
        extract_dir = self.extract_path.get()

        if not deb_file:
            messagebox.showerror("错误", "请选择DEB文件")
            return

        if not extract_dir:
            messagebox.showerror("错误", "请选择解包路径")
            return

        # 确保解包目录存在
        os.makedirs(extract_dir, exist_ok=True)

        self.log(f"正在解包 {deb_file} 到 {extract_dir}...")

        try:
            # 尝试使用dpkg-deb解包
            result = subprocess.run(
                ["dpkg-deb", "-R", deb_file, extract_dir],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.log("dpkg-deb解包失败，尝试替代方法...")

                # 创建临时目录
                temp_dir = tempfile.mkdtemp()
                try:
                    # 使用ar提取文件
                    subprocess.run(["ar", "x", deb_file], cwd=temp_dir, check=True)

                    # 检查提取的文件
                    data_tar = None
                    control_tar = None
                    for file in os.listdir(temp_dir):
                        if file.startswith("data.tar"):
                            data_tar = os.path.join(temp_dir, file)
                        elif file.startswith("control.tar"):
                            control_tar = os.path.join(temp_dir, file)

                    if data_tar and control_tar:
                        # 提取data.tar.*
                        subprocess.run(["tar", "-xf", data_tar, "-C", extract_dir], check=True)

                        # 创建DEBIAN目录
                        debian_dir = os.path.join(extract_dir, "DEBIAN")
                        os.makedirs(debian_dir, exist_ok=True)

                        # 提取control.tar.*到临时目录
                        control_extract = os.path.join(temp_dir, "control")
                        os.makedirs(control_extract, exist_ok=True)
                        subprocess.run(["tar", "-xf", control_tar, "-C", control_extract], check=True)

                        # 移动控制文件到DEBIAN目录
                        for item in os.listdir(control_extract):
                            src = os.path.join(control_extract, item)
                            dst = os.path.join(debian_dir, item)
                            shutil.copy2(src, dst)
                    else:
                        raise Exception("未找到data.tar和control.tar文件")

                    self.log("替代方法解包成功!")
                except Exception as e:
                    self.log(f"替代解包方法失败: {str(e)}")
                    messagebox.showerror("错误", f"无法解包DEB文件: {str(e)}")
                    return
                finally:
                    # 清理临时目录
                    shutil.rmtree(temp_dir)
            else:
                self.log("dpkg-deb解包成功!")

            # 设置文件权限
            self.fix_permissions(extract_dir)

            self.log(f"成功解包DEB文件到: {extract_dir}")
            messagebox.showinfo("成功", "DEB文件解包成功!")

        except Exception as e:
            self.log(f"解包时出错: {str(e)}")
            messagebox.showerror("错误", f"解包失败: {str(e)}")

    def fix_permissions(self, directory):
        """修复提取文件的权限"""
        # 确保DEBIAN/control有正确权限
        control_file = os.path.join(directory, "DEBIAN", "control")
        if os.path.exists(control_file):
            os.chmod(control_file, 0o644)  # rw-r--r--

        # 确保所有可执行文件权限正确
        for root, dirs, files in os.walk(directory):
            # 设置目录权限
            for d in dirs:
                path = os.path.join(root, d)
                os.chmod(path, 0o755)  # rwxr-xr-x

            # 对可能的可执行文件设置权限
            for f in files:
                path = os.path.join(root, f)
                # 检查是否在bin目录下或以.sh结尾
                if "bin" in root or f.endswith(".sh") or not os.path.splitext(f)[1]:
                    os.chmod(path, 0o755)  # rwxr-xr-x
                else:
                    os.chmod(path, 0o644)  # rw-r--r--

    def repack_deb(self):
        """重新打包为deb文件"""
        extract_dir = self.extract_path.get()
        output_file = self.output_path.get()

        if not extract_dir:
            messagebox.showerror("错误", "请指定要打包的目录")
            return

        if not output_file:
            messagebox.showerror("错误", "请指定输出DEB文件路径")
            return

        if not os.path.exists(extract_dir):
            messagebox.showerror("错误", f"目录不存在: {extract_dir}")
            return

        # 确保DEBIAN目录存在
        debian_dir = os.path.join(extract_dir, "DEBIAN")
        if not os.path.exists(debian_dir):
            messagebox.showerror("错误", f"找不到DEBIAN目录: {debian_dir}")
            return

        # 确保control文件存在
        control_file = os.path.join(debian_dir, "control")
        if not os.path.exists(control_file):
            messagebox.showerror("错误", f"找不到control文件: {control_file}")
            return

        self.log(f"正在打包 {extract_dir} 到 {output_file}...")

        try:
            # 修复文件权限
            self.fix_permissions(extract_dir)

            # 使用dpkg-deb打包
            result = subprocess.run(
                ["dpkg-deb", "-b", extract_dir, output_file],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.log(f"打包错误: {result.stderr}")
                messagebox.showerror("错误", f"打包失败: {result.stderr}")
                return

            self.log(f"成功打包DEB文件: {output_file}")
            messagebox.showinfo("成功", "DEB文件打包成功!")

        except Exception as e:
            self.log(f"打包时出错: {str(e)}")
            messagebox.showerror("错误", f"打包失败: {str(e)}")


def check_dependencies():
    """检查必要的依赖是否已安装"""
    missing = []

    # 检查dpkg-deb
    try:
        subprocess.run(["dpkg-deb", "--version"],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    except:
        missing.append("dpkg-deb")

    # 检查ar
    try:
        subprocess.run(["ar", "--version"],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    except:
        missing.append("ar")

    # 检查tar
    try:
        subprocess.run(["tar", "--version"],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    except:
        missing.append("tar")

    return missing


def main():
    # 检查依赖
    missing = check_dependencies()
    if missing:
        print(f"缺少必要的依赖: {', '.join(missing)}")
        print("请安装缺少的依赖后再运行此程序")

        if "dpkg-deb" in missing:
            if sys.platform == "darwin":  # macOS
                print("在macOS上安装dpkg: brew install dpkg")
            elif sys.platform.startswith("linux"):
                print("在Linux上安装dpkg: sudo apt-get install dpkg")

        if "ar" in missing or "tar" in missing:
            if sys.platform == "darwin":  # macOS
                print("在macOS上安装binutils: brew install binutils")
            elif sys.platform.startswith("linux"):
                print("在Linux上安装binutils: sudo apt-get install binutils")

        sys.exit(1)

    # 创建GUI
    root = tk.Tk()
    app = SimpleTweakEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
