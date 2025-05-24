# -*- coding: utf-8 -*-
"""
文件操作工具模块
包含解包和打包.deb文件的核心功能
"""

import os
import shutil
import subprocess
from datetime import datetime
import platform

from .system_utils import set_debian_permissions, get_package_info_from_control, suggest_output_filename


def find_dpkg_deb():
    """
    查找dpkg-deb命令的路径
    
    Returns:
        str: dpkg-deb的完整路径，如果找不到则返回None
    """
    # 可能的dpkg-deb路径
    possible_paths = [
        "dpkg-deb",  # 系统PATH中
        "/usr/bin/dpkg-deb",
        "/usr/local/bin/dpkg-deb",
        "/opt/homebrew/bin/dpkg-deb",  # Homebrew on Apple Silicon
        "/usr/local/opt/dpkg/bin/dpkg-deb",  # Homebrew on Intel
    ]
    
    # 在Windows上可能的路径
    if platform.system() == "Windows":
        possible_paths.extend([
            r"C:\Program Files\dpkg\bin\dpkg-deb.exe",
            r"C:\dpkg\bin\dpkg-deb.exe",
        ])
    
    # 检查每个可能的路径
    for path in possible_paths:
        try:
            # 尝试运行dpkg-deb --version
            result = subprocess.run([path, "--version"], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    
    # 最后尝试使用which/where命令
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["where", "dpkg-deb"], 
                                  capture_output=True, 
                                  text=True)
        else:
            result = subprocess.run(["which", "dpkg-deb"], 
                                  capture_output=True, 
                                  text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    return None


def unpack_deb_file(deb_path, output_dir):
    """
    解包.deb文件

    Args:
        deb_path: .deb文件路径
        output_dir: 输出目录

    Returns:
        tuple: (成功标志, 消息, 目标目录)
    """
    try:
        # 安全路径验证
        deb_path = os.path.abspath(os.path.expanduser(deb_path))
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        
        # 验证文件
        if not os.path.exists(deb_path):
            return False, f"文件不存在: {deb_path}", None
        if not deb_path.endswith('.deb'):
            return False, "不是有效的.deb文件", None
        if os.path.getsize(deb_path) > 500 * 1024 * 1024:
            return False, "文件过大（超过500MB）", None
        
        # 准备目标目录（以.deb文件命名的文件夹）
        deb_name = os.path.splitext(os.path.basename(deb_path))[0]
        target_dir = os.path.join(output_dir, deb_name)

        # 如果目标目录已存在，删除它
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        # 创建目标目录
        os.makedirs(target_dir, exist_ok=True)

        # 查找dpkg-deb
        dpkg_deb = find_dpkg_deb()
        if not dpkg_deb:
            return False, "'dpkg-deb' tool not installed or not in PATH.\nPlease install dpkg to use this feature.\nOn macOS: brew install dpkg\nOn Linux: sudo apt-get install dpkg", None
        
        # 提取文件系统内容
        result1 = subprocess.run(
            [dpkg_deb, "-x", deb_path, target_dir],
            capture_output=True, text=True
        )

        # 提取control文件到DEBIAN/
        debian_dir = os.path.join(target_dir, "DEBIAN")
        os.makedirs(debian_dir, exist_ok=True)
        result2 = subprocess.run(
            [dpkg_deb, "-e", deb_path, debian_dir],
            capture_output=True, text=True
        )

        # 检查解包结果
        if result1.returncode != 0 or result2.returncode != 0:
            error_msg = ""
            if result1.stderr:
                error_msg += result1.stderr.strip() + "\n"
            if result2.stderr:
                error_msg += result2.stderr.strip() + "\n"
            return False, error_msg, target_dir

        # 设置DEBIAN目录权限
        permissions_set, permission_errors = set_debian_permissions(debian_dir)

        # 收集输出消息
        output_msg = ""
        if result1.stdout:
            output_msg += result1.stdout.strip() + "\n"
        if result2.stdout:
            output_msg += result2.stdout.strip() + "\n"

        # 添加权限设置信息
        for perm_msg in permissions_set:
            output_msg += perm_msg + "\n"

        if permission_errors:
            for error in permission_errors:
                output_msg += f"Warning: {error}\n"

        return True, output_msg, target_dir

    except FileNotFoundError:
        return False, "'dpkg-deb' tool not installed or not in PATH.\nPlease install dpkg to use this feature.", None
    except Exception as e:
        return False, f"Exception during unpacking: {str(e)}", None


def pack_folder_to_deb(folder_path, output_path):
    """
    将文件夹打包为.deb文件

    Args:
        folder_path: 要打包的文件夹路径
        output_path: 输出.deb文件路径

    Returns:
        tuple: (成功标志, 消息)
    """
    # 初始化变量
    temp_structure_file = None
    structure_file = os.path.join(folder_path, "DIRECTORY_STRUCTURE.md")
    
    try:
        # 检查文件夹结构
        debian_dir = os.path.join(folder_path, "DEBIAN")
        control_file = os.path.join(debian_dir, "control")

        if not os.path.isdir(debian_dir):
            return False, f"Missing DEBIAN directory in {folder_path}"

        if not os.path.isfile(control_file):
            return False, f"Missing control file in {debian_dir}"

        # 临时移动DIRECTORY_STRUCTURE.md文件（如果存在）
        if os.path.exists(structure_file):
            temp_structure_file = structure_file + ".tmp"
            shutil.move(structure_file, temp_structure_file)

        # 查找dpkg-deb
        dpkg_deb = find_dpkg_deb()
        if not dpkg_deb:
            # 恢复文件（如果需要）
            if temp_structure_file and os.path.exists(temp_structure_file):
                shutil.move(temp_structure_file, structure_file)
            return False, "'dpkg-deb' tool not installed or not in PATH.\nPlease install dpkg to use this feature.\nOn macOS: brew install dpkg\nOn Linux: sudo apt-get install dpkg"
        
        # 设置DEBIAN目录权限
        permissions_set, permission_errors = set_debian_permissions(debian_dir)

        # 构建dpkg-deb命令
        build_cmd = [dpkg_deb, "--root-owner-group", "-b", folder_path, output_path]

        # 执行打包命令
        result = subprocess.run(build_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            error_msg = ""
            if result.stdout:
                error_msg += result.stdout.strip() + "\n"
            if result.stderr:
                error_msg += result.stderr.strip() + "\n"
            return False, error_msg

        # 收集输出消息
        output_msg = ""
        if result.stdout:
            output_msg += result.stdout.strip() + "\n"
        if result.stderr:
            output_msg += result.stderr.strip() + "\n"

        # 添加权限设置信息
        for perm_msg in permissions_set:
            output_msg += perm_msg + "\n"

        if permission_errors:
            for error in permission_errors:
                output_msg += f"Warning: {error}\n"

        # 恢复DIRECTORY_STRUCTURE.md文件
        if temp_structure_file and os.path.exists(temp_structure_file):
            shutil.move(temp_structure_file, structure_file)

        return True, output_msg

    except FileNotFoundError:
        # 恢复文件（如果打包失败）
        if temp_structure_file and os.path.exists(temp_structure_file):
            shutil.move(temp_structure_file, structure_file)
        return False, "'dpkg-deb' tool not installed or not in PATH.\nPlease install dpkg to use this feature."
    except Exception as e:
        # 恢复文件（如果打包失败）
        if temp_structure_file and os.path.exists(temp_structure_file):
            shutil.move(temp_structure_file, structure_file)
        return False, f"Exception during packaging: {str(e)}"


def batch_unpack_deb(deb_path, output_dir=None):
    """
    命令行模式下解包deb文件

    Args:
        deb_path: .deb文件路径
        output_dir: 输出目录（可选）

    Returns:
        bool: 成功标志
    """
    if not os.path.exists(deb_path):
        print(f"\nError: File '{deb_path}' does not exist")
        return False

    if not deb_path.lower().endswith('.deb'):
        print(f"\nError: '{deb_path}' is not a .deb file")
        return False

    # 准备输出目录
    if output_dir is None:
        # 默认在当前目录下创建以deb文件名的文件夹
        output_dir = os.path.dirname(os.path.abspath(deb_path))

    print(f"\nUnpacking '{deb_path}' to '{output_dir}'...")

    success, message, target_dir = unpack_deb_file(deb_path, output_dir)

    if success:
        print(f"\nSuccessfully unpacked to: {target_dir}")
        if message:
            print("Details:")
            print(message)
        return True
    else:
        print(f"\nUnpack failed:")
        if message:
            print(message)
        return False


def batch_repack_folder(folder_path, output_path=None):
    """
    命令行模式下打包文件夹

    Args:
        folder_path: 文件夹路径
        output_path: 输出文件路径（可选）

    Returns:
        bool: 成功标志
    """
    if not os.path.isdir(folder_path):
        print(f"\nError: '{folder_path}' is not a valid directory")
        return False

    # 检查目录结构
    debian_dir = os.path.join(folder_path, "DEBIAN")
    control_file = os.path.join(debian_dir, "control")

    if not os.path.isdir(debian_dir):
        print(f"\nError: '{folder_path}' does not contain DEBIAN directory")
        return False

    if not os.path.isfile(control_file):
        print(f"\nError: '{debian_dir}' does not contain control file")
        return False

    # 准备输出路径
    if output_path is None:
        # 从控制文件中提取信息生成文件名
        package_info = get_package_info_from_control(control_file)
        output_name = suggest_output_filename(package_info)
        output_path = os.path.join(os.path.dirname(folder_path), output_name)

    print(f"\nPacking '{folder_path}' to '{output_path}'...")

    success, message = pack_folder_to_deb(folder_path, output_path)

    if success:
        print(f"\nSuccessfully packed to: {output_path}")
        if message:
            print("Details:")
            print(message)
        return True
    else:
        print(f"\nPack failed:")
        if message:
            print(message)
        return False


def validate_control_file(control_content):
    """
    验证control文件格式

    Args:
        control_content: control文件内容

    Returns:
        tuple: (是否有效, 错误消息列表)
    """
    errors = []

    # 检查必填字段
    required_fields = ["Package", "Version", "Architecture", "Description"]
    missing_fields = []

    for field in required_fields:
        if not any(line.startswith(f"{field}:") for line in control_content.splitlines()):
            missing_fields.append(field)

    if missing_fields:
        errors.append(f"Missing required fields: {', '.join(missing_fields)}")

    # 检查字段格式
    for line_num, line in enumerate(control_content.splitlines(), 1):
        if line and not line.startswith(" ") and ":" not in line:
            errors.append(f"Line {line_num}: Invalid field format: '{line}'")

    return len(errors) == 0, errors


def read_control_file(control_path):
    """
    读取control文件内容

    Args:
        control_path: control文件路径

    Returns:
        tuple: (成功标志, 内容或错误消息)
    """
    try:
        with open(control_path, "r", encoding='utf-8') as f:
            return True, f.read()
    except Exception as e:
        return False, str(e)


def write_control_file(control_path, content):
    """
    写入control文件内容

    Args:
        control_path: control文件路径
        content: 文件内容

    Returns:
        tuple: (成功标志, 错误消息)
    """
    try:
        # 确保内容以换行符结束
        if not content.endswith("\n"):
            content += "\n"

        with open(control_path, "w", encoding='utf-8') as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, str(e)


def generate_directory_structure(directory_path, output_file=None):
    """
    生成目录结构的Markdown文件
    
    Args:
        directory_path: 要分析的目录路径
        output_file: 输出文件路径，如果为None则自动生成
    
    Returns:
        tuple: (成功标志, 输出文件路径或错误消息)
    """
    try:
        directory_path = os.path.abspath(directory_path)
        if not os.path.exists(directory_path):
            return False, f"Directory does not exist: {directory_path}"
        
        if output_file is None:
            output_file = os.path.join(directory_path, "DIRECTORY_STRUCTURE.md")
        
        # 生成目录结构
        structure_lines = []
        dir_name = os.path.basename(directory_path)
        
        # 添加标题和基本信息
        structure_lines.append(f"# Directory Structure: {dir_name}")
        structure_lines.append("")
        structure_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        structure_lines.append(f"Total path: `{directory_path}`")
        structure_lines.append("")
        
        # 生成树状结构
        structure_lines.append("## File Tree")
        structure_lines.append("")
        structure_lines.append("```")
        structure_lines.append(f"{dir_name}/")
        
        def scan_directory(path, prefix=""):
            """递归扫描目录"""
            try:
                entries = sorted(os.listdir(path))
                dir_files = []
                dir_subdirs = []
                
                for entry in entries:
                    entry_path = os.path.join(path, entry)
                    if os.path.isdir(entry_path):
                        dir_subdirs.append(entry)
                    else:
                        dir_files.append(entry)
                
                # 先处理目录
                for i, dirname in enumerate(dir_subdirs):
                    is_last_dir = (i == len(dir_subdirs) - 1) and len(dir_files) == 0
                    connector = "└── " if is_last_dir else "├── "
                    structure_lines.append(f"{prefix}{connector}{dirname}/")
                    
                    # 递归处理子目录
                    new_prefix = prefix + ("    " if is_last_dir else "│   ")
                    scan_directory(os.path.join(path, dirname), new_prefix)
                
                # 再处理文件
                for i, filename in enumerate(dir_files):
                    is_last_file = (i == len(dir_files) - 1)
                    connector = "└── " if is_last_file else "├── "
                    
                    # 获取文件大小
                    current_file_path = os.path.join(path, filename)
                    try:
                        size = os.path.getsize(current_file_path)
                        if size < 1024:
                            size_str = f"{size}B"
                        elif size < 1024*1024:
                            size_str = f"{size/1024:.1f}KB"
                        else:
                            size_str = f"{size/(1024*1024):.1f}MB"
                        structure_lines.append(f"{prefix}{connector}{filename} ({size_str})")
                    except Exception:
                        structure_lines.append(f"{prefix}{connector}{filename}")
                        
            except PermissionError:
                structure_lines.append(f"{prefix}├── [Permission Denied]")
            except Exception as scan_error:
                structure_lines.append(f"{prefix}├── [Error: {str(scan_error)}]")
        
        scan_directory(directory_path)
        structure_lines.append("```")
        structure_lines.append("")
        
        # 添加统计信息
        structure_lines.append("## Statistics")
        structure_lines.append("")
        
        total_files = 0
        total_dirs = 0
        total_size = 0
        
        for root, dirs, files in os.walk(directory_path):
            total_dirs += len(dirs)
            total_files += len(files)
            for file in files:
                try:
                    current_file = os.path.join(root, file)
                    total_size += os.path.getsize(current_file)
                except Exception:
                    pass
        
        size_mb = total_size / (1024 * 1024)
        structure_lines.append(f"- **Total Directories**: {total_dirs}")
        structure_lines.append(f"- **Total Files**: {total_files}")
        structure_lines.append(f"- **Total Size**: {size_mb:.2f} MB")
        structure_lines.append("")
        
        # 如果是.deb解包目录，添加包信息
        control_file = os.path.join(directory_path, "DEBIAN", "control")
        if os.path.exists(control_file):
            structure_lines.append("## Package Information")
            structure_lines.append("")
            try:
                with open(control_file, 'r', encoding='utf-8') as f:
                    control_content = f.read()
                structure_lines.append("```")
                structure_lines.append(control_content.strip())
                structure_lines.append("```")
                structure_lines.append("")
            except Exception:
                structure_lines.append("*Could not read control file*")
                structure_lines.append("")
        
        # 重要文件列表
        important_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file in ['control', 'postinst', 'prerm', 'postrm', 'preinst', 'conffiles']:
                    rel_path = os.path.relpath(os.path.join(root, file), directory_path)
                    important_files.append(rel_path)
        
        if important_files:
            structure_lines.append("## Important Files")
            structure_lines.append("")
            for file in sorted(important_files):
                structure_lines.append(f"- `{file}`")
            structure_lines.append("")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(structure_lines))
        
        return True, output_file
        
    except Exception as e:
        return False, f"Error generating directory structure: {str(e)}"
