import os
import numpy as np
import pydicom
from typing import Optional
from PIL import Image
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Qt
from PySide6.QtGui import QImage, QPixmap, QColor

_THUMBNAIL_CACHE = {}
_MAX_CACHE_SIZE = 500

def get_cached_thumbnail(file_path: str, size: tuple = (180, 180)) -> Optional[QPixmap]:
    key = (file_path, size)
    return _THUMBNAIL_CACHE.get(key)

def set_cached_thumbnail(file_path: str, size: tuple, pixmap: QPixmap):
    if len(_THUMBNAIL_CACHE) > _MAX_CACHE_SIZE:
        for _ in range(100):
            _THUMBNAIL_CACHE.pop(next(iter(_THUMBNAIL_CACHE)), None)
    key = (file_path, size)
    _THUMBNAIL_CACHE[key] = pixmap


class ThumbnailSignals(QObject):
    loaded = Signal(str, QPixmap)


class ThumbnailLoaderRunnable(QRunnable):
    def __init__(self, file_path: str, signals: ThumbnailSignals, target_size: tuple = (180, 180)):
        super().__init__()
        self.file_path = file_path
        self.signals = signals
        self.target_size = target_size

    def run(self):
        cached = get_cached_thumbnail(self.file_path, self.target_size)
        if cached:
            try:
                self.signals.loaded.emit(self.file_path, cached)
            except RuntimeError:
                pass
            return

        pixmap = None
        try:
            ds = pydicom.dcmread(self.file_path, force=True)
            if hasattr(ds, 'pixel_array'):
                arr = ds.pixel_array.astype(float)

                slope = float(getattr(ds, 'RescaleSlope', 1.0))
                intercept = float(getattr(ds, 'RescaleIntercept', 0.0))
                arr = arr * slope + intercept

                if hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth'):
                    wc = ds.WindowCenter
                    ww = ds.WindowWidth
                    if isinstance(wc, pydicom.multival.MultiValue):
                        wc = wc[0]
                    if isinstance(ww, pydicom.multival.MultiValue):
                        ww = ww[0]
                    wc, ww = float(wc), float(ww)
                    amin = wc - ww / 2.0
                    amax = wc + ww / 2.0
                    arr = np.clip(arr, amin, amax)

                pmin, pmax = arr.min(), arr.max()
                if pmax > pmin:
                    norm = ((arr - pmin) / (pmax - pmin) * 255.0).astype(np.uint8)
                else:
                    norm = np.zeros(arr.shape, dtype=np.uint8)

                height, width = norm.shape[:2]
                qimg = QImage(norm.data, width, height, width, QImage.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimg)

                if self.target_size:
                    pixmap = pixmap.scaled(
                        self.target_size[0], self.target_size[1],
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                set_cached_thumbnail(self.file_path, self.target_size, pixmap)
        except Exception:
            pixmap = None

        if pixmap is None:
            pixmap = QPixmap(self.target_size[0], self.target_size[1])
            pixmap.fill(QColor("#1A233A"))

        try:
            self.signals.loaded.emit(self.file_path, pixmap)
        except RuntimeError:
            pass


class ThumbnailManager(QObject):
    """Manages thread pool for lazy asynchronous thumbnail extraction."""
    def __init__(self, max_threads: int = 4, parent=None):
        super().__init__(parent)
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(max_threads)
        self._signals_registry = []

    def request_thumbnail(self, file_path: str, callback, target_size: tuple = (180, 180)):
        cached = get_cached_thumbnail(file_path, target_size)
        if cached:
            callback(file_path, cached)
            return

        signals = ThumbnailSignals()
        signals.setParent(self)
        signals.loaded.connect(callback)

        runnable = ThumbnailLoaderRunnable(file_path, signals, target_size)
        self.thread_pool.start(runnable)
