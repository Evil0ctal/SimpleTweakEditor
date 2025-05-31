# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-29
作者: Evil0ctal

中文介绍:
纯 Python 实现的 dpkg-deb 功能模块，为 Windows 平台提供 .deb 包处理支持。
无需外部依赖，完全兼容 dpkg-deb 命令行接口，支持解包、打包、查看信息等核心功能。
处理 AR 归档格式和 tar 压缩，支持 gz、xz、lzma 等多种压缩格式。

英文介绍:
Pure Python implementation of dpkg-deb functionality providing .deb package support for Windows platform.
Requires no external dependencies and is fully compatible with dpkg-deb command line interface.
Supports core functions including unpacking, packing, and information viewing.
Handles AR archive format and tar compression with support for gz, xz, lzma and other compression formats.
"""

import gzip
import io
import logging
import lzma
import shutil
import struct
import tarfile
import tempfile
import platform
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Windows file permission handling
IS_WINDOWS = platform.system() == 'Windows'
MAINTAINER_SCRIPTS = ['preinst', 'postinst', 'prerm', 'postrm', 'config']


class ARArchive:
    """Handles AR archive format used by .deb files"""
    
    MAGIC = b"!<arch>\n"
    HEADER_FORMAT = "16s12s6s6s8s10s2s"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.entries = []
    
    def read(self) -> Dict[str, bytes]:
        """Read AR archive and return dictionary of files"""
        files = {}
        
        with open(self.file_path, 'rb') as f:
            # Check magic header
            magic = f.read(8)
            if magic != self.MAGIC:
                raise ValueError(f"Invalid AR archive: incorrect magic header")
            
            while True:
                # Read entry header
                header_data = f.read(self.HEADER_SIZE)
                if len(header_data) < self.HEADER_SIZE:
                    break
                
                # Parse header
                header = struct.unpack(self.HEADER_FORMAT, header_data)
                filename = header[0].decode('ascii').rstrip()
                size = int(header[5].decode('ascii').strip())
                
                # Remove trailing /
                if filename.endswith('/'):
                    filename = filename[:-1]
                
                # Read file content
                content = f.read(size)
                files[filename] = content
                
                # Skip padding byte if size is odd
                if size % 2 == 1:
                    f.read(1)
        
        return files
    
    def write(self, files: Dict[str, bytes]):
        """Write files to AR archive"""
        with open(self.file_path, 'wb') as f:
            # Write magic header
            f.write(self.MAGIC)
            
            for filename, content in files.items():
                # Prepare header fields
                size = len(content)
                header = struct.pack(
                    self.HEADER_FORMAT,
                    f"{filename}/".ljust(16).encode('ascii'),  # filename
                    b"0           ",  # timestamp
                    b"0     ",        # owner
                    b"0     ",        # group
                    b"100644  ",      # mode
                    f"{size}".ljust(10).encode('ascii'),  # size
                    b"`\n"            # terminator
                )
                
                # Write header and content
                f.write(header)
                f.write(content)
                
                # Add padding byte if size is odd
                if size % 2 == 1:
                    f.write(b"\n")


class DpkgDeb:
    """Pure Python implementation of dpkg-deb functionality"""
    
    def __init__(self):
        self.temp_dir = None
    
    def _extract_tar_archive(self, data: bytes, fmt: str, output_dir: Path, safe_extract: bool = True) -> None:
        """
        Extract tar archive with support for different compression formats.
        
        Args:
            data: Archive data bytes
            fmt: Format ('gz', 'xz', 'lzma' or 'uncompressed')
            output_dir: Directory to extract to
            safe_extract: Whether to perform path traversal checks
        """
        with io.BytesIO(data) as data_io:
            # Open compressed stream based on format
            if fmt == 'gz':
                fileobj = gzip.open(data_io, 'rb')
            elif fmt == 'xz' or fmt == 'lzma':
                fileobj = lzma.open(data_io, 'rb')
            elif fmt == 'uncompressed':
                fileobj = data_io
            else:
                raise ValueError(f"Unsupported compression format: {fmt}")
            
            try:
                with tarfile.open(fileobj=fileobj, mode='r') as tar:
                    if safe_extract:
                        # Safe extraction with path traversal protection
                        for member in tar.getmembers():
                            # Resolve the full path and ensure it's within output_dir
                            member_path = (output_dir / member.name).resolve()
                            try:
                                member_path.relative_to(output_dir.resolve())
                            except ValueError:
                                logger.warning(f"Skipping potentially unsafe path: {member.name}")
                                continue
                            
                            # Extract this member
                            tar.extract(member, output_dir)
                    else:
                        # Standard extraction (less safe but faster)
                        tar.extractall(output_dir)
            finally:
                if fmt in ('gz', 'xz', 'lzma'):
                    fileobj.close()
    
    def _create_tar_archive(self, source_dir: Path, fmt: str, base_dir: str = ".",
                          force_root: bool = True, save_permissions: bool = True) -> bytes:
        """
        Create tar archive with specified compression format.
        
        Args:
            source_dir: Directory to archive
            fmt: Format ('gz', 'xz', 'lzma' or 'uncompressed')
            base_dir: Base directory name in archive
            force_root: Whether to force root ownership
            save_permissions: Whether to save permissions on Windows
            
        Returns:
            Compressed archive data
        """
        tar_data = io.BytesIO()
        
        # On Windows, we'll handle permissions in the filter function
        
        # Create tar archive
        with tarfile.open(fileobj=tar_data, mode='w') as tar:
            # Custom filter for permissions
            def add_with_permissions(tarinfo):
                if force_root:
                    tarinfo.uid = 0
                    tarinfo.gid = 0
                    tarinfo.uname = 'root'
                    tarinfo.gname = 'root'
                
                # Handle Windows permission mapping
                if IS_WINDOWS:
                    # Get the base filename
                    basename = Path(tarinfo.name).name
                    parent_dir = Path(tarinfo.name).parent.name
                    
                    # Check if it's a maintainer script
                    if parent_dir == 'DEBIAN' and basename in MAINTAINER_SCRIPTS:
                        tarinfo.mode = 0o755
                    # Check if it's in a bin directory
                    elif parent_dir in ['bin', 'sbin'] or 'bin' in Path(tarinfo.name).parts:
                        tarinfo.mode = 0o755
                    # Check for shebang in regular files
                    elif tarinfo.isreg():
                        try:
                            full_path = source_dir / Path(tarinfo.name).relative_to(base_dir)
                            with open(full_path, 'rb') as f:
                                if f.read(2) == b'#!':
                                    tarinfo.mode = 0o755
                                else:
                                    tarinfo.mode = 0o644
                        except:
                            tarinfo.mode = 0o644
                    elif tarinfo.isdir():
                        tarinfo.mode = 0o755
                    else:
                        tarinfo.mode = 0o644
                
                return tarinfo
            
            # Add files with proper permissions
            for item in source_dir.iterdir():
                arcname = f"{base_dir}/{item.name}"
                tar.add(item, arcname=arcname, recursive=True, filter=add_with_permissions)
        
        # Compress based on format
        tar_data.seek(0)
        if fmt == 'gz':
            compressed_data = io.BytesIO()
            with gzip.open(compressed_data, 'wb', compresslevel=9) as gz:
                gz.write(tar_data.read())
            return compressed_data.getvalue()
        elif fmt == 'xz':
            compressed_data = io.BytesIO()
            with lzma.open(compressed_data, 'wb', preset=6) as xz:
                xz.write(tar_data.read())
            return compressed_data.getvalue()
        elif fmt == 'lzma':
            # Use FORMAT_ALONE for pure LZMA format
            return lzma.compress(tar_data.read(), format=lzma.FORMAT_ALONE, preset=6)
        elif fmt == 'uncompressed':
            return tar_data.getvalue()
        else:
            raise ValueError(f"Unsupported compression format: {fmt}")
    
    def extract(self, deb_path: str, output_dir: str, safe_extract: bool = True) -> bool:
        """
        Extract a .deb file to the specified directory (dpkg-deb -x).
        
        Args:
            deb_path: Path to the .deb file
            output_dir: Directory to extract contents to
            safe_extract: Whether to perform path traversal checks
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Read AR archive
            ar = ARArchive(deb_path)
            files = ar.read()
            
            # Verify debian-binary
            if 'debian-binary' not in files:
                raise ValueError("Invalid .deb file: missing debian-binary")
            
            version = files['debian-binary'].strip()
            if version != b'2.0':
                logger.warning(f"Unexpected debian version: {version}")
            
            # Detect and extract control archive
            control_data = None
            control_format = None
            if 'control.tar.gz' in files:
                control_data = files['control.tar.gz']
                control_format = 'gz'
            elif 'control.tar.xz' in files:
                control_data = files['control.tar.xz']
                control_format = 'xz'
            elif 'control.tar' in files:
                control_data = files['control.tar']
                control_format = 'uncompressed'
            else:
                raise ValueError("Invalid .deb file: missing control archive")
            
            # Detect and extract data archive
            data_data = None
            data_format = None
            if 'data.tar.gz' in files:
                data_data = files['data.tar.gz']
                data_format = 'gz'
            elif 'data.tar.xz' in files:
                data_data = files['data.tar.xz']
                data_format = 'xz'
            elif 'data.tar.lzma' in files:
                data_data = files['data.tar.lzma']
                data_format = 'lzma'
            elif 'data.tar' in files:
                data_data = files['data.tar']
                data_format = 'uncompressed'
            else:
                raise ValueError("Invalid .deb file: missing data archive")
            
            # Extract control archive to DEBIAN directory
            debian_dir = output_path / 'DEBIAN'
            debian_dir.mkdir(exist_ok=True)
            self._extract_tar_archive(control_data, control_format, debian_dir, safe_extract)
            
            # Extract data archive to output directory
            self._extract_tar_archive(data_data, data_format, output_path, safe_extract)
            
            logger.info(f"Successfully unpacked {deb_path} to {output_dir}")
            logger.info(f"Control format: {control_format}, Data format: {data_format}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unpack .deb file: {e}")
            return False
    
    def build(self, folder_path: str, output_path: str, compression: str = 'gz', verify: bool = True) -> bool:
        """
        Build a .deb file from a directory (dpkg-deb -b).
        
        Args:
            folder_path: Path to the folder containing DEBIAN directory
            output_path: Path for the output .deb file
            compression: Compression format ('gz', 'xz', 'lzma' or 'uncompressed')
            verify: Whether to verify the package after creation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            folder_path = Path(folder_path)
            debian_dir = folder_path / 'DEBIAN'
            
            # Verify DEBIAN directory exists
            if not debian_dir.exists():
                raise ValueError("DEBIAN directory not found")
            
            # Verify control file exists
            control_file = debian_dir / 'control'
            if not control_file.exists():
                raise ValueError("DEBIAN/control file not found")
            
            # Create debian-binary
            debian_binary = b'2.0\n'
            
            # On Windows, ensure maintainer scripts are marked as executable
            if IS_WINDOWS:
                for script_name in MAINTAINER_SCRIPTS:
                    script_path = debian_dir / script_name
                    if script_path.exists():
                        logger.info(f"Marking {script_name} as executable in package")
            
            # Create control archive
            control_archive_name = f'control.tar.{compression}' if compression != 'uncompressed' else 'control.tar'
            control_data = self._create_tar_archive(debian_dir, compression, force_root=True)
            
            # Create data archive
            data_archive_name = f'data.tar.{compression}' if compression != 'uncompressed' else 'data.tar'
            # Create temporary directory for data files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                # Copy all non-DEBIAN files
                for item in folder_path.iterdir():
                    if item.name != 'DEBIAN':
                        dest = temp_path / item.name
                        if item.is_dir():
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)
                
                data_data = self._create_tar_archive(temp_path, compression, force_root=True)
            
            # Create AR archive
            ar = ARArchive(output_path)
            ar.write({
                'debian-binary': debian_binary,
                control_archive_name: control_data,
                data_archive_name: data_data
            })
            
            logger.info(f"Successfully packed {folder_path} to {output_path}")
            logger.info(f"Compression format: {compression}")
            
            # Verify the package if requested
            if verify:
                logger.info("Verifying created package...")
                if self.verify(output_path):
                    logger.info("Package verification successful")
                else:
                    logger.error("Package verification failed")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to pack .deb file: {e}")
            return False
    
    def verify(self, deb_path: str) -> bool:
        """
        Verify a .deb package by unpacking and checking its structure.
        
        Args:
            deb_path: Path to the .deb file
            
        Returns:
            True if package is valid, False otherwise
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Try to unpack the package
                if not self.extract(deb_path, temp_dir, safe_extract=True):
                    return False
                
                # Check required structure
                temp_path = Path(temp_dir)
                debian_dir = temp_path / 'DEBIAN'
                control_file = debian_dir / 'control'
                
                if not debian_dir.exists():
                    logger.error("Verification failed: DEBIAN directory missing")
                    return False
                
                if not control_file.exists():
                    logger.error("Verification failed: control file missing")
                    return False
                
                # Try to read package info
                info = self.info(deb_path)
                if not info:
                    logger.error("Verification failed: cannot read package info")
                    return False
                
                # Check required fields
                required_fields = ['Package', 'Version', 'Architecture']
                for field in required_fields:
                    if field not in info:
                        logger.error(f"Verification failed: missing required field '{field}'")
                        return False
                
                return True
                
        except Exception as e:
            logger.error(f"Package verification error: {e}")
            return False
    
    def info(self, deb_path: str) -> Optional[Dict[str, str]]:
        """
        Extract package information from a .deb file (dpkg-deb -I).
        
        Args:
            deb_path: Path to the .deb file
            
        Returns:
            Dictionary containing package information or None if failed
        """
        try:
            # Read AR archive
            ar = ARArchive(deb_path)
            files = ar.read()
            
            # Find control archive
            control_data = None
            control_format = None
            
            if 'control.tar.gz' in files:
                control_data = files['control.tar.gz']
                control_format = 'gz'
            elif 'control.tar.xz' in files:
                control_data = files['control.tar.xz']
                control_format = 'xz'
            elif 'control.tar' in files:
                control_data = files['control.tar']
                control_format = 'uncompressed'
            else:
                return None
            
            # Extract control file content
            with io.BytesIO(control_data) as data_io:
                if control_format == 'gz':
                    fileobj = gzip.open(data_io, 'rb')
                elif control_format == 'xz' or control_format == 'lzma':
                    fileobj = lzma.open(data_io, 'rb')
                else:
                    fileobj = data_io
                
                try:
                    with tarfile.open(fileobj=fileobj, mode='r') as tar:
                        # Find control file
                        for member in tar.getmembers():
                            if member.name.endswith('control'):
                                control_content = tar.extractfile(member).read().decode('utf-8')
                                # Parse control file
                                info = {}
                                current_key = None
                                for line in control_content.split('\n'):
                                    if line.startswith(' ') and current_key:
                                        # Continuation of previous field
                                        info[current_key] += '\n' + line[1:]
                                    elif ':' in line:
                                        key, value = line.split(':', 1)
                                        current_key = key.strip()
                                        info[current_key] = value.strip()
                                return info
                finally:
                    if control_format in ('gz', 'xz', 'lzma'):
                        fileobj.close()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get package info: {e}")
            return None
    
    def contents(self, deb_path: str) -> Optional[Dict[str, list]]:
        """
        List the contents of a .deb file without extracting (dpkg-deb -c).
        
        Args:
            deb_path: Path to the .deb file
            
        Returns:
            Dictionary with 'control' and 'data' file lists, or None if failed
        """
        try:
            # Read AR archive
            ar = ARArchive(deb_path)
            files = ar.read()
            
            contents = {'control': [], 'data': []}
            
            # List control archive contents
            for archive_name in ['control.tar.gz', 'control.tar.xz', 'control.tar.lzma', 'control.tar']:
                if archive_name in files:
                    data = files[archive_name]
                    fmt = 'gz' if archive_name.endswith('.gz') else 'xz' if archive_name.endswith('.xz') else 'lzma' if archive_name.endswith('.lzma') else 'uncompressed'
                    
                    with io.BytesIO(data) as data_io:
                        if fmt == 'gz':
                            fileobj = gzip.open(data_io, 'rb')
                        elif fmt == 'xz' or fmt == 'lzma':
                            fileobj = lzma.open(data_io, 'rb')
                        else:
                            fileobj = data_io
                        
                        try:
                            with tarfile.open(fileobj=fileobj, mode='r') as tar:
                                contents['control'] = [m.name for m in tar.getmembers()]
                        finally:
                            if fmt in ('gz', 'xz', 'lzma'):
                                fileobj.close()
                    break
            
            # List data archive contents
            for archive_name in ['data.tar.gz', 'data.tar.xz', 'data.tar.lzma', 'data.tar']:
                if archive_name in files:
                    data = files[archive_name]
                    fmt = 'gz' if archive_name.endswith('.gz') else 'xz' if archive_name.endswith('.xz') else 'lzma' if archive_name.endswith('.lzma') else 'uncompressed'
                    
                    with io.BytesIO(data) as data_io:
                        if fmt == 'gz':
                            fileobj = gzip.open(data_io, 'rb')
                        elif fmt == 'xz' or fmt == 'lzma':
                            fileobj = lzma.open(data_io, 'rb')
                        else:
                            fileobj = data_io
                        
                        try:
                            with tarfile.open(fileobj=fileobj, mode='r') as tar:
                                contents['data'] = [m.name for m in tar.getmembers()]
                        finally:
                            if fmt in ('gz', 'xz', 'lzma'):
                                fileobj.close()
                    break
            
            return contents
            
        except Exception as e:
            logger.error(f"Failed to list package contents: {e}")
            return None
    
    def show_info(self, info: Dict[str, str], detailed: bool = False) -> None:
        """
        Display package information in a formatted way.
        
        Args:
            info: Package information dictionary
            detailed: Whether to show all fields or just essential ones
        """
        if not info:
            print("No package information available")
            return
        
        # Essential fields to always show
        essential_fields = [
            'Package', 'Version', 'Architecture', 'Maintainer',
            'Installed-Size', 'Section', 'Priority', 'Description'
        ]
        
        print("=" * 60)
        print("PACKAGE INFORMATION")
        print("=" * 60)
        
        # Show essential fields first
        for field in essential_fields:
            if field in info:
                if field == 'Description':
                    # Special handling for multi-line description
                    lines = info[field].split('\n')
                    print(f"{field:15}: {lines[0]}")
                    for line in lines[1:]:
                        print(f"{'':17}{line}")
                else:
                    print(f"{field:15}: {info[field]}")
        
        # Show dependencies if present
        dep_fields = ['Depends', 'Pre-Depends', 'Recommends', 'Suggests', 'Conflicts', 'Breaks', 'Replaces']
        has_deps = any(field in info for field in dep_fields)
        
        if has_deps:
            print("\nDEPENDENCIES:")
            for field in dep_fields:
                if field in info:
                    deps = info[field].split(', ')
                    print(f"  {field}:")
                    for dep in deps:
                        print(f"    - {dep}")
        
        # Show all other fields if detailed view requested
        if detailed:
            shown_fields = set(essential_fields + dep_fields)
            other_fields = {k: v for k, v in info.items() if k not in shown_fields}
            
            if other_fields:
                print("\nOTHER FIELDS:")
                for field, value in sorted(other_fields.items()):
                    print(f"  {field}: {value}")
        
        print("=" * 60)
    
    # Compatibility aliases for backward compatibility
    def unpack(self, deb_path: str, output_dir: str, safe_extract: bool = True) -> bool:
        """Alias for extract() - maintained for backward compatibility"""
        return self.extract(deb_path, output_dir, safe_extract)
    
    def pack(self, folder_path: str, output_path: str, compression: str = 'gz', verify: bool = True) -> bool:
        """Alias for build() - maintained for backward compatibility"""
        return self.build(folder_path, output_path, compression, verify)
    
    def get_package_info(self, deb_path: str) -> Optional[Dict[str, str]]:
        """Alias for info() - maintained for backward compatibility"""
        return self.info(deb_path)
    
    def verify_package(self, deb_path: str) -> bool:
        """Alias for verify() - maintained for backward compatibility"""
        return self.verify(deb_path)
    
    def list_contents(self, deb_path: str) -> Optional[Dict[str, list]]:
        """Alias for contents() - maintained for backward compatibility"""
        return self.contents(deb_path)
    
    def print_package_info(self, info: Dict[str, str], detailed: bool = False) -> None:
        """Alias for show_info() - maintained for backward compatibility"""
        self.show_info(info, detailed)


# Create singleton instance with dpkg-deb compatible name
dpkg_deb = DpkgDeb()

# Also keep old name for backward compatibility
deb_handler = dpkg_deb
