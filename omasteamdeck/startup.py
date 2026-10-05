"""Isolated, offline Three.js startup surface; the shell remains native Qt.

Qt WebEngine is imported lazily so --skip-splash and native unit tests do not
require a browser engine. No Core launch, workspace or controller APIs are exposed.
"""
from pathlib import Path
from PySide6.QtCore import QObject,Signal,Slot,QTimer,QUrl,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout
from PySide6.QtGui import QColor

class StartupBridge(QObject):
    sceneReady=Signal()
    finished=Signal()
    error=Signal(str)
    @Slot()
    def ready(self): self.sceneReady.emit()
    @Slot()
    def complete(self): self.finished.emit()
    @Slot(str)
    def failed(self,message): self.error.emit(message)

class StartupView(QWidget):
    ready=Signal()
    finished=Signal()
    failed=Signal(str)
    def __init__(self,motion=True,parent=None):
        super().__init__(parent)
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineSettings,QWebEngineUrlRequestInterceptor
        from PySide6.QtWebChannel import QWebChannel
        self.disposed=False; self.completed=False; self.scene_ready=False
        class OfflineOnly(QWebEngineUrlRequestInterceptor):
            def interceptRequest(self,info):
                if info.requestUrl().scheme() not in ('file','qrc','data'): info.block(True)
        class LocalPage(QWebEnginePage):
            def acceptNavigationRequest(page,url,kind,is_main_frame):
                return url.scheme()=='file' and url.toLocalFile()==str(Path(__file__).with_name('assets')/'startup/index.html')
            def javaScriptConsoleMessage(page,level,message,line,source):
                # Do not print verbose Chromium diagnostics or arbitrary page content.
                if level==QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                    self.failed.emit('Startup script error: '+message[:200])
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        self.view=QWebEngineView(self); self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus); layout.addWidget(self.view)
        self.profile=QWebEngineProfile(self); self.interceptor=OfflineOnly(self.profile); self.profile.setUrlRequestInterceptor(self.interceptor)
        self.page=LocalPage(self.profile,self.view); self.view.setPage(self.page); self.page.setBackgroundColor(QColor('#03070c'))
        settings=self.page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled,False)
        self.bridge=StartupBridge(self); self.channel=QWebChannel(self.page); self.channel.registerObject('startup',self.bridge); self.page.setWebChannel(self.channel)
        self.bridge.sceneReady.connect(self._ready); self.bridge.finished.connect(self._finished); self.bridge.error.connect(self.failed)
        self.page.loadFinished.connect(self._loaded)
        self.timeout=QTimer(self); self.timeout.setSingleShot(True); self.timeout.timeout.connect(self._timeout); self.timeout.start(8000)
        url=QUrl.fromLocalFile(str(Path(__file__).with_name('assets')/'startup/index.html')); url.setQuery('motion='+('1' if motion else '0')); self.view.load(url)
    def _loaded(self,ok):
        if not ok: self.failed.emit('Could not load the local startup scene.'); self._finished()
    def _ready(self):
        if self.disposed:return
        self.scene_ready=True; self.ready.emit()
    def _timeout(self):
        if not self.completed:
            self.failed.emit('3D startup timed out. Continuing to profiles.'); self._finished()
    def _finished(self):
        if self.completed or self.disposed:return
        self.completed=True; self.timeout.stop(); self.finished.emit()
    def dispose(self):
        if self.disposed:return
        self.disposed=True; self.timeout.stop()
        self.page.runJavaScript('window.omaflowDispose?.()')
        self.view.stop()
    def hideEvent(self,event):
        self.dispose(); super().hideEvent(event)
