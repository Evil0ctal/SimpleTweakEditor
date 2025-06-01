# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-27
作者: Evil0ctal

中文介绍:
下载线程模块。实现了用于下载deb包的工作线程，包括单个包下载（DownloadWorker）、
批量下载（BatchDownloadWorker）和软件源刷新（RepoRefreshWorker）。这些线程类
提供了下载进度反馈、状态更新和错误处理功能，支持取消操作。

英文介绍:
Download thread module. Implements worker threads for downloading deb packages, including 
single package download (DownloadWorker), batch download (BatchDownloadWorker), and 
repository refresh (RepoRefreshWorker). These thread classes provide download progress 
feedback, status updates, and error handling capabilities, with support for cancellation.
"""

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from typing import Optional, Tuple
import os
from pathlib import Path


class DownloadWorker(QThread):
    """下载工作线程"""
    
    # 信号定义
    progress = pyqtSignal(int, int, int)  # 进度百分比, 已下载, 总大小
    status = pyqtSignal(str)  # 状态信息
    finished = pyqtSignal(bool, str)  # 成功标志, 文件路径或错误信息
    
    def __init__(self, repo_manager, repo_url: str, package, download_path: str, lang_mgr=None):
        super().__init__()
        self.repo_manager = repo_manager
        self.repo_url = repo_url
        self.package = package
        self.download_path = download_path
        self.lang_mgr = lang_mgr
        self._is_cancelled = False
        
        print(f"[DEBUG] DownloadWorker initialized for {package.package}")
    
    def run(self):
        """执行下载任务"""
        try:
            status_msg = self.lang_mgr.format_text("start_downloading", self.package.get_display_name()) if self.lang_mgr else f"Starting download {self.package.get_display_name()}..."
            self.status.emit(status_msg)
            
            # 确保下载目录存在
            Path(self.download_path).mkdir(parents=True, exist_ok=True)
            
            # 下载包
            success, result = self.repo_manager.download_package(
                self.repo_url,
                self.package,
                self.download_path,
                progress_callback=self._progress_callback
            )
            
            if self._is_cancelled:
                cancel_msg = self.lang_mgr.get_text("download_cancelled") if self.lang_mgr else "Download cancelled"
                self.finished.emit(False, cancel_msg)
            else:
                self.finished.emit(success, result)
                
        except Exception as e:
            error_msg = self.lang_mgr.format_text("download_error", str(e)) if self.lang_mgr else f"Download error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.finished.emit(False, error_msg)
    
    def _progress_callback(self, percent: int, downloaded: int, total: int):
        """进度回调"""
        if not self._is_cancelled:
            self.progress.emit(percent, downloaded, total)
            
            # 格式化进度信息
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            status_msg = self.lang_mgr.format_text("downloading_progress", downloaded_mb, total_mb, percent) if self.lang_mgr else f"Downloading... {downloaded_mb:.1f}/{total_mb:.1f} MB ({percent}%)"
            self.status.emit(status_msg)
    
    def cancel(self):
        """取消下载"""
        self._is_cancelled = True
        print(f"[DEBUG] Download cancelled for {self.package.package}")


class BatchDownloadWorker(QThread):
    """批量下载工作线程"""
    
    # 信号定义
    package_started = pyqtSignal(str, int, int)  # 包名, 当前索引, 总数
    package_progress = pyqtSignal(str, int)  # 包名, 进度百分比
    package_finished = pyqtSignal(str, bool, str)  # 包名, 成功标志, 结果信息
    all_finished = pyqtSignal(int, int)  # 成功数, 失败数
    
    def __init__(self, repo_manager, download_tasks, download_path: str, lang_mgr=None):
        """
        download_tasks: List[Tuple[repo_url, package]]
        """
        super().__init__()
        self.repo_manager = repo_manager
        self.download_tasks = download_tasks
        self.download_path = download_path
        self.lang_mgr = lang_mgr
        self._is_cancelled = False
        
        print(f"[DEBUG] BatchDownloadWorker initialized with {len(download_tasks)} tasks")
    
    def run(self):
        """执行批量下载"""
        success_count = 0
        failed_count = 0
        
        Path(self.download_path).mkdir(parents=True, exist_ok=True)
        
        for i, (repo_url, package) in enumerate(self.download_tasks):
            if self._is_cancelled:
                break
            
            package_name = package.get_display_name()
            self.package_started.emit(package_name, i + 1, len(self.download_tasks))
            
            try:
                # 定义进度回调
                def progress_callback(percent, downloaded, total):
                    if not self._is_cancelled:
                        self.package_progress.emit(package_name, percent)
                
                # 下载包
                success, result = self.repo_manager.download_package(
                    repo_url,
                    package,
                    self.download_path,
                    progress_callback=progress_callback
                )
                
                if success:
                    success_count += 1
                    self.package_finished.emit(package_name, True, result)
                else:
                    failed_count += 1
                    self.package_finished.emit(package_name, False, result)
                    
            except Exception as e:
                failed_count += 1
                error_msg = self.lang_mgr.format_text("download_error", str(e)) if self.lang_mgr else f"Download error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.package_finished.emit(package_name, False, error_msg)
        
        # 发送完成信号
        self.all_finished.emit(success_count, failed_count)
        print(f"[DEBUG] Batch download finished: {success_count} success, {failed_count} failed")
    
    def cancel(self):
        """取消批量下载"""
        self._is_cancelled = True
        print("[DEBUG] Batch download cancelled")


class RepoRefreshWorker(QThread):
    """软件源刷新工作线程"""
    
    # 信号定义
    status = pyqtSignal(str, int, int)  # 状态信息, 当前数, 总数
    finished = pyqtSignal(bool, str)  # 成功标志, 信息
    
    def __init__(self, repo_manager, repos_to_refresh=None, lang_mgr=None):
        super().__init__()
        self.repo_manager = repo_manager
        self.repos_to_refresh = repos_to_refresh  # None表示刷新所有
        self.lang_mgr = lang_mgr
        
    def run(self):
        """执行刷新任务"""
        try:
            if self.repos_to_refresh is None:
                # 刷新所有源
                # 定义进度回调，格式化消息
                def progress_callback(msg, current, total):
                    # msg 来自 repo_manager，包含 "正在刷新 {repo.name}..."
                    # 我们需要提取 repo name 并重新格式化
                    if self.lang_mgr and "正在刷新" in msg:
                        # 提取 repo name
                        import re
                        match = re.search(r'正在刷新 (.+)\.\.\.$', msg)
                        if match:
                            repo_name = match.group(1)
                            formatted_msg = self.lang_mgr.format_text("refreshing_repo", repo_name)
                        else:
                            formatted_msg = msg
                    else:
                        # 英文环境或无法解析，直接使用原消息
                        formatted_msg = msg
                    self.status.emit(formatted_msg, current, total)
                
                self.repo_manager.refresh_all_repos(progress_callback=progress_callback)
                msg = self.lang_mgr.get_text("all_repos_refreshed") if self.lang_mgr else "All repositories refreshed"
                self.finished.emit(True, msg)
            else:
                # 刷新指定源
                total = len(self.repos_to_refresh)
                for i, repo_url in enumerate(self.repos_to_refresh):
                    repo = self.repo_manager.get_repository(repo_url)
                    if repo:
                        status_msg = self.lang_mgr.format_text("refreshing_repo", repo.name) if self.lang_mgr else f"Refreshing {repo.name}..."
                        self.status.emit(status_msg, i + 1, total)
                        self.repo_manager.fetch_packages(repo_url, force_refresh=True)
                
                msg = self.lang_mgr.format_text("n_repos_refreshed", total) if self.lang_mgr else f"Refreshed {total} repositories"
                self.finished.emit(True, msg)
                
        except Exception as e:
            error_msg = self.lang_mgr.format_text("refresh_failed_with_error", str(e)) if self.lang_mgr else f"Refresh failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.finished.emit(False, error_msg)
