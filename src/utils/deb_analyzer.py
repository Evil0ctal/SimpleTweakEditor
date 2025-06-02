# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-06
作者: Evil0ctal

中文介绍:
DEB 文件分析器
分析 deb 文件的越狱兼容性

英文介绍:
DEB file analyzer
Analyzes jailbreak compatibility of deb files
"""

import os
import tempfile
import subprocess
from typing import Tuple, Optional
from ..utils.debug_logger import debug, info, warning
from ..utils.dpkg_deb import DpkgDeb
from ..utils.system_utils import check_dpkg_available


class DebAnalyzer:
    """DEB 文件分析器"""
    
    @staticmethod
    def analyze_jailbreak_compatibility(deb_path: str) -> Tuple[bool, str]:
        """
        分析 deb 文件的越狱兼容性
        
        Returns:
            (成功标志, 兼容性类型: 'Rootful'/'Rootless'/'Both'/'Unknown')
        """
        try:
            # 提取 control 信息
            control_info = DebAnalyzer._extract_control_info(deb_path)
            if not control_info:
                return False, "Unknown"
            
            # 获取基本信息
            depends = control_info.get('Depends', '').lower()
            description = control_info.get('Description', '').lower()
            architecture = control_info.get('Architecture', '').lower()
            package_name = control_info.get('Package', '').lower()
            
            # 从文件名获取线索
            filename_lower = os.path.basename(deb_path).lower()
            
            # 优先级1: Rootless 标记
            rootless_field = control_info.get('Rootless', '').lower()
            if rootless_field in ['yes', 'true', '1']:
                return True, "Rootless"
            
            # 优先级2: 文件名中的线索（最可靠）
            if 'rootless' in filename_lower:
                return True, "Rootless"
            if 'rootful' in filename_lower:
                return True, "Rootful"
            
            # 优先级3: 包名中的线索
            if 'rootless' in package_name:
                return True, "Rootless"
            if 'rootful' in package_name:
                return True, "Rootful"
            
            # 优先级4: 描述中的路径线索
            if any(text in description for text in ['/var/jb', 'rootless', '无根']):
                return True, "Rootless"
            
            # 优先级5: 架构检查
            is_modern_arch = 'arm64' in architecture or 'arm64e' in architecture
            
            # 优先级6: 依赖分析
            # Rootless 特有依赖
            rootless_only_indicators = [
                'ellekit', 'libhooker', 'com.ex.substitute',
                'org.coolstar.libhooker', 'com.opa334.altlist'
            ]
            
            if any(indicator in depends for indicator in rootless_only_indicators):
                return True, "Rootless"
            
            # mobilesubstrate 不再是 Rootful 的决定性指标
            has_mobilesubstrate = 'mobilesubstrate' in depends
            
            # 现代架构 + mobilesubstrate = 很可能是 Rootless
            if is_modern_arch and has_mobilesubstrate:
                # 检查是否有强 Rootful 指标
                rootful_strong_indicators = ['cydia', 'com.saurik', 'substrate.safemode']
                if not any(indicator in depends for indicator in rootful_strong_indicators):
                    return True, "Rootless"
            
            # 传统架构通常是 Rootful
            if 'arm' in architecture and 'arm64' not in architecture:
                return True, "Rootful"
            
            # 无法确定
            return True, "Unknown"
                
        except Exception as e:
            warning(f"Failed to analyze deb compatibility: {e}")
            return False, "Unknown"
    
    @staticmethod
    def _extract_control_info(deb_path: str) -> Optional[dict]:
        """提取 control 文件信息"""
        try:
            if check_dpkg_available():
                # 使用 dpkg-deb 提取信息
                result = subprocess.run(
                    ['dpkg-deb', '-f', deb_path],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return DebAnalyzer._parse_control_content(result.stdout)
            else:
                # 使用 Python 实现提取
                dpkg = DpkgDeb()
                with tempfile.TemporaryDirectory() as temp_dir:
                    success, msg = dpkg.extract(deb_path, temp_dir)
                    if success:
                        control_path = os.path.join(temp_dir, 'DEBIAN', 'control')
                        if os.path.exists(control_path):
                            with open(control_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            return DebAnalyzer._parse_control_content(content)
            
        except Exception as e:
            debug(f"Failed to extract control info: {e}")
        
        return None
    
    @staticmethod
    def _parse_control_content(content: str) -> dict:
        """解析 control 文件内容"""
        info = {}
        current_key = None
        
        for line in content.split('\n'):
            if line.startswith(' ') and current_key:
                # 多行值的延续
                info[current_key] += '\n' + line[1:]
            elif ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                info[key] = value
                current_key = key
        
        return info