# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
终端模拟器，在客户端维护shell状态，提供类似真实终端的体验。
支持工作目录跟踪、命令历史、环境变量模拟等功能。

英文介绍:
Terminal emulator that maintains shell state on the client side, providing a real terminal-like experience.
Supports working directory tracking, command history, environment variable simulation, etc.
"""

import os
import re
import logging
from typing import List, Dict, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


class TerminalEmulator:
    """终端模拟器"""
    
    def __init__(self, ssh_client):
        self.ssh_client = ssh_client
        self.cwd = "~"  # 当前工作目录
        self.home_dir = None  # 用户主目录
        self.env_vars: Dict[str, str] = {}  # 环境变量
        self.command_history: deque = deque(maxlen=1000)  # 命令历史
        self.history_index = -1
        
        # 初始化
        self._initialize()
    
    def _initialize(self):
        """初始化终端状态"""
        if not self.ssh_client.is_connected:
            return
            
        # 获取主目录
        stdout, _ = self.ssh_client.execute_command("echo $HOME")
        if stdout:
            self.home_dir = stdout.strip()
            self.cwd = self.home_dir
            
        # 获取当前工作目录
        stdout, _ = self.ssh_client.execute_command("pwd")
        if stdout:
            self.cwd = stdout.strip()
            
        # 获取基本环境变量
        stdout, _ = self.ssh_client.execute_command("env")
        if stdout:
            for line in stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    self.env_vars[key] = value
    
    def execute_command(self, command: str) -> Tuple[str, str, bool]:
        """
        执行命令并维护终端状态
        返回: (stdout, stderr, is_internal_command)
        """
        if not command.strip():
            return "", "", True
            
        # 添加到历史
        self.command_history.append(command)
        self.history_index = -1
        
        # 处理内置命令
        if command.strip() == 'clear':
            return "", "", True
            
        # 处理cd命令
        if command.strip().startswith('cd '):
            return self._handle_cd(command)
            
        # 处理export命令
        if command.strip().startswith('export '):
            return self._handle_export(command)
            
        # 构建实际命令（在正确的工作目录执行）
        actual_command = self._build_command(command)
        
        # 执行命令
        stdout, stderr = self.ssh_client.execute_command(actual_command)
        
        # 更新工作目录（如果命令可能改变了它）
        if any(cmd in command for cmd in ['cd', 'pushd', 'popd']):
            self._update_cwd()
            
        return stdout, stderr, False
    
    def _handle_cd(self, command: str) -> Tuple[str, str, bool]:
        """处理cd命令"""
        parts = command.strip().split(None, 1)
        if len(parts) == 1:
            # cd without arguments goes to home
            target = "~"
        else:
            target = parts[1]
            
        # 处理特殊路径
        if target == "~":
            target = self.home_dir or "/var/mobile"
        elif target.startswith("~/"):
            target = os.path.join(self.home_dir or "/var/mobile", target[2:])
        elif target == "-":
            # cd - goes to previous directory
            stdout, stderr = self.ssh_client.execute_command(f"cd {self.cwd} && cd - && pwd")
            if stdout and not stderr:
                self.cwd = stdout.strip()
                return f"Changed to {self.cwd}\n", "", False
            return "", stderr, False
        elif not target.startswith("/"):
            # 相对路径
            target = os.path.join(self.cwd, target)
            
        # 测试目录是否存在
        stdout, stderr = self.ssh_client.execute_command(f"cd '{target}' && pwd")
        if stdout and not stderr:
            self.cwd = stdout.strip()
            return "", "", False
        else:
            return "", f"cd: {target}: No such file or directory\n", False
    
    def _handle_export(self, command: str) -> Tuple[str, str, bool]:
        """处理export命令"""
        match = re.match(r'export\s+(\w+)=(.*)', command.strip())
        if match:
            var_name, var_value = match.groups()
            # 去除引号
            var_value = var_value.strip('"\'')
            self.env_vars[var_name] = var_value
            return "", "", False
        else:
            return "", "export: invalid syntax\n", False
    
    def _build_command(self, command: str) -> str:
        """构建实际要执行的命令"""
        # 设置工作目录和环境变量
        cmd_parts = [f"cd '{self.cwd}'"]
        
        # 添加环境变量
        for key, value in self.env_vars.items():
            if key not in ['PWD', 'OLDPWD']:  # 这些由cd管理
                cmd_parts.append(f"export {key}='{value}'")
                
        # 添加实际命令
        cmd_parts.append(command)
        
        # 用 && 连接命令
        return " && ".join(cmd_parts)
    
    def _update_cwd(self):
        """更新当前工作目录"""
        stdout, stderr = self.ssh_client.execute_command("pwd")
        if stdout and not stderr:
            self.cwd = stdout.strip()
    
    def get_prompt(self) -> str:
        """获取命令提示符"""
        # 简化路径显示
        display_path = self.cwd
        if self.home_dir and self.cwd.startswith(self.home_dir):
            display_path = "~" + self.cwd[len(self.home_dir):]
            
        username = self.env_vars.get('USER', 'mobile')
        hostname = self.env_vars.get('HOSTNAME', 'iPhone')
        
        return f"{username}@{hostname}:{display_path}$ "
    
    def get_history_prev(self) -> Optional[str]:
        """获取上一条历史命令"""
        if not self.command_history:
            return None
            
        if self.history_index == -1:
            self.history_index = len(self.command_history) - 1
        elif self.history_index > 0:
            self.history_index -= 1
            
        return self.command_history[self.history_index]
    
    def get_history_next(self) -> Optional[str]:
        """获取下一条历史命令"""
        if not self.command_history or self.history_index == -1:
            return None
            
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            return self.command_history[self.history_index]
        else:
            self.history_index = -1
            return ""
    
    def reset(self):
        """重置终端状态"""
        self._initialize()