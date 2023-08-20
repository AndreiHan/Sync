""" Main sync py file """
import os
import argparse
from dataclasses import dataclass

from sync_logger import SyncLogger
from folder_sync import FolderSync


@dataclass(frozen=True, slots=True)
class SyncSettings:
    """ Stores the sync settings """
    source_folder: str
    backup_folder: str
    logger_path: str
    verbose_logging: bool = False
    backup_interval: float = 5


def get_args() -> SyncSettings:
    """ Returns a SynsSetting dataclass with the wanted settings """
    parser = argparse.ArgumentParser(description='Backup a folder to another location.')

    parser.add_argument("source_path", help="The source folder", type=str)
    parser.add_argument("backup_path", help="The backup folder", type=str)
    parser.add_argument("logger_path", help="The logger path", type=str)
    parser.add_argument("-t", "--time", action="store", default=5, type=float,
                        help="Backup interval (in minutes)")
    parser.add_argument("-v", "--verbose", action="store_const", const=True, default=False,
                        help="Backup interval (in minutes)")
    args = parser.parse_args()

    data: SyncSettings = SyncSettings(
        source_folder=args.source_path,
        backup_folder=args.backup_path,
        logger_path=args.logger_path,
        verbose_logging=args.verbose,
        backup_interval=args.time
    )
    dir_list: list[str] = [data.source_folder, data.backup_folder, data.logger_path]
    for folder in dir_list:
        if not os.path.isdir(folder):
            parser.error(f"{folder} is not a directory")

    return data


def main():
    """ Main start method """
    sync_settings: SyncSettings = get_args()
    logger = SyncLogger(sync_settings.logger_path, sync_settings.verbose_logging).main_logger
    logger.info("Received following args: %ss", sync_settings)
    sync_obj = FolderSync(source_folder=sync_settings.source_folder,
                          backup_folder=sync_settings.backup_folder,
                          backup_interval=sync_settings.backup_interval,
                          logger=logger)
    sync_obj.sync()


if __name__ == "__main__":
    main()
