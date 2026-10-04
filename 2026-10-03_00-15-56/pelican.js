/* 鹈鹕骑自行车 —— 动画与交互逻辑 */
(function () {
  'use strict';

  var S = function (id) { return document.getElementById(id); };
  var svg = S('scene');
  var NS = 'http://www.w3.org/2000/svg';

  function el(name, attrs, parent) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    parent.appendChild(n);
    return n;
  }

  /* ---------- 几何常量 ---------- */
  var BB = { x: 452, y: 480 };   // 五通（曲柄中心）
  var CR = 45;                   // 曲柄长度
  var WR = 90;                   // 车轮半径
  var LEG_N = { a: 103, b: 105, hip: { x: 396, y: 336 } }; // 近侧腿
  var LEG_F = { a: 101, b: 103, hip: { x: 384, y: 334 } }; // 远侧腿

  /* ---------- 车轮 ---------- */
  function buildWheel(parent, cx, cy) {
    var g = el('g', { transform: 'translate(' + cx + ',' + cy + ')' }, parent);
    el('circle', { r: 90, fill: 'none', stroke: '#2f3640', 'stroke-width': 13 }, g);
    el('circle', { r: 90, fill: 'none', stroke: '#4a525c', 'stroke-width': 3 }, g);
    el('circle', { r: 77, fill: 'none', stroke: '#cfd8e3', 'stroke-width': 5 }, g);
    var spokes = el('g', {}, g);
    for (var i = 0; i < 10; i++) {
      var a = i * Math.PI / 5;
      el('line', {
        x1: (Math.cos(a) * 10).toFixed(1), y1: (Math.sin(a) * 10).toFixed(1),
        x2: (Math.cos(a) * 75).toFixed(1), y2: (Math.sin(a) * 75).toFixed(1),
        stroke: '#aab6c2', 'stroke-width': 2.5
      }, spokes);
    }
    el('rect', { x: 62, y: -2, width: 12, height: 4, rx: 2, fill: '#c0392b', transform: 'rotate(25)' }, spokes);
    el('circle', { r: 9, fill: '#3a3f44' }, g);
    el('circle', { r: 4, fill: '#cfd8e3' }, g);
    return spokes;
  }
  var rearSpokes = buildWheel(S('wheelRearG'), 300, 470);
  var frontSpokes = buildWheel(S('wheelFrontG'), 665, 470);

  /* ---------- 太阳光芒 ---------- */
  var sunRays = S('sunRays');
  for (var r = 0; r < 12; r++) {
    var ra = r * Math.PI / 6;
    el('line', {
      x1: (858 + Math.cos(ra) * 44).toFixed(1), y1: (92 + Math.sin(ra) * 44).toFixed(1),
      x2: (858 + Math.cos(ra) * 62).toFixed(1), y2: (92 + Math.sin(ra) * 62).toFixed(1),
      stroke: '#ffd94d', 'stroke-width': 4, 'stroke-linecap': 'round'
    }, sunRays);
  }

  /* ---------- 星星 ---------- */
  var starsG = S('stars');
  for (var s = 0; s < 28; s++) {
    var c = el('circle', {
      cx: (Math.random() * 1000).toFixed(0), cy: (Math.random() * 250).toFixed(0),
      r: (0.9 + Math.random() * 1.5).toFixed(1), fill: '#fff'
    }, starsG);
    if (s % 5 === 0) c.setAttribute('class', 'tw');
  }

  /* ---------- 云 ---------- */
  var clouds = [];
  var cloudsG = S('clouds');
  for (var ci = 0; ci < 6; ci++) {
    var cg = el('g', {}, cloudsG);
    var cs = 0.55 + Math.random() * 0.9;
    el('ellipse', { cx: 0, cy: 0, rx: (55 * cs).toFixed(0), ry: (24 * cs).toFixed(0), 'class': 'cloud' }, cg);
    el('ellipse', { cx: (-40 * cs).toFixed(0), cy: (9 * cs).toFixed(0), rx: (34 * cs).toFixed(0), ry: (16 * cs).toFixed(0), 'class': 'cloud' }, cg);
    el('ellipse', { cx: (43 * cs).toFixed(0), cy: (10 * cs).toFixed(0), rx: (37 * cs).toFixed(0), ry: (15 * cs).toFixed(0), 'class': 'cloud' }, cg);
    clouds.push({ g: cg, x: Math.random() * 1250, y: 40 + Math.random() * 155 });
  }

  /* ---------- 路边植被 ---------- */
  var bushes = [];
  var bushesG = S('bushes');
  function addScenery(kind, x) {
    var g = el('g', {}, bushesG);
    if (kind === 'tree') {
      el('rect', { x: -4, y: -42, width: 8, height: 42, rx: 3, fill: '#7a5b3a' }, g);
      el('circle', { cx: 0, cy: -56, r: 30, fill: '#57a85c' }, g);
      el('circle', { cx: -20, cy: -44, r: 20, fill: '#4c9a52' }, g);
      el('circle', { cx: 20, cy: -45, r: 21, fill: '#63b168' }, g);
    } else if (kind === 'bush') {
      el('ellipse', { cx: 0, cy: 0, rx: 30, ry: 16, fill: '#5fae64' }, g);
      el('ellipse', { cx: -22, cy: 5, rx: 18, ry: 11, fill: '#549f59' }, g);
      el('circle', { cx: -8, cy: -4, r: 2.5, fill: '#e05c6a' }, g);
      el('circle', { cx: 10, cy: 2, r: 2.5, fill: '#e05c6a' }, g);
    } else {
      el('line', { x1: 0, y1: 0, x2: 0, y2: -12, stroke: '#4c9a52', 'stroke-width': 2 }, g);
      el('circle', { cx: 0, cy: -15, r: 4, fill: '#fff' }, g);
      el('circle', { cx: -4.5, cy: -13, r: 3, fill: '#fff' }, g);
      el('circle', { cx: 4.5, cy: -13, r: 3, fill: '#fff' }, g);
      el('circle', { cx: 0, cy: -14, r: 2, fill: '#ffd94d' }, g);
    }
    var y = kind === 'tree' ? 546 : (kind === 'bush' ? 541 : 551);
    var sc = 0.7 + Math.random() * 0.5;
    g.setAttribute('transform', 'translate(' + x.toFixed(1) + ',' + y + ') scale(' + sc.toFixed(2) + ')');
    bushes.push({ g: g, x: x, y: y, s: sc });
  }
  var kinds = ['tree', 'bush', 'flower', 'tree', 'flower', 'bush', 'tree', 'flower', 'bush'];
  for (var bi = 0; bi < 18; bi++) {
    addScenery(kinds[bi % kinds.length], 30 + bi * 69 + Math.random() * 40);
  }

  /* ---------- 腿部两段式反向运动学 ---------- */
  function legIK(hip, foot, a, b) {
    var dx = foot.x - hip.x, dy = foot.y - hip.y;
    var d = Math.hypot(dx, dy);
    if (d < 0.001) { dx = 1; dy = 0; d = 1; }
    var dMax = a + b - 2, dMin = Math.abs(a - b) + 2;
    var dc = Math.max(dMin, Math.min(dMax, d));
    var fx = hip.x + dx / d * dc, fy = hip.y + dy / d * dc;
    var ang = Math.atan2(fy - hip.y, fx - hip.x);
    var cosA = (dc * dc + a * a - b * b) / (2 * dc * a);
    cosA = Math.max(-1, Math.min(1, cosA));
    var kAng = ang - Math.acos(cosA); // 膝盖朝前
    return { kx: hip.x + a * Math.cos(kAng), ky: hip.y + a * Math.sin(kAng), fx: fx, fy: fy };
  }

  /* ---------- 状态 ---------- */
  var speed = 1;
  var pedalA = -0.9;
  var roadOff = 0, hillFarOff = 0, hillNearOff = 0, raysA = 0, tSec = 0;
  var last = performance.now();
  var lastRing = -10;

  var bodyBobG = S('bodyBobG'), headBobG = S('headBobG'), bikeG = S('bikeG');
  var nearLeg = S('nearLeg'), farLeg = S('farLeg');
  var nearFoot = S('nearFoot'), farFoot = S('farFoot');
  var nearCrank = S('nearCrank'), farCrank = S('farCrank');
  var nearPedal = S('nearPedal'), farPedal = S('farPedal');
  var roadDash = S('roadDash');
  var chainTop = S('chainTop'), chainBot = S('chainBot');
  var scarfTrail = S('scarfTrail');
  var fishG = S('fishG');
  var hillsFarG = S('hillsFarG'), hillsNearG = S('hillsNearG');
  var bubble = S('bubble'), bubbleText = S('bubbleText'), bellEl = S('bell');
  var speedLabel = S('speedLabel');

  function setSpeed(v) {
    speed = Math.max(0, Math.min(3, v));
    speedLabel.textContent = speed === 0 ? '×0 歇会' : '×' + speed.toFixed(2).replace(/\.?0+$/, '');
  }

  /* ---------- 主循环 ---------- */
  function frame(now) {
    var dt = Math.min((now - last) / 1000, 0.05);
    last = now; tSec += dt;

    var pedalOmega = (2 * Math.PI / 2.2) * speed;   // 踏频
    pedalA += pedalOmega * dt;
    var wheelA = pedalA * 2;                         // 脚踏一圈，车轮两圈
    var v = pedalOmega * 2 * WR;                     // 地面线速度

    roadOff = (roadOff + v * dt) % 120;
    hillFarOff = (hillFarOff + v * 0.22 * dt) % 1200;
    hillNearOff = (hillNearOff + v * 0.45 * dt) % 1200;
    raysA += dt * (0.12 + speed * 0.05);

    for (var i = 0; i < clouds.length; i++) {
      var c = clouds[i];
      c.x -= (v * 0.12 + 7) * dt;
      if (c.x < -260) { c.x = 1260; c.y = 40 + Math.random() * 155; }
      c.g.setAttribute('transform', 'translate(' + c.x.toFixed(1) + ',' + c.y.toFixed(1) + ')');
    }
    for (var j = 0; j < bushes.length; j++) {
      var b = bushes[j];
      b.x -= v * 0.6 * dt;
      if (b.x < -160) b.x += 1310;
      b.g.setAttribute('transform', 'translate(' + b.x.toFixed(1) + ',' + b.y + ') scale(' + b.s.toFixed(2) + ')');
    }
    hillsFarG.setAttribute('transform', 'translate(' + (-hillFarOff).toFixed(1) + ',0)');
    hillsNearG.setAttribute('transform', 'translate(' + (-hillNearOff).toFixed(1) + ',0)');
    roadDash.setAttribute('stroke-dashoffset', roadOff.toFixed(1));

    var wd = (wheelA * 180 / Math.PI) % 360;
    rearSpokes.setAttribute('transform', 'rotate(' + wd.toFixed(1) + ')');
    frontSpokes.setAttribute('transform', 'rotate(' + wd.toFixed(1) + ')');
    var co = ((wheelA * 11) % 7 + 7) % 7;
    chainTop.setAttribute('stroke-dashoffset', co.toFixed(2));
    chainBot.setAttribute('stroke-dashoffset', co.toFixed(2));

    /* 曲柄与踏板 */
    var p1 = { x: BB.x + Math.cos(pedalA) * CR, y: BB.y + Math.sin(pedalA) * CR };
    var p2 = { x: BB.x - Math.cos(pedalA) * CR, y: BB.y - Math.sin(pedalA) * CR };
    nearCrank.setAttribute('x2', p1.x.toFixed(1)); nearCrank.setAttribute('y2', p1.y.toFixed(1));
    farCrank.setAttribute('x2', p2.x.toFixed(1)); farCrank.setAttribute('y2', p2.y.toFixed(1));
    nearPedal.setAttribute('x', (p1.x - 13).toFixed(1)); nearPedal.setAttribute('y', (p1.y - 4.5).toFixed(1));
    farPedal.setAttribute('x', (p2.x - 12).toFixed(1)); farPedal.setAttribute('y', (p2.y - 4).toFixed(1));

    /* 上下起伏 */
    var energy = Math.min(1, speed + 0.2);
    var bob = Math.sin(pedalA * 2) * 3 * energy;
    var nodT = tSec - lastRing;
    var nod = nodT < 0.35 ? Math.sin(nodT / 0.35 * Math.PI) * 7 : 0;
    bodyBobG.setAttribute('transform', 'translate(0,' + bob.toFixed(2) + ')');
    headBobG.setAttribute('transform', 'translate(0,' + (Math.sin(pedalA * 2 + 0.9) * 2.2 * energy + nod).toFixed(2) + ')');
    bikeG.setAttribute('transform', 'translate(0,' + (Math.sin(pedalA * 2 + 0.5) * 1.7 * energy).toFixed(2) + ')');

    /* 踩踏的双腿 */
    var ikN = legIK({ x: LEG_N.hip.x, y: LEG_N.hip.y + bob }, { x: p1.x, y: p1.y - 6 }, LEG_N.a, LEG_N.b);
    nearLeg.setAttribute('points',
      LEG_N.hip.x + ',' + (LEG_N.hip.y + bob).toFixed(1) + ' ' +
      ikN.kx.toFixed(1) + ',' + ikN.ky.toFixed(1) + ' ' +
      ikN.fx.toFixed(1) + ',' + ikN.fy.toFixed(1));
    nearFoot.setAttribute('transform', 'translate(' + ikN.fx.toFixed(1) + ',' + ikN.fy.toFixed(1) + ') rotate(6)');

    var ikF = legIK({ x: LEG_F.hip.x, y: LEG_F.hip.y + bob }, { x: p2.x, y: p2.y - 5 }, LEG_F.a, LEG_F.b);
    farLeg.setAttribute('points',
      LEG_F.hip.x + ',' + (LEG_F.hip.y + bob).toFixed(1) + ' ' +
      ikF.kx.toFixed(1) + ',' + ikF.ky.toFixed(1) + ' ' +
      ikF.fx.toFixed(1) + ',' + ikF.fy.toFixed(1));
    farFoot.setAttribute('transform', 'translate(' + ikF.fx.toFixed(1) + ',' + ikF.fy.toFixed(1) + ') rotate(10)');

    /* 飘动的围巾 */
    var amp = 2.5 + speed * 2, freq = 5 + speed * 2.5, pts = '';
    for (var k = 0; k <= 5; k++) {
      pts += (446 - 16 * k).toFixed(1) + ',' +
        (256 - 2 * k + Math.sin(tSec * freq - k * 0.85) * amp * (0.5 + k * 0.13)).toFixed(1) + ' ';
    }
    scarfTrail.setAttribute('points', pts.trim());

    /* 鱼尾摆动 & 太阳光芒旋转 */
    fishG.setAttribute('transform', 'translate(508,236) rotate(' + (Math.sin(tSec * 7) * 14).toFixed(1) + ')');
    sunRays.setAttribute('transform', 'rotate(' + (raysA * 57.3).toFixed(1) + ' 858 92)');

    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  /* ---------- 铃铛：音效 + 气泡 + 点头 ---------- */
  var MSGS = ['叮铃铃！', '让一让~', '冲鸭！', '咕咕咕~'];
  var audioCtx = null, bubbleTimer = null;

  function ding(t0, f, gain) {
    var o = audioCtx.createOscillator(), g = audioCtx.createGain();
    o.type = 'sine'; o.frequency.value = f;
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(gain, t0 + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.45);
    o.connect(g); g.connect(audioCtx.destination);
    o.start(t0); o.stop(t0 + 0.5);
  }

  function ringBell() {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume();
      var t0 = audioCtx.currentTime;
      ding(t0, 1568, 0.22); ding(t0 + 0.02, 2349, 0.12);
      ding(t0 + 0.14, 1568, 0.18); ding(t0 + 0.16, 2349, 0.1);
    } catch (e) { /* 无音频环境时静默 */ }

    lastRing = tSec;
    bubbleText.textContent = MSGS[(Math.random() * MSGS.length) | 0];
    bubble.classList.add('show');
    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(function () { bubble.classList.remove('show'); }, 950);

    bellEl.classList.remove('ring');
    void bellEl.getBoundingClientRect(); // 重置动画
    bellEl.classList.add('ring');
  }

  /* ---------- 昼夜切换 ---------- */
  var btnNight = S('btnNight');
  function toggleNight() {
    svg.classList.toggle('night');
    btnNight.textContent = svg.classList.contains('night') ? '☀️' : '🌙';
  }

  /* ---------- 事件绑定 ---------- */
  S('btnSlow').addEventListener('click', function () { setSpeed(speed - 0.25); });
  S('btnFast').addEventListener('click', function () { setSpeed(speed + 0.25); });
  S('btnBell').addEventListener('click', ringBell);
  btnNight.addEventListener('click', toggleNight);
  S('pelicanHit').addEventListener('click', ringBell);

  window.addEventListener('keydown', function (e) {
    if (e.code === 'ArrowUp') { e.preventDefault(); setSpeed(speed + 0.25); }
    else if (e.code === 'ArrowDown') { e.preventDefault(); setSpeed(speed - 0.25); }
    else if (e.code === 'Space') { e.preventDefault(); ringBell(); }
    else if (e.key === 'n' || e.key === 'N') { toggleNight(); }
  });
})();
