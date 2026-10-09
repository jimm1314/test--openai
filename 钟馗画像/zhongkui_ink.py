#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钟馗水墨画 · 纯 Python 程序化水墨渲染器
=================================================
零第三方依赖（仅标准库 math/random/zlib/struct/array），
输出中国传统写意水墨风格的钟馗像 PNG：
  - zhongkui_full.png  全身立像·持剑（1024×1536）
  - zhongkui_bust.png  半身怒目特写（1024×1536）

用法：
  python3 zhongkui_ink.py                 # 全尺寸双图
  python3 zhongkui_ink.py --draft         # 512×768 快速预览
  python3 zhongkui_ink.py --only bust     # 只出半身像
  python3 zhongkui_ink.py --test          # 笔刷/印章测试页
  python3 zhongkui_ink.py --seed 7        # 换随机种子（同 seed 完全可复现）
"""

import argparse
import math
import os
import random
import struct
import zlib
from array import array


# =====================================================================
# 1. PNG 编码（RGB 8-bit，filter 0，单 IDAT —— 最朴素、全兼容）
# =====================================================================

def write_png(path, w, h, rgb):
    """rgb: bytes/bytearray，长度 w*h*3，行主序。"""
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)  # 8-bit, color type 2 (RGB)
    stride = w * 3
    raw = bytearray(h * (stride + 1))
    pos = 0
    for y in range(h):
        raw[pos] = 0  # filter: None
        seg = rgb[y * stride:(y + 1) * stride]
        raw[pos + 1: pos + 1 + stride] = seg
        pos += stride + 1
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
           + chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


# =====================================================================
# 2. 值噪声（自制 2D value noise + fbm）
# =====================================================================

class Noise2D:
    __slots__ = ('g', 'gw', 'gh')

    def __init__(self, rng, gw, gh):
        self.gw, self.gh = gw, gh
        self.g = [[rng.random() for _ in range(gw + 2)] for _ in range(gh + 2)]

    def at(self, x, y):
        g, gw, gh = self.g, self.gw, self.gh
        xi = int(math.floor(x)); yi = int(math.floor(y))
        if xi < 0: xi = 0
        if yi < 0: yi = 0
        if xi > gw: xi = gw
        if yi > gh: yi = gh
        fx = x - xi; fy = y - yi
        fx = fx * fx * (3 - 2 * fx)   # smoothstep
        fy = fy * fy * (3 - 2 * fy)
        r0 = g[yi]; r1 = g[yi + 1]
        v00 = r0[xi]; v10 = r0[xi + 1]
        v01 = r1[xi]; v11 = r1[xi + 1]
        a = v00 + (v10 - v00) * fx
        b = v01 + (v11 - v01) * fx
        return a + (b - a) * fy

    def fbm(self, x, y):
        return (0.60 * self.at(x, y)
                + 0.28 * self.at(x * 2.13 + 7.3, y * 2.13 + 3.1)
                + 0.12 * self.at(x * 4.31 + 13.7, y * 4.31 + 9.4))


# =====================================================================
# 3. 画布、宣纸、墨色
# =====================================================================

PAPER = (0.962, 0.942, 0.893)        # 宣纸米白
INK_JIAO = (0.062, 0.062, 0.078)     # 焦墨（松烟微蓝）
INK_NONG = (0.145, 0.149, 0.173)     # 浓墨
INK_ZHONG = (0.302, 0.306, 0.333)    # 重墨
INK_DAN = (0.498, 0.502, 0.529)      # 淡墨
INK_QING = (0.682, 0.686, 0.710)     # 清墨
ZHU_SHA = (0.784, 0.086, 0.118)      # 朱砂 #C8161E
A_JIAO, A_NONG, A_ZHONG, A_DAN, A_QING = 0.92, 0.78, 0.60, 0.35, 0.18


class Canvas:
    __slots__ = ('w', 'h', 'r', 'g', 'b')

    def __init__(self, w, h, paper=PAPER):
        self.w, self.h = w, h
        n = w * h
        self.r = array('f', [paper[0]]) * n
        self.g = array('f', [paper[1]]) * n
        self.b = array('f', [paper[2]]) * n

    def blend(self, i, sr, sg, sb, a):
        ia = 1.0 - a
        self.r[i] = self.r[i] * ia + sr * a
        self.g[i] = self.g[i] * ia + sg * a
        self.b[i] = self.b[i] * ia + sb * a

    def tonemap(self):
        n = self.w * self.h
        out = bytearray(n * 3)
        r, g, b = self.r, self.g, self.b
        i = 0
        for p in range(n):
            v = r[p]
            out[i] = 255 if v > 1 else (0 if v < 0 else int(v * 255 + 0.5))
            v = g[p]
            out[i + 1] = 255 if v > 1 else (0 if v < 0 else int(v * 255 + 0.5))
            v = b[p]
            out[i + 2] = 255 if v > 1 else (0 if v < 0 else int(v * 255 + 0.5))
            i += 3
        return out

    def save(self, path):
        write_png(path, self.w, self.h, self.tonemap())


def make_paper(cv, rng):
    """宣纸：米白底 + 双 octave 帘纹 + 纤维丝 + 杂质点。"""
    w, h = cv.w, cv.h
    nz_lo = Noise2D(rng, 24, 36)     # 大块云絮（竹帘纹）
    nz_hi = Noise2D(rng, 96, 144)    # 细颗粒
    rr, gg, bb = cv.r, cv.g, cv.b
    sx, sy = 24.0 / w, 36.0 / h
    hx, hy = 96.0 / w, 144.0 / h
    lo_at, hi_at = nz_lo.at, nz_hi.at
    i = 0
    for py in range(h):
        fy_lo = py * sy; fy_hi = py * hy
        # 廉价整数哈希颗粒
        rowseed = (py * 7549) & 1023
        for px in range(w):
            m = 1.0 + 0.028 * (lo_at(px * sx, fy_lo) - 0.5) * 2 \
                + 0.011 * (hi_at(px * hx, fy_hi) - 0.5) * 2 \
                + 0.006 * (((px * 1237 + rowseed) & 1023) / 1023.0 - 0.5) * 2
            rr[i] *= m; gg[i] *= m; bb[i] *= m
            i += 1
    # 纤维丝：随机短弧，极淡
    br = Brush(cv, rng)  # 临时笔刷（不带噪声扰动边缘）
    for _ in range(int(150 * (w / 1024))):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        ang = rng.uniform(0, math.pi)
        ln = rng.uniform(20, 80) * (w / 1024)
        pts = [(x, y),
               (x + math.cos(ang) * ln * 0.5, y + math.sin(ang) * ln * 0.5),
               (x + math.cos(ang + rng.uniform(-0.3, 0.3)) * ln,
                y + math.sin(ang + rng.uniform(-0.3, 0.3)) * ln)]
        dark = rng.random() < 0.5
        col = (0.88, 0.86, 0.80) if dark else (1.0, 0.995, 0.97)
        br.polyline(pts, col, max(0.6, 0.8 * w / 1024), rng.uniform(0.02, 0.045),
                    edge_amp=0.0)
    # 杂质点
    for _ in range(rng.randint(5, 9)):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        br.dab(x, y, rng.uniform(0.8, 1.8) * (w / 1024),
               (0.78, 0.72, 0.62), rng.uniform(0.10, 0.22), edge_amp=0.3)


# =====================================================================
# 4. 笔刷引擎（dab / stroke / blob / carve / polyline）
# =====================================================================

def _prof(kind, p):
    """四种描法的宽度曲线，p∈[0,1]。"""
    if kind == 'iron':                       # 铁线描：均匀
        return 1.0
    if kind == 'nail':                       # 钉头鼠尾：起笔重，收笔尖
        return 1.0 if p < 0.12 else max(0.10, 1.0 - (p - 0.12) / 0.88 * 0.9)
    if kind == 'orchid':                     # 兰叶描：两端细、中段饱满
        s = math.sin(math.pi * min(1.0, max(0.0, p)))
        return max(0.08, s ** 0.7)
    if kind == 'dry':                        # 枯柴描：均匀偏枯
        return 1.0
    return 1.0


def bezier_pts(p0, p1, p2, p3, step):
    """三次贝塞尔采样，步长 step（px），返回 [(x,y), ...]。"""
    peri = (math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            + math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            + math.hypot(p3[0] - p2[0], p3[1] - p2[1]))
    n = max(4, int(peri / max(0.5, step)))
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt * mt * mt * p0[0] + 3 * mt * mt * t * p1[0] \
            + 3 * mt * t * t * p2[0] + t * t * t * p3[0]
        y = mt * mt * mt * p0[1] + 3 * mt * mt * t * p1[1] \
            + 3 * mt * t * t * p2[1] + t * t * t * p3[1]
        pts.append((x, y))
    return pts


def arc_pts(cx, cy, rx, ry, a0, a1, step=2.0, rot=0.0):
    """椭圆弧采样（角度弧度制）。"""
    peri = abs(a1 - a0) * max(rx, ry)
    n = max(3, int(peri / max(0.5, step)))
    cr, sr = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        ex, ey = math.cos(a) * rx, math.sin(a) * ry
        pts.append((cx + ex * cr - ey * sr, cy + ex * sr + ey * cr))
    return pts


class Brush:
    """绑定画布 + 随机源 + 边缘噪声的笔。"""

    def __init__(self, cv, rng, nz_edge=None, S=None):
        self.cv = cv
        self.rng = rng
        self.nz_edge = nz_edge or Noise2D(rng, 160, 240)
        self.S = S if S is not None else cv.w / 1024.0

    # ---- 原子落墨 ----
    def dab(self, cx, cy, r, ink, alpha, edge_amp=0.15, carve=False):
        if r < 0.45 or alpha <= 0.002:
            return
        cv = self.cv; W = cv.w; H = cv.h
        x0 = int(cx - r - 2); x1 = int(cx + r + 2)
        y0 = int(cy - r - 2); y1 = int(cy + r + 2)
        if x1 < 0 or y1 < 0 or x0 >= W or y0 >= H:
            return
        if x0 < 0: x0 = 0
        if y0 < 0: y0 = 0
        if x1 >= W: x1 = W - 1
        if y1 >= H: y1 = H - 1
        rr = cv.r; gg = cv.g; bb = cv.b
        if carve:
            sr, sg, sb = PAPER
        else:
            sr, sg, sb = ink
        use_nz = edge_amp > 0.001 and r >= 2.5
        nz_at = self.nz_edge.at
        sqrt = math.sqrt
        for py in range(y0, y1 + 1):
            dy = py - cy; dy2 = dy * dy
            base = py * W
            for px in range(x0, x1 + 1):
                dx = px - cx
                d2 = dx * dx + dy2
                if use_nz:
                    re = r * (1.0 + edge_amp * (nz_at(px * 0.09, py * 0.09) - 0.5) * 2.0)
                else:
                    re = r
                lim = re + 0.75
                if d2 > lim * lim:
                    continue
                cov = re + 0.5 - sqrt(d2)
                if cov <= 0.0:
                    continue
                a = alpha * (cov if cov < 1.0 else 1.0)
                ia = 1.0 - a
                i = base + px
                rr[i] = rr[i] * ia + sr * a
                gg[i] = gg[i] * ia + sg * a
                bb[i] = bb[i] * ia + sb * a

    # ---- 折线细笔（无 profile，用于纤维/纹理）----
    def polyline(self, pts, col, w, alpha, edge_amp=0.0, carve=False):
        if len(pts) < 2:
            return
        step = max(0.6, w * 0.45)
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]; x1, y1 = pts[i + 1]
            ln = math.hypot(x1 - x0, y1 - y0)
            n = max(2, int(ln / step))
            for k in range(n + 1):
                t = k / n
                self.dab(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t,
                         w / 2, col, alpha, edge_amp, carve)

    # ---- 核心笔触 ----
    def stroke(self, pts, ink, w0, alpha=1.0, profile='iron', dry=0.0,
               bleed=0.0, fly=0.0, edge_amp=0.15, step=None):
        """沿 pts 路径落墨。w0 为全尺寸基准笔宽（自动乘 S）。"""
        if len(pts) < 2:
            return
        S = self.S
        w0 = w0 * S
        rng = self.rng
        if step is None:
            step = max(0.9, w0 * 0.28)
        # 重采样：按 step 均匀加密，保证 dab 重叠
        pts = _resample(pts, step)
        n = len(pts)
        # 1) 晕染层（先虚后实）
        if bleed > 0:
            br_ = bleed * S
            for i in range(0, n, 2):
                p = i / (n - 1)
                w = w0 * _prof(profile, p)
                self.dab(pts[i][0], pts[i][1], w * 0.62 + br_,
                         ink, alpha * 0.055, edge_amp=0.50)
        # 2) 核心层
        for i in range(n):
            p = i / (n - 1)
            w = w0 * _prof(profile, p) * (1.0 - 0.22 * dry * p)
            if w < 0.7:
                w = 0.7
            a = alpha * (1.0 - dry * p * 0.72)
            x, y = pts[i]
            j = i + 1 if i + 1 < n else n - 1
            k = i - 1 if i > 0 else 0
            tx = pts[j][0] - pts[k][0]; ty = pts[j][1] - pts[k][1]
            L = math.sqrt(tx * tx + ty * ty) or 1.0
            nx, ny = -ty / L, tx / L
            if fly > 0 and w > 3.4 * S:
                K = max(2, min(9, int(w / (2.3 * S)) + 1))
                gap_p = fly * (0.10 + 0.55 * p)
                for b_ in range(K):
                    if rng.random() < gap_p:
                        continue
                    off = (b_ / (K - 1) - 0.5) * w * 0.85
                    ba = a * (0.45 + 0.50 * rng.random())
                    self.dab(x + nx * off, y + ny * off,
                             max(0.9 * S, w * 0.20), ink, ba, edge_amp)
            else:
                self.dab(x, y, w / 2, ink, a, edge_amp)

    # ---- 泼墨块 ----
    def blob(self, cx, cy, rx, ry, ink, alpha, rot=0.0, edge=0.35,
             bleed=0.0, fill=0.10, rings=((0.45, 1.0), (0.75, 0.85), (1.0, 0.70))):
        S = self.S
        rx *= S; ry *= S
        rng = self.rng
        nz_at = self.nz_edge.at
        cr, sr = math.cos(rot), math.sin(rot)
        # 内部填墨（抖动网格）
        rf = fill * min(rx, ry)
        stepi = max(2.0, rf * 1.15)
        yy = -0.78 * ry
        while yy <= 0.78 * ry:
            xx = -0.78 * rx
            while xx <= 0.78 * rx:
                if (xx / rx) ** 2 + (yy / ry) ** 2 <= 0.62:
                    jx = xx + rng.uniform(-0.3, 0.3) * stepi
                    jy = yy + rng.uniform(-0.3, 0.3) * stepi
                    x = cx + jx * cr - jy * sr
                    y = cy + jx * sr + jy * cr
                    self.dab(x, y, rf, ink, alpha * rng.uniform(0.55, 0.95), edge * 0.5)
                xx += stepi
            yy += stepi
        # 同心菜花边
        for rf_, af in rings:
            per = 6.2832 * ((rx + ry) / 2) * rf_
            nn = max(6, int(per / max(2.0, 3.2 * S)))
            for i in range(nn):
                th = 6.2832 * i / nn + rng.uniform(-0.12, 0.12)
                wob = 1.0 + edge * 0.75 * (nz_at(math.cos(th) * 2.3 + cx * 0.002 + 5,
                                                 math.sin(th) * 2.3 + cy * 0.002 + 9) - 0.5) * 2
                ex = math.cos(th) * rx * rf_ * wob
                ey = math.sin(th) * ry * rf_ * wob
                x = cx + ex * cr - ey * sr
                y = cy + ex * sr + ey * cr
                self.dab(x, y, max(1.6 * S, min(rx, ry) * 0.22 * rf_),
                         ink, alpha * af, edge)
        # 外圈水渍晕
        if bleed > 0:
            per = 6.2832 * ((rx + ry) / 2)
            nn = max(8, int(per / max(2.0, 9.0 * S)))
            for i in range(nn):
                th = 6.2832 * i / nn + rng.uniform(-0.15, 0.15)
                wob = 1.0 + 0.5 * (nz_at(math.cos(th) * 1.7 + 31,
                                         math.sin(th) * 1.7 + 17) - 0.5) * 2
                ex = math.cos(th) * rx * 1.06 * wob
                ey = math.sin(th) * ry * 1.06 * wob
                x = cx + ex * cr - ey * sr
                y = cy + ex * sr + ey * cr
                self.dab(x, y, bleed * S * rng.uniform(0.6, 1.15),
                         ink, alpha * 0.10, 0.55)

    # ---- 挖白（眼白/剑身/印章白文）----
    def carve_ellipse(self, cx, cy, rx, ry, alpha=0.9, rot=0.0, edge=0.12):
        S = self.S
        rx *= S; ry *= S
        cr, sr = math.cos(rot), math.sin(rot)
        step = max(1.5, min(rx, ry) * 0.5)
        yy = -ry
        while yy <= ry:
            xx = -rx
            while xx <= rx:
                if (xx / rx) ** 2 + (yy / ry) ** 2 <= 1.0:
                    x = cx + xx * cr - yy * sr
                    y = cy + xx * sr + yy * cr
                    self.dab(x, y, step * 0.72, PAPER, alpha, edge, carve=True)
                xx += step
            yy += step


def _resample(pts, step):
    """把折线/曲线按 step 均匀重采样。"""
    if len(pts) < 2:
        return pts
    out = [pts[0]]
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]; x1, y1 = pts[i + 1]
        ln = math.hypot(x1 - x0, y1 - y0)
        nn = max(1, int(ln / step))
        for k in range(1, nn + 1):
            t = k / nn
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


# =====================================================================
# 5. 印章与题款（glyph 笔画 DSL + 白文方印）
# =====================================================================

# 篆意「鍾」：金 + 重（64×64 glyph 空间，y 向下）
GLYPH_ZHONG = [
    # 金
    [(20, 3), (8, 16)], [(20, 3), (30, 16)],
    [(12, 19), (28, 19)],
    [(20, 16), (20, 52)],
    [(13, 31), (27, 31)],
    [(14, 40), (17, 44)], [(26, 40), (23, 44)],
    [(11, 52), (29, 52)],
    # 重
    [(46, 3), (42, 8)],
    [(39, 8), (59, 8)],
    [(41, 13), (57, 13)], [(57, 13), (57, 25)],
    [(57, 25), (41, 25)], [(41, 25), (41, 13)],
    [(41, 19), (57, 19)],
    [(49, 8), (49, 57)],
    [(39, 34), (59, 34)],
    [(42, 44), (56, 44)],
    [(37, 56), (61, 56)],
]

# 篆意「馗」：九 半包围 + 首
GLYPH_KUI = [
    # 首（右上）
    [(38, 6), (33, 12)], [(46, 6), (51, 12)],
    [(30, 15), (56, 15)],
    [(43, 15), (41, 20)],
    [(35, 20), (51, 20)],
    [(35, 20), (35, 44)], [(51, 20), (51, 44)],
    [(35, 28), (51, 28)], [(35, 36), (51, 36)],
    [(35, 44), (51, 44)],
    # 九（左下，竖弯钩横扫托底）
    [(21, 14), (10, 34)],
    [(15, 12), (14, 40), (18, 50), (56, 52), (56, 46)],
]


def draw_glyph(br, table, ox, oy, size, ink, alpha, w=None, carve=False,
               edge_amp=0.10):
    """按笔画表画一个篆意字。"""
    if w is None:
        w = size / 9.0
    S = br.S
    for line in table:
        pts = [(ox + gx / 64.0 * size, oy + gy / 64.0 * size) for gx, gy in line]
        br.polyline(pts, ink, w, alpha, edge_amp, carve)


def seal(br, ox, oy, size, chars=(GLYPH_ZHONG, GLYPH_KUI)):
    """白文方印：朱砂底 + 残破蚀边 + 白字 + 剥蚀点。"""
    S = br.S
    rng = br.rng
    nz = br.nz_edge
    # 1) 朱砂方（圆角 + 边缘蚀）
    rad = size * 0.09
    step = max(1.5, 2.2 * S)
    y = 0.0
    while y <= size:
        x = 0.0
        while x <= size:
            # 圆角裁切
            cx_ = min(max(x, rad), size - rad)
            cy_ = min(max(y, rad), size - rad)
            if (x - cx_) ** 2 + (y - cy_) ** 2 > rad * rad:
                x += step; continue
            # 边缘蚀：越靠边界剥蚀概率越高
            db = min(x, y, size - x, size - y)
            erode = nz.at((ox + x) * 0.35 / S, (oy + y) * 0.35 / S)
            if db < size * 0.055 and erode < 0.40 + db / (size * 0.055) * 0.35:
                x += step; continue
            a = 0.86 * (0.82 + 0.30 * nz.at((ox + x) * 0.11 / S + 40,
                                            (oy + y) * 0.11 / S + 3))
            br.dab(ox + x, oy + y, step * 0.75, ZHU_SHA, a, edge_amp=0.0)
            x += step
        y += step
    # 2) 白文刻字（上下排列）
    cw = size * 0.62
    cx0 = ox + (size - cw) / 2
    draw_glyph(br, chars[0], cx0, oy + size * 0.045, cw, PAPER, 0.95,
               w=size * 0.075, carve=True, edge_amp=0.06)
    draw_glyph(br, chars[1], cx0, oy + size * 0.515, cw, PAPER, 0.95,
               w=size * 0.075, carve=True, edge_amp=0.06)
    # 3) 剥蚀点
    for _ in range(int(size * size / (90 * S * S))):
        x = rng.uniform(0, size); y = rng.uniform(0, size)
        if rng.random() < 0.5:
            br.dab(ox + x, oy + y, rng.uniform(0.6, 1.8) * S,
                   PAPER, rng.uniform(0.3, 0.7), edge_amp=0.3, carve=True)


def inscription(br, x, y, size, tables, alpha=0.80):
    """竖排题款。"""
    for i, t in enumerate(tables):
        draw_glyph(br, t, x, y + i * size * 1.24, size,
                   INK_NONG, alpha, w=size / 11.0, edge_amp=0.12)


# =====================================================================
# 6. 共用人物部件（面部 / 须髯 / 乌纱帽）—— 局部坐标以脸 rx 为单位
# =====================================================================

def draw_face(br, cx, cy, rx, ry, detail=1.0):
    """钟馗面部：铁面、环眼怒目、剑眉倒竖。局部坐标以 rx 为 1。"""
    S = br.S

    def LX(u): return cx + u * rx
    def LY(v): return cy + v * ry

    # ---- 面部轮廓（只画两颊+下颌，额头由帽子压住；下颌略收）----
    face_pts = []
    n = 26
    a0, a1 = -0.12 * math.pi, 1.12 * math.pi   # 右太阳穴 → 下巴 → 左太阳穴
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        wmod = 1.0 - 0.10 * max(0.0, math.sin(a)) ** 2
        face_pts.append((cx + math.cos(a) * rx * wmod,
                         cy + math.sin(a) * ry))
    br.stroke(face_pts, INK_ZHONG, 2.2 * detail, alpha=0.55, edge_amp=0.10,
              dry=0.25)

    # ---- 颧/颊皴擦阴影 ----
    for sx in (-1, 1):
        br.stroke(arc_pts(LX(0.52 * sx), LY(0.10), 0.30 * rx, 0.20 * ry,
                          0.4 if sx < 0 else math.pi - 1.6,
                          1.6 if sx < 0 else math.pi - 0.4),
                  INK_DAN, 6 * detail, alpha=0.16, edge_amp=0.3)
    # 下颌阴影
    br.stroke(arc_pts(cx, LY(0.62), 0.62 * rx, 0.34 * ry, 0.35, math.pi - 0.35),
              INK_DAN, 7 * detail, alpha=0.15, edge_amp=0.3)
    # 皱眉纹（竖纹两根）
    for dx in (-0.055, 0.055):
        br.stroke([(LX(dx), LY(-0.50)), (LX(dx * 0.6), LY(-0.26))],
                  INK_ZHONG, 1.8 * detail, alpha=0.5, profile='nail')

    # ---- 怒眉（内端下压、外端飞挑，钉头鼠尾）----
    for sx in (-1, 1):
        brow = bezier_pts(
            (LX(0.09 * sx), LY(-0.30)),           # 内端（低、压眼）
            (LX(0.36 * sx), LY(-0.40)),
            (LX(0.58 * sx), LY(-0.55)),
            (LX(0.76 * sx), LY(-0.68)),           # 外端（高挑）
            step=2 * S)
        br.stroke(brow, INK_NONG, 8.5 * detail, alpha=0.88,
                  profile='nail', fly=0.30, dry=0.12)
        # 补眉梢
        br.stroke(bezier_pts((LX(0.11 * sx), LY(-0.26)),
                             (LX(0.38 * sx), LY(-0.35)),
                             (LX(0.60 * sx), LY(-0.48)),
                             (LX(0.78 * sx), LY(-0.60)), step=2 * S),
                  INK_JIAO, 2.6 * detail, alpha=0.8, profile='nail', fly=0.3)

    # ---- 环眼（怒目三要素：上睑压线 / 瞳上留白高光 / 眉内端下压）----
    for sx in (-1, 1):
        ex, ey = LX(0.35 * sx), LY(-0.02)
        erx, ery = 0.295 * rx, 0.150 * ry
        # 眼白（挖白，纸色）
        br.carve_ellipse(ex, ey, erx / S, ery / S, alpha=0.92, edge=0.10)
        # 瞳：大而圆，位置贴睑（瞪视），虹膜+瞳孔双层
        px_, py_ = ex + 0.02 * rx * sx, ey - 0.10 * ery
        ir = 0.52 * erx
        br.dab(px_, py_, ir, INK_NONG, 0.80, edge_amp=0.08)
        br.dab(px_, py_, ir * 0.72, INK_JIAO, 0.95, edge_amp=0.05)
        # 高光留白
        br.dab(px_ - 0.28 * ir, py_ - 0.30 * ir, max(1.0, 0.20 * ir),
               PAPER, 0.95, edge_amp=0.0, carve=True)
        # 上睑重线（压住眼白上缘，怒目关键）
        lid = bezier_pts((ex - 1.08 * erx, ey + 0.05 * ery),
                         (ex - 0.45 * erx, ey - 0.62 * ery),
                         (ex + 0.45 * erx, ey - 0.66 * ery),
                         (ex + 1.08 * erx, ey - 0.02 * ery), step=1.6 * S)
        br.stroke(lid, INK_JIAO, 4.2 * detail, alpha=0.92, profile='orchid')
        # 下睑淡线
        br.stroke(arc_pts(ex, ey + 0.10 * ery, erx * 0.95, ery * 0.85,
                          0.30, math.pi - 0.30),
                  INK_ZHONG, 1.4 * detail, alpha=0.45)
        # 内眼角钩（近鼻侧）
        br.dab(ex - sx * 0.98 * erx, ey + 0.10 * ery, 1.4 * S * detail,
               INK_JIAO, 0.7, edge_amp=0.2)

    # ---- 鼻 ----
    br.stroke(bezier_pts((LX(0.0), LY(-0.16)), (LX(-0.02), LY(0.10)),
                         (LX(0.01), LY(0.32)), (LX(0.0), LY(0.40)), step=2 * S),
              INK_ZHONG, 2.0 * detail, alpha=0.55)
    for sx in (-1, 1):  # 鼻翼
        br.stroke(arc_pts(LX(0.13 * sx), LY(0.38), 0.10 * rx, 0.07 * ry,
                          math.pi * 0.9 if sx < 0 else math.pi * 1.6,
                          math.pi * 1.6 if sx < 0 else math.pi * 2.1),
                  INK_ZHONG, 1.8 * detail, alpha=0.55)
        br.dab(LX(0.085 * sx), LY(0.42), 1.6 * S * detail, INK_JIAO, 0.85,
               edge_amp=0.15)

    # ---- 口（紧抿下撇，没入髯）----
    br.stroke(bezier_pts((LX(-0.20), LY(0.54)), (LX(-0.06), LY(0.57)),
                         (LX(0.06), LY(0.57)), (LX(0.20), LY(0.54)), step=2 * S),
              INK_JIAO, 2.2 * detail, alpha=0.8, dry=0.3)
    # 法令纹
    for sx in (-1, 1):
        br.stroke(bezier_pts((LX(0.16 * sx), LY(0.42)), (LX(0.24 * sx), LY(0.52)),
                             (LX(0.26 * sx), LY(0.60)), (LX(0.24 * sx), LY(0.66)),
                             step=2 * S),
                  INK_ZHONG, 1.5 * detail, alpha=0.40, profile='nail')


def draw_mustache(br, cx, cy, rx, ry, len_f=1.0, detail=1.0):
    """虬髯之上髭（八字浓须，末梢上卷）。"""
    S = br.S
    rng = br.rng
    for sx in (-1, 1):
        for k in range(4):
            t = k / 3.0
            y0 = cy + ry * (0.36 + 0.06 * t)
            spread = (0.72 + 0.28 * t) * rx
            pts = bezier_pts(
                (cx + 0.05 * rx * sx, y0),
                (cx + sx * 0.35 * rx, y0 + 0.10 * ry),
                (cx + sx * spread * 0.9, y0 + (0.30 + 0.16 * t) * ry * len_f),
                (cx + sx * spread, y0 + (0.42 + 0.22 * t) * ry * len_f),
                step=2.2 * S)
            br.stroke(pts, INK_NONG if k < 3 else INK_ZHONG,
                      (3.6 - 0.5 * t) * detail, alpha=0.75,
                      profile='nail', dry=0.45, fly=0.30)
            # 末梢上卷小钩
            ex, ey_ = pts[-1]
            curl = arc_pts(ex, ey_ - 0.05 * ry, 0.055 * rx, 0.045 * ry,
                           math.pi * 0.5, math.pi * (1.9 if sx > 0 else 1.1),
                           step=1.8 * S)
            br.stroke(curl, INK_NONG, 2.2 * detail, alpha=0.7, profile='nail')


def draw_beard(br, cx, face_cy, rx, ry, spread, y_end, density=1.0,
               detail=1.0, curl=1.0):
    """虬髯主体：沿下颌弧线扎根，淡墨打底 + 浓墨长 S 主绺 + 焦墨根簇 + 边缘卷弧。"""
    S = br.S
    rng = br.rng
    chin_y = face_cy + 0.72 * ry
    depth = y_end - chin_y

    def root_at(t):
        """t∈[0,1] 沿下颌弧线（左鬓→下巴→右鬓）取根点。"""
        a = math.pi * (0.12 + 0.76 * t)          # 下颌弧（局部椭圆角）
        return (cx + math.cos(a) * 0.95 * rx,
                face_cy + math.sin(a) * 0.98 * ry)

    def flow(t, len_lo, len_hi):
        x0, y0 = root_at(t)
        x0 += rng.uniform(-0.05, 0.05) * rx
        to_side = (t * 2 - 1)                     # -1 左 … +1 右
        ex = cx + to_side * spread * rng.uniform(0.70, 1.05)
        ey = y0 + depth * rng.uniform(len_lo, len_hi)
        bow = to_side * spread * 0.30 * rng.uniform(0.5, 1.0)
        pts = bezier_pts(
            (x0, y0),
            (x0 + bow * 0.3, y0 + depth * 0.28),
            (ex - bow * 0.5, y0 + depth * 0.60),
            (ex, ey), step=2.4 * S)
        return pts, ex, ey, to_side

    # 1) 淡墨底卷（长而稀）
    for _ in range(int(22 * density)):
        pts, ex, ey, sd = flow(rng.random(), 0.80, 1.02)
        br.stroke(pts, INK_DAN, 4.2 * detail, alpha=0.30,
                  profile='nail', dry=0.25, fly=0.10)
    # 2) 浓墨主绺（钉头鼠尾 + 枯梢飞白，长短错落）
    for _ in range(int(42 * density)):
        pts, ex, ey, sd = flow(rng.random(), 0.55, 1.0)
        br.stroke(pts, INK_NONG, 3.2 * detail, alpha=0.72,
                  profile='nail', dry=0.60, fly=0.38)
    # 3) 焦墨近根重簇（短）
    for _ in range(int(9 * density)):
        pts, ex, ey, sd = flow(rng.uniform(0.2, 0.8), 0.30, 0.50)
        br.stroke(pts, INK_JIAO, 2.6 * detail, alpha=0.8, profile='nail')
    # 4) 边缘虬卷（小 C 弧，贴合外缘）
    for _ in range(int(20 * density * curl)):
        t = rng.random()
        sd = 1 if t > 0.5 else -1
        bx = cx + sd * spread * rng.uniform(0.68, 0.98)
        by = chin_y + depth * rng.uniform(0.25, 0.92)
        rr_ = rng.uniform(4, 9) * S * detail
        a0 = rng.uniform(0, math.pi)
        br.stroke(arc_pts(bx, by, rr_, rr_ * rng.uniform(0.7, 1.0),
                          a0, a0 + rng.uniform(2.2, 3.4), step=1.8 * S),
                  INK_NONG, 1.8 * detail, alpha=rng.uniform(0.35, 0.55),
                  profile='nail', dry=0.3)


def draw_hat(br, cx, sit_y, rx, wing_len, hat_h=None, detail=1.0):
    """乌纱帽：sit_y = 帽檐落在额头的 y。帽体焦墨，帽翅为细长实心椭圆、末端微翘。"""
    S = br.S
    hat_h = hat_h or 1.08 * rx
    cy_hat = sit_y - hat_h * 0.40          # 帽体中心（底缘压在 sit_y）
    # 帽体
    br.blob(cx, cy_hat, rx * 1.06 / S, hat_h * 0.52 / S,
            INK_JIAO, 0.90, edge=0.26, fill=0.14)
    # 顶部双角（幞头隆起）
    br.blob(cx - 0.48 * rx, cy_hat - hat_h * 0.42, 0.30 * rx / S,
            hat_h * 0.22 / S, INK_JIAO, 0.90, edge=0.28, fill=0.16)
    br.blob(cx + 0.48 * rx, cy_hat - hat_h * 0.42, 0.30 * rx / S,
            hat_h * 0.22 / S, INK_JIAO, 0.90, edge=0.28, fill=0.16)
    # 帽檐线（压在额头的一道重线，使帽子"戴"在头上）
    br.stroke([(cx - rx * 0.98, sit_y), (cx + rx * 0.98, sit_y)],
              INK_JIAO, 3.0 * detail, alpha=0.75, edge_amp=0.08)
    # 双帽翅（细长实心，微上翘）
    for sx in (-1, 1):
        wx0 = cx + sx * rx * 0.82
        wcx = wx0 + sx * wing_len * 0.5
        wcy = cy_hat + hat_h * 0.06
        br.blob(wcx, wcy, wing_len * 0.5 / S, 4.6 * detail,
                INK_JIAO, 0.90, rot=sx * -0.055, edge=0.18, fill=0.22)
        # 翅尖
        br.dab(wcx + sx * wing_len * 0.5, wcy - sx * wing_len * 0.028,
               3.4 * S * detail, INK_JIAO, 0.9, edge_amp=0.12)


# =====================================================================
# 7. 全身立像·持剑
# =====================================================================

def compose_full(cv, rng):
    br = Brush(cv, rng, Noise2D(rng, 160, 240))
    W, H = cv.w, cv.h

    def X(u): return u * W
    def Y(v): return v * H

    S = br.S
    head_cx, head_cy = X(0.500), Y(0.240)
    face_rx, face_ry = 0.078 * W, 0.066 * H

    # ---- 1. 背景淡晕（头肩背后）----
    br.blob(X(0.50), Y(0.22), 0.20 * W / S, 0.13 * H / S, INK_QING, 0.10,
            edge=0.55, bleed=26, fill=0.08)

    # ---- 2. 乌纱帽 + 帽翅 ----
    draw_hat(br, head_cx, head_cy - 0.72 * face_ry, face_rx * 1.18,
             0.205 * W, detail=0.85)

    # ---- 3. 面部 ----
    draw_face(br, head_cx, head_cy, face_rx, face_ry, detail=0.85)

    # ---- 4. 虬髯（垂至胸前）----
    draw_mustache(br, head_cx, head_cy, face_rx, face_ry, len_f=1.15, detail=0.85)
    draw_beard(br, head_cx, head_cy, face_rx, face_ry,
               spread=0.115 * W, y_end=Y(0.475), density=0.85, detail=0.85)

    # ---- 5. 袍服（圆领官袍，泼墨块面 + 积墨）----
    # 肩/胸大块
    br.blob(X(0.50), Y(0.42), 0.205 * W / S, 0.135 * H / S, INK_DAN, 0.32,
            edge=0.42, bleed=18, fill=0.10)
    br.blob(X(0.47), Y(0.47), 0.17 * W / S, 0.10 * H / S, INK_ZHONG, 0.42,
            edge=0.42, bleed=14, fill=0.11, rot=0.05)
    # 袍下身（裙摆梯形）
    br.blob(X(0.50), Y(0.66), 0.225 * W / S, 0.155 * H / S, INK_DAN, 0.34,
            edge=0.45, bleed=18, fill=0.10, rot=-0.02)
    br.blob(X(0.52), Y(0.72), 0.19 * W / S, 0.11 * H / S, INK_ZHONG, 0.38,
            edge=0.45, bleed=12, fill=0.11, rot=0.04)
    # 领口圆领
    br.stroke(arc_pts(head_cx, Y(0.318), 0.105 * W, 0.030 * H, 0.15, math.pi - 0.15),
              INK_ZHONG, 3.2, alpha=0.65)
    # 肩线轮廓（断笔写意）
    br.stroke(bezier_pts((X(0.295), Y(0.335)), (X(0.24), Y(0.40)),
                         (X(0.225), Y(0.48)), (X(0.245), Y(0.56)), step=2.4 * S),
              INK_ZHONG, 4.5, alpha=0.55, profile='orchid', dry=0.35, fly=0.15)
    br.stroke(bezier_pts((X(0.705), Y(0.335)), (X(0.76), Y(0.40)),
                         (X(0.775), Y(0.48)), (X(0.755), Y(0.56)), step=2.4 * S),
              INK_ZHONG, 4.5, alpha=0.55, profile='orchid', dry=0.35, fly=0.15)
    # 袍侧轮廓至摆
    br.stroke(bezier_pts((X(0.245), Y(0.55)), (X(0.225), Y(0.65)),
                         (X(0.215), Y(0.76)), (X(0.235), Y(0.845)), step=2.4 * S),
              INK_ZHONG, 5, alpha=0.55, profile='orchid', dry=0.4, fly=0.18)
    br.stroke(bezier_pts((X(0.755), Y(0.55)), (X(0.775), Y(0.65)),
                         (X(0.785), Y(0.76)), (X(0.765), Y(0.845)), step=2.4 * S),
              INK_ZHONG, 5, alpha=0.55, profile='orchid', dry=0.4, fly=0.18)

    # ---- 6. 袍褶（兰叶描，自腰带放射）----
    for k in range(11):
        t = k / 10.0
        x0 = X(0.36 + 0.28 * t)
        x1 = X(0.28 + 0.44 * t) + rng.uniform(-0.02, 0.02) * W
        pts = bezier_pts((x0, Y(0.49)),
                         (x0 + (x1 - x0) * 0.2, Y(0.58)),
                         (x1 - (x1 - x0) * 0.15, Y(0.72)),
                         (x1, Y(0.83) + rng.uniform(-0.008, 0.008) * H),
                         step=2.6 * S)
        br.stroke(pts, INK_ZHONG if k % 3 else INK_NONG, 4.2,
                  alpha=0.42 if k % 3 else 0.55, profile='orchid',
                  dry=0.30, fly=0.12)

    # ---- 7. 袍摆底边（枯笔横扫）----
    br.stroke(bezier_pts((X(0.24), Y(0.848)), (X(0.38), Y(0.862)),
                         (X(0.62), Y(0.862)), (X(0.76), Y(0.848)), step=2.6 * S),
              INK_NONG, 5.5, alpha=0.7, profile='iron', dry=0.55, fly=0.5)

    # ---- 8. 玉带 ----
    belt_y = Y(0.472)
    br.stroke([(X(0.335), belt_y), (X(0.665), belt_y)],
              INK_ZHONG, 16, alpha=0.55, edge_amp=0.12)
    for k in range(6):  # 带銙六方
        bx = X(0.365 + 0.054 * k)
        bw = 0.036 * W; bh = 0.016 * H
        br.carve_ellipse(bx, belt_y, bw / S, bh / S, alpha=0.85, edge=0.05)
        for pts in ([(bx - bw, belt_y - bh), (bx + bw, belt_y - bh)],
                    [(bx - bw, belt_y + bh), (bx + bw, belt_y + bh)],
                    [(bx - bw, belt_y - bh), (bx - bw, belt_y + bh)],
                    [(bx + bw, belt_y - bh), (bx + bw, belt_y + bh)]):
            br.polyline(pts, INK_JIAO, 1.6 * S, 0.8, edge_amp=0.05)

    # ---- 9. 左臂按带 ----
    br.blob(X(0.315), Y(0.415), 0.055 * W / S, 0.075 * H / S, INK_ZHONG, 0.45,
            edge=0.4, fill=0.12, rot=0.35)
    # 左手（简笔拳）
    br.dab(X(0.365), Y(0.487), 9 * S, INK_DAN, 0.5, edge_amp=0.2)
    for f in range(3):
        br.dab(X(0.358 + 0.009 * f), Y(0.481), 2.2 * S, INK_JIAO, 0.6,
               edge_amp=0.2)

    # ---- 10. 右臂举剑 ----
    # 宽袖
    br.blob(X(0.71), Y(0.385), 0.075 * W / S, 0.055 * H / S, INK_ZHONG, 0.5,
            edge=0.42, fill=0.12, rot=-0.5)
    br.stroke(bezier_pts((X(0.66), Y(0.34)), (X(0.735), Y(0.36)),
                         (X(0.75), Y(0.42)), (X(0.715), Y(0.45)), step=2.4 * S),
              INK_ZHONG, 5, alpha=0.6, profile='orchid', fly=0.2, dry=0.3)
    # 袖口
    br.stroke(arc_pts(X(0.70), Y(0.30), 0.030 * W, 0.022 * H,
                      math.pi * 0.7, math.pi * 1.9),
              INK_ZHONG, 4, alpha=0.6, fly=0.2)
    # 手
    br.dab(X(0.705), Y(0.295), 7.5 * S, INK_DAN, 0.6, edge_amp=0.15)

    # ---- 11. 宝剑（双勾留白，剑穗）----
    hilt = (X(0.705), Y(0.285))
    tip = (X(0.872), Y(0.062))
    dx = tip[0] - hilt[0]; dy = tip[1] - hilt[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    bw = 5.2 * S  # 剑身半宽
    # 剑身双勾
    br.stroke([(hilt[0] + nx * bw + ux * 26 * S, hilt[1] + ny * bw + uy * 26 * S),
               (tip[0] + nx * bw * 0.3, tip[1] + ny * bw * 0.3)],
              INK_ZHONG, 2.4, alpha=0.85, profile='iron', edge_amp=0.05)
    br.stroke([(hilt[0] - nx * bw + ux * 26 * S, hilt[1] - ny * bw + uy * 26 * S),
               (tip[0] - nx * bw * 0.3, tip[1] - ny * bw * 0.3)],
              INK_ZHONG, 2.4, alpha=0.85, profile='iron', edge_amp=0.05)
    # 脊线
    br.stroke([(hilt[0] + ux * 30 * S, hilt[1] + uy * 30 * S),
               (tip[0], tip[1])], INK_NONG, 1.2, alpha=0.6, edge_amp=0.04)
    # 剑尖收锋
    br.stroke([(tip[0] + nx * bw * 0.3, tip[1] + ny * bw * 0.3),
               (tip[0] - ux * 8 * S, tip[1] - uy * 8 * S)],
              INK_ZHONG, 2.0, alpha=0.85, edge_amp=0.05)
    br.stroke([(tip[0] - nx * bw * 0.3, tip[1] - ny * bw * 0.3),
               (tip[0] - ux * 8 * S, tip[1] - uy * 8 * S)],
              INK_ZHONG, 2.0, alpha=0.85, edge_amp=0.05)
    # 剑格（横）
    gp = (hilt[0] + ux * 22 * S, hilt[1] + uy * 22 * S)
    br.stroke([(gp[0] + nx * 13 * S, gp[1] + ny * 13 * S),
               (gp[0] - nx * 13 * S, gp[1] - ny * 13 * S)],
              INK_JIAO, 4.5, alpha=0.9, edge_amp=0.08)
    # 柄
    br.stroke([(hilt[0] - ux * 4 * S, hilt[1] - uy * 4 * S),
               (hilt[0] - ux * 20 * S, hilt[1] - uy * 20 * S)],
              INK_JIAO, 5, alpha=0.9, edge_amp=0.08)
    br.dab((hilt[0] - ux * 23 * S), (hilt[1] - uy * 23 * S), 4 * S,
           INK_JIAO, 0.9, edge_amp=0.1)
    # 剑穗（两条飘带）
    for k in range(2):
        sx = 1 if k == 0 else -1
        br.stroke(bezier_pts(gp,
                             (gp[0] + sx * 20 * S, gp[1] + 26 * S),
                             (gp[0] + sx * 34 * S, gp[1] + 52 * S),
                             (gp[0] + sx * 26 * S, gp[1] + 78 * S), step=2 * S),
                  INK_NONG, 2.0, alpha=0.65, profile='nail', fly=0.3, dry=0.3)

    # ---- 12. 皂靴（翘头）----
    for sx, cx0 in ((-1, X(0.415)), (1, X(0.585))):
        br.blob(cx0, Y(0.885), 0.042 * W / S, 0.026 * H / S, INK_JIAO, 0.85,
                edge=0.25, fill=0.16)
        # 翘头
        br.stroke(arc_pts(cx0 + sx * 0.036 * W, Y(0.878), 0.016 * W, 0.014 * H,
                          math.pi * (1.15 if sx > 0 else 1.55),
                          math.pi * (1.85 if sx > 0 else 2.15)),
                  INK_JIAO, 5, alpha=0.9, edge_amp=0.1)
        # 靴底白线
        br.stroke([(cx0 - 0.038 * W, Y(0.912)), (cx0 + 0.038 * W, Y(0.912))],
                  PAPER, 2.2, alpha=0.85, edge_amp=0.05)

    # ---- 13. 地影（枯扫）----
    br.stroke(bezier_pts((X(0.30), Y(0.928)), (X(0.45), Y(0.936)),
                         (X(0.60), Y(0.932)), (X(0.72), Y(0.924)), step=3 * S),
              INK_QING, 9, alpha=0.16, profile='dry', dry=0.5, fly=0.55)

    # ---- 14. 蝙蝠（福）----
    bat_cx, bat_cy = X(0.185), Y(0.128)
    draw_bat(br, bat_cx, bat_cy, 0.052 * W, tilt=-0.28)

    # ---- 15. 题款 + 印章 ----
    inscription(br, X(0.895), Y(0.545), 0.042 * H, (GLYPH_ZHONG, GLYPH_KUI))
    seal(br, X(0.888), Y(0.700), 0.052 * W)


def draw_bat(br, cx, cy, span, tilt=0.0):
    """写意蝙蝠：身 + 双翼 scallop 剪影。"""
    S = br.S
    cr, sr = math.cos(tilt), math.sin(tilt)

    def T(x, y):
        return (cx + x * cr - y * sr, cy + x * sr + y * cr)

    # 身
    bx, by = T(0, 0)
    br.dab(bx, by, span * 0.16, INK_NONG, 0.85, edge_amp=0.25)
    hx, hy = T(0, -span * 0.20)
    br.dab(hx, hy, span * 0.10, INK_NONG, 0.85, edge_amp=0.25)
    for sx in (-1, 1):  # 耳
        ex, ey = T(sx * span * 0.06, -span * 0.30)
        br.dab(ex, ey, span * 0.045, INK_NONG, 0.85, edge_amp=0.2)
    # 双翼：每翼两段上凸弧 + 三段下凹 scallop
    for sx in (-1, 1):
        wing = []
        # 上缘
        wing += bezier_pts(T(sx * span * 0.10, -span * 0.10),
                           T(sx * span * 0.55, -span * 0.55),
                           T(sx * span * 1.00, -span * 0.35),
                           T(sx * span * 1.10, -span * 0.02), step=2 * S)
        # 下缘 scallop（三个凹弧）
        for k in range(3):
            t0 = k / 3.0
            x0 = sx * span * (1.10 - 0.34 * k)
            y0 = -span * 0.02 + span * 0.06 * k
            x1 = sx * span * (1.10 - 0.34 * (k + 1))
            y1 = -span * 0.02 + span * 0.06 * (k + 1)
            cxm = (x0 + x1) / 2
            wing += bezier_pts(T(x0, y0), T(cxm, y0 + span * 0.16),
                               T(cxm, y1 + span * 0.16), T(x1, y1), step=2 * S)[1:]
        # 翼膜：沿上缘 dab 填充
        for (px_, py_) in wing:
            br.dab(px_, py_, span * 0.13, INK_NONG, 0.55, edge_amp=0.3)
        br.stroke(wing, INK_NONG, 2.0, alpha=0.8, edge_amp=0.2)


# =====================================================================
# 8. 半身怒目特写
# =====================================================================

def compose_bust(cv, rng):
    br = Brush(cv, rng, Noise2D(rng, 160, 240))
    W, H = cv.w, cv.h

    def X(u): return u * W
    def Y(v): return v * H

    S = br.S
    head_cx, head_cy = X(0.500), Y(0.335)
    face_rx, face_ry = 0.170 * W, 0.145 * H

    # ---- 1. 乌纱帽（帽翅裁出画外）----
    draw_hat(br, head_cx, head_cy - 0.72 * face_ry, face_rx * 1.10,
             0.62 * W, detail=1.6)

    # ---- 2. 面部（视觉锚点）----
    draw_face(br, head_cx, head_cy, face_rx, face_ry, detail=1.6)

    # ---- 3. 虬髯（画面主体，垂出画底）----
    draw_mustache(br, head_cx, head_cy, face_rx, face_ry, len_f=1.3, detail=1.6)
    draw_beard(br, head_cx, head_cy, face_rx, face_ry,
               spread=0.345 * W, y_end=Y(1.05), density=1.5, detail=1.6)

    # ---- 4. 肩部暗示（两条大弧出画）----
    br.stroke(bezier_pts((X(-0.04), Y(0.99)), (X(0.16), Y(0.90)),
                         (X(0.30), Y(0.88)), (X(0.36), Y(0.895)), step=3 * S),
              INK_DAN, 10, alpha=0.28, profile='orchid', dry=0.3, fly=0.2)
    br.stroke(bezier_pts((X(1.04), Y(0.99)), (X(0.84), Y(0.90)),
                         (X(0.70), Y(0.88)), (X(0.64), Y(0.895)), step=3 * S),
              INK_DAN, 10, alpha=0.28, profile='orchid', dry=0.3, fly=0.2)

    # ---- 5. 右上破白一笔 ----
    br.stroke(bezier_pts((X(0.80), Y(0.10)), (X(0.87), Y(0.07)),
                         (X(0.93), Y(0.06)), (X(0.99), Y(0.058)), step=3 * S),
              INK_QING, 8, alpha=0.12, profile='dry', dry=0.5, fly=0.5)

    # ---- 6. 题款 + 印章（左侧）----
    inscription(br, X(0.048), Y(0.290), 0.046 * H, (GLYPH_ZHONG, GLYPH_KUI))
    seal(br, X(0.043), Y(0.505), 0.056 * W)


# =====================================================================
# 9. 笔刷测试页
# =====================================================================

def compose_test(cv, rng):
    br = Brush(cv, rng, Noise2D(rng, 160, 240))
    W, H = cv.w, cv.h

    def X(u): return u * W
    def Y(v): return v * H

    # 五色墨条
    inks = [('焦', INK_JIAO, A_JIAO), ('浓', INK_NONG, A_NONG),
            ('重', INK_ZHONG, A_ZHONG), ('淡', INK_DAN, A_DAN),
            ('清', INK_QING, A_QING)]
    for i, (name, ink, al) in enumerate(inks):
        y = Y(0.06 + 0.05 * i)
        br.stroke(bezier_pts((X(0.08), y), (X(0.3), y - 8),
                             (X(0.5), y + 8), (X(0.7), y), step=2 * br.S),
                  ink, 12, alpha=al, profile='orchid', fly=0.1)
        draw_glyph(br, GLYPH_ZHONG if i % 2 == 0 else GLYPH_KUI,
                   X(0.74), y - 18, 36, ink, al)

    # 四种描法
    profs = ['iron', 'nail', 'orchid', 'dry']
    for i, pf in enumerate(profs):
        y = Y(0.36 + 0.055 * i)
        br.stroke(bezier_pts((X(0.08), y), (X(0.35), y - 30 * br.S),
                             (X(0.6), y + 30 * br.S), (X(0.85), y), step=2 * br.S),
                  INK_NONG, 10, alpha=0.75, profile=pf,
                  dry=0.6 if pf == 'dry' else 0.2,
                  fly=0.55 if pf == 'dry' else 0.25)

    # 晕染 vs 无晕染
    y = Y(0.62)
    br.stroke(bezier_pts((X(0.08), y), (X(0.2), y - 20 * br.S),
                         (X(0.35), y + 10 * br.S), (X(0.45), y), step=2 * br.S),
              INK_ZHONG, 10, alpha=0.6, bleed=10, profile='orchid')
    br.stroke(bezier_pts((X(0.55), y), (X(0.65), y - 20 * br.S),
                         (X(0.8), y + 10 * br.S), (X(0.9), y), step=2 * br.S),
              INK_ZHONG, 10, alpha=0.6, bleed=0, profile='orchid')

    # 泼墨块
    br.blob(X(0.2), Y(0.76), 0.10 * W / br.S, 0.06 * H / br.S,
            INK_ZHONG, 0.5, edge=0.4, bleed=12)
    br.blob(X(0.5), Y(0.76), 0.10 * W / br.S, 0.06 * H / br.S,
            INK_DAN, 0.4, edge=0.4, bleed=16, rot=0.3)
    # 蝙蝠
    draw_bat(br, X(0.8), Y(0.76), 0.05 * W, tilt=-0.2)

    # 印章 + 题款
    seal(br, X(0.12), Y(0.86), 0.075 * W)
    inscription(br, X(0.30), Y(0.855), 0.040 * H, (GLYPH_ZHONG, GLYPH_KUI))


# =====================================================================
# 10. 入口
# =====================================================================

def render(kind, w, h, seed, out_dir, suffix=''):
    cv = Canvas(w, h)
    kind_off = {'full': 101, 'bust': 202, 'test': 303}[kind]  # 固定偏移，保证可复现
    rng = random.Random(seed + kind_off)
    make_paper(cv, rng)
    if kind == 'full':
        compose_full(cv, rng)
    elif kind == 'bust':
        compose_bust(cv, rng)
    else:
        compose_test(cv, rng)
    path = os.path.join(out_dir, 'zhongkui_%s%s.png' % (kind, suffix))
    cv.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description='钟馗水墨画生成器（纯 Python 零依赖）')
    ap.add_argument('--seed', type=int, default=20261006, help='随机种子')
    ap.add_argument('--draft', action='store_true', help='512×768 快速预览')
    ap.add_argument('--only', choices=['full', 'bust'], help='只渲染一张')
    ap.add_argument('--test', action='store_true', help='笔刷/印章测试页')
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)),
                    help='输出目录（默认脚本所在目录）')
    a = ap.parse_args()

    W, H = (512, 768) if a.draft else (1024, 1536)
    suffix = '_draft' if a.draft else ''
    os.makedirs(a.out, exist_ok=True)

    import time
    if a.test:
        t0 = time.time()
        p = render('test', W, H, a.seed, a.out, suffix)
        print('测试页 → %s (%.1fs)' % (p, time.time() - t0))
        return
    kinds = [a.only] if a.only else ['full', 'bust']
    for k in kinds:
        t0 = time.time()
        p = render(k, W, H, a.seed, a.out, suffix)
        print('%s → %s (%.1fs)' % (k, p, time.time() - t0))


if __name__ == '__main__':
    main()
