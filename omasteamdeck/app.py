"""OmaFlow native handheld shell. No web server or elevated privileges."""
from __future__ import annotations
import argparse
import configparser
import os
from pathlib import Path
import subprocess
import sys
from PySide6.QtCore import Qt, QTimer, QEvent, QUrl, QProcess, QLockFile, QPropertyAnimation, QEasingCurve, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QScrollArea, QDialog, QLineEdit, QGraphicsOpacityEffect)
from .core import State, Item, MEDIA, STORES, discover_apps, discover_games, desktop_command
from .controller import Controller
from .desktop import Desktop, DesktopError, WORKSPACES, omarchy_command

from .visuals import DISPLAY_NAME, STYLE, Logo, Card, ProfileCard, DetailArtwork, Backdrop, NavButton, CategoryCard

TABS = ['Home', 'Games', 'Media', 'Store', 'Library', 'Apps', 'Settings']

def label(text, name=None):
    obj = QLabel(text)
    obj.setTextFormat(Qt.TextFormat.PlainText)
    if name: obj.setObjectName(name)
    return obj

def button(text, callback, name=None):
    obj=QPushButton(text)
    if name: obj.setObjectName(name)
    obj.setCursor(Qt.CursorShape.PointingHandCursor)
    obj.clicked.connect(callback)
    return obj

