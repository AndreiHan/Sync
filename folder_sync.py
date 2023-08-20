""" Folder sync class """
import os
import time
import logging
import hashlib
import typing
import shutil
import stat

from sync_logger import SyncLogger


class FolderSync:
    """ Folder sync class"""

    __slots__ = ("source_folder", "backup_folder", "backup_interval", "logger")

    def __init__(
            self, source_folder: str, backup_folder: str,
            backup_interval: float = 5, logger: logging.Logger = None
    ) -> None:

        self.source_folder = source_folder
        self.backup_folder = backup_folder
        self.backup_interval = backup_interval

        self.logger = logger
        if logger is None:
            self.logger = SyncLogger().main_logger

    @staticmethod
    def __compare_progressive_file_hash(first_file: typing.BinaryIO,
                                        second_file: typing.BinaryIO) -> bool:
        """ Returns the hash of a file """
        first_md5 = hashlib.md5().copy()
        second_md5 = hashlib.md5().copy()
        for (first_chunk, second_chunks) in zip(iter(lambda: first_file.read(4096), b""),
                                                iter(lambda: second_file.read(4096), b"")):
            first_md5.update(first_chunk)
            second_md5.update(second_chunks)
            if first_md5.hexdigest() != second_md5.hexdigest():
                return False
        return first_md5.hexdigest() == second_md5.hexdigest()

    @staticmethod
    def get_folder_and_files(path: str) -> tuple[set[str], set[str]]:
        """ returns a tuple: dirlist, filelist"""
        file_list: set[str] = set()
        dir_list: set[str] = set()
        for root, dirs, files in os.walk(path):
            for file in files:
                file_list.add(os.path.join(root, file))
            for current_dir in dirs:
                dir_list.add(os.path.join(root, current_dir))
        return dir_list, file_list

    @staticmethod
    def onerror(func, path, exc_info):
        """ Error handler for shutil.rmtree """
        # pylint: disable= [misplaced-bare-raise, unused-argument]
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWUSR)
            func(path)
        else:
            raise

    def __make_dirs(self, path):
        """ Make dirs"""
        try:
            os.makedirs(path)
            self.logger.warning("Created %s", path)
        except OSError as err:
            self.logger.warning("Failed to create %s with err %s", path, err)

    def __compare_file_hashes(self, file1: str, file2: str) -> bool:
        """ Compares 2 file haches """
        if os.path.isdir(file1) or os.path.isdir(file2):
            return self.__compare_folder_hashes(file1, file2)
        if not os.path.isfile(file1) or not os.path.isfile(file2):
            return False
        try:
            if os.path.getsize(file1) != os.path.getsize(file2):
                return False
        except OSError:
            self.logger.debug("Could not get file size for %s %s", file1, file2)
        try:
            with open(file1, 'rb') as first_file, open(file2, 'rb') as second_file:
                return self.__compare_progressive_file_hash(first_file, second_file)
        except OSError as err:
            self.logger.debug("Failed comparing: %s and %s with err: %s",
                              file1, file2, err)
            return False

    def __compare_folder_hashes(self, first_folder: str, second_folder: str) -> bool:
        """ Compares the hashes of 2 folders """
        if not os.path.isdir(first_folder):
            self.logger.debug("Could not find: %s", first_folder)
            return False

        if not os.path.isdir(second_folder):
            self.logger.debug("Could not find: %s", second_folder)
            return False

        first_dirs = os.listdir(first_folder)
        second_dirs = os.listdir(second_folder)
        if len(first_dirs) != len(second_dirs):
            return False

        for file in first_dirs:
            if file in second_dirs:
                if not self.__compare_file_hashes(os.path.join(first_folder, file),
                                                  os.path.join(second_folder, file)):
                    return False
            else:
                return False
        return True

    def __sync_two_files(self, source, backup) -> bool:
        """ Syncs 2 files """
        status = True
        if not os.path.isfile(source):
            return False
        if os.path.isfile(backup):
            try:
                os.remove(backup)
            except OSError as err:
                self.logger.debug("Failed to delete %s with err %s", backup, err)

        backup_folder = os.path.dirname(backup)
        if not os.path.isdir(os.path.dirname(backup)):
            try:
                os.makedirs(backup_folder)
                self.logger.info("Created dir %s", backup_folder)
            except OSError as err:
                self.logger.warning("Failed to create dir %s with err %s", backup_folder, err)
                status = False
        try:
            shutil.copy(source, backup)
            self.logger.info("Created file %s", backup)
        except OSError as err:
            self.logger.warning("Failed to sync/copy %s with err %s", backup, err)

            return False
        return status

    def __sync_file_list(self, source_files: set[str],
                         backup_files: set[str]) -> bool:
        """ Syncs 2 files from lists """
        status = True
        for file in source_files:
            backup_file = file.replace(self.source_folder, self.backup_folder)
            if self.__compare_file_hashes(file, backup_file):
                continue
            if not self.__sync_two_files(file, backup_file):
                status = False

        for file in backup_files:
            if os.path.isfile(file.replace(self.backup_folder, self.source_folder)):
                continue
            if not os.path.isfile(file):
                continue
            try:
                os.remove(file)
                self.logger.info("Removed %s", file)
            except OSError as err:
                self.logger.warning("Failed to remove %s with err %s", file, err)
                status = False
        return status

    def __sync_dir_list(self, source_dirs: set[str],
                        backup_dirs: set[str]) -> bool:
        """ Syncs two sets of dirs from lists """
        status = True
        for current_dir in source_dirs:
            backup_dir = current_dir.replace(self.source_folder, self.backup_folder)
            try:
                if not os.listdir(current_dir) and not os.path.isdir(backup_dir):
                    self.__make_dirs(backup_dir)
            except OSError:
                self.logger.debug("dir --Cannot find dir %s or %s", current_dir, backup_dir)
                continue

        for current_dir in backup_dirs:
            if os.path.isdir(current_dir.replace(self.backup_folder, self.source_folder)):
                continue
            if not os.path.isdir(current_dir):
                continue
            try:
                shutil.rmtree(current_dir, onerror=self.onerror)
                self.logger.info("Removed %s", current_dir)
            except OSError as err:
                self.logger.warning("Failed to remove %s with err %s", current_dir, err)
                status = False
        return status

    def __start_sync(self):
        """ Starts a sync run """
        start_time = time.time()

        source_dirs, source_files = self.get_folder_and_files(self.source_folder)
        backup_dirs, backup_files = self.get_folder_and_files(self.backup_folder)

        self.__sync_file_list(source_files, backup_files)
        self.__sync_dir_list(source_dirs, backup_dirs)

        self.logger.info("Finished sync (%s)",
                         round(time.time() - start_time))

    def sync(self):
        """ Main loop """
        self.logger.info("Start sync")

        while True:
            if self.__compare_folder_hashes(self.source_folder, self.backup_folder):
                self.logger.info("Done checking, waiting for: %ss", self.backup_interval * 60)
                time.sleep(self.backup_interval * 60)
                continue
            self.__start_sync()
