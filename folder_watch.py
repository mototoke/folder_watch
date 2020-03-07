# -*- coding: utf-8 -*-
import os
import time
import sys
import logging
import hashlib
import argparse
import textwrap
import pathlib
from pathlib import Path
import shutil
from datetime import datetime
from watchdog.observers import Observer
from logging.handlers import TimedRotatingFileHandler
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

try:
    import codecs
except ImportError:
    codecs = None


class MyTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    日付log出力用のファイルハンドラ―クラス
    """
    def __init__(self, dir_log):
        self.dir_log = dir_log
        filename = self.dir_log + time.strftime("%Y%m%d") + ".log"  # dir_log here MUST be with os.sep on the end
        logging.handlers.TimedRotatingFileHandler.__init__(self, filename, when='midnight', interval=1, backupCount=0,
                                                           encoding=None)

    def doRollover(self):
        """
        TimedRotatingFileHandler remix - rotates logs on daily basis, and filename of current logfile is time.strftime("%m%d%Y")+".txt" always
        """
        self.stream.close()
        # get the time that this sequence started at and make it a TimeTuple
        t = self.rolloverAt - self.interval
        timeTuple = time.localtime(t)
        self.baseFilename = self.dir_log + time.strftime("%Y%m%d") + ".log"
        if self.encoding:
            self.stream = codecs.open(self.baseFilename, 'w', self.encoding)
        else:
            self.stream = open(self.baseFilename, 'w')
        self.rolloverAt = self.rolloverAt + self.interval


# 監視イベント取得クラス
class WacthFileHandler(FileSystemEventHandler):
    def __init__(self, watch_path, copy_to_path, backup_path):
        super(WacthFileHandler, self).__init__()
        self.watch_path = watch_path
        self.copy_to_path = copy_to_path
        self.backup_path = backup_path

    def on_moved(self, event):
        """
        ファイル移動検知
        :param event:
        :return:
        """
        src_path = event.src_path
        src_name = os.path.basename(src_path)
        logger.info(f'{src_name}が移動しました')

    def on_created(self, event):
        """
        ファイル作成検知
        :param event:
        :return:
        """
        # ファイル名取得
        src_name = os.path.basename(event.src_path)
        logger.info(f'{src_name}ができました')
        # 監視元のフォルダパスを生成
        src_path = pathlib.Path(self.watch_path) / pathlib.Path(f'{src_name}')
        # コピー(移動)先のフォルダパスを生成
        copy_path = pathlib.Path(self.copy_to_path) / pathlib.Path(f'{src_name}')
        # バックアップ先のフォルダパスを生成
        backup_link = pathlib.Path(self.backup_path)

        try:
            # 処理を実行
            self._run(src_path, copy_path, backup_link)
        except TimeoutError as e:
            # でかすぎるッピ！
            logger.error('でかすぎるッピ！')
            logger.error(e)
        except Exception as e:
            logger.error(e)

    def on_modified(self, event):
        """
        ファイル変更検知
        :param event:
        :return:
        """
        src_path = event.src_path
        src_name = os.path.basename(src_path)
        logger.info(f'{src_name}を変更しました')

    def on_deleted(self, event):
        """
        ファイル削除検知
        :param event:
        :return:
        """
        src_path = event.src_path
        src_name = os.path.basename(src_path)
        logger.info(f'{src_name}sを削除しました')

    def _run(self, src: Path, copy: Path, bk: Path):
        """
        ファイル検知時、コピー、チェック、削除/移動
        :param src:
        :param copy:
        :return:
        """
        # 配置が完了するまで待機(一定時間[600s]待機)
        if not self._wait_for_file_created_finished_windows(file_path=src, time_out=600):
            raise TimeoutError

        # 配置されたファイルをコピー
        if not self._copy_to_file(src, copy):
            return

        # 二つのファイルのハッシュを取得
        src_hash = self._get_md5_hash(src)
        copy_hash = self._get_md5_hash(copy)

        if self._check_hash(src_hash, copy_hash):
            # ハッシュが一致
            # 元ファイルを削除
            self._del_original_file(src)
        else:
            # ハッシュが不一致
            # 退避先に移動
            self._move_original_file(bk)

    def _copy_to_file(self, src, copy):
        """
        配置されたファイルを指定フォルダにコピーする
        :param src:
        :param copy_to:
        :return:
        """
        # 配置されたファイルがなければ以降の処理は行わない
        if not src.exists():
            return False

        # ファイルのメタデータ(作成時間や変更時間など)も含めてコピー
        copy_link = shutil.copy2(src, copy, follow_symlinks=True)

        # コピーしようとしていたパスとコピーしたパスの一致を確認
        if copy != copy_link:
            return False

        if not copy.exists():
            return False

        return True

    @staticmethod
    def _wait_for_file_created_finished_linux(file_path, time_out):
        """
        Linuxで動作未確認
        配置されたファイルの作成完了判定メソッド
        参考URL:https://stackoverflow.com/questions/32092645/python-watchdog-windows-wait-till-copy-finishes
        :param file_path:
        :param time_out:
        :return:
        """
        size_now = 0
        size_past = -1
        start = time.time()
        while True:
            size_now = os.path.getsize(file_path)
            time.sleep(1)
            elapsed_time = time.time() - start
            logger.info(f"size_now: {size_now}")
            logger.info(f"size_past: {size_past}")
            if size_now == size_past and os.access(file_path, os.R_OK):
                logger.info("file has copied completely now size: %s", size_now)
                return True
            else:
                size_past = os.path.getsize(file_path)
                if elapsed_time >= time_out:
                    logger.info('time out error')
                    return False

    @staticmethod
    def _wait_for_file_created_finished_windows(file_path: Path, time_out):
        """
        配置されたファイルの作成(コピー)完了判定メソッド
        参考URL:https://stackoverflow.com/questions/34586744/os-path-getsize-on-windows-reports-full-file-size-while-copying
        :param file_path:
        :param time_out:
        :return:
        """
        start = time.time()
        while True:
            try:
                elapsed_time = time.time() - start
                new_path = str(file_path) + "_"
                os.rename(file_path, new_path)
                os.rename(new_path, file_path)
                time.sleep(1)
                logger.info('file copy...')
                return True
            except OSError:
                time.sleep(1)
                if elapsed_time >= time_out:
                    logger.info('time out error')
                    return False

    @staticmethod
    def _get_md5_hash(file_path):
        """
        ファイルのmd5ハッシュ値(16進数形式)を取得
        :param file_path:
        :return:
        """
        with open(file_path, 'rb') as file:
            binary_data = file.read()
            # ハッシュ値を16進数形式で取得
            md5 = hashlib.md5(binary_data).hexdigest()
            logger.info(f'ファイル:{file_path} - ハッシュ値 - {md5}')
            return md5

    @staticmethod
    def _check_hash(src_hash, target_hash):
        """
        二つのハッシュを比較
        :param src_hash:
        :param target_hash:
        :return:
        """
        return src_hash == target_hash

    @staticmethod
    def _del_original_file( src):
        """
        コピー元ファイルを削除
        :param src:
        :return:
        """
        os.remove(src)

    @staticmethod
    def _move_original_file(src_path, move_path):
        """
        コピー元ファイルを移動(退避)
        :return:
        """
        shutil.move(src_path, move_path)


def watch_start(from_watch_path, to_copy_path, backup_path):
    """
    フォルダ監視処理開始
    :param from_watch_path  :   監視フォルダパス
    :param to_copy_path     :   移動先フォルダパス
    :param backup_path      :   退避先フォルダパス
    :return:
    """
    event_handler = WacthFileHandler(from_watch_path, to_copy_path, backup_path)
    observer = Observer()
    observer.schedule(event_handler, from_watch_path, recursive=True)
    logger.info(f'フォルダ監視起動')
    observer.start()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    except Exception as e:
        observer.stop()
        raise e
    finally:
        # finaly = 例外の発生に関係なく最後に処理
        logger.info(f'フォルダ監視終了')
        observer.join()


def make_log_folder():
    """
    起動時にlogsフォルダが無ければ作成
    :return:
    """
    p = pathlib.Path(sys.argv[0])
    p2 = pathlib.Path(p.parent) / pathlib.Path('logs')
    if not p2.exists():
        os.makedirs(str(p2))


def interpret_args():
    """
    実行時引数の解釈メソッド
    :return: 実行時引数
    """
    # オブジェクト作成
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    # 引数設定
    # 監視フォルダパス(必須)
    parser.add_argument("-wp", "--watch_path", help=textwrap.dedent(
        '''\
        please set me.
        this is essential argument.
        this is watch folder path'''), type=str)

    # コピー先フォルダパス(必須)
    parser.add_argument("-cp", "--copy_to_path", help=textwrap.dedent(
        '''\
        please set me.
        this is essential argument.
        this is copy to folder path'''), type=str)

    # 退避先フォルダパス(必須)
    parser.add_argument("-bk", "--backup_path", help=textwrap.dedent(
        '''\
        please set me.
        this is essential argument.
        this is backup folder path'''), type=str)

    # 結果を返却
    return parser.parse_args()


def check_args(args):
    """
    実行引数の判定メソッド
    :param args:
    :return: True or False
    """
    # 監視フォルダのパスが指定されていなければエラー
    if not hasattr(args, 'watch_path') and args.watch_path is None:
        raise argparse.ArgumentError('監視フォルダ指定ないよ！')

    # 移動先フォルダのパスが指定されていなければエラー
    if not hasattr(args, 'copy_to_path') and args.copy_to_path is None:
        raise argparse.ArgumentError('移動先フォルダ指定ないよ！')

    # 退避先フォルダのパスが指定されていなければエラー
    if not hasattr(args, 'backup_path') and args.backup_path is None:
        raise argparse.ArgumentError('退避先先フォルダ指定ないよ！')

    # 各パスのオブジェクト生成
    watch_path = pathlib.Path(args.watch_path)
    copy_to_path = pathlib.Path(args.copy_to_path)
    backup_path = pathlib.Path(args.backup_path)

    # 監視フォルダのパスが存在するかチェック
    if not watch_path.exists():
        raise FileNotFoundError('監視フォルダ存在ないよ！')

    # 監視フォルダがディレクトリかどうかチェック
    if not watch_path.is_dir():
        raise TypeError('指定された監視フォルダはフォルダじゃないよ！')

    # 移動先フォルダのパスが存在するかチェック
    if not copy_to_path.exists():
        raise FileNotFoundError('移動先フォルダ存在ないよ！')

    # 移動先フォルダがディレクトリかどうかチェック
    if not copy_to_path.is_dir():
        raise TypeError('指定された移動先フォルダはフォルダじゃないよ！')

    # 移動先フォルダのパスが存在するかチェック
    if not backup_path.exists():
        raise FileNotFoundError('退避先フォルダ存在ないよ！')

    # 移動先フォルダがディレクトリかどうかチェック
    if not backup_path.is_dir():
        raise TypeError('指定された退避先フォルダはフォルダじゃないよ！')


# 実行処理
if __name__ == '__main__':

    # ログフォルダなければ作成(※loggingはフォルダまでは作ってくれないので)
    make_log_folder()

    # ロギング設定
    # get the root logger
    root_logger = logging.getLogger()
    # set overall level to debug, default is warning for root logger
    root_logger.setLevel(logging.DEBUG)

    # setup logging to file, rotating at midnight
    file_log = MyTimedRotatingFileHandler(f'./logs/log_')
    file_log.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('■%(asctime)s - %(levelname)s - [%(funcName)s() %(lineno)d行] : %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S')
    file_log.setFormatter(file_formatter)
    root_logger.addHandler(file_log)

    # setup logging to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('■%(asctime)s - %(levelname)s - [%(funcName)s() %(lineno)d行] : %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # get a logger for my script
    logger = logging.getLogger(__name__)

    try:
        with open('pid', mode='w') as f:
            logger.info(f'pid = [{str(os.getpid())}]')
            f.write(str(os.getpid()))

        # 引数解釈,判定
        args = interpret_args()
        # 引数チェック
        check_args(args)
        # 監視実行
        watch_start(args.watch_path, args.copy_to_path, args.backup_path)
    except argparse.ArgumentError as e:
        logger.error(e)
    except FileNotFoundError as e:
        logger.error(e)
    except TypeError as e:
        logger.error(e)
    except Exception as e:
        logger.error(e)