class TextDialog(QDialog):
    """Controller-operable on-screen keyboard; physical typing also works."""
    def __init__(self,title,value='',parent=None):
        super().__init__(parent)
        self.setWindowTitle(title); self.setModal(True); self.setFixedSize(720,440)
        layout=QVBoxLayout(self); layout.setContentsMargins(24,20,24,20)
        layout.addWidget(label(title,'title'))
        self.edit=QLineEdit(value); self.edit.setMaxLength(80 if title=='Search library' else 24)
        layout.addWidget(self.edit)
        grid=QGridLayout(); self.keys=[]
        for i,char in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
            key=button(char,lambda checked=False,c=char:self.insert(c),'key'); grid.addWidget(key,i//9,i%9); self.keys.append(key)
        layout.addLayout(grid)
        row=QHBoxLayout()
        for name,action in [('Space',lambda:self.insert(' ')),('⌫',self.edit.backspace),('Cancel',self.reject),('Done',self.accept)]:
            key=button(name,action); self.keys.append(key); row.addWidget(key)
        layout.addLayout(row)
        self.keys[0].setFocus()
    def insert(self,char): self.edit.insert(char)
    def navigate(self,action):
        if action=='back': self.reject(); return
        if action=='accept':
            focus=self.focusWidget()
            if isinstance(focus,QPushButton): focus.click()
            else: self.accept()
            return
        focus=self.focusWidget(); index=self.keys.index(focus) if focus in self.keys else 0
        delta={'left':-1,'right':1,'up':-9,'down':9}.get(action,0)
        if delta: self.keys[max(0,min(len(self.keys)-1,index+delta))].setFocus()

class Shell(Backdrop):
    def __init__(self,state=None,windowed=False,skip_splash=False,desktop=None):
        super().__init__()
        self.state=state or State(); self.profile_index=0; self.tab='Home'; self.query=''; self.page='splash'; self.rows=[]; self.cards=[]; self.current_items=[]; self.children_processes=[]
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.setWindowTitle(DISPLAY_NAME); self.resize(1280,800); self.setMinimumSize(800,600)
        self.root=QVBoxLayout(self); self.root.setContentsMargins(34,28,34,20); self.root.setSpacing(14)
        self.controller=Controller()
        self.desktop=desktop or Desktop(enabled=QApplication.platformName()!='offscreen')
        self.system_processes=[]
        self.desktop_session_ready=False
        self.attach_attempts=0
        self.apps=discover_apps(); self.games=discover_games()
        self.toast_timer=QTimer(self); self.toast_timer.setSingleShot(True); self.toast_timer.timeout.connect(self.clear_status)
        self.poll_timer=QTimer(self); self.poll_timer.timeout.connect(self.poll); self.poll_timer.start(16)
        self.clock_timer=QTimer(self); self.clock_timer.timeout.connect(self.update_status); self.clock_timer.start(15000)
        QApplication.instance().installEventFilter(self)
        self.apply_scale()
        if windowed or not self.state.data['fullscreen']: self.show()
        else: self.showFullScreen()
        if skip_splash: self.show_profiles()
        else:
            self.show_splash()
        if self.desktop.available: QTimer.singleShot(250,self.attach_desktop)
    @property
    def profile(self): return self.state.data['profiles'][self.profile_index]
    def persist(self):
        try: self.state.save()
        except OSError: self.message('Could not save preferences. Check your config folder permissions.')
    def apply_scale(self):
        scale=self.state.data['scale']/100
        import re
        self.setStyleSheet(re.sub(r'font-size: (\d+)px',lambda m:f'font-size: {int(int(m[1])*scale)}px',STYLE))
    def clear(self):
        self.root.setContentsMargins(34,28,34,20)
        while self.root.count():
            item=self.root.takeAt(0)
            if item.widget(): item.widget().hide(); item.widget().deleteLater()
            elif item.layout(): self.clear_layout(item.layout())
        self.rows=[]; self.cards=[]; self.current_items=[]
    def clear_layout(self,layout):
        while layout.count():
            item=layout.takeAt(0)
            if item.widget(): item.widget().hide(); item.widget().deleteLater()
            elif item.layout(): self.clear_layout(item.layout())
    def show_splash(self):
        self.clear(); self.page='splash'; self.update(); self.startup=None
        # Only the startup is web-rendered; profiles and every action remain native.
        try:
            if QApplication.platformName()=='offscreen' and os.environ.get('OMAFLOW_TEST_WEBENGINE')!='1':
                raise ImportError('Native-only test surface')
            from .startup import StartupView
            # PySide6 6.11 can recursively wrap private Qt Quick focus objects
            # through an application-wide Python filter. Limit keyboard handling
            # to this window while WebEngine lives; Core controller polling stays
            # active, and the page also handles Enter/Escape via its narrow bridge.
            QApplication.instance().removeEventFilter(self)
            self.installEventFilter(self)
            self.startup=StartupView(self.state.data['motion'],self)
            self.startup.destroyed.connect(self.resume_native_input,Qt.ConnectionType.QueuedConnection)
        except ImportError:
            self.resume_native_input()
            # Explicit native-only development path. No imitation 3D animation.
            self.root.addStretch(); title=label(DISPLAY_NAME,'title'); title.setAlignment(Qt.AlignmentFlag.AlignCenter); self.root.addWidget(title)
            hint=label('A / ENTER  Continue','muted'); hint.setAlignment(Qt.AlignmentFlag.AlignCenter); self.root.addWidget(hint); self.root.addStretch()
            QTimer.singleShot(900,title,self.finish_splash)
            return
        self.root.setContentsMargins(0,0,0,0); self.root.addWidget(self.startup)
        self.startup.finished.connect(self.finish_splash)
        self.startup.failed.connect(lambda message:print(message,file=sys.stderr))
    @Slot()
    def resume_native_input(self):
        # Queued until the browser's private children have also been destroyed.
        self.removeEventFilter(self)
        if self.poll_timer.isActive(): QApplication.instance().installEventFilter(self)
    def finish_splash(self):
        if self.page!='splash': return
        if getattr(self,'startup',None): self.startup.dispose()
        self.show_profiles()
        if self.state.data['motion']:
            # The WebGL scene fades to this same color before native profiles appear.
            overlay=QLabel(self); overlay.setStyleSheet('background: #03070c;'); overlay.setGeometry(self.rect())
            overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); overlay.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.transition=overlay
            effect=QGraphicsOpacityEffect(overlay); overlay.setGraphicsEffect(effect)
            animation=QPropertyAnimation(effect,b'opacity',overlay); animation.setDuration(320)
            animation.setStartValue(1.0); animation.setEndValue(0.0); animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            def completed():
                overlay.deleteLater()
                if getattr(self,'transition',None) is overlay:self.transition=None
            animation.finished.connect(completed); overlay.show(); animation.start()
    def show_profiles(self):
        self.clear(); self.page='profiles'; self.query=''; self.update()
        top=QHBoxLayout(); top.addWidget(label(DISPLAY_NAME,'brand')); top.addStretch(); top.addWidget(label(self.status_text(),'muted')); self.root.addLayout(top)
        self.root.addSpacing(30)
        self.root.addWidget(label('Choose a profile','title'))
        self.root.addWidget(label('Pick your space to continue.','heroCopy'))
        self.profile_scroll=QScrollArea(); self.profile_scroll.setWidgetResizable(True)
        self.profile_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content=QWidget(); outer=QVBoxLayout(content); outer.setContentsMargins(0,0,0,0); outer.addStretch()
        panel=QWidget(); grid=QGridLayout(panel); grid.setContentsMargins(0,10,0,10); grid.setSpacing(8)
        all_buttons=[]; scale=self.state.data['scale']/100; count=len(self.state.data['profiles']); total=count+(count<8)
        columns=min(total,5) if total<=5 else 4
        panel.setFixedWidth(min(1160,columns*round(195*scale)))
        for i,profile in enumerate(self.state.data['profiles']):
            count=len(profile['favorites']); subtitle=f'{count} pinned favorites' if count else 'Personal space'
            b=ProfileCard(profile['name'],i,lambda checked=False,index=i:self.choose_profile(index),scale,subtitle=subtitle)
            grid.addWidget(b,i//columns,i%columns); all_buttons.append(b)
        if len(all_buttons)<8:
            add=ProfileCard('Add profile',3,self.add_profile,scale,adding=True,subtitle='A space of your own')
            grid.addWidget(add,len(all_buttons)//columns,len(all_buttons)%columns); all_buttons.append(add)
        for column in range(columns): grid.setColumnStretch(column,1)
        outer.addWidget(panel,0,Qt.AlignmentFlag.AlignHCenter); outer.addStretch()
        self.profile_scroll.setWidget(content); self.root.addWidget(self.profile_scroll,1)
        bottom=QHBoxLayout(); bottom.addWidget(label('D-PAD  Navigate     A / ENTER  Select','muted')); bottom.addStretch()
        quit_button=button('Exit to desktop',self.close); bottom.addWidget(quit_button); self.root.addLayout(bottom)
        self.rows=[all_buttons[i:i+columns] for i in range(0,len(all_buttons),columns)]+[[quit_button]]
        target=all_buttons[min(self.profile_index,len(all_buttons)-1)]; target.setFocus()
        QTimer.singleShot(0,target,lambda:self.profile_scroll.ensureWidgetVisible(target,16,16))
    def choose_profile(self,index): self.profile_index=index; self.query=''; self.show_home()
    def add_profile(self):
        dialog=TextDialog('Name your profile',parent=self)
        if dialog.exec():
            try:
                if self.state.add_profile(dialog.edit.text()): self.profile_index=len(self.state.data['profiles'])-1; self.show_home()
                else: self.message('Choose a unique name, up to 24 characters. Maximum 8 profiles.')
            except OSError: self.message('Profile could not be saved. Check config folder permissions.')
    def status_text(self):
        from datetime import datetime
        power=''
        for p in Path('/sys/class/power_supply').glob('BAT*'):
            try: power=f"  ·  {int((p/'capacity').read_text())}% battery"; break
            except (OSError,ValueError): pass
        pad='Controller connected' if self.controller.handles else 'Keyboard / touch'
        return f'{pad}{power}  ·  {datetime.now():%I:%M %p}'
    def update_status(self):
        if self.page=='home' and hasattr(self,'status'): self.status.setText(self.status_text())
    def show_home(self):
        focused=QApplication.focusWidget()
        focus_id=getattr(getattr(focused,'item',None),'id',None)
        focus_title=getattr(focused,'title',None) if self.page=='home' else None
        self.clear(); self.page='home'; self.update()
        scale=self.state.data['scale']/100
        top=QHBoxLayout(); intro=QVBoxLayout(); intro.setSpacing(8)
        intro.addWidget(label(DISPLAY_NAME,'brand'))
        greeting='Welcome back, '+self.profile['name'] if self.tab=='Home' else self.tab
        title=label(greeting,'greeting'); title.setToolTip(greeting)
        title.setText(title.fontMetrics().elidedText(greeting,Qt.TextElideMode.ElideRight,560)); intro.addWidget(title)
        subtitles={'Home':'What would you like to do today?','Games':'Your next adventure is right here.','Media':'Movies, music and your favorite creators.','Store':'Discover games, independent creators and apps.','Library':'Your favorites and recent launches.','Apps':'Productivity, creativity and everyday tools.','Settings':'Customize your experience.'}
        intro.addWidget(label(subtitles[self.tab],'muted')); top.addLayout(intro,1)
        actions=QVBoxLayout(); actions.setSpacing(12); self.status=label(self.status_text(),'muted'); self.status.setAlignment(Qt.AlignmentFlag.AlignRight); actions.addWidget(self.status)
        action_row=QHBoxLayout(); action_row.addStretch()
        search=button('Search',self.search); action_row.addWidget(search)
        desktop_btn=button('Workspaces',self.workspaces); action_row.addWidget(desktop_btn)
        profile_btn=button('Profiles',self.show_profiles); profile_btn.setAccessibleName('Profiles: '+self.profile['name']); action_row.addWidget(profile_btn)
        actions.addLayout(action_row); top.addLayout(actions); self.root.addLayout(top)
        self.root.addSpacing(12)
        body=QHBoxLayout(); body.setSpacing(20); sidebar=QVBoxLayout(); sidebar.setSpacing(5); self.nav=[]
        for name in TABS:
            b=NavButton(name,lambda checked=False,t=name:self.set_tab(t),scale); b.setProperty('active',name==self.tab); b.setFixedWidth(round(156*scale)); sidebar.addWidget(b); self.nav.append(b)
        sidebar.addStretch()
        logo=Logo(self.state.data['motion']); logo.setFixedSize(136,66); sidebar.addWidget(logo,0,Qt.AlignmentFlag.AlignLeft)
        sidebar.addWidget(label('BUILD 1 · HANDHELD','eyebrow')); body.addLayout(sidebar)
        main=QVBoxLayout(); main.setSpacing(8)
        row=QHBoxLayout(); self.section=label('','eyebrow'); row.addWidget(self.section,1)
        refresh=button('Refresh',self.refresh); refresh.setFixedHeight(round(42*scale)); row.addWidget(refresh); main.addLayout(row)
        self.rows=[[search,desktop_btn,profile_btn],self.nav,[refresh]]
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content=QWidget(); self.grid=QGridLayout(content); self.grid.setContentsMargins(0,1,7,8); self.grid.setSpacing(10); self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(content); main.addWidget(self.scroll,1); body.addLayout(main,1); self.root.addLayout(body,1)
        self.populate()
        self.notice=label('D-PAD  Navigate     A  Select     B  Profiles     X  Pin     Y  Search     LB / RB  Sections','notice'); self.root.addWidget(self.notice)
        target=next((c for c in self.cards if (focus_id and getattr(getattr(c,'item',None),'id',None)==focus_id) or (focus_title and getattr(c,'title',None)==focus_title)), self.cards[0] if self.cards else self.nav[TABS.index(self.tab)])
        target.setFocus()
        # Rebuilt cards need their final geometry before restoring scroll position.
        # Tie the callback to the target so a subsequent page change cancels it.
        scroll=self.scroll
        QTimer.singleShot(0,target,lambda:scroll.ensureWidgetVisible(target,16,16))
    def catalog(self): return self.games+self.apps+MEDIA+STORES
    def populate(self):
        if self.tab=='Home' and not self.query:
            self.section.setText('YOUR DECK. MORE POSSIBILITIES.')
            categories=[('Play Games','Your Steam library','Games'),('Watch & Stream','Movies, music & more','Media'),('Browse Apps','Productivity & tools','Apps'),('System Settings','Make yourself at home','Settings')]
            for i,(title,subtitle,section) in enumerate(categories):
                b=CategoryCard(title,subtitle,section,lambda checked=False,t=section:self.set_tab(t),self.state.data['scale']/100)
                self.grid.addWidget(b,0,i); self.cards.append(b)
            catalog={item.id:item for item in self.catalog()}
            recent=[catalog[id] for id in self.profile['recent'] if id in catalog][:4]
            favorites=[catalog[id] for id in self.profile['favorites'] if id in catalog and id not in self.profile['recent']][:4]
            items=(recent+favorites)[:4]
            heading='Recently used' if recent else 'Your favorites' if favorites else 'Explore your Deck'
            if not items: items=(self.games[:2]+[MEDIA[2],MEDIA[0],MEDIA[1],STORES[1]])[:4]
            self.current_items=items
            shelf=label(heading,'heroCopy'); shelf.setContentsMargins(6,13,0,3); self.grid.addWidget(shelf,1,0,1,4)
            for i,item in enumerate(items):
                card=Card(('★ ' if item.id in self.profile['favorites'] else '')+item.name,item.subtitle,item.icon,i,lambda checked=False,v=item:self.details(v),self.state.data['scale']/100)
                card.item=item; card.setMinimumHeight(round(176*self.state.data['scale']/100)); self.grid.addWidget(card,2,i); self.cards.append(card)
        elif self.tab=='Settings':
            entries=[('Desktop & workspaces','Omarchy + Hyprland' if self.desktop.available else 'Session setup needed',self.workspaces),('Sound & brightness','Handheld quick controls',self.quick_controls),('Omarchy tools','Files, terminal & system menu',self.omarchy_tools),('Display', 'Full screen' if self.isFullScreen() else 'Windowed',self.toggle_fullscreen),('Motion','Animated logo' if self.state.data['motion'] else 'Reduced motion',self.toggle_motion),('Text size',str(self.state.data['scale'])+'%',self.toggle_scale),('Profiles','Switch or create a profile',self.show_profiles),('Rename profile',self.profile['name'],self.rename),('Controller help','Controls & Steam Deck setup',self.help),('About',DISPLAY_NAME+' · Build 1',self.about),('Exit to desktop','Close OmaFlow',self.close)]
            self.section.setText('PREFERENCES')
            for title,subtitle,callback in entries: self.add_card(title,subtitle,'⚙',callback)
        else:
            items={'Home':self.catalog(),'Games':self.games,'Media':MEDIA,'Store':STORES,'Apps':self.apps}.get(self.tab)
            if self.tab=='Library':
                ids=self.profile['favorites']+self.profile['recent']; catalog={i.id:i for i in self.catalog()}; items=[catalog[id] for id in dict.fromkeys(ids) if id in catalog]
            if self.query: items=[i for i in items if self.query.casefold() in (i.name+' '+i.subtitle).casefold()]
            self.current_items=items
            self.section.setText((f'RESULTS FOR “{self.query}”  ·  ' if self.query else '')+f'{len(items)} '+('DESTINATIONS' if self.tab in ('Store','Media') else 'IN YOUR COLLECTION'))
            for item in items:
                star='★ ' if item.id in self.profile['favorites'] else ''
                self.add_card(star+item.name,item.subtitle,item.icon,lambda checked=False,i=item:self.details(i),item)
            if not items:
                if self.query:
                    self.add_card('No matches','Try a shorter name or clear your search.','search',self.empty_action)
                elif self.tab=='Games':
                    self.add_card('Open Steam','Install a game, then select Refresh.','games',self.empty_action)
                    self.add_card('Explore game stores','Find your next adventure.','store',lambda:self.set_tab('Store'))
                    self.add_card('Browse Apps','Your installed launchers & tools.','apps',lambda:self.set_tab('Apps'))
                    self.add_card('Controller guide','Get comfortable with every control.','controller help',self.help)
                elif self.tab=='Library':
                    self.add_card('Find your favorites','Open any item and choose Pin to Library.','library',lambda:self.set_tab('Media'))
                    self.add_card('Explore Games','Make room for your next adventure.','games',lambda:self.set_tab('Games'))
                    self.add_card('Watch & listen','A home for your favorite services.','media',lambda:self.set_tab('Media'))
                    self.add_card('Browse Apps','Bring your everyday tools together.','apps',lambda:self.set_tab('Apps'))
                else:
                    self.add_card('Nothing here yet','Refresh to find installed applications.','apps',self.refresh)
        self.rows.extend([self.cards[i:i+4] for i in range(0,len(self.cards),4)])
        for c in range(4): self.grid.setColumnStretch(c,1)
    def add_card(self,title,subtitle,icon,callback,item=None):
        i=len(self.cards)
        b=Card(title,subtitle,icon,i,callback,self.state.data['scale']/100); b.item=item
        self.grid.addWidget(b,i//4,i%4); self.cards.append(b)
    def empty_action(self):
        if self.query: self.query=''; self.show_home()
        elif self.tab=='Games': self.launch(Item('steam-client','Steam','Steam library','url','steam://open/library'))
        else: self.set_tab('Apps')
    def set_tab(self,tab): self.tab=tab; self.query=''; self.show_home()
    def refresh(self): self.games=discover_games(); self.apps=discover_apps(); self.show_home(); self.message('Library refreshed.')
    def search(self):
        if self.tab=='Settings': self.tab='Library'
        dialog=TextDialog('Search library',self.query,self)
        if dialog.exec(): self.query=dialog.edit.text().strip(); self.show_home()
    def details(self,item):
        dialog=QDialog(self); dialog.setWindowTitle(item.name); dialog.setFixedWidth(min(740,self.width()-64))
        layout=QVBoxLayout(dialog); layout.setContentsMargins(24,20,24,20); layout.setSpacing(12)
        layout.addWidget(DetailArtwork(item))
        title=label(item.name,'title'); title.setWordWrap(True); layout.addWidget(title)
        subtitle=label(item.subtitle,'muted'); subtitle.setWordWrap(True); layout.addWidget(subtitle)
        desc='Opens externally. Return to '+DISPLAY_NAME+' when you finish.'
        if item in STORES: desc='Browse the store externally. Purchases and installations are handled by the store.'
        if item in MEDIA: desc='Opens in your default browser. A subscription or sign-in may be required. Playback support depends on your browser.'
        body=label(desc,'muted'); body.setWordWrap(True); layout.addWidget(body)
        launch=button('Open store' if item in STORES else 'Launch',lambda:(dialog.accept(),self.launch(item)))
        pin=button('Unpin from Library' if item.id in self.profile['favorites'] else 'Pin to Library',lambda:(self.favorite(item),dialog.accept()))
        close=button('Back',dialog.reject)
        for b in (launch,pin,close): layout.addWidget(b)
        launch.setFocus(); dialog.exec()
    def launch(self,item):
        try:
            if self.desktop.available and self.desktop_session_ready:
                destination=WORKSPACES['Play'] if item.id.startswith('steam:') or item.id=='steam-client' else WORKSPACES['Media'] if item in MEDIA else WORKSPACES['Desktop']
                self.desktop.focus_workspace(destination)
            if item.kind=='app':
                args,cwd=desktop_command(item.target)
                process=subprocess.Popen(args,cwd=cwd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                self.children_processes.append(process)
            elif not QDesktopServices.openUrl(QUrl(item.target)):
                if self.desktop.available: self.desktop.return_console(os.getpid())
                self.message('No application can open this link. Install a compatible browser or Steam.'); return
            recent=self.profile['recent']; self.profile['recent']=[item.id]+[v for v in recent if v!=item.id][:11]; self.persist()
            self.message('Opened '+item.name+'. Hold View + Start to return to the console.' if self.desktop.available else 'Opened '+item.name+'. Use your desktop window switcher to return.')
        except (OSError,ValueError,KeyError,configparser.Error,DesktopError) as exc:
            if self.desktop.available:
                try: self.desktop.return_console(os.getpid())
                except DesktopError: pass
            self.message('Could not launch '+item.name+': '+str(exc))
    def favorite(self,item=None):
        if item is None: item=getattr(QApplication.focusWidget(),'item',None)
        if not item: return
        fav=self.profile['favorites']
        if item.id in fav: fav.remove(item.id)
        else: fav.append(item.id)
        self.persist(); self.show_home(); self.message('Updated your Library.')
    def toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()
        self.state.data['fullscreen']=self.isFullScreen(); self.persist(); self.show_home()
    def toggle_motion(self): self.state.data['motion']=not self.state.data['motion']; self.persist(); self.show_home()
    def toggle_scale(self):
        values=[100,115,130]; self.state.data['scale']=values[(values.index(self.state.data['scale'])+1)%3]; self.persist(); self.apply_scale(); self.show_home()
    def rename(self):
        dialog=TextDialog('Rename profile',self.profile['name'],self)
        if dialog.exec():
            name=dialog.edit.text().strip()
            if name and not any(i!=self.profile_index and p['name'].casefold()==name.casefold() for i,p in enumerate(self.state.data['profiles'])):
                self.profile['name']=name; self.persist(); self.show_home()
            else: self.message('Choose a nonempty, unique profile name.')
    def info(self,title,text):
        d=QDialog(self); d.setWindowTitle(title); d.setMinimumWidth(650); layout=QVBoxLayout(d); layout.setContentsMargins(28,24,28,24); layout.setSpacing(20)
        layout.addWidget(label(title,'title')); body=label(text,'muted'); body.setWordWrap(True); layout.addWidget(body); b=button('Got it',d.accept); layout.addWidget(b); b.setFocus(); d.exec()
    def help(self): self.info('Every control, within reach.','D-pad / left stick: move · A / Enter: choose · B / Esc: back\nX / F: pin · Y / /: search · LB / RB: sections\nStart / F1: Settings · View / F2: workspaces\nF11: full screen · Alt+F4: exit\n\nWhile in Hyprland, hold View (Back):\n+ Start: return to the console from any app\n+ D-pad: focus a tiled window\n+ LB / RB: switch OmaFlow workspaces\n+ X: tile the focused app · + Y: move it to Desktop\n\nIn Steam Input, select Gamepad (not keyboard emulation) to expose these controls. Trackpads or touch operate desktop apps. The shell does not intercept normal gameplay input. Steam may reserve the Guide button; View + Start is the fallback.')
    def about(self): self.info(DISPLAY_NAME+' · Build 1','Native handheld console + Omarchy desktop, built for Steam Deck at 1280 × 800.\n\nHyprland: '+self.desktop.version+'\nOmarchy: '+('Detected' if self.desktop.omarchy else 'Not detected')+'\n\nProfiles keep favorites and recent launch requests locally; they are not separate OS accounts. Games use Steam, apps use desktop launchers, and media / stores open in your browser.\n\nNo partitioning, bootloader changes or automatic OS installation. TV and docked optimization comes later. Not affiliated with Valve or Omarchy.')
    def attach_desktop(self):
        try:
            address=self.desktop.shell_address(os.getpid())
            if not address:
                self.attach_attempts+=1
                if self.attach_attempts<12: QTimer.singleShot(250,self.attach_desktop)
                else: self.message('Console window could not attach to Hyprland. Reopen the app to retry.')
                return
            self.desktop.move_window(address,WORKSPACES['Console'])
            self.desktop.focus_window(address)
            self.desktop_session_ready=True
        except DesktopError as exc: self.message(str(exc))
    def desktop_control(self,action):
        if not self.desktop.available: return
        try:
            if action=='console':
                self.desktop.return_console(os.getpid()); return
            if action in ('wm:previous','wm:next'):
                self.desktop.cycle_workspace(-1 if action=='wm:previous' else 1); return
            if action in ('wm:left','wm:right','wm:up','wm:down'):
                self.desktop.focus_direction(action.split(':')[1][0]); return
            active=self.desktop.query('activewindow')
            if active.get('pid')==os.getpid() or not active.get('address'): return
            if action=='wm:tile': self.desktop.tile(active['address'])
            if action=='wm:move': self.desktop.move_window(active['address'],WORKSPACES['Desktop']); self.desktop.focus_workspace(WORKSPACES['Desktop'])
        except DesktopError as exc:
            if self.isActiveWindow(): self.message(str(exc))
    def workspaces(self):
        if not self.desktop.available:
            self.info('Your desktop, connected.','Build 1 uses an existing Omarchy + Hyprland session for real tiled windows and workspaces.\n\n'+self.desktop.reason+'\n\nRun ./run.sh from that session. Stock SteamOS Gaming Mode can run the console UI, but cannot provide Hyprland integration. See docs/BUILD1.md for the target environment. No disk or boot changes are made.'); return
        try: spaces,clients=self.desktop.snapshot()
        except DesktopError as exc: self.message(str(exc)); return
        d=QDialog(self); d.setWindowTitle('Workspaces'); d.resize(940,650)
        layout=QVBoxLayout(d); layout.setContentsMargins(24,24,24,24); layout.setSpacing(14)
        layout.addWidget(label('Your handheld. More room.','title'))
        layout.addWidget(label('Real Hyprland workspaces · View + Start returns to the console','muted'))
        row=QHBoxLayout()
        for name,value in WORKSPACES.items():
            count=sum(1 for c in clients if c.get('workspace',{}).get('name')==value)
            b=button(f'{name}  ·  {count}',lambda checked=False,w=value:self.workspace_action(d,lambda:self.desktop.focus_workspace(w)))
            row.addWidget(b)
        layout.addLayout(row)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); body=QWidget(); rows=QVBoxLayout(body)
        external=[c for c in clients if c.get('pid')!=os.getpid()]
        for client in external:
            title=client.get('title') or client.get('class','Application'); ws=client.get('workspace',{}).get('name','?')
            b=button(title[:72]+'  ·  '+ws,lambda checked=False,c=client:self.window_actions(d,c)); rows.addWidget(b)
        if not external: rows.addWidget(label('Open an app from Apps to start a tiled workspace.','muted'))
        rows.addStretch(); scroll.setWidget(body); layout.addWidget(scroll,1)
        back=button('Back to console',d.reject); layout.addWidget(back)
        d.findChildren(QPushButton)[0].setFocus(); d.exec()
    def workspace_action(self,dialog,callback):
        # Close the modal first so a focus switch cannot leave an orphaned dialog.
        dialog.accept()
        def execute():
            try: callback()
            except DesktopError as exc: self.message(str(exc))
        QTimer.singleShot(0,execute)
    def window_actions(self,parent,client):
        d=QDialog(self); d.setWindowTitle('Window controls'); layout=QVBoxLayout(d); layout.setContentsMargins(24,24,24,24); layout.setSpacing(12)
        title=label((client.get('title') or client.get('class','Application'))[:70],'title'); title.setWordWrap(True); layout.addWidget(title)
        address=client['address']
        def run(callback):
            d.accept(); self.workspace_action(parent,callback)
        actions=[('Focus window',lambda:self.desktop.focus_window(address)),('Tile window',lambda:(self.desktop.tile(address),self.desktop.focus_window(address))),('Toggle floating',lambda:(self.desktop.toggle_float(address),self.desktop.focus_window(address)))]
        for name,value in WORKSPACES.items():
            if name!='Console': actions.append(('Move to '+name,lambda v=value:(self.desktop.move_window(address,v),self.desktop.focus_workspace(v))))
        for name,callback in actions: layout.addWidget(button(name,lambda checked=False,f=callback:run(f)))
        layout.addWidget(button('Back',d.reject)); d.findChildren(QPushButton)[0].setFocus(); d.exec()
    def system_action(self,action):
        try: command=omarchy_command(action)
        except DesktopError as exc: self.message(str(exc)); return
        process=QProcess(self); self.system_processes.append(process)
        def finished(code,status):
            if code: self.message('Omarchy could not finish that action: '+bytes(process.readAllStandardError()).decode(errors='replace')[:180])
            if process in self.system_processes: self.system_processes.remove(process)
            process.deleteLater()
        def error(error):
            self.message('Could not start Omarchy: '+process.errorString())
        process.finished.connect(finished); process.errorOccurred.connect(error)
        process.start(command[0],command[1:])
    def quick_controls(self):
        self.action_dialog('Sound & brightness',[('Volume +',lambda:self.system_action('volume-up')),('Volume −',lambda:self.system_action('volume-down')),('Mute / unmute',lambda:self.system_action('mute')),('Brightness +',lambda:self.system_action('brightness-up')),('Brightness −',lambda:self.system_action('brightness-down'))])
    def omarchy_tools(self):
        def launch(action):
            if self.desktop.available: self.desktop.focus_workspace(WORKSPACES['Desktop'])
            self.system_action(action)
        self.action_dialog('Omarchy tools',[('Files',lambda:launch('files')),('Terminal',lambda:launch('terminal')),('System menu',lambda:launch('menu'))],close_on_action=True)
    def action_dialog(self,title,actions,close_on_action=False):
        if not self.desktop.omarchy: self.info(title,'These controls use Omarchy. Start in your Omarchy session to enable them.'); return
        d=QDialog(self); d.setWindowTitle(title); d.setMinimumWidth(580); layout=QVBoxLayout(d); layout.setContentsMargins(24,24,24,24); layout.setSpacing(12); layout.addWidget(label(title,'title'))
        def execute(callback):
            if close_on_action: d.accept()
            try: callback()
            except DesktopError as exc: self.message(str(exc))
        for name,callback in actions: layout.addWidget(button(name,lambda checked=False,f=callback:execute(f)))
        layout.addWidget(button('Back',d.reject)); d.findChildren(QPushButton)[0].setFocus(); d.exec()
    def message(self,text):
        if self.page=='home': self.notice.setText(text); self.notice.setWordWrap(True); self.toast_timer.start(6500)
        else: self.info(DISPLAY_NAME,text)
    def clear_status(self):
        if self.page=='home': self.notice.setText('D-PAD  Navigate     A  Select     B  Profiles     X  Pin     Y  Search     LB / RB  Sections')
    def navigate(self,action):
        dialog=QApplication.activeModalWidget()
        if dialog:
            if isinstance(dialog,TextDialog): dialog.navigate(action)
            elif action=='back': dialog.reject()
            elif action=='accept':
                focus=dialog.focusWidget()
                if isinstance(focus,QPushButton): focus.click()
            elif action in ('left','up','right','down'):
                dialog.focusNextPrevChild(action in ('right','down'))
                focus=dialog.focusWidget()
                for scroll in dialog.findChildren(QScrollArea):
                    if scroll.widget().isAncestorOf(focus): scroll.ensureWidgetVisible(focus,12,12)
            return
        if self.page=='splash':
            if action in ('accept','back'): self.finish_splash()
            return
        if action=='back':
            if self.page=='home':
                if self.query: self.query=''; self.show_home()
                else: self.show_profiles()
            return
        if action=='accept':
            focus=QApplication.focusWidget()
            if isinstance(focus,QPushButton): focus.click()
            return
        if action=='workspaces': self.workspaces(); return
        if action=='profiles': self.show_profiles(); return
        if self.page=='home':
            if action in ('next','previous'): self.set_tab(TABS[(TABS.index(self.tab)+(1 if action=='next' else -1))%len(TABS)]); return
            if action=='menu': self.set_tab('Settings'); return
            if action=='favorite': self.favorite(); return
            if action=='search': self.search(); return
        if action not in ('left','right','up','down'): return
        focus=QApplication.focusWidget(); pos=next(((r,row.index(focus)) for r,row in enumerate(self.rows) if focus in row),(0,0)); r,c=pos
        if self.page=='home' and focus in self.nav:
            index=self.nav.index(focus)
            if action=='right': target=self.cards[0] if self.cards else self.rows[2][0]
            elif action=='up': target=self.nav[index-1] if index else self.rows[0][0]
            elif action=='down': target=self.nav[min(index+1,len(self.nav)-1)]
            else: return
            target.setFocus()
            if target in self.cards: self.scroll.ensureWidgetVisible(target,16,16)
            return
        if self.page=='home' and action=='left' and (focus in self.cards and c==0 or focus in self.rows[2]):
            self.nav[TABS.index(self.tab)].setFocus(); return
        if action in ('left','right'): c=max(0,min(len(self.rows[r])-1,c+(1 if action=='right' else -1)))
        else: r=max(0,min(len(self.rows)-1,r+(1 if action=='down' else -1))); c=min(c,len(self.rows[r])-1)
        target=self.rows[r][c]
        if target.isEnabled():
            target.setFocus()
            if self.page=='home' and target in self.cards: self.scroll.ensureWidgetVisible(target,16,16)
            elif self.page=='profiles' and self.profile_scroll.widget().isAncestorOf(target): self.profile_scroll.ensureWidgetVisible(target,16,16)
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.KeyPress:
            if event.modifiers() & (Qt.KeyboardModifier.AltModifier|Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.MetaModifier): return False
            key=event.key(); dialog=QApplication.activeModalWidget()
            if isinstance(dialog,TextDialog) and key not in (Qt.Key.Key_Escape,Qt.Key.Key_Up,Qt.Key.Key_Down,Qt.Key.Key_Left,Qt.Key.Key_Right,Qt.Key.Key_Return,Qt.Key.Key_Enter):
                if key==Qt.Key.Key_Backspace: dialog.edit.backspace(); return True
                if event.text().isprintable() and event.text(): dialog.insert(event.text()); return True
                return False
            mapping={Qt.Key.Key_Left:'left',Qt.Key.Key_Right:'right',Qt.Key.Key_Up:'up',Qt.Key.Key_Down:'down',Qt.Key.Key_Return:'accept',Qt.Key.Key_Enter:'accept',Qt.Key.Key_Escape:'back',Qt.Key.Key_PageDown:'next',Qt.Key.Key_PageUp:'previous',Qt.Key.Key_F:'favorite',Qt.Key.Key_Slash:'search',Qt.Key.Key_F1:'menu',Qt.Key.Key_F2:'workspaces'}
            if key==Qt.Key.Key_F11 and self.page=='home' and not dialog: self.toggle_fullscreen(); return True
            if key in mapping:
                if not event.isAutoRepeat() or mapping[key] in ('left','right','up','down'): self.navigate(mapping[key])
                return True
        return super().eventFilter(obj,event)
    def poll(self):
        before=bool(self.controller.handles)
        for action in self.controller.poll():
            if action=='console' or action.startswith('wm:'):
                self.desktop_control(action); continue
            if self.isActiveWindow() or (QApplication.activeModalWidget() and QApplication.activeModalWidget().isActiveWindow()): self.navigate(action)
        if before!=bool(self.controller.handles): self.update_status()
        self.children_processes=[p for p in self.children_processes if p.poll() is None]
    def closeEvent(self,event):
        self.controller.close(); self.poll_timer.stop(); QApplication.instance().removeEventFilter(self); event.accept()

def main():
    parser=argparse.ArgumentParser(description=DISPLAY_NAME+' native handheld shell')
    parser.add_argument('--windowed',action='store_true'); parser.add_argument('--skip-splash',action='store_true'); parser.add_argument('--config',type=Path,help='Alternative state file for testing')
    args=parser.parse_args()
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app=QApplication(sys.argv[:1]); app.setApplicationName('OmaSteamDeck')
    state=State(args.config)
    try: state.path.parent.mkdir(parents=True,exist_ok=True)
    except OSError as exc:
        print('Cannot create '+DISPLAY_NAME+' config folder: '+str(exc),file=sys.stderr); return 1
    lock=QLockFile(str(state.path.with_suffix('.lock'))); lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        info=lock.getLockInfo()
        desktop=Desktop()
        if info and info[0]>0 and desktop.available:
            try: desktop.return_console(info[0]); return 0
            except DesktopError: pass
        print(DISPLAY_NAME+' is already running, or its config folder is not writable.',file=sys.stderr); return 1
    shell=Shell(state,args.windowed,args.skip_splash)
    result=app.exec(); lock.unlock(); return result

if __name__=='__main__': sys.exit(main())
