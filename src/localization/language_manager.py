# -*- coding: utf-8 -*-
"""
语言管理器模块
负责管理应用程序的多语言支持
"""

import locale
from .translations import Translations


class LanguageManager:
    """语言管理器，管理多语言支持"""

    def __init__(self):
        # 支持的语言
        self.supported_languages = Translations.get_supported_languages()
        self.language_names = Translations.get_language_names()

        # 默认使用系统语言，如果不支持则默认英文
        self.current_language = self.detect_system_language()

    def detect_system_language(self):
        """检测系统语言并返回支持的语言代码"""
        try:
            # 获取系统语言
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                # 从语言代码中提取两个字母的语言代码
                system_lang = system_locale.split('_')[0].lower()
                if system_lang in self.supported_languages:
                    return system_lang
        except Exception:
            # 如果检测失败，使用默认语言
            pass

        # 默认返回英文
        return "en"

    def set_language(self, lang_code):
        """设置当前语言"""
        if lang_code in self.supported_languages:
            self.current_language = lang_code
            return True
        return False

    def get_current_language(self):
        """获取当前语言代码"""
        return self.current_language

    def get_language_name(self, lang_code=None):
        """获取语言的显示名称"""
        if lang_code is None:
            lang_code = self.current_language
        return self.language_names.get(lang_code, lang_code)

    def get_text(self, key):
        """获取当前语言的文本"""
        if self.current_language == "zh":
            # 中文
            if key in Translations.ZH:
                return Translations.ZH[key]

        # 默认英文或找不到翻译时使用英文
        if key in Translations.EN:
            return Translations.EN[key]

        # 如果翻译缺失，返回键名
        return key

    def format_text(self, key, *args):
        """使用参数格式化文本"""
        text = self.get_text(key)
        if args:
            try:
                return text.format(*args)
            except Exception:
                return text
        return text

    def get_command_presets(self, target_path=None):
        """获取快捷命令预设（本地化版本）"""
        import os
        
        # 通用命令（不需要目标）
        general_commands = [
            self.get_text("cmd_preset_title"),
            ("dpkg -l", self.get_text("cmd_list_packages")),
            ("find . -name '*.deb'", self.get_text("cmd_find_deb_files")),
        ]
        
        if not target_path or not os.path.exists(target_path):
            # 没有选择目标时，显示提示和通用命令
            return general_commands + [
                self.get_text("cmd_target_required"),
            ]
        
        # 根据目标类型生成相应命令
        if os.path.isfile(target_path):
            if target_path.endswith('.deb'):
                return general_commands + self._get_deb_commands(target_path)
            else:
                return general_commands + self._get_file_commands(target_path)
        elif os.path.isdir(target_path):
            return general_commands + self._get_folder_commands(target_path)
        
        return general_commands
    
    def _get_deb_commands(self, deb_path):
        """获取.deb文件相关命令"""
        import shlex
        quoted_path = shlex.quote(deb_path)
        return [
            "--- .deb File Commands ---",
            (f"dpkg-deb --info {quoted_path}", self.get_text("cmd_view_deb_info")),
            (f"dpkg-deb --contents {quoted_path}", self.get_text("cmd_list_deb_contents")),
            (f"ar t {quoted_path}", self.get_text("cmd_check_deb_structure")),
            (f"dpkg-deb --control {quoted_path} /tmp/control_extract", self.get_text("cmd_extract_deb_control")),
            (f"ar x {quoted_path} data.tar.xz", self.get_text("cmd_extract_deb_data")),
            (f"ls -lh {quoted_path}", "View file details"),
        ]
    
    def _get_file_commands(self, file_path):
        """获取普通文件相关命令"""
        import shlex
        quoted_path = shlex.quote(file_path)
        return [
            "--- File Commands ---",
            (f"file {quoted_path}", "Check file type"),
            (f"ls -lh {quoted_path}", "View file details"),
            (f"stat {quoted_path}", "View file statistics"),
            (f"head -20 {quoted_path}", "View first 20 lines"),
            (f"tail -20 {quoted_path}", "View last 20 lines"),
        ]
    
    def _get_folder_commands(self, folder_path):
        """获取文件夹相关命令"""
        import shlex
        import os
        quoted_path = shlex.quote(folder_path)
        debian_path = shlex.quote(os.path.join(folder_path, "DEBIAN"))
        control_path = shlex.quote(os.path.join(folder_path, "DEBIAN", "control"))
        
        commands = [
            "--- Folder Commands ---",
            (f"ls -la {quoted_path}", "List folder contents"),
            (f"du -sh {quoted_path}", self.get_text("cmd_check_folder_size")),
            (f"find {quoted_path} -size +1M", self.get_text("cmd_find_large_files")),
            (f"find {quoted_path} -type f -exec ls -l {{}} \\;", self.get_text("cmd_list_permissions")),
        ]
        
        # 如果是包文件夹，添加DEBIAN相关命令
        if os.path.exists(os.path.join(folder_path, "DEBIAN")):
            commands.extend([
                "--- Package Commands ---",
                (f"ls -la {debian_path}", self.get_text("cmd_list_debian_dir")),
                (f"cat {control_path}", self.get_text("cmd_view_control")),
                (f"chmod 755 {debian_path}/postinst", self.get_text("cmd_set_script_permission")),
                (f"find {debian_path} -type f -exec chmod 644 {{}} \\;", "Set all DEBIAN files to 644"),
            ])
        
        return commands

