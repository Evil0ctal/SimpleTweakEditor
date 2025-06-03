# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
凭据存储管理器，负责安全地存储和管理SSH登录凭据。
使用base64编码和文件权限保护来存储敏感信息。

英文介绍:
Credential store manager responsible for securely storing and managing SSH login credentials.
Uses base64 encoding and file permissions to protect sensitive information.
"""

import json
import base64
import os
import platform
import stat
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from cryptography.fernet import Fernet

# 尝试导入系统密钥存储库
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    logging.info("keyring not available, using file-based encryption")

# Windows特定导入
if platform.system() == 'Windows':
    try:
        import ctypes
        from ctypes import wintypes
        HAS_WINDOWS_API = True
    except ImportError:
        HAS_WINDOWS_API = False

logger = logging.getLogger(__name__)


class CredentialStore:
    """SSH凭据存储管理器"""
    
    KEYRING_SERVICE = "SimpleTweakEditor"
    KEYRING_KEY_PREFIX = "ssh_cred_"
    
    def __init__(self, config_dir: Optional[Path] = None, use_keyring: bool = True):
        """
        初始化凭据存储
        
        Args:
            config_dir: 配置目录路径，默认为用户目录下的.simpletweakeditor
            use_keyring: 是否使用系统密钥环（如果可用）
        """
        if config_dir is None:
            config_dir = Path.home() / '.simpletweakeditor'
            
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.credentials_file = self.config_dir / 'ssh_credentials.json'
        self.key_file = self.config_dir / '.ssh_key'
        self.use_keyring = use_keyring and HAS_KEYRING
        
        # 初始化加密密钥
        self._init_encryption_key()
        
        # 设置文件权限
        self._set_file_permissions()
        
        # Windows特定：隐藏配置文件
        if platform.system() == 'Windows':
            self._hide_windows_files()
        
        # 加载现有凭据
        self._credentials: Dict[str, Dict] = self._load_credentials()
        
    def _init_encryption_key(self):
        """初始化或加载加密密钥"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                self._key = f.read()
        else:
            # 生成新密钥
            self._key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self._key)
            # 设置密钥文件权限
            if hasattr(os, 'chmod'):
                os.chmod(self.key_file, 0o600)
                
        self._fernet = Fernet(self._key)
        
    def _set_file_permissions(self):
        """设置文件权限"""
        if platform.system() != 'Windows':
            # Unix系统权限设置
            try:
                # 设置目录权限为700（仅所有者可读写执行）
                os.chmod(self.config_dir, 0o700)
                
                # 如果凭据文件存在，设置权限为600（仅所有者可读写）
                if self.credentials_file.exists():
                    os.chmod(self.credentials_file, 0o600)
                    
                if self.key_file.exists():
                    os.chmod(self.key_file, 0o600)
                    
            except Exception as e:
                logger.warning(f"设置文件权限失败: {str(e)}")
    
    def _hide_windows_files(self):
        """在Windows系统上隐藏配置文件"""
        if not HAS_WINDOWS_API:
            return
            
        try:
            FILE_ATTRIBUTE_HIDDEN = 0x02
            
            # 隐藏主配置目录
            if self.config_dir.exists():
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(self.config_dir), FILE_ATTRIBUTE_HIDDEN
                )
            
            # 隐藏密钥文件
            if self.key_file.exists():
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(self.key_file), FILE_ATTRIBUTE_HIDDEN
                )
                
            logger.info("Windows文件隐藏属性设置成功")
        except Exception as e:
            logger.warning(f"设置Windows文件隐藏属性失败: {str(e)}")
                
    def _encrypt_data(self, data: str) -> str:
        """加密数据"""
        try:
            encrypted = self._fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"加密数据失败: {str(e)}")
            # 降级为base64编码
            return base64.b64encode(data.encode()).decode()
            
    def _decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted = base64.b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception:
            # 尝试base64解码（兼容旧数据）
            try:
                return base64.b64decode(encrypted_data.encode()).decode()
            except Exception as e:
                logger.error(f"解密数据失败: {str(e)}")
                return ""
    
    def _store_in_keyring(self, device_id: str, password: str) -> bool:
        """将密码存储到系统密钥环"""
        if not self.use_keyring:
            return False
            
        try:
            keyring.set_password(
                self.KEYRING_SERVICE,
                f"{self.KEYRING_KEY_PREFIX}{device_id}",
                password
            )
            return True
        except Exception as e:
            logger.warning(f"存储到密钥环失败: {str(e)}")
            return False
    
    def _get_from_keyring(self, device_id: str) -> Optional[str]:
        """从系统密钥环获取密码"""
        if not self.use_keyring:
            return None
            
        try:
            return keyring.get_password(
                self.KEYRING_SERVICE,
                f"{self.KEYRING_KEY_PREFIX}{device_id}"
            )
        except Exception as e:
            logger.warning(f"从密钥环获取失败: {str(e)}")
            return None
    
    def _delete_from_keyring(self, device_id: str) -> bool:
        """从系统密钥环删除密码"""
        if not self.use_keyring:
            return False
            
        try:
            keyring.delete_password(
                self.KEYRING_SERVICE,
                f"{self.KEYRING_KEY_PREFIX}{device_id}"
            )
            return True
        except Exception as e:
            logger.warning(f"从密钥环删除失败: {str(e)}")
            return False
                
    def _load_credentials(self) -> Dict[str, Dict]:
        """加载凭据文件"""
        if not self.credentials_file.exists():
            return {}
            
        try:
            with open(self.credentials_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 解密密码
            for device_id, cred in data.items():
                if 'password' in cred and cred['password']:
                    cred['password'] = self._decrypt_data(cred['password'])
                    
            return data
            
        except Exception as e:
            logger.error(f"加载凭据失败: {str(e)}")
            return {}
            
    def _save_credentials(self):
        """保存凭据到文件"""
        try:
            # 创建副本并加密密码
            data_to_save = {}
            for device_id, cred in self._credentials.items():
                cred_copy = cred.copy()
                if 'password' in cred_copy and cred_copy['password']:
                    cred_copy['password'] = self._encrypt_data(cred_copy['password'])
                data_to_save[device_id] = cred_copy
                
            # 保存到文件
            with open(self.credentials_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
            # 设置文件权限
            self._set_file_permissions()
            
        except Exception as e:
            logger.error(f"保存凭据失败: {str(e)}")
            
    def save_credential(self, device_id: str, username: str, password: str,
                       host: str = 'localhost', port: int = 2222,
                       connection_type: str = 'usb', device_name: str = ''):
        """
        保存设备凭据
        
        Args:
            device_id: 设备唯一标识符
            username: SSH用户名
            password: SSH密码
            host: 主机地址
            port: 端口号
            connection_type: 连接类型 (usb/wifi)
            device_name: 设备名称
        """
        # 尝试存储到密钥环
        stored_in_keyring = False
        if self.use_keyring and password:
            stored_in_keyring = self._store_in_keyring(device_id, password)
        
        self._credentials[device_id] = {
            'username': username,
            'password': password if not stored_in_keyring else '',  # 如果存储在密钥环则不存储在文件中
            'host': host,
            'port': port,
            'connection_type': connection_type,
            'device_name': device_name,
            'last_used': datetime.now().isoformat(),
            'created_at': self._credentials.get(device_id, {}).get(
                'created_at', datetime.now().isoformat()
            ),
            'password_in_keyring': stored_in_keyring
        }
        
        self._save_credentials()
        logger.info(f"保存凭据: {device_id} ({device_name})")
        
    def get_credential(self, device_id: str) -> Optional[Dict]:
        """
        获取设备凭据
        
        Args:
            device_id: 设备唯一标识符
            
        Returns:
            包含凭据信息的字典，如果不存在则返回None
        """
        cred = self._credentials.get(device_id)
        if cred:
            # 如果密码存储在密钥环中，尝试获取
            if cred.get('password_in_keyring') and not cred.get('password'):
                keyring_password = self._get_from_keyring(device_id)
                if keyring_password:
                    cred = cred.copy()
                    cred['password'] = keyring_password
            
            # 更新最后使用时间
            self._credentials[device_id]['last_used'] = datetime.now().isoformat()
            self._save_credentials()
            
        return cred
        
    def get_all_credentials(self) -> List[Dict]:
        """
        获取所有保存的凭据
        
        Returns:
            凭据列表，每个元素包含device_id和其他信息
        """
        credentials_list = []
        for device_id, cred in self._credentials.items():
            cred_info = cred.copy()
            cred_info['device_id'] = device_id
            # 不返回实际密码，只返回是否已保存
            cred_info['has_password'] = bool(cred_info.get('password'))
            cred_info.pop('password', None)
            credentials_list.append(cred_info)
            
        # 按最后使用时间排序
        credentials_list.sort(
            key=lambda x: x.get('last_used', ''),
            reverse=True
        )
        
        return credentials_list
        
    def delete_credential(self, device_id: str) -> bool:
        """
        删除设备凭据
        
        Args:
            device_id: 设备唯一标识符
            
        Returns:
            是否删除成功
        """
        if device_id in self._credentials:
            # 如果密码存储在密钥环中，也要删除
            if self._credentials[device_id].get('password_in_keyring'):
                self._delete_from_keyring(device_id)
            
            del self._credentials[device_id]
            self._save_credentials()
            logger.info(f"删除凭据: {device_id}")
            return True
            
        return False
        
    def update_device_name(self, device_id: str, device_name: str):
        """更新设备名称"""
        if device_id in self._credentials:
            self._credentials[device_id]['device_name'] = device_name
            self._save_credentials()
            
    def get_recent_devices(self, limit: int = 5) -> List[Dict]:
        """
        获取最近使用的设备
        
        Args:
            limit: 返回的设备数量限制
            
        Returns:
            最近使用的设备列表
        """
        all_credentials = self.get_all_credentials()
        return all_credentials[:limit]
        
    def export_credentials(self, export_path: Path, include_passwords: bool = False):
        """
        导出凭据（用于备份）
        
        Args:
            export_path: 导出文件路径
            include_passwords: 是否包含密码
        """
        try:
            export_data = {}
            for device_id, cred in self._credentials.items():
                cred_copy = cred.copy()
                if not include_passwords:
                    cred_copy.pop('password', None)
                else:
                    # 如果包含密码，确保密码是加密的
                    if 'password' in cred_copy and cred_copy['password']:
                        # 加密密码后再导出
                        cred_copy['password'] = self._encrypt_data(cred_copy['password'])
                        cred_copy['password_encrypted'] = True  # 标记密码已加密
                export_data[device_id] = cred_copy
                
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"导出凭据到: {export_path}")
            
        except Exception as e:
            logger.error(f"导出凭据失败: {str(e)}")
            
    def import_credentials(self, import_path: Path):
        """
        导入凭据
        
        Args:
            import_path: 导入文件路径
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
                
            # 合并凭据
            for device_id, cred in import_data.items():
                if device_id not in self._credentials:
                    # 检查密码是否已加密
                    if cred.get('password_encrypted') and 'password' in cred and cred['password']:
                        # 如果密码已加密，先解密
                        try:
                            cred['password'] = self._decrypt_data(cred['password'])
                        except Exception:
                            # 解密失败，可能是不同的密钥，清除密码
                            logger.warning(f"无法解密设备 {device_id} 的密码，可能使用了不同的加密密钥")
                            cred['password'] = ''
                    
                    # 移除加密标记
                    cred.pop('password_encrypted', None)
                    self._credentials[device_id] = cred
                    
            self._save_credentials()
            logger.info(f"从 {import_path} 导入凭据")
            
        except Exception as e:
            logger.error(f"导入凭据失败: {str(e)}")
    
    def clear_all_credentials(self) -> Tuple[int, int]:
        """
        清除所有凭据
        
        Returns:
            (成功删除数, 失败数)
        """
        success_count = 0
        fail_count = 0
        
        device_ids = list(self._credentials.keys())
        for device_id in device_ids:
            try:
                if self.delete_credential(device_id):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"删除凭据 {device_id} 失败: {str(e)}")
                fail_count += 1
        
        return success_count, fail_count
    
    def get_keyring_status(self) -> Dict[str, bool]:
        """
        获取密钥环状态
        
        Returns:
            包含密钥环可用性和使用状态的字典
        """
        backend_name = None
        if HAS_KEYRING:
            try:
                backend_name = keyring.get_keyring().__class__.__name__
            except Exception:
                backend_name = "Unknown"
        
        return {
            'available': HAS_KEYRING,
            'enabled': self.use_keyring,
            'backend': backend_name
        }
    
    def migrate_to_keyring(self) -> Tuple[int, int]:
        """
        将现有密码迁移到系统密钥环
        
        Returns:
            (成功迁移数, 失败数)
        """
        if not self.use_keyring:
            return 0, 0
        
        success_count = 0
        fail_count = 0
        
        for device_id, cred in self._credentials.items():
            if cred.get('password') and not cred.get('password_in_keyring'):
                if self._store_in_keyring(device_id, cred['password']):
                    # 更新凭据，从文件中移除密码
                    cred['password'] = ''
                    cred['password_in_keyring'] = True
                    success_count += 1
                else:
                    fail_count += 1
        
        if success_count > 0:
            self._save_credentials()
        
        return success_count, fail_count
