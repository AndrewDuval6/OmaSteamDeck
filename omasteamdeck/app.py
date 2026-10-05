"""OmaSteamDeck native handheld shell. No web server or elevated privileges."""
from __future__ import annotations
import argparse
import configparser
import math
import os
from pathlib import Path
import subprocess
import sys
from PySide6.QtCore import Qt, QTimer, QPointF, QEvent, QUrl, QProcess, QLockFile
from PySide6.QtGui import QColor, QPainter, QPolygonF, QLinearGradient, QFont, QDesktopServices, QKeyEvent, QPen
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QScrollArea, QFrame, QDialog, QLineEdit)
from .core import State, Item, MEDIA, STORES, discover_apps, discover_games, desktop_command
from .controller import Controller
from .desktop import Desktop, DesktopError, WORKSPACES, omarchy_command

TABS = ['Games', 'Media', 'Store', 'Library', 'Apps', 'Settings']
ACCENTS = ['#a8e6bb','#9dcfff','#dfb7ff','#ffd49a','#ffadbb','#88e1dc','#e2deac','#bcc4ff']
STYLE = '''
QWidget { background: #0c1115; color: #edf3ef; font-family: "DejaVu Sans"; font-size: 15px; }
QLabel { background: transparent; }
QLabel#eyebrow { color: #91b49d; font-size: 12px; font-weight: 700; letter-spacing: 2px; }
QLabel#title { font-size: 34px; font-weight: 700; }
QLabel#muted { color: #9eafa6; font-size: 14px; }
QLabel#brand { font-size: 19px; font-weight: 700; letter-spacing: 1px; }
QLabel#heroTitle { font-size: 31px; font-weight: 700; }
QFrame#hero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #253d33,stop:.6 #172b25,stop:1 #17212c); border: 1px solid #3a5145; border-radius: 22px; }
QFrame#hero QLabel { background: transparent; }
QPushButton { background: #17211d; color: #dce6df; border: 2px solid transparent; border-radius: 12px; padding: 11px 16px; text-align: left; }
QPushButton:hover { background: #24382e; }
QPushButton:focus { border: 2px solid #baf5ca; background: #293f32; color: white; }
QPushButton:disabled { color: #617168; }
QPushButton[active="true"] { background: #b5e9c5; color: #102219; font-weight: 700; }
QPushButton#nav { padding: 10px 14px; font-size: 15px; }
QPushButton#card { text-align: left; border-radius: 18px; padding: 18px; font-size: 18px; background: #19251f; }
QPushButton#card:focus { background: #2b4535; border: 2px solid #c3fbd1; }
QPushButton#card:hover { background: #263b30; }
QPushButton#key { padding: 8px; font-size: 16px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #101a15; width: 6px; border-radius: 3px; }
QScrollBar::handle:vertical { background: #53765e; min-height: 30px; border-radius: 3px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height: 0; }
QDialog { background: #111c16; border: 1px solid #456b50; }
QLineEdit { background: #0b130e; border: 2px solid #3f5c47; border-radius: 10px; padding: 12px; font-size: 21px; }
QLineEdit:focus { border-color: #c3fbd1; }
'''

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

class Logo(QWidget):
    """Perspective-projected, depth-sorted 3D monogram with a gentle idle turn."""
    def __init__(self, motion=True, parent=None):
        super().__init__(parent)
        self.angle=.4
        self.setMinimumSize(180,145)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick)
        if motion: self.timer.start(33)
    def tick(self):
        self.angle+=.012; self.update()
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        angle=.4+math.sin(self.angle)*.28
        points=[]
        for x,y,z in [(-1,-1,-.42),(1,-1,-.42),(1,1,-.42),(-1,1,-.42),(-1,-1,.42),(1,-1,.42),(1,1,.42),(-1,1,.42)]:
            rx=x*math.cos(angle)+z*math.sin(angle); rz=-x*math.sin(angle)+z*math.cos(angle)
            ry=y*math.cos(-.20)-rz*math.sin(-.20); rz=y*math.sin(-.20)+rz*math.cos(-.20)
            scale=min(self.width()/3.2,self.height()/3.2)*4/(4+rz)
            points.append((QPointF(self.width()/2+rx*scale,self.height()/2+ry*scale),rz))
        faces=[([0,1,2,3],'#274735'),([4,5,6,7],'#1b3526'),([0,4,7,3],'#4d815b'),([1,5,6,2],'#568e67'),([0,1,5,4],'#b5edc3'),([3,2,6,7],'#3f6a4b')]
        for ids,color in sorted(faces,key=lambda f:sum(points[i][1] for i in f[0]),reverse=True):
            painter.setPen(QColor('#c1f4cc')); painter.setBrush(QColor(color)); painter.drawPolygon(QPolygonF([points[i][0] for i in ids]))
        painter.setPen(QColor('#e2ffe9')); painter.setFont(QFont('DejaVu Sans',max(14,int(min(self.width(),self.height())*.15)),QFont.Weight.Bold))
        painter.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'OSD')

