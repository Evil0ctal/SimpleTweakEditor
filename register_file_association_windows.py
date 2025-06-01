# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-31
作者: Evil0ctal

中文介绍:
Windows 文件关联注册脚本
将 .plist 文件与 SimpleTweakEditor 关联，支持右键菜单"使用 SimpleTweakEditor 打开"

英文介绍:
Windows File Association Registration Script
Associates .plist files with SimpleTweakEditor, adds "Open with SimpleTweakEditor" context menu
"""

import os
import sys
import winreg
import ctypes


def is_admin():
    """检查是否有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def register_plist_association():
    """注册 .plist 文件关联"""
    
    # 获取程序路径
    if getattr(sys, 'frozen', False):
        # 打包后的 exe
        app_path = sys.executable
    else:
        # Python 脚本
        app_path = os.path.abspath(sys.argv[0])
        if app_path.endswith('.py'):
            # 构建启动命令
            python_path = sys.executable
            main_py = os.path.join(os.path.dirname(app_path), 'main.py')
            app_path = f'"{python_path}" "{main_py}"'
    
    try:
        # 创建 .plist 文件类型
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, '.plist') as key:
            winreg.SetValue(key, '', winreg.REG_SZ, 'SimpleTweakEditor.PlistFile')
            winreg.SetValueEx(key, 'Content Type', 0, winreg.REG_SZ, 'application/x-plist')
        
        # 创建 SimpleTweakEditor.PlistFile 类型
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, 'SimpleTweakEditor.PlistFile') as key:
            winreg.SetValue(key, '', winreg.REG_SZ, 'Property List File')
            
            # 设置图标
            with winreg.CreateKey(key, 'DefaultIcon') as icon_key:
                icon_path = os.path.join(os.path.dirname(app_path), 'icons', 'app_icon.ico')
                if os.path.exists(icon_path):
                    winreg.SetValue(icon_key, '', winreg.REG_SZ, icon_path)
            
            # 设置打开命令
            with winreg.CreateKey(key, r'shell\open\command') as cmd_key:
                winreg.SetValue(cmd_key, '', winreg.REG_SZ, f'{app_path} "%1"')
            
            # 添加右键菜单 "使用 SimpleTweakEditor 编辑"
            with winreg.CreateKey(key, r'shell\Edit with SimpleTweakEditor') as edit_key:
                winreg.SetValue(edit_key, '', winreg.REG_SZ, '使用 SimpleTweakEditor 编辑(&E)')
                # 设置图标
                if os.path.exists(icon_path):
                    winreg.SetValueEx(edit_key, 'Icon', 0, winreg.REG_SZ, icon_path)
                
                with winreg.CreateKey(edit_key, 'command') as cmd_key:
                    winreg.SetValue(cmd_key, '', winreg.REG_SZ, f'{app_path} "%1"')
        
        # 刷新 Windows Explorer
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
        
        print("✅ 文件关联注册成功！")
        print(f"✅ .plist 文件现在将使用 SimpleTweakEditor 打开")
        print(f"✅ 右键菜单已添加 '使用 SimpleTweakEditor 编辑' 选项")
        
    except Exception as e:
        print(f"❌ 注册失败: {e}")
        return False
    
    return True


def unregister_plist_association():
    """取消注册 .plist 文件关联"""
    try:
        # 删除文件关联
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'SimpleTweakEditor.PlistFile\shell\Edit with SimpleTweakEditor\command')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'SimpleTweakEditor.PlistFile\shell\Edit with SimpleTweakEditor')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'SimpleTweakEditor.PlistFile\shell\open\command')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'SimpleTweakEditor.PlistFile\shell\open')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'SimpleTweakEditor.PlistFile\shell')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'SimpleTweakEditor.PlistFile\DefaultIcon')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, 'SimpleTweakEditor.PlistFile')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, '.plist')
        
        # 刷新 Windows Explorer
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
        
        print("✅ 文件关联已取消注册")
        
    except Exception as e:
        print(f"❌ 取消注册失败: {e}")
        return False
    
    return True


def main():
    """主函数"""
    if sys.platform != 'win32':
        print("❌ 此脚本仅支持 Windows 系统")
        return
    
    if not is_admin():
        print("⚠️  需要管理员权限来注册文件关联")
        print("请右键点击此脚本，选择'以管理员身份运行'")
        
        # 尝试自动提升权限
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return
    
    print("SimpleTweakEditor 文件关联注册工具")
    print("=" * 50)
    print("1. 注册 .plist 文件关联")
    print("2. 取消注册文件关联")
    print("3. 退出")
    print()
    
    choice = input("请选择操作 (1-3): ")
    
    if choice == '1':
        register_plist_association()
    elif choice == '2':
        unregister_plist_association()
    else:
        print("退出")
    
    input("\n按回车键关闭...")


if __name__ == '__main__':
    main()