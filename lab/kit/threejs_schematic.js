/* threejs_schematic.js - Shared REVA Clay/CAD schematic engine & structural primitives. */
(function (global) {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";

  const PALETTE = {
    bg: 0xeef3f7,
    board: 0xe2e8f0,
    plate: 0xcbd5e1,
    pin: 0x1e293b,
    mainBar: 0x273244,
    ok: 0xe07a14,
    bad: 0xdc2626,
    coreMint: 0x6ee7b7,
    coverGrey: 0xcbd5e1,
    spall: 0x94a3b8,
    floor: 0xdbe3ea,
    beamA: 0x2563eb,
    beamB: 0xea580c,
    dowel: 0xd97706,
    brick: 0xc85a3a,
    brickAlt: 0xb64c2e,
    mortar: 0xdcd7cf,
    formwork: 0xe6c896,
    decking: 0xf8fafc,
    soil: 0x8d6748,
    soilDark: 0x6b4b32,
    rust: 0xb45309,
    stressHot: 0xef4444,
    stressWarn: 0xf59e0b,
    zoneSafe: 0x16a34a,
    coverBlue: 0x38bdf8,
    wire: 0x64748b,
  };

  function V(x, y, z) {
    return new THREE.Vector3(x, y, z);
  }

  function clay(hex, extra) {
    return new THREE.MeshLambertMaterial(Object.assign({ color: hex }, extra || {}));
  }

  function addMesh(parent, geo, mat, x = 0, y = 0, z = 0, shadow = true) {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    m.castShadow = shadow;
    m.receiveShadow = true;
    parent.add(m);
    return m;
  }

  function _ensureStyles() {
    if (document.getElementById("reva-cad-style")) return;
    const st = document.createElement("style");
    st.id = "reva-cad-style";
    st.textContent = `
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 100%; height: 100%; overflow: hidden; background: #eef3f7; font-family: "Segoe UI", Arial, sans-serif; }
      canvas, svg#lines, #chips { position: fixed; inset: 0; width: 100%; height: 100%; display: block; pointer-events: none; }
      #header { position: fixed; top: 54px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; gap: 10px; z-index: 20; pointer-events: none; }
      #pill { display: flex; align-items: center; gap: 14px; padding: 12px 26px 12px 14px; border-radius: 999px; background: rgba(255,255,255,0.96); box-shadow: 0 8px 24px rgba(15,23,42,0.12); font-weight: 800; font-size: 29px; color: #0f172a; white-space: nowrap; }
      #pill .num { width: 44px; height: 44px; border-radius: 50%; background: #1d4ed8; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 25px; }
      #subtitle { padding: 8px 18px; border-radius: 12px; background: rgba(15,23,42,0.88); color: #f8fafc; font-size: 21px; font-weight: 600; white-space: nowrap; box-shadow: 0 4px 14px rgba(0,0,0,0.16); }
      .chip { position: absolute; padding: 7px 14px; border-radius: 12px; font-weight: 800; font-size: 20px; line-height: 1.22; color: #fff; background: #1e293b; box-shadow: 0 4px 14px rgba(15,23,42,0.22); white-space: pre-line; text-align: center; }
      .chip.green { background: #15803d; }
      .chip.blue { background: #1d4ed8; }
      .chip.red { background: #dc2626; }
      .chip.amber { background: #c2410c; }
      .chip.mint { background: #0f766e; }
      .chip.muted { background: #475569; }
      .chip.deg { background: #15803d; font-size: 26px; padding: 9px 18px; border-radius: 14px; }
    `;
    document.head.appendChild(st);
  }

  function hud(camera, svg, chips, W, H) {
    function proj(pt) {
      const p = pt.clone().project(camera);
      return { x: (p.x * 0.5 + 0.5) * W, y: (-p.y * 0.5 + 0.5) * H };
    }
    function mkSvg(tag, attrs) {
      const el = document.createElementNS(NS, tag);
      for (const k in attrs) el.setAttribute(k, attrs[k]);
      svg.appendChild(el);
      return el;
    }
    function clear() {
      svg.innerHTML = "";
      chips.innerHTML = "";
    }
    function chip(pt, text, cls = "", dx = 0, dy = 0, leader = false) {
      const s = proj(pt), cx = s.x + dx, cy = s.y + dy;
      if (leader) {
        mkSvg("line", { x1: s.x, y1: s.y, x2: cx, y2: cy, stroke: "#1e293b", "stroke-width": 3.5, "stroke-linecap": "round" });
        mkSvg("circle", { cx: s.x, cy: s.y, r: 6.5, fill: "#fff", stroke: "#1d4ed8", "stroke-width": 3.5 });
      }
      const el = document.createElement("div");
      el.className = ("chip " + cls).trim();
      el.textContent = text;
      el.style.transform = `translate(-50%, -50%) translate(${cx.toFixed(1)}px, ${cy.toFixed(1)}px)`;
      chips.appendChild(el);
      return el;
    }
    function bracket(p1, p2, label, cls = "green", colorHex = "#15803d", offX = 0, offY = 0, tagDx = 0, tagDy = 0) {
      const a = proj(p1), b = proj(p2);
      const ax = a.x + offX, ay = a.y + offY, bx = b.x + offX, by = b.y + offY;
      const d = Math.hypot(bx - ax, by - ay) || 1;
      const nx = -(by - ay) / d * 13, ny = (bx - ax) / d * 13;
      mkSvg("line", { x1: ax, y1: ay, x2: bx, y2: by, stroke: colorHex, "stroke-width": 4.5, "stroke-linecap": "round" });
      mkSvg("line", { x1: ax - nx, y1: ay - ny, x2: ax + nx, y2: ay + ny, stroke: colorHex, "stroke-width": 4, "stroke-linecap": "round" });
      mkSvg("line", { x1: bx - nx, y1: by - ny, x2: bx + nx, y2: by + ny, stroke: colorHex, "stroke-width": 4, "stroke-linecap": "round" });
      const mx = (ax + bx) / 2, my = (ay + by) / 2;
      if (tagDx || tagDy) {
        mkSvg("line", { x1: mx, y1: my, x2: mx + tagDx, y2: my + tagDy, stroke: colorHex, "stroke-width": 3 });
      }
      const tag = document.createElement("div");
      tag.className = ("chip " + cls).trim();
      tag.textContent = label;
      tag.style.transform = `translate(-50%, -50%) translate(${(mx + tagDx).toFixed(1)}px, ${(my + tagDy).toFixed(1)}px)`;
      chips.appendChild(tag);
    }
    function angleSector(center3d, ray03d, ray13d, radiusPx = 150, stroke = "#15803d", fill = "rgba(21,128,61,0.22)", sweepFlag = 1) {
      const cP = proj(center3d), p0 = proj(ray03d), p1 = proj(ray13d);
      const a0 = Math.atan2(p0.y - cP.y, p0.x - cP.x);
      const a1 = Math.atan2(p1.y - cP.y, p1.x - cP.x);
      const x0 = cP.x + Math.cos(a0) * radiusPx, y0 = cP.y + Math.sin(a0) * radiusPx;
      const x1 = cP.x + Math.cos(a1) * radiusPx, y1 = cP.y + Math.sin(a1) * radiusPx;
      mkSvg("path", { d: `M ${cP.x} ${cP.y} L ${x0} ${y0} A ${radiusPx} ${radiusPx} 0 0 ${sweepFlag} ${x1} ${y1} Z`, fill, stroke, "stroke-width": 4.5 });
      return { cP, p0, p1 };
    }
    function polyline(pts3d, stroke = "#ef4444", width = 4.5, fill = "none", dash = "", opacity = 1) {
      if (!pts3d || pts3d.length < 2) return null;
      const coords = pts3d.map((pt) => {
        const s = proj(pt);
        return `${s.x.toFixed(1)},${s.y.toFixed(1)}`;
      }).join(" ");
      const attrs = { points: coords, stroke, "stroke-width": width, fill, "stroke-linejoin": "round", "stroke-linecap": "round", opacity };
      if (dash) attrs["stroke-dasharray"] = dash;
      return mkSvg("polyline", attrs);
    }
    function polygon(pts3d, stroke = "#ef4444", width = 3.5, fill = "rgba(239,68,68,0.22)", opacity = 1) {
      if (!pts3d || pts3d.length < 3) return null;
      const coords = pts3d.map((pt) => {
        const s = proj(pt);
        return `${s.x.toFixed(1)},${s.y.toFixed(1)}`;
      }).join(" ");
      return mkSvg("polygon", { points: coords, stroke, "stroke-width": width, fill, "stroke-linejoin": "round", opacity });
    }
    function arrow(p1, p2, colorHex = "#dc2626", width = 5, headSize = 18) {
      const a = proj(p1), b = proj(p2);
      const ang = Math.atan2(b.y - a.y, b.x - a.x);
      mkSvg("line", { x1: a.x.toFixed(1), y1: a.y.toFixed(1), x2: b.x.toFixed(1), y2: b.y.toFixed(1), stroke: colorHex, "stroke-width": width, "stroke-linecap": "round" });
      const hx1 = b.x - Math.cos(ang - 0.45) * headSize, hy1 = b.y - Math.sin(ang - 0.45) * headSize;
      const hx2 = b.x - Math.cos(ang + 0.45) * headSize, hy2 = b.y - Math.sin(ang + 0.45) * headSize;
      mkSvg("polygon", { points: `${b.x.toFixed(1)},${b.y.toFixed(1)} ${hx1.toFixed(1)},${hy1.toFixed(1)} ${hx2.toFixed(1)},${hy2.toFixed(1)}`, fill: colorHex });
      return { a, b };
    }
    function badge(pt, text, cls = "blue", dx = 0, dy = 0, leader = false) {
      const s = proj(pt), cx = s.x + dx, cy = s.y + dy;
      if (leader) {
        mkSvg("line", { x1: s.x.toFixed(1), y1: s.y.toFixed(1), x2: cx.toFixed(1), y2: cy.toFixed(1), stroke: "#1e293b", "stroke-width": 3, "stroke-linecap": "round" });
        mkSvg("circle", { cx: s.x.toFixed(1), cy: s.y.toFixed(1), r: 5.5, fill: "#fff", stroke: "#1d4ed8", "stroke-width": 3 });
      }
      const el = document.createElement("div");
      el.className = ("chip badge-circle " + cls).trim();
      el.textContent = text;
      el.style.transform = `translate(-50%, -50%) translate(${cx.toFixed(1)}px, ${cy.toFixed(1)}px)`;
      chips.appendChild(el);
      return el;
    }
    return { clear, proj, mkSvg, chip, bracket, angleSector, polyline, polygon, arrow, badge };
  }

  function boot(opts = {}) {
    _ensureStyles();
    const qs = new URLSearchParams(location.search);
    const W = parseInt(opts.w || qs.get("w") || String(window.innerWidth || 1080), 10);
    const H = parseInt(opts.h || qs.get("h") || String(window.innerHeight || 1920), 10);
    const tInit = parseFloat(qs.get("t") || "0") || 0;

    let hdr = document.getElementById("header");
    if (!hdr) {
      hdr = document.createElement("div");
      hdr.id = "header";
      const pill = document.createElement("div");
      pill.id = "pill";
      const num = document.createElement("span");
      num.className = "num";
      num.textContent = String(opts.headerNum != null ? opts.headerNum : "1");
      const title = document.createElement("span");
      title.id = "pill-title";
      title.textContent = opts.headerTitle || "REVA Clay/CAD Schematic";
      pill.append(num, title);
      const sub = document.createElement("div");
      sub.id = "subtitle";
      hdr.append(pill, sub);
      document.body.appendChild(hdr);
    }

    let svg = document.getElementById("lines");
    if (!svg) {
      svg = document.createElementNS(NS, "svg");
      svg.id = "lines";
      document.body.appendChild(svg);
    }
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("preserveAspectRatio", "none");

    let chips = document.getElementById("chips");
    if (!chips) {
      chips = document.createElement("div");
      chips.id = "chips";
      document.body.appendChild(chips);
    }

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(W, H, false);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    document.body.insertBefore(renderer.domElement, document.body.firstChild);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(opts.bg != null ? opts.bg : PALETTE.bg);
    const camera = new THREE.PerspectiveCamera(opts.fov || 34, W / H, 0.2, 200);
    camera.position.set(3.4, 3.8, 4.2);
    camera.lookAt(0, 1.0, 0);

    scene.add(new THREE.HemisphereLight(0xffffff, 0xcbd5e1, 0.90));
    const key = new THREE.DirectionalLight(0xffffff, 0.58);
    key.position.set(10, 18, 12);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.left = -6; key.shadow.camera.right = 6;
    key.shadow.camera.top = 7; key.shadow.camera.bottom = -6;
    scene.add(key);

    const subEl = document.getElementById("subtitle");
    const setSubtitle = (txt) => {
      if (!subEl) return;
      subEl.textContent = txt || "";
      subEl.style.display = txt ? "block" : "none";
    };
    setSubtitle(opts.subtitle || "");

    return {
      W, H, tInit, renderer, scene, camera, svg, chips, setSubtitle,
      V, clay, addMesh,
      hud: hud(camera, svg, chips, W, H),
    };
  }

  /* Structural engineering clay/CAD primitives (SNI 2847 / ACI 318) */
  function buildStirrup135(c, rMain, rS, extFactor = 6.0, mat) {
    const d = rS * 2.0;
    const R = Math.max(rMain + rS, 2.5 * d); // inner bend dia >= 4*d
    const lExt = extFactor * d;
    const dy = rS * 1.15;
    const pts = [];
    function arcCorner(cx, cz, y0, y1, a0, a1, n) {
      for (let i = 0; i <= n; i++) {
        const k = i / n, a = a0 + (a1 - a0) * k;
        pts.push(V(cx + Math.cos(a) * R, y0 + (y1 - y0) * k, cz + Math.sin(a) * R));
      }
    }
    const dirIn = V(-Math.SQRT1_2, 0, -Math.SQRT1_2);
    const tanA = V(c + Math.cos(-Math.PI * 0.25) * R, dy, c + Math.sin(-Math.PI * 0.25) * R);
    const tipA = V(tanA.x + dirIn.x * lExt, dy, tanA.z + dirIn.z * lExt);
    pts.push(tipA, tanA);
    arcCorner(c, c, dy, dy * 0.35, -Math.PI * 0.25, Math.PI * 0.5, 10);
    arcCorner(-c, c, dy * 0.35, 0, Math.PI * 0.5, Math.PI, 8);
    arcCorner(-c, -c, 0, -dy * 0.35, Math.PI, Math.PI * 1.5, 8);
    arcCorner(c, -c, -dy * 0.35, -dy, -Math.PI * 0.5, 0, 8);
    arcCorner(c, c, -dy, -dy, 0, Math.PI * 0.75, 10);
    const tanB = V(c + Math.cos(Math.PI * 0.75) * R, -dy, c + Math.sin(Math.PI * 0.75) * R);
    const tipB = V(tanB.x + dirIn.x * lExt, -dy, tanB.z + dirIn.z * lExt);
    pts.push(tipB);

    const curve = new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.08);
    const useMat = mat || clay(PALETTE.ok);
    const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 160, rS, 14, false), useMat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    // Solid circular end caps so 135 deg hook tails are filled steel rods rather than hollow open tubes
    const capGeo = new THREE.CylinderGeometry(rS, rS, rS * 0.20, 14);
    const capRot = new THREE.Quaternion().setFromUnitVectors(V(0, 1, 0), dirIn);
    for (const tip of [tipA, tipB]) {
      const cap = new THREE.Mesh(capGeo, useMat);
      cap.position.copy(tip);
      cap.quaternion.copy(capRot);
      cap.castShadow = true;
      mesh.add(cap);
    }

    return { mesh, tipA, tanA, tipB, tanB, cCorner: V(c, 0, c), R, d, lExt };
  }

  function buildFailingHoop90(c, rMain, rS, openAmt, mat) {
    const grp = new THREE.Group();
    const useMat = mat || clay(PALETTE.bad);
    const R = rMain + rS;
    const dy = rS * 0.9;
    const pts = [];
    function arc(cx, cz, yv, a0, a1) {
      for (let i = 0; i <= 6; i++) {
        const a = a0 + (a1 - a0) * (i / 6);
        pts.push(V(cx + Math.cos(a) * R, yv, cz + Math.sin(a) * R));
      }
    }
    pts.push(V(c * 0.35, dy, c + R));
    arc(-c, c, dy * 0.5, Math.PI * 0.5, Math.PI);
    arc(-c, -c, 0, Math.PI, Math.PI * 1.5);
    arc(c, -c, -dy * 0.5, -Math.PI * 0.5, 0);
    pts.push(V(c + R, -dy, c * 0.35));
    addMesh(grp, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.1), 80, rS, 10, false), useMat);

    const armA = [V(c * 0.35, dy, c + R), V(c + 0.15, dy, c + R + openAmt), V(c + 0.52, dy, c + R + openAmt + 0.08)];
    const armB = [V(c + R, -dy, c * 0.35), V(c + R + openAmt, -dy, c + 0.15), V(c + R + openAmt + 0.08, -dy, c + 0.52)];
    addMesh(grp, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(armA, false, "catmullrom", 0.2), 20, rS, 10, false), useMat);
    addMesh(grp, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(armB, false, "catmullrom", 0.2), 20, rS, 10, false), useMat);
    return grp;
  }

  function buildCoreAndCoverCutaway(coreHalf, coverHalf, height, coverMat, coreMat) {
    const grp = new THREE.Group();
    const rimW = coverHalf - coreHalf;
    const covM = coverMat || clay(PALETTE.coverGrey, { transparent: true, opacity: 0.42 });
    const corM = coreMat || clay(PALETTE.coreMint, { transparent: true, opacity: 0.48 });
    addMesh(grp, new THREE.BoxGeometry(coverHalf * 2, height, rimW), covM, 0, height / 2, coreHalf + rimW / 2, false);
    addMesh(grp, new THREE.BoxGeometry(coverHalf * 2, height, rimW), covM, 0, height / 2, -coreHalf - rimW / 2, false);
    addMesh(grp, new THREE.BoxGeometry(rimW, height, coreHalf * 2), covM, coreHalf + rimW / 2, height / 2, 0, false);
    addMesh(grp, new THREE.BoxGeometry(rimW, height, coreHalf * 2), covM, -coreHalf - rimW / 2, height / 2, 0, false);
    addMesh(grp, new THREE.BoxGeometry(coreHalf * 2, height + 0.02, coreHalf * 2), corM, 0, (height + 0.02) / 2, 0, false);
    return grp;
  }

  function buildBucklingColumnBar(bx, bz, height, rMain, yStart, yEnd, bowAmp, mat) {
    const pts = [];
    for (let i = 0; i <= 18; i++) {
      const u = i / 18, y = u * height;
      let bow = 0;
      if (y > yStart && y < yEnd) {
        const k = (y - yStart) / (yEnd - yStart);
        bow = Math.sin(k * Math.PI) * bowAmp;
      }
      const L = Math.hypot(bx, bz) || 1;
      pts.push(V(bx + (bx / L) * bow, y, bz + (bz / L) * bow));
    }
    const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 36, rMain, 14, false), mat || clay(PALETTE.mainBar));
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }

  function buildBentBar(pts, r, mat, segs = 48) {
    const curve = new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.08);
    const m = new THREE.Mesh(new THREE.TubeGeometry(curve, segs, r, 12, false), mat || clay(PALETTE.mainBar));
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }

  function buildFilletHookBar(pStart, pCorner, pEnd, r, bendR, mat, segs = 48) {
    const vIn = pStart.clone().sub(pCorner);
    const vOut = pEnd.clone().sub(pCorner);
    const lenIn = vIn.length(), lenOut = vOut.length();
    const dIn = vIn.clone().normalize(), dOut = vOut.clone().normalize();
    const rUse = Math.min(bendR, lenIn * 0.45, lenOut * 0.45);
    const pA = pCorner.clone().addScaledVector(dIn, rUse);
    const pB = pCorner.clone().addScaledVector(dOut, rUse);
    const pts = [pStart.clone(), pStart.clone().lerp(pA, 0.5), pA];
    for (let i = 1; i <= 7; i++) {
      const u = i / 8, om = 1 - u;
      pts.push(V(
        om * om * pA.x + 2 * om * u * pCorner.x + u * u * pB.x,
        om * om * pA.y + 2 * om * u * pCorner.y + u * u * pB.y,
        om * om * pA.z + 2 * om * u * pCorner.z + u * u * pB.z
      ));
    }
    pts.push(pB, pB.clone().lerp(pEnd, 0.5), pEnd.clone());
    return buildBentBar(pts, r, mat, segs);
  }

  function buildSimpleRectHoop(cx, cz, rMain, rS, mat) {
    const R = rMain + rS;
    const pts = [];
    const corners = [
      [cx, cz, 0, Math.PI * 0.5],
      [-cx, cz, Math.PI * 0.5, Math.PI],
      [-cx, -cz, Math.PI, Math.PI * 1.5],
      [cx, -cz, -Math.PI * 0.5, 0],
    ];
    for (const [x0, z0, a0, a1] of corners) {
      for (let i = 0; i <= 5; i++) {
        const a = a0 + (a1 - a0) * (i / 5);
        pts.push(V(x0 + Math.cos(a) * R, 0, z0 + Math.sin(a) * R));
      }
    }
    const curve = new THREE.CatmullRomCurve3(pts, true, "catmullrom", 0.08);
    const m = new THREE.Mesh(new THREE.TubeGeometry(curve, 64, rS, 10, true), mat || clay(PALETTE.ok));
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }

  function buildColumnCage(opts = {}) {
    const c = opts.c != null ? opts.c : 0.42;
    const h = opts.height != null ? opts.height : 4.8;
    const rMain = opts.rMain != null ? opts.rMain : 0.055;
    const rS = opts.rS != null ? opts.rS : 0.024;
    const mainMat = opts.mainMat || clay(PALETTE.mainBar);
    const stMat = opts.stirrupMat || clay(PALETTE.ok);
    const ys = opts.stirrupYs || [0.3, 0.7, 1.1, 1.8, 2.4, 3.0, 3.7, 4.1, 4.5];
    const grp = new THREE.Group();
    const barGeo = new THREE.CylinderGeometry(rMain, rMain, h, 14);
    for (const [bx, bz] of [[-c, -c], [c, -c], [c, c], [-c, c]]) {
      addMesh(grp, barGeo, mainMat, bx, h / 2, bz);
    }
    const stirrups = [];
    for (const y of ys) {
      const m = opts.use135 ? buildStirrup135(c, rMain, rS, 5.2, stMat).mesh : buildSimpleRectHoop(c, c, rMain, rS, stMat);
      m.position.y = y;
      grp.add(m);
      stirrups.push(m);
    }
    return { group: grp, stirrups };
  }

  function buildLapSpliceAssembly(opts = {}) {
    const c = opts.c != null ? opts.c : 0.44;
    const rMain = opts.rMain != null ? opts.rMain : 0.062;
    const rS = opts.rS != null ? opts.rS : 0.026;
    const lapBot = opts.lapBot != null ? opts.lapBot : 1.45;
    const lapTop = opts.lapTop != null ? opts.lapTop : 3.25;
    const totalH = opts.totalH != null ? opts.totalH : 5.2;
    const lowMat = opts.lowerMat || clay(PALETTE.mainBar);
    const upMat = opts.upperMat || clay(PALETTE.beamA);
    const tieMat = opts.tieMat || clay(PALETTE.ok);

    const grp = new THREE.Group();
    const lowerGrp = new THREE.Group();
    const upperGrp = new THREE.Group();
    const tiesGrp = new THREE.Group();
    grp.add(lowerGrp, upperGrp, tiesGrp);

    const lowGeo = new THREE.CylinderGeometry(rMain, rMain, lapTop, 16);
    const upLen = totalH - lapBot;
    const upGeo = new THREE.CylinderGeometry(rMain, rMain, upLen, 16);
    const off = rMain * 2.08;

    for (const [bx, bz] of [[-c, -c], [c, -c], [c, c], [-c, c]]) {
      addMesh(lowerGrp, lowGeo, lowMat, bx, lapTop / 2, bz);
      // Offset upper bar neatly inward along tangential face so paired lap bars touch cleanly without colliding
      const ux = bx > 0 ? bx - off : bx + off;
      addMesh(upperGrp, upGeo, upMat, ux, lapBot + upLen / 2, bz);
    }
    const tieYs = [];
    for (let y = lapBot + 0.14; y <= lapTop - 0.10; y += 0.30) tieYs.push(y);
    const ties = [];
    for (const y of tieYs) {
      const s = buildStirrup135(c, rMain, rS, 5.0, tieMat).mesh;
      s.position.y = y;
      tiesGrp.add(s);
      ties.push(s);
    }
    return { group: grp, lowerGrp, upperGrp, tiesGrp, ties, lapBot, lapTop };
  }

  function buildCornerJoint(opts = {}) {
    const colC = opts.colC != null ? opts.colC : 0.42;
    const colH = opts.colH != null ? opts.colH : 4.2;
    const beamLen = opts.beamLen != null ? opts.beamLen : 2.8;
    const rCol = opts.rCol != null ? opts.rCol : 0.055;
    const rBeam = opts.rBeam != null ? opts.rBeam : 0.048;
    const rS = opts.rS != null ? opts.rS : 0.022;
    const isGood = opts.isGood !== false;

    const grp = new THREE.Group();
    const colMat = clay(PALETTE.mainBar);
    const beamAMat = clay(isGood ? PALETTE.beamA : PALETTE.bad);
    const beamBMat = clay(isGood ? PALETTE.beamB : PALETTE.bad);
    const hoopMat = clay(PALETTE.ok);
    const wireMat = clay(PALETTE.wire);

    // Translucent mint column core so interlocking hooks inside the joint read effortlessly
    const coreHalf = colC + rCol + rS + 0.05;
    addMesh(grp, new THREE.BoxGeometry(coreHalf * 2, colH, coreHalf * 2), clay(PALETTE.coreMint, { transparent: true, opacity: 0.24 }), 0, colH / 2, 0, false);

    // Column longitudinal bars + joint hoops
    const colGeo = new THREE.CylinderGeometry(rCol, rCol, colH, 14);
    for (const [bx, bz] of [[-colC, -colC], [colC, -colC], [colC, colC], [-colC, colC]]) {
      addMesh(grp, colGeo, colMat, bx, colH / 2, bz);
    }
    for (const y of [0.35, 0.85, 1.35, 1.85, 2.35, 2.85, 3.35, 3.85]) {
      const hp = buildSimpleRectHoop(colC, colC, rCol, rS, hoopMat);
      hp.position.y = y;
      grp.add(hp);
    }

    const beamXGrp = new THREE.Group();
    const beamZGrp = new THREE.Group();
    grp.add(beamXGrp, beamZGrp);

    const yLevels = [1.55, 2.45];
    const zOffs = [-0.24, 0.24];
    const xOffs = [-0.24, 0.24];

    if (isGood) {
      // Beam X bars pass THROUGH column core to far face (-colC + 0.08) and bend 90° inward into Beam Z / core!
      for (const yi of [0, 1]) {
        const y = yLevels[yi];
        const hookDirY = yi === 0 ? 0.62 : -0.62;
        for (const z of zOffs) {
          const farX = -colC + 0.11;
          beamXGrp.add(buildFilletHookBar(V(beamLen, y, z), V(farX, y, z), V(farX, y + hookDirY, z), rBeam, 0.14, beamAMat));
        }
      }
      // Beam Z bars pass THROUGH column core to far face (-colC + 0.08) and bend 90° inward vertically into core!
      for (const yi of [0, 1]) {
        const y = yLevels[yi] + (yi === 0 ? 0.11 : -0.11);
        const hookDirY = yi === 0 ? 0.56 : -0.56;
        for (const x of xOffs) {
          const farZ = -colC + 0.11;
          beamZGrp.add(buildFilletHookBar(V(x, y, beamLen), V(x, y, farZ), V(x, y + hookDirY, farZ), rBeam, 0.14, beamBMat));
        }
      }
    } else {
      // BAD: butt-ended bars stopping outside the column face with flimsy wire loops
      const stopX = colC + rCol + 0.07;
      for (const y of yLevels) {
        for (const z of zOffs) {
          beamXGrp.add(buildBentBar([V(beamLen, y, z), V(stopX, y, z)], rBeam, beamAMat, 12));
          addMesh(beamXGrp, new THREE.TorusGeometry(rBeam * 1.45, 0.011, 8, 16), wireMat, stopX + 0.04, y, z);
        }
      }
      const stopZ = colC + rCol + 0.07;
      for (const y of yLevels) {
        for (const x of xOffs) {
          beamZGrp.add(buildBentBar([V(x, y + 0.09, beamLen), V(x, y + 0.09, stopZ)], rBeam, beamBMat, 12));
          addMesh(beamZGrp, new THREE.TorusGeometry(rBeam * 1.45, 0.011, 8, 16), wireMat, x, y + 0.09, stopZ + 0.04);
        }
      }
    }

    // Beam stirrups outside column
    const bStGeoX = new THREE.BoxGeometry(0.036, 1.02, 0.62);
    const bStMat = clay(0x94a3b8, { transparent: true, opacity: 0.35 });
    for (let d = 0.85; d <= beamLen - 0.3; d += 0.55) {
      addMesh(beamXGrp, bStGeoX, bStMat, d, 2.0, 0, false);
      const bStZ = new THREE.Mesh(new THREE.BoxGeometry(0.62, 1.02, 0.036), bStMat);
      bStZ.position.set(0, 2.0, d);
      beamZGrp.add(bStZ);
    }

    return { group: grp, beamXGrp, beamZGrp };
  }

  function buildDeckingSpacer(size = 0.16, mat) {
    const g = new THREE.Group();
    const m = mat || clay(PALETTE.decking);
    addMesh(g, new THREE.BoxGeometry(size, size * 0.9, size), m, 0, 0, 0);
    // Subtle dark wire tie clip around spacer
    addMesh(g, new THREE.BoxGeometry(size * 1.08, 0.018, size * 0.25), clay(PALETTE.wire), 0, 0, 0, false);
    return g;
  }

  global.RevaCAD = {
    PALETTE,
    V,
    clay,
    addMesh,
    boot,
    hud,
    rebar: {
      buildStirrup135,
      buildFailingHoop90,
      buildCoreAndCoverCutaway,
      buildBucklingColumnBar,
      buildBentBar,
      buildFilletHookBar,
      buildSimpleRectHoop,
      buildColumnCage,
      buildLapSpliceAssembly,
      buildCornerJoint,
      buildDeckingSpacer,
    },
  };
})(window);