class Card(QPushButton):
    def __init__(self,title,subtitle,icon,index,callback,scale=1):
        super().__init__()
        self.title=title; self.subtitle=subtitle; self.icon=icon; self.accent=QColor(ACCENTS[index%len(ACCENTS)]); self.scale=scale
        self.setAccessibleName(title+' — '+subtitle); self.setToolTip(title+'\n'+subtitle)
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.clicked.connect(callback)
        self.setMinimumHeight(int(180*scale)); self.setMinimumWidth(0)
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=self.rect().adjusted(2,2,-2,-2); gradient=QLinearGradient(0,0,self.width(),self.height())
        gradient.setColorAt(0,self.accent.darker(380 if not self.hasFocus() else 240)); gradient.setColorAt(1,QColor('#142019'))
        p.setBrush(gradient); p.setPen(QPen(QColor('#c3fbd1') if self.hasFocus() else QColor('#314338'),2 if self.hasFocus() else 1)); p.drawRoundedRect(rect,18,18)
        p.save(); p.setClipRect(rect.adjusted(3,3,-3,-3))
        glow=QColor(self.accent); glow.setAlpha(24); p.setPen(QPen(glow,1)); p.setBrush(Qt.BrushStyle.NoBrush)
        for radius in (42,68,94): p.drawEllipse(QPointF(self.width()-20,25),radius,radius)
        p.restore(); p.setPen(self.accent); p.setFont(QFont('DejaVu Sans',26)); p.drawText(20,53,self.icon)
        p.setPen(QColor('#f0f8f2')); font=QFont('DejaVu Sans'); font.setPixelSize(int(19*self.scale)); font.setBold(True); p.setFont(font)
        p.drawText(20,self.height()-51,p.fontMetrics().elidedText(self.title,Qt.TextElideMode.ElideRight,self.width()-40))
        font.setPixelSize(int(13*self.scale)); font.setBold(False); p.setFont(font); p.setPen(QColor('#acbfb1'))
        p.drawText(20,self.height()-25,p.fontMetrics().elidedText(self.subtitle,Qt.TextElideMode.ElideRight,self.width()-40))

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

