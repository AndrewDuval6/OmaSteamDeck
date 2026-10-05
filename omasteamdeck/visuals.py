"""Offline, resolution-independent artwork and handheld visual components.

Presentation only: no launch, device, controller, network or workspace operations.
"""
from __future__ import annotations

import configparser
import hashlib
import math
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, QElapsedTimer
from PySide6.QtGui import (QColor, QFont, QIcon, QImageReader, QLinearGradient,
    QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap, QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QWidget, QPushButton, QSizePolicy

# Product name confirmed by the user; emblem design remains under review.
DISPLAY_NAME = 'OmaFlow'
INK = '#070b10'
MINT = '#9bd4ff'  # Shared focus color; name retained for existing drawing helpers.
PALETTES = [('#183d48','#5d9d9b','#e6c8a0'), ('#292d59','#888bc1','#edbdaa'),
            ('#413253','#c08094','#f1d2ab'), ('#163f3e','#66ac90','#d7e5bd')]
STYLE = '''
QWidget { background: transparent; color: #edf1f7; font-family: "DejaVu Sans"; font-size: 15px; }
QLabel { background: transparent; }
QLabel#eyebrow { color: #9eafc3; font-size: 12px; font-weight: 700; letter-spacing: 2px; }
QLabel#title { font-size: 32px; font-weight: 500; }
QLabel#greeting { font-size: 27px; font-weight: 500; }
QLabel#muted { color: #acb7ca; font-size: 14px; }
QLabel#brand { color: #d7e0ee; font-size: 14px; letter-spacing: 1px; }
QLabel#heroTitle { font-size: 30px; font-weight: 500; }
QLabel#heroCopy { color: #bac7d8; font-size: 15px; }
QLabel#notice { color: #bcc9db; font-size: 13px; padding-top: 6px; }
QPushButton { background: rgba(19,30,43,205); color: #e0e8f4; border: 1px solid #29394c; border-radius: 10px; padding: 10px 14px; text-align: left; }
QPushButton:hover { background: rgba(39,60,82,220); }
QPushButton:focus { border: 2px solid #9bd4ff; background: #20364b; color: white; }
QPushButton:disabled { color: #75808e; }
QPushButton[active="true"] { background: #1b3044; color: #eef6ff; }
QPushButton#nav { padding: 10px 12px; font-size: 14px; }
QPushButton#key { padding: 8px; font-size: 16px; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: #101722; width: 5px; border-radius: 2px; }
QScrollBar::handle:vertical { background: #627f9c; min-height: 32px; border-radius: 2px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height: 0; }
QDialog { background: #0e1723; border: 1px solid #41566e; }
QLineEdit { background: #09111d; border: 2px solid #40596c; border-radius: 10px; padding: 12px; font-size: 21px; }
QLineEdit:focus { border-color: #9bd4ff; }
'''


def color(value, alpha=None):
    c = QColor(value)
    if alpha is not None:
        c.setAlpha(alpha)
    return c


def font(pixels, bold=False):
    f = QFont('DejaVu Sans')
    f.setPixelSize(round(pixels))
    f.setBold(bold)
    return f


def polygon(points):
    return QPolygonF([QPointF(x, y) for x, y in points])


def scene(p, rect, variant=0):
    """Original landscape illustration, drawn at any size without downloads."""
    p.save()
    p.setClipRect(rect, Qt.ClipOperation.IntersectClip)
    p.translate(rect.x(), rect.y())
    p.scale(rect.width()/1000, rect.height()/420)
    sky, ridge, sun = PALETTES[variant % len(PALETTES)]
    gradient = QLinearGradient(0, 0, 900, 420)
    gradient.setColorAt(0, color(sky))
    gradient.setColorAt(.65, color(ridge).darker(150))
    gradient.setColorAt(1, color(sky))
    p.fillRect(QRectF(0, 0, 1000, 420), gradient)
    glow = QRadialGradient(740, 125, 210)
    glow.setColorAt(0, color(sun, 100)); glow.setColorAt(1, color(sun, 0))
    p.fillRect(QRectF(0, 0, 1000, 420), glow)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(color(sun))
    p.drawEllipse(QPointF(752, 106), 44*(rect.height()/420)/(rect.width()/1000), 44)
    p.setBrush(color(ridge).darker(140))
    p.drawPolygon(polygon([(0,300),(165,193),(275,276),(449,120),(575,236),(662,144),(852,295),(1000,214),(1000,420),(0,420)]))
    p.setBrush(color(ridge))
    p.drawPolygon(polygon([(449,120),(500,238),(472,216),(439,244),(396,232)]))
    p.setBrush(color(ridge).lighter(130))
    p.drawPolygon(polygon([(449,120),(472,216),(442,197),(429,213),(415,199)]))
    p.setBrush(color(sky).darker(150))
    p.drawPolygon(polygon([(0,318),(150,275),(298,345),(506,253),(650,313),(807,224),(1000,309),(1000,420),(0,420)]))
    p.setBrush(color(sky).darker(230))
    p.drawPolygon(polygon([(0,364),(275,365),(443,326),(623,380),(809,298),(1000,339),(1000,420),(0,420)]))
    # Quiet illuminated path through the foreground.
    path = QPainterPath(QPointF(582,420)); path.cubicTo(681,365,734,384,809,298)
    p.setPen(QPen(color(sun,140),3)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(path)
    p.setPen(QPen(color('#f1f7f9',90),1.2))
    for x,y in [(90,80),(180,127),(352,56),(527,75),(922,55),(896,153)]:
        p.drawPoint(QPointF(x,y))
    p.restore()


def symbol(p, rect, name, tint=MINT):
    """Small consistent line icons; no dependency on platform symbol fonts."""
    p.save(); p.translate(rect.x(),rect.y()); p.scale(rect.width()/48,rect.height()/48)
    p.setPen(QPen(color(tint),2.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    key=name.lower()
    if key=='home':
        p.drawPolyline(polygon([(6,23),(24,7),(42,23)])); p.drawPolyline(polygon([(11,20),(11,41),(21,41),(21,29),(28,29),(28,41),(37,41),(37,20)]))
    elif key in ('games','steam','steam library','steam-client','steam-store','controller help') or key.startswith('steam:'):
        path=QPainterPath(QPointF(12,14)); path.cubicTo(3,14,1,35,7,36); path.cubicTo(12,38,14,29,19,29); path.lineTo(29,29); path.cubicTo(34,29,36,38,41,36); path.cubicTo(47,34,44,14,36,14); path.closeSubpath(); p.drawPath(path)
        p.drawLine(12,20,12,28); p.drawLine(8,24,16,24); p.drawEllipse(QPointF(33,21),1.6,1.6); p.drawEllipse(QPointF(37,26),1.6,1.6)
    elif key in ('media','youtube','prime','prime video'):
        p.drawRoundedRect(QRectF(4,10,40,28),7,7); p.setBrush(color(tint)); p.setPen(Qt.PenStyle.NoPen); p.drawPolygon(polygon([(20,17),(20,31),(32,24)]))
    elif key in ('spotify','sound & brightness'):
        for i in range(3):
            path=QPainterPath(QPointF(7+i*2,17+i*8)); path.cubicTo(17,10+i*8,30,11+i*8,41-i*2,18+i*8); p.drawPath(path)
    elif key in ('store','flathub'):
        for x,y in [(7,7),(27,7),(7,27),(27,27)]: p.drawRoundedRect(QRectF(x,y,14,14),3,3)
    elif key in ('library','favorites'):
        for x,h in [(8,30),(20,35),(32,26)]: p.drawRoundedRect(QRectF(x,42-h,8,h),2,2)
    elif key in ('profiles','rename profile'):
        p.drawEllipse(QPointF(24,15),8,8); path=QPainterPath(QPointF(9,40)); path.cubicTo(9,21,39,21,39,40); p.drawPath(path)
    elif key in ('display','desktop & workspaces','apps','omarchy tools'):
        p.drawRoundedRect(QRectF(5,7,38,28),4,4); p.drawLine(24,35,24,42); p.drawLine(15,42,33,42)
    elif key=='motion':
        p.drawEllipse(QRectF(7,7,34,34)); p.drawArc(QRectF(15,15,18,18),30*16,270*16)
    elif key in ('settings','text size','about'):
        p.drawEllipse(QRectF(10,10,28,28)); p.drawEllipse(QRectF(19,19,10,10))
        for a in range(0,360,45):
            r=math.radians(a); p.drawLine(QPointF(24+14*math.cos(r),24+14*math.sin(r)),QPointF(24+20*math.cos(r),24+20*math.sin(r)))
    elif key=='new profile':
        p.drawLine(24,12,24,36); p.drawLine(12,24,36,24)
    else:
        p.setFont(font(25,True)); p.drawText(QRectF(0,0,48,48),Qt.AlignmentFlag.AlignCenter,name[:1].upper())
    p.restore()


def tile_art(p, rect, key, variant=0):
    """Distinct editorial artwork for destinations, built entirely from paths."""
    if key.startswith('steam:') or key in ('games','steam-client'):
        scene(p,rect,variant); return
    p.save(); p.setClipRect(rect,Qt.ClipOperation.IntersectClip)
    p.translate(rect.x(),rect.y()); p.scale(rect.width()/300,rect.height()/132)
    colors={'youtube':('#552635','#d95159'),'spotify':('#143d3a','#62b39c'),
            'netflix':('#381e36','#ab3955'),'prime':('#143b58','#54aad0'),
            'steam-store':('#193755','#599db3'),'flathub':('#273657','#929ad2'),
            'gog':('#3b2557','#b58bd4'),'itch':('#552d3a','#e29a83')}
    dark,light=colors.get(key,(PALETTES[variant][0],PALETTES[variant][1]))
    gradient=QLinearGradient(0,132,300,0); gradient.setColorAt(0,color(dark).darker(140)); gradient.setColorAt(1,color(dark).lighter(155))
    p.fillRect(QRectF(0,0,300,132),gradient)
    p.setPen(Qt.PenStyle.NoPen)
    if key=='spotify':
        p.setBrush(color('#091c24')); p.drawEllipse(QPointF(220,68),92,92)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for radius in (26,40,53,66,80):
            p.setPen(QPen(color(light,95),1)); p.drawEllipse(QPointF(220,68),radius,radius)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(color(light)); p.drawEllipse(QPointF(220,68),20,20)
        p.setBrush(color('#143d3a')); p.drawEllipse(QPointF(220,68),4,4)
    elif key in ('youtube','prime'):
        p.translate(216,68); p.rotate(-12)
        for offset,opacity in [(25,35),(12,70),(0,155)]:
            p.setBrush(color(light,opacity)); p.drawRoundedRect(QRectF(-63+offset,-43+offset,106,77),12,12)
        p.setBrush(color('#e1f1f3',200)); p.drawPolygon(polygon([(-20,-20),(-20,20),(10,0)]))
    elif key=='netflix':
        p.setBrush(color(light,95)); p.drawPolygon(polygon([(130,0),(211,0),(255,132),(174,132)]))
        p.setBrush(color('#ec4961',220)); p.drawPolygon(polygon([(181,15),(197,15),(242,116),(226,116)]))
        p.setBrush(color('#b83150',220)); p.drawRect(QRectF(181,15,16,101)); p.drawRect(QRectF(226,15,16,101))
    elif key in ('flathub','store'):
        p.translate(215,65)
        for x,y,tint in [(-32,-26,'#bedbd6'),(2,-7,'#ceaddd'),(-32,13,'#8eace7'),(-66,-7,'#eac5a0')]:
            p.setBrush(color(tint)); p.drawPolygon(polygon([(x,y),(x+29,y-16),(x+58,y),(x+29,y+16)]))
            p.setBrush(color(tint).darker(160)); p.drawPolygon(polygon([(x,y),(x+29,y+16),(x+29,y+34),(x,y+18)]))
            p.setBrush(color(tint).darker(120)); p.drawPolygon(polygon([(x+29,y+16),(x+58,y),(x+58,y+18),(x+29,y+34)]))
    elif key in ('gog','steam-store'):
        p.setBrush(Qt.BrushStyle.NoBrush)
        for radius in (34,56,80,104):
            p.setPen(QPen(color(light,160 if radius==56 else 65),2)); p.drawEllipse(QPointF(223,67),radius,radius)
        p.setPen(Qt.PenStyle.NoPen); glow=QRadialGradient(213,51,47); glow.setColorAt(0,color('#e4fff1')); glow.setColorAt(.35,color(light)); glow.setColorAt(1,color(dark)); p.setBrush(glow); p.drawEllipse(QPointF(213,62),40,40)
    elif key=='itch':
        p.setBrush(color(light))
        for row,line in enumerate(('00100100','01111110','11011011','11111111','10100101','00111100','01000010')):
            for col,bit in enumerate(line):
                if bit=='1': p.drawRoundedRect(QRectF(171+col*11,24+row*11,10,10),1,1)
    else:
        p.setPen(QPen(color(light,80),1.2)); p.setBrush(Qt.BrushStyle.NoBrush)
        for n in range(4): p.drawRoundedRect(QRectF(157+n*16,22-n*7,80,80),15,15)
        p.setBrush(color(light,100)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(254,34),7,7)
    p.restore()


def flow_contours():
    """Current concept: three open paths join at one destination (under review)."""
    stroker=QPainterPathStroker(); stroker.setWidth(19)
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap); stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    path=QPainterPath()
    for start,points in [(76,(80,76,76,35,145,35)),(110,(93,110,98,35,145,35)),(144,(116,144,120,35,145,35))]:
        center=QPainterPath(QPointF(26,start)); center.cubicTo(*points)
        path=path.united(stroker.createStroke(center))
    return [[(point.x()/50,point.y()/50) for point in contour] for contour in path.simplified().toSubpathPolygons()]


class Logo(QWidget):
    """Perspective-extruded Current concept; design pending user feedback."""
    def __init__(self,motion=True,parent=None):
        super().__init__(parent)
        self.motion=motion; self.angle=.4; self.contours=flow_contours()
        self.setMinimumSize(120,90)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAccessibleName('OmaFlow three-dimensional Current concept')
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick)
        self.timer.setInterval(33)
    def tick(self):
        self.angle+=.026; self.update()
    def showEvent(self,event):
        if self.motion: self.timer.start()
        super().showEvent(event)
    def hideEvent(self,event):
        self.timer.stop(); super().hideEvent(event)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height(); size=min(w/4.2,h/3.8)
        yaw=-.18+math.sin(self.angle)*.35; pitch=.20+math.cos(self.angle*.7)*.10
        def project(x,y,z):
            x-=1.8; y-=1.8
            rx=x*math.cos(yaw)+z*math.sin(yaw); rz=-x*math.sin(yaw)+z*math.cos(yaw)
            ry=y*math.cos(pitch)-rz*math.sin(pitch); depth=y*math.sin(pitch)+rz*math.cos(pitch)
            k=5/(5+depth)
            return QPointF(w/2+rx*size*k,h/2+ry*size*k),depth
        glow=QRadialGradient(w*.5,h*.5,min(w*.45,h*.49))
        glow.setColorAt(0,color(MINT,32)); glow.setColorAt(1,color(MINT,0))
        p.fillRect(self.rect(),glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color('#000000',65)); p.drawEllipse(QRectF(w*.13,h*.79,w*.74,h*.07))
        faces=[]
        for contours in [self.contours]:
            offset=0
            for contour in contours:
                for j,(x,y) in enumerate(contour):
                    xx,yy=contour[(j+1)%len(contour)]
                    vertices=[project(x+offset,y,0),project(xx+offset,yy,0),project(xx+offset,yy,.28),project(x+offset,y,.28)]
                    faces.append((sum(v[1] for v in vertices)/4,QPolygonF([v[0] for v in vertices]),'#527b9c' if j%2 else '#b8cadd'))
        for _,shape,tint in sorted(faces,key=lambda f:f[0],reverse=True):
            p.setPen(QPen(color(tint).lighter(120),.8)); p.setBrush(color(tint)); p.drawPolygon(shape)
        for contours in [self.contours]:
            path=QPainterPath(); path.setFillRule(Qt.FillRule.OddEvenFill)
            for contour in contours:
                shape=[project(x,y,0)[0] for x,y in contour]
                path.addPolygon(QPolygonF(shape)); path.closeSubpath()
            front=QLinearGradient(0,h*.2,0,h*.8); front.setColorAt(0,color('#fff1ec')); front.setColorAt(.5,color('#dfe7ee')); front.setColorAt(1,color('#8097b1'))
            p.setBrush(front); p.setPen(QPen(color('#f4f8ff'),1)); p.drawPath(path)


class LoadingLine(QWidget):
    def __init__(self,motion=True,parent=None):
        super().__init__(parent); self.motion=motion; self.elapsed=QElapsedTimer(); self.elapsed.start()
        self.setFixedSize(200,4); self.timer=QTimer(self); self.timer.setInterval(33); self.timer.timeout.connect(self.update)
        self.setAccessibleName('Opening your space')
    def showEvent(self,event):
        if self.motion: self.timer.start()
        super().showEvent(event)
    def hideEvent(self,event):
        self.timer.stop(); super().hideEvent(event)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color('#273c49')); p.drawRoundedRect(QRectF(self.rect()),2,2)
        progress=min(1,self.elapsed.elapsed()/1600) if self.motion else 1
        p.setBrush(color(MINT)); p.drawRoundedRect(QRectF(0,0,self.width()*progress,4),2,2)



def local_art(item):
    """Use already-cached Steam art or desktop icons; never perform network I/O."""
    if item is None: return QPixmap()
    if item.kind=='app':
        config=configparser.ConfigParser(interpolation=None,strict=False)
        try:
            config.read(item.target,encoding='utf-8'); name=config['Desktop Entry'].get('Icon','')
            if not name: return QPixmap()
            icon=QIcon(name) if Path(name).is_absolute() else QIcon.fromTheme(name)
            return icon.pixmap(96,96)
        except (OSError,UnicodeError,configparser.Error,KeyError): return QPixmap()
    if item.id.startswith('steam:') and item.id[6:].isdigit():
        appid=item.id[6:]; home=Path.home()
        for root in (home/'.local/share/Steam',home/'.steam/steam',home/'.var/app/com.valvesoftware.Steam/.local/share/Steam'):
            cache=root/'appcache/librarycache'
            paths=[cache/(appid+'_library_600x900.jpg'),cache/(appid+'_header.jpg')]
            paths.extend(sorted((cache/appid).glob('*_header.jpg')))
            for path in paths:
                if path.is_file():
                    reader=QImageReader(str(path)); size=reader.size()
                    if size.isValid():
                        size.scale(600,400,Qt.AspectRatioMode.KeepAspectRatio); reader.setScaledSize(size)
                        image=reader.read()
                        if not image.isNull(): return QPixmap.fromImage(image)
    return QPixmap()


def title_lines(text,metrics,width):
    """At most two readable title lines; the full name remains accessible."""
    if metrics.horizontalAdvance(text)<=width: return [text]
    words=text.split(); first=[]
    while words and metrics.horizontalAdvance(' '.join(first+[words[0]]))<=width:
        first.append(words.pop(0))
    if not first: return [metrics.elidedText(text,Qt.TextElideMode.ElideRight,width)]
    return [' '.join(first),metrics.elidedText(' '.join(words),Qt.TextElideMode.ElideRight,width)]


class Card(QPushButton):
    def __init__(self,title,subtitle,icon,index,callback,scale=1):
        super().__init__(); self.title=title; self.subtitle=subtitle; self.icon=icon; self.scale=scale; self.index=index
        self._item=None; self.art=QPixmap(); self.variant=int.from_bytes(hashlib.sha256(title.encode()).digest()[:2],'big')%4
        self.setAccessibleName(title+' — '+subtitle); self.setToolTip(title+'\n'+subtitle)
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.clicked.connect(callback)
        self.setMinimumHeight(round(202*scale)); self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
    @property
    def item(self): return self._item
    @item.setter
    def item(self,value):
        self._item=value; self.art=local_art(value); self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=QRectF(self.rect()).adjusted(3,3,-3,-3); clip=QPainterPath(); clip.addRoundedRect(rect,15,15); p.setClipPath(clip)
        name=self.title.removeprefix('★ '); key=self.item.id if self.item else name.lower()
        art_height=self.height()-round(88*self.scale)
        art_rect=QRectF(3,3,self.width()-6,art_height)
        tile_art(p,art_rect,key,self.variant)
        if not self.art.isNull() and self.item and self.item.kind!='app':
            scaled=self.art.scaled(art_rect.size().toSize(),Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(art_rect,scaled,QRectF((scaled.width()-art_rect.width())/2,(scaled.height()-art_rect.height())/2,art_rect.width(),art_rect.height()))
        else:
            p.fillRect(art_rect,color('#091321',80))
            size=min(54*self.scale,max(28*self.scale,art_height-50*self.scale)); icon_rect=QRectF(22,19,size,size)
            if not self.art.isNull(): p.drawPixmap(icon_rect,self.art,QRectF(self.art.rect()))
            else: symbol(p,icon_rect,key,'#f0f8f5')
            # Editorial category label, real source rather than fictional game metadata.
            tag='APPLICATION' if self.item and self.item.kind=='app' else 'STEAM' if key.startswith('steam:') else 'QUICK ACCESS'
            if key in ('youtube','spotify','netflix','prime'): tag='WATCH & LISTEN'
            if key in ('steam-store','flathub','gog','itch'): tag='DISCOVER'
            p.setFont(font(10*self.scale,True)); p.setPen(color('#e1efeb')); p.drawText(QRectF(22,art_height-26,self.width()-44,20),Qt.AlignmentFlag.AlignLeft,tag)
        p.fillRect(QRectF(3,art_height,self.width()-6,self.height()-art_height),color('#1b2b3f' if self.hasFocus() else '#101a27',238))
        p.setPen(color('#f3f6f7')); p.setFont(font(17*self.scale,True))
        lines=title_lines(self.title,p.fontMetrics(),self.width()-38)
        first=self.height()-round((52 if len(lines)>1 else 41)*self.scale)
        for number,line in enumerate(lines): p.drawText(19,first+round(number*21*self.scale),line)
        p.setFont(font(12*self.scale)); p.setPen(color('#b6c6d3'))
        p.drawText(19,self.height()-round(13*self.scale),p.fontMetrics().elidedText(self.subtitle,Qt.TextElideMode.ElideRight,self.width()-38))
        p.setClipping(False); focus_frame(p,rect,self.hasFocus(),15)
        if self.hasFocus():
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(color(MINT)); p.drawRoundedRect(QRectF(self.width()-43,12,28,26),7,7)
            p.setPen(color('#122e49')); p.setFont(font(13,True)); p.drawText(QRectF(self.width()-43,12,28,26),Qt.AlignmentFlag.AlignCenter,'A')


class ProfileCard(QPushButton):
    def __init__(self,name,index,callback,scale=1,adding=False,subtitle='Personal space'):
        super().__init__(); self.name=name; self.index=index; self.scale=scale; self.adding=adding; self.subtitle=subtitle
        self.setMinimumHeight(round(225*scale)); self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        self.setAccessibleName(name+' — '+subtitle); self.setToolTip(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.clicked.connect(callback)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=QRectF(self.rect()).adjusted(8,8,-8,-8)
        g=QLinearGradient(0,0,self.width(),self.height()); g.setColorAt(0,color('#192331',220)); g.setColorAt(1,color('#09131f',235))
        p.setBrush(g); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(rect,13,13); focus_frame(p,rect,self.hasFocus())
        size=78*self.scale; bounds=QRectF((self.width()-size)/2,36*self.scale,size,size)
        if self.adding:
            p.setBrush(color('#1d2a3a')); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(bounds.adjusted(8,8,-8,-8)); symbol(p,bounds.adjusted(17,17,-17,-17),'new profile','#c3d1e5')
        else: avatar(p,bounds,self.index)
        p.setFont(font(19*self.scale)); p.setPen(color('#f1f5fc'))
        p.drawText(QRectF(16,137*self.scale,self.width()-32,28*self.scale),Qt.AlignmentFlag.AlignCenter,p.fontMetrics().elidedText(self.name,Qt.TextElideMode.ElideRight,self.width()-32))
        p.setFont(font(11*self.scale)); p.setPen(color('#aebdd2'))
        p.drawText(QRectF(12,171*self.scale,self.width()-24,25*self.scale),Qt.AlignmentFlag.AlignCenter,p.fontMetrics().elidedText(self.subtitle,Qt.TextElideMode.ElideRight,self.width()-24))




class DetailArtwork(QWidget):
    def __init__(self,item,parent=None):
        super().__init__(parent); self.item=item; self.art=local_art(item); self.setFixedHeight(124)
        self.setAccessibleName(item.name+' artwork')
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=QRectF(self.rect()); path=QPainterPath(); path.addRoundedRect(rect,14,14); p.setClipPath(path)
        tile_art(p,rect,self.item.id)
        if not self.art.isNull() and self.item.kind!='app':
            art=self.art.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(rect,art,QRectF((art.width()-self.width())/2,(art.height()-self.height())/2,self.width(),self.height()))
        elif not self.art.isNull(): p.drawPixmap(26,26,72,72,self.art)
        else: symbol(p,QRectF(28,26,72,72),self.item.id)


def focus_frame(p,rect,focused,radius=13):
    p.setBrush(Qt.BrushStyle.NoBrush)
    if focused:
        for spread in (7,5,3):
            p.setPen(QPen(color(MINT,14+spread*2),spread)); p.drawRoundedRect(rect,radius,radius)
    p.setPen(QPen(color(MINT if focused else '#6c8097',235 if focused else 65),1.5 if focused else 1))
    p.drawRoundedRect(rect,radius,radius)


def avatar(p,rect,index=0):
    p.save(); path=QPainterPath(); path.addEllipse(rect); p.setClipPath(path,Qt.ClipOperation.IntersectClip)
    p.translate(rect.x(),rect.y()); p.scale(rect.width()/100,rect.height()/100)
    tone=['#4e5396','#344354','#865999','#b58b51'][index%4]
    grad=QLinearGradient(0,0,100,100); grad.setColorAt(0,color(tone).lighter(130)); grad.setColorAt(1,color(tone).darker(170))
    p.fillRect(QRectF(0,0,100,100),grad)
    if index%4==0:
        p.setPen(QPen(color('#8796bd'),2)); p.setBrush(color('#7989b0')); p.drawRoundedRect(QRectF(16,30,68,61),26,26)
        p.setBrush(color('#212e46')); p.drawRoundedRect(QRectF(10,44,9,26),4,4); p.drawRoundedRect(QRectF(81,44,9,26),4,4)
        p.setBrush(color('#071426')); p.drawRoundedRect(QRectF(23,40,54,33),14,14)
        for x in (37,63):
            glow=QRadialGradient(x,56,11); glow.setColorAt(0,color('#64ceff')); glow.setColorAt(.5,color('#1699fb',150)); glow.setColorAt(1,color('#1699fb',0)); p.setPen(Qt.PenStyle.NoPen); p.setBrush(glow); p.drawEllipse(QPointF(x,56),11,11)
            p.setBrush(color('#c3f3ff')); p.drawEllipse(QPointF(x,56),3,6)
        p.setBrush(color('#a5b5d3')); p.drawRoundedRect(QRectF(39,80,22,3),1,1)
    elif index%4==1:
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(color('#202734')); p.drawEllipse(QRectF(0,45,100,80))
        symbol(p,QRectF(12,16,76,76),'games','#c7d3e5')
    elif index%4==2:
        scene(p,QRectF(0,0,100,100),2)
    else:
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(color('#e5b78b'))
        p.drawPolygon(polygon([(22,51),(21,21),(43,36)])); p.drawPolygon(polygon([(57,36),(81,21),(78,53)]))
        p.drawEllipse(QRectF(21,31,58,53)); p.setBrush(color('#f6e4cf')); p.drawEllipse(QRectF(34,49,32,33))
        p.setBrush(color('#202b36')); p.drawEllipse(QPointF(37,54),3,4); p.drawEllipse(QPointF(63,54),3,4)
        p.setBrush(color('#b57771')); p.drawPolygon(polygon([(45,63),(55,63),(50,69)]))
        p.setPen(QPen(color('#72544c'),1.3)); p.drawLine(50,69,46,73); p.drawLine(50,69,54,73)
    p.restore()


class Backdrop(QWidget):
    """One shared backdrop, scaled once per window size; foreground stays native."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self._background=QPixmap(str(Path(__file__).with_name('assets')/'mountain-dusk.png'))
        self._scaled_background=QPixmap()
        self._background_size=None
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.fillRect(self.rect(),color('#03070c'))
        if getattr(self,'page','splash')=='splash':
            w,h=self.width(),self.height(); glow=QRadialGradient(w*.5,h*.71,w*.43)
            glow.setColorAt(0,color('#345f7e',135)); glow.setColorAt(.35,color('#122a3e',85)); glow.setColorAt(1,color('#02060c',0)); p.fillRect(self.rect(),glow)
            # The illuminated planetary horizon from the reference, under the flow emblem.
            ellipse=QRectF(-w*.17,h*.70,w*1.34,h*1.2)
            p.setBrush(color('#030810')); p.setPen(QPen(color('#8fc9f1',20),18)); p.drawEllipse(ellipse)
            p.setPen(QPen(color('#9bdbff',40),6)); p.drawEllipse(ellipse)
            edge=QLinearGradient(0,0,w,0); edge.setColorAt(0,color('#0b1722')); edge.setColorAt(.5,color('#b8e4ff')); edge.setColorAt(1,color('#0b1722'))
            p.setPen(QPen(edge,1.4)); p.drawEllipse(ellipse)
            return
        if not self._background.isNull():
            if self._background_size!=self.size():
                self._scaled_background=self._background.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
                self._background_size=self.size()
            art=self._scaled_background
            p.drawPixmap(self.rect(),art,art.rect().adjusted((art.width()-self.width())//2,(art.height()-self.height())//2,-(art.width()-self.width())//2,-(art.height()-self.height())//2))
        shade=QLinearGradient(0,0,0,self.height()); shade.setColorAt(0,color('#03070d',80)); shade.setColorAt(.45,color('#03070d',120)); shade.setColorAt(1,color('#03070d',245)); p.fillRect(self.rect(),shade)
        side=QLinearGradient(0,0,self.width(),0); side.setColorAt(0,color('#03070d',150)); side.setColorAt(.4,color('#03070d',15)); side.setColorAt(1,color('#03070d',90)); p.fillRect(self.rect(),side)


class NavButton(QPushButton):
    def __init__(self,name,callback,scale=1):
        super().__init__(name); self.name=name; self.scale=scale; self.clicked.connect(callback)
        self.setAccessibleName(name); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFixedHeight(round(48*scale))
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=QRectF(self.rect()).adjusted(2,3,-2,-3); active=self.property('active')
        if active or self.hasFocus():
            gradient=QLinearGradient(0,0,self.width(),0); gradient.setColorAt(0,color('#243f59',230)); gradient.setColorAt(1,color('#172a3d',210))
            p.setBrush(gradient); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(rect,8,8)
            p.setPen(QPen(color(MINT),2)); p.drawLine(QPointF(3,12),QPointF(3,self.height()-12))
        if self.hasFocus(): focus_frame(p,rect,True,8)
        tint='#e0eafb' if active or self.hasFocus() else '#a3b0c4'
        symbol(p,QRectF(15,(self.height()-22)/2,22,22),self.name,tint)
        p.setFont(font(14*self.scale)); p.setPen(color(tint)); p.drawText(QRectF(49,0,self.width()-52,self.height()),Qt.AlignmentFlag.AlignVCenter,self.name)


class CategoryCard(QPushButton):
    def __init__(self,title,subtitle,section,callback,scale=1):
        super().__init__(); self.title=title; self.subtitle=subtitle; self.section=section; self.scale=scale
        self.setMinimumHeight(round(212*scale)); self.setMinimumWidth(0); self.clicked.connect(callback)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title+' — '+subtitle)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=QRectF(self.rect()).adjusted(7,7,-7,-7)
        gradient=QLinearGradient(0,0,self.width(),self.height())
        gradient.setColorAt(0,color('#243343',220)); gradient.setColorAt(1,color('#0f242d' if self.section=='Media' else '#172332',220))
        p.setBrush(gradient); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(rect,13,13)
        glow=QRadialGradient(self.width()/2,self.height()*.83,self.width()*.65); glow.setColorAt(0,color('#6b95b3',30)); glow.setColorAt(1,color('#6b95b3',0)); p.setBrush(glow); p.drawRoundedRect(rect,13,13)
        focus_frame(p,rect,self.hasFocus())
        size=48*self.scale; symbol(p,QRectF((self.width()-size)/2,self.height()*.18,size,size),self.section,'#d2deef')
        p.setFont(font(17*self.scale)); p.setPen(color('#f2f5fb'))
        p.drawText(QRectF(12,self.height()*.57,self.width()-24,30*self.scale),Qt.AlignmentFlag.AlignCenter,p.fontMetrics().elidedText(self.title,Qt.TextElideMode.ElideRight,self.width()-24))
        p.setFont(font(11*self.scale)); p.setPen(color('#b0bfd1'))
        p.drawText(QRectF(12,self.height()*.74,self.width()-24,25*self.scale),Qt.AlignmentFlag.AlignCenter,p.fontMetrics().elidedText(self.subtitle,Qt.TextElideMode.ElideRight,self.width()-24))