class Shell(QWidget):
    def __init__(self,state=None,windowed=False,skip_splash=False,desktop=None):
        super().__init__()
        self.state=state or State(); self.profile_index=0; self.tab='Games'; self.query=''; self.page='splash'; self.rows=[]; self.cards=[]; self.current_items=[]; self.children_processes=[]
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.setWindowTitle('OmaSteamDeck'); self.resize(1280,800); self.setMinimumSize(800,600)
        self.root=QVBoxLayout(self); self.root.setContentsMargins(32,24,32,18); self.root.setSpacing(18)
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
            self.show_splash(); QTimer.singleShot(1800,self.finish_splash)
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
        self.clear(); self.page='splash'; self.root.addStretch()
        logo=Logo(self.state.data['motion']); logo.setFixedSize(320,240); self.root.addWidget(logo,0,Qt.AlignmentFlag.AlignHCenter)
        title=label('OmaSteamDeck','title'); title.setAlignment(Qt.AlignmentFlag.AlignCenter); self.root.addWidget(title)
        sub=label('A LITTLE MACHINE.  A WHOLE WORLD.','eyebrow'); sub.setAlignment(Qt.AlignmentFlag.AlignCenter); self.root.addWidget(sub)
        self.root.addStretch()
    def finish_splash(self):
        if self.page=='splash': self.show_profiles()
    def show_profiles(self):
        self.clear(); self.page='profiles'; self.query=''
        self.root.addWidget(label('OSD  /  OMASTEAMDECK','eyebrow')); self.root.addStretch()
        self.root.addWidget(label('Make yourself at home.','title')); self.root.addWidget(label('Choose your space. Your favorites and recent launches stay with you.','muted'))
        grid=QGridLayout(); all_buttons=[]
        for i,p in enumerate(self.state.data['profiles']):
            b=button(f"{p['name'][0].upper()}\n\n{p['name']}\nPersonal library",lambda checked=False,index=i:self.choose_profile(index),'card'); b.setMinimumHeight(150); grid.addWidget(b,i//4,i%4); all_buttons.append(b)
        add=button('+\n\nNew profile',self.add_profile,'card'); add.setMinimumHeight(150); add.setEnabled(len(all_buttons)<8); grid.addWidget(add,len(all_buttons)//4,len(all_buttons)%4); all_buttons.append(add)
        self.root.addLayout(grid); self.root.addStretch()
        quit_button=button('Exit to desktop',self.close); self.root.addWidget(quit_button,0,Qt.AlignmentFlag.AlignLeft)
        self.root.addWidget(label('D-PAD  Move     A  Choose     Enter  Choose     Esc  Back','muted'))
        self.rows=[all_buttons[i:i+4] for i in range(0,len(all_buttons),4)]+[[quit_button]]
        all_buttons[min(self.profile_index,len(all_buttons)-1)].setFocus()
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
        self.clear(); self.page='home'
        top=QHBoxLayout(); top.addWidget(label('◈  OmaSteamDeck','brand')); top.addStretch()
        self.status=label(self.status_text(),'muted'); top.addWidget(self.status)
        desktop_btn=button('▦  Workspaces',self.workspaces); top.addWidget(desktop_btn)
        profile_btn=button(self.profile['name']+'  ▾',self.show_profiles); top.addWidget(profile_btn); self.root.addLayout(top)
        nav=QHBoxLayout(); self.nav=[]
        for name in TABS:
            b=button(name,lambda checked=False,t=name:self.set_tab(t),'nav'); b.setProperty('active',name==self.tab); nav.addWidget(b); self.nav.append(b)
        nav.addStretch(); search=button('⌕  Search',self.search); nav.addWidget(search); self.root.addLayout(nav)
        self.rows=[[desktop_btn,profile_btn],self.nav+[search]]
        hero=QFrame(); hero.setObjectName('hero'); hl=QHBoxLayout(hero); hl.setContentsMargins(26,16,26,16)
        copy=QVBoxLayout(); copy.setSpacing(6)
        headings={'Games':('PICK UP & PLAY','Your next adventure starts here.',f'{len(self.games)} installed games · A space built for play.'),'Media':('PRESS PLAY','Take a break. Tune in.','Music, films and your favorite creators.'),'Store':('FIND SOMETHING GOOD','A world beyond your library.','Browse trusted stores in your default browser.'),'Library':('YOUR COLLECTION','All your favorites. One place.','Pinned games, apps and media, saved to this profile.'),'Apps':('BEYOND THE GAME','Small screen. Big possibilities.','Your installed desktop applications, ready to launch.'),'Settings':('MAKE IT YOURS','Comfort comes first.','Display, motion, profiles and controller help.')}
        eyebrow,title,subtitle=headings[self.tab]
        copy.addWidget(label(eyebrow,'eyebrow')); title_label=label(title,'heroTitle'); title_label.setWordWrap(True); copy.addWidget(title_label); copy.addWidget(label(subtitle,'muted')); hl.addLayout(copy,1)
        logo=Logo(self.state.data['motion']); logo.setFixedSize(190,145); hl.addWidget(logo); self.root.addWidget(hero)
        row=QHBoxLayout(); self.section=label('','eyebrow'); row.addWidget(self.section); row.addStretch()
        refresh=button('↻  Refresh',self.refresh); row.addWidget(refresh); self.root.addLayout(row); self.rows.append([refresh])
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content=QWidget(); self.grid=QGridLayout(content); self.grid.setContentsMargins(2,2,8,8); self.grid.setSpacing(12); self.grid.setAlignment(Qt.AlignmentFlag.AlignTop); self.scroll.setWidget(content); self.root.addWidget(self.scroll,1)
        self.populate()
        self.notice=label('A  Open    B  Back    X  Pin    Y  Search    LB / RB  Sections    ☰  Settings','muted'); self.root.addWidget(self.notice)
        target=next((c for c in self.cards if (focus_id and getattr(getattr(c,'item',None),'id',None)==focus_id) or (focus_title and getattr(c,'title',None)==focus_title)), self.cards[0] if self.cards else self.nav[TABS.index(self.tab)])
        target.setFocus()
        # Rebuilt cards need their final geometry before restoring scroll position.
        # Tie the callback to the target so a subsequent page change cancels it.
        scroll=self.scroll
        QTimer.singleShot(0,target,lambda:scroll.ensureWidgetVisible(target,16,16))
    def catalog(self): return self.games+self.apps+MEDIA+STORES
    def populate(self):
        if self.tab=='Settings':
            entries=[('Desktop & workspaces','Omarchy + Hyprland' if self.desktop.available else 'Session setup needed',self.workspaces),('Sound & brightness','Handheld quick controls',self.quick_controls),('Omarchy tools','Files, terminal & system menu',self.omarchy_tools),('Display', 'Full screen' if self.isFullScreen() else 'Windowed',self.toggle_fullscreen),('Motion','Animated logo' if self.state.data['motion'] else 'Reduced motion',self.toggle_motion),('Text size',str(self.state.data['scale'])+'%',self.toggle_scale),('Profiles','Switch or create a profile',self.show_profiles),('Rename profile',self.profile['name'],self.rename),('Controller help','Controls & Steam Deck setup',self.help),('About','OmaSteamDeck · Build 1',self.about),('Exit to desktop','Close OmaSteamDeck',self.close)]
            self.section.setText('PREFERENCES')
            for title,subtitle,callback in entries: self.add_card(title,subtitle,'⚙',callback)
        else:
            items={'Games':self.games,'Media':MEDIA,'Store':STORES,'Apps':self.apps}.get(self.tab)
            if self.tab=='Library':
                ids=self.profile['favorites']+self.profile['recent']; catalog={i.id:i for i in self.catalog()}; items=[catalog[id] for id in dict.fromkeys(ids) if id in catalog]
            if self.query: items=[i for i in items if self.query.casefold() in (i.name+' '+i.subtitle).casefold()]
            self.current_items=items
            self.section.setText((f'RESULTS FOR “{self.query}”  ·  ' if self.query else '')+f'{len(items)} '+('DESTINATIONS' if self.tab in ('Store','Media') else 'IN YOUR COLLECTION'))
            for item in items:
                star='★ ' if item.id in self.profile['favorites'] else ''
                self.add_card(star+item.name,item.subtitle,item.icon,lambda checked=False,i=item:self.details(i),item)
            if not items:
                messages={'Games':('Your games belong here.','Install a game through Steam, then select Refresh. External Steam libraries are detected too.'),'Library':('Start your collection.','Open a game, app or media service and choose Pin. Your recent launches also appear here.')}
                title,subtitle=messages.get(self.tab,('Nothing here yet.','Try another search or refresh your installed applications.'))
                if self.query: title,subtitle='No matches.','Try a shorter name or clear your search.'
                msg=label(title,'title'); msg.setWordWrap(True); self.grid.addWidget(msg,0,0,1,4)
                sub=label(subtitle,'muted'); sub.setWordWrap(True); self.grid.addWidget(sub,1,0,1,4)
                action=button('Clear search' if self.query else 'Open Steam' if self.tab=='Games' else 'Browse Apps',self.empty_action); self.grid.addWidget(action,2,0,1,2); self.cards.append(action)
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
        dialog=QDialog(self); dialog.setWindowTitle(item.name); dialog.setMinimumWidth(580)
        layout=QVBoxLayout(dialog); layout.setContentsMargins(28,24,28,24); layout.setSpacing(18)
        title=label(item.name,'title'); title.setWordWrap(True); layout.addWidget(title)
        subtitle=label(item.subtitle,'muted'); subtitle.setWordWrap(True); layout.addWidget(subtitle)
        desc='Opens externally. Return to OmaSteamDeck when you finish.'
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
    def help(self): self.info('Every control, within reach.','D-pad / left stick: move · A / Enter: choose · B / Esc: back\nX / F: pin · Y / /: search · LB / RB: sections\nStart / F1: Settings · View / F2: workspaces\nF11: full screen · Alt+F4: exit\n\nWhile in Hyprland, hold View (Back):\n+ Start: return to the console from any app\n+ D-pad: focus a tiled window\n+ LB / RB: switch OSD workspaces\n+ X: tile the focused app · + Y: move it to Desktop\n\nIn Steam Input, select Gamepad (not keyboard emulation) to expose these controls. Trackpads or touch operate desktop apps. The shell does not intercept normal gameplay input. Steam may reserve the Guide button; View + Start is the fallback.')
    def about(self): self.info('OmaSteamDeck · Build 1','Native handheld console + Omarchy desktop, built for Steam Deck at 1280 × 800.\n\nHyprland: '+self.desktop.version+'\nOmarchy: '+('Detected' if self.desktop.omarchy else 'Not detected')+'\n\nProfiles keep favorites and recent launch requests locally; they are not separate OS accounts. Games use Steam, apps use desktop launchers, and media / stores open in your browser.\n\nNo partitioning, bootloader changes or automatic OS installation. TV and docked optimization comes later. Not affiliated with Valve or Omarchy.')
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
        else: self.info('OmaSteamDeck',text)
    def clear_status(self):
        if self.page=='home': self.notice.setText('A  Open    B  Back    X  Pin    Y  Search    LB / RB  Sections    ☰  Settings')
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
            if action in ('next','previous'): self.set_tab(TABS[(TABS.index(self.tab)+(1 if action=='next' else -1))%6]); return
            if action=='menu': self.set_tab('Settings'); return
            if action=='favorite': self.favorite(); return
            if action=='search': self.search(); return
        if action not in ('left','right','up','down'): return
        focus=QApplication.focusWidget(); pos=next(((r,row.index(focus)) for r,row in enumerate(self.rows) if focus in row),(0,0)); r,c=pos
        if action in ('left','right'): c=max(0,min(len(self.rows[r])-1,c+(1 if action=='right' else -1)))
        else: r=max(0,min(len(self.rows)-1,r+(1 if action=='down' else -1))); c=min(c,len(self.rows[r])-1)
        target=self.rows[r][c]
        if target.isEnabled():
            target.setFocus()
            if self.page=='home' and target in self.cards: self.scroll.ensureWidgetVisible(target,16,16)
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
    parser=argparse.ArgumentParser(description='OmaSteamDeck native handheld shell')
    parser.add_argument('--windowed',action='store_true'); parser.add_argument('--skip-splash',action='store_true'); parser.add_argument('--config',type=Path,help='Alternative state file for testing')
    args=parser.parse_args()
    app=QApplication(sys.argv[:1]); app.setApplicationName('OmaSteamDeck')
    state=State(args.config)
    try: state.path.parent.mkdir(parents=True,exist_ok=True)
    except OSError as exc:
        print('Cannot create OmaSteamDeck config folder: '+str(exc),file=sys.stderr); return 1
    lock=QLockFile(str(state.path.with_suffix('.lock'))); lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        info=lock.getLockInfo()
        desktop=Desktop()
        if info and info[0]>0 and desktop.available:
            try: desktop.return_console(info[0]); return 0
            except DesktopError: pass
        print('OmaSteamDeck is already running, or its config folder is not writable.',file=sys.stderr); return 1
    shell=Shell(state,args.windowed,args.skip_splash)
    result=app.exec(); lock.unlock(); return result

if __name__=='__main__': sys.exit(main())
