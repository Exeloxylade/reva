/* threejs_pbr_materials.js - REVA Lab Shared Physical-Stylized Material & 3D Geometry Engine (Three.js 0.149).
 *
 * Calibrated for warm, recognizable "Blender-in-Three.js" matte-real visuals:
 *   - 3D Vertex-Sculpted Helical Deformed Rebar (Besi Ulir) — straight cylinders & curved/buckling tubes
 *   - Warm Matte Mill-Scale Steel + Subtle Rust Patina (zero harsh chrome glare, sRGB-safe for W3 post-pass!)
 *   - Smooth Cold-Drawn Steel Stirrups (Besi Polos) + 3D Twisted Tie Wire (Kawat Bendrat)
 *   - Creamy Voronoi Crushed-Aggregate Concrete Cross-Section (low-contrast natural stone packing)
 *   - Cast Architectural Concrete, Fractured Concrete Rubble Chunks, Timber Formwork, Terracotta Brick, Clay Soil
 */
(function (global) {
  "use strict";

  function mulberry32(seed) {
    let a = seed | 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function makeTileNoise(gridN, seed) {
    const r = mulberry32(seed);
    const g = new Float32Array(gridN * gridN);
    for (let i = 0; i < g.length; i++) g[i] = r();
    return function sample(u, v) {
      const x = ((u % 1) + 1) % 1 * gridN;
      const y = ((v % 1) + 1) % 1 * gridN;
      const x0 = Math.floor(x) % gridN, y0 = Math.floor(y) % gridN;
      const x1 = (x0 + 1) % gridN, y1 = (y0 + 1) % gridN;
      const fx = x - Math.floor(x), fy = y - Math.floor(y);
      const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
      const v00 = g[y0 * gridN + x0], v10 = g[y0 * gridN + x1];
      const v01 = g[y1 * gridN + x0], v11 = g[y1 * gridN + x1];
      return (v00 * (1 - sx) + v10 * sx) * (1 - sy) + (v01 * (1 - sx) + v11 * sx) * sy;
    };
  }

  function fbm(u, v, octaves) {
    let sum = 0, amp = 0.5, norm = 0;
    for (let i = 0; i < octaves.length; i++) {
      sum += octaves[i](u, v) * amp;
      norm += amp;
      amp *= 0.5;
    }
    return sum / norm;
  }

  function heightToNormalTex(height, W, H, strength, repX = 1, repY = 1) {
    const c = document.createElement("canvas");
    c.width = W; c.height = H;
    const ctx = c.getContext("2d");
    const img = ctx.createImageData(W, H);
    const d = img.data;
    for (let y = 0; y < H; y++) {
      const ym = (y - 1 + H) % H, yp = (y + 1) % H;
      for (let x = 0; x < W; x++) {
        const xm = (x - 1 + W) % W, xp = (x + 1) % W;
        const tl = height[ym * W + xm], t = height[ym * W + x], tr = height[ym * W + xp];
        const l = height[y * W + xm], r = height[y * W + xp];
        const bl = height[yp * W + xm], b = height[yp * W + x], br = height[yp * W + xp];
        const dx = (tr + 2 * r + br - tl - 2 * l - bl) * strength;
        const dy = (bl + 2 * b + br - tl - 2 * t - tr) * strength;
        let nx = -dx, ny = -dy, nz = 1.0;
        const inv = 1.0 / Math.hypot(nx, ny, nz);
        nx *= inv; ny *= inv; nz *= inv;
        const p = (y * W + x) * 4;
        d[p] = Math.round((nx * 0.5 + 0.5) * 255);
        d[p + 1] = Math.round((ny * 0.5 + 0.5) * 255);
        d[p + 2] = Math.round((nz * 0.5 + 0.5) * 255);
        d[p + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(repX, repY);
    tex.anisotropy = 8;
    return tex;
  }

  function makeCanvasTex(c, repX = 1, repY = 1, useSRGB = false) {
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(repX, repY);
    tex.anisotropy = 8;
    tex.encoding = useSRGB && THREE.sRGBEncoding ? THREE.sRGBEncoding : THREE.LinearEncoding;
    return tex;
  }

  /* 1. WARM MATTE FORGED MILL-SCALE DEFORMED REBAR MATERIAL (Cozy Stylized Realism, Zero Black Crush!) */
  function createRebarMaterial(opts = {}) {
    const W = 512, H = 512;
    const height = new Float32Array(W * H);
    const n1 = makeTileNoise(8, 111), n2 = makeTileNoise(24, 112), n3 = makeTileNoise(72, 113);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const cRgh = document.createElement("canvas"); cRgh.width = W; cRgh.height = H;
    const gAlb = cAlb.getContext("2d"), gRgh = cRgh.getContext("2d");
    const iAlb = gAlb.createImageData(W, H), iRgh = gRgh.createImageData(W, H);

    // Calibrated warm iron-brown-grey matching real construction rebar in soft daylight
    const base = opts.rgb || [146, 124, 108];
    for (let y = 0; y < H; y++) {
      const v = y / H;
      for (let x = 0; x < W; x++) {
        const u = x / W;
        const m = fbm(u, v, [n1, n2, n3]);
        height[y * W + x] = m;
        // Soft natural oxidized rust patches (like warm iron in viral Blender refs)
        const rust = Math.max(0, m - 0.56) * 1.15;
        const sh = 0.86 + (m - 0.5) * 0.26;
        const p = (y * W + x) * 4;
        iAlb.data[p] = Math.min(255, Math.round(base[0] * sh + rust * 68));
        iAlb.data[p + 1] = Math.min(255, Math.round(base[1] * sh + rust * 24));
        iAlb.data[p + 2] = Math.min(255, Math.round(base[2] * sh - rust * 14));
        iAlb.data[p + 3] = 255;

        const rgh = Math.round((0.66 + (m - 0.5) * 0.20 + rust * 0.14) * 255);
        iRgh.data[p] = iRgh.data[p + 1] = iRgh.data[p + 2] = Math.min(242, Math.max(115, rgh));
        iRgh.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(iAlb, 0, 0);
    gRgh.putImageData(iRgh, 0, 0);

    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, 1, 3, !!opts.srgb),
      normalMap: heightToNormalTex(height, W, H, 0.85, 1, 3),
      roughnessMap: makeCanvasTex(cRgh, 1, 3, false),
      metalness: opts.metalness != null ? opts.metalness : 0.16,
      roughness: 1.0,
      emissive: new THREE.Color(opts.emissive || 0x16110e),
      emissiveIntensity: opts.emissiveInt != null ? opts.emissiveInt : 0.08,
      envMapIntensity: opts.envInt != null ? opts.envInt : 0.16,
    });
  }

  /* Helical Deformed Rebar Rib Profile */
  function rebarRibDisp(theta, axialPos, ribPitch) {
    const u = ((theta / (Math.PI * 2)) % 1 + 1) % 1;
    const dSeam = Math.min(Math.abs(u), Math.abs(u - 1), Math.abs(u - 0.5));
    const seam = Math.exp(-Math.pow(dSeam / 0.042, 2)) * 0.70;
    const side = u < 0.5 ? 1 : -1;
    const phase = ((axialPos / ribPitch + u * side * 0.72) % 1 + 1) % 1;
    const dRib = Math.abs(phase - 0.5);
    const lugMask = Math.min(1.0, Math.max(0.0, (dSeam - 0.022) / 0.036));
    const lug = Math.exp(-Math.pow(dRib / 0.155, 2.2)) * 1.0 * lugMask;
    return Math.max(seam, lug);
  }

  function buildSculptedRebarCylinder(r, height, mat, ribPitch) {
    const pitch = ribPitch || r * 1.40;
    const radialSegs = 36;
    const heightSegs = Math.max(44, Math.min(160, Math.round((height / pitch) * 5.8)));
    const geo = new THREE.CylinderGeometry(r, r, height, radialSegs, heightSegs, true);
    const pos = geo.attributes.position;
    const amp = r * 0.125;

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      const theta = Math.atan2(z, x);
      const endFade = Math.min(1, Math.min(Math.abs(y - height / 2), Math.abs(y + height / 2)) / (pitch * 0.35));
      const disp = rebarRibDisp(theta, y + height / 2, pitch) * amp * endFade;
      const rad = Math.hypot(x, z) || 1;
      pos.setXYZ(i, x + (x / rad) * disp, y, z + (z / rad) * disp);
    }
    geo.computeVertexNormals();

    const grp = new THREE.Group();
    const body = new THREE.Mesh(geo, mat);
    body.castShadow = true;
    body.receiveShadow = true;
    grp.add(body);

    // Warm matching sheared-iron end cap calibrated for linear W3 canvas
    const cutMat = new THREE.MeshStandardMaterial({
      color: 0x6f5e52, metalness: 0.18, roughness: 0.62,
      emissive: 0x120e0b, emissiveIntensity: 0.08, envMapIntensity: 0.14,
    });
    const topCap = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.94, r * 1.0, r * 0.10, 28), cutMat);
    topCap.position.y = height / 2 + r * 0.045;
    topCap.castShadow = true;
    grp.add(topCap);
    const botCap = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.0, r * 0.94, r * 0.10, 28), cutMat);
    botCap.position.y = -height / 2 - r * 0.045;
    grp.add(botCap);
    return grp;
  }

  function buildSculptedRebarTube(curve, r, mat, ribPitch) {
    const len = curve.getLength();
    const pitch = ribPitch || r * 1.44;
    const tubularSegs = Math.max(56, Math.min(190, Math.round((len / pitch) * 5.2)));
    const radialSegs = 26;
    const geo = new THREE.TubeGeometry(curve, tubularSegs, r, radialSegs, false);
    const pos = geo.attributes.position;
    const uv = geo.attributes.uv;
    const amp = r * 0.125;

    for (let i = 0; i <= tubularSegs; i++) {
      const uT = i / tubularSegs;
      const center = curve.getPointAt(uT);
      const axial = uT * len;
      const endFade = Math.min(1, Math.min(axial, len - axial) / (pitch * 0.35));
      for (let j = 0; j <= radialSegs; j++) {
        const idx = i * (radialSegs + 1) + j;
        const theta = (j / radialSegs) * Math.PI * 2;
        const disp = rebarRibDisp(theta, axial, pitch) * amp * endFade;
        const vx = pos.getX(idx) - center.x;
        const vy = pos.getY(idx) - center.y;
        const vz = pos.getZ(idx) - center.z;
        const vl = Math.hypot(vx, vy, vz) || 1;
        pos.setXYZ(idx, center.x + (vx / vl) * (r + disp), center.y + (vy / vl) * (r + disp), center.z + (vz / vl) * (r + disp));
        uv.setXY(idx, j / radialSegs, axial * 0.55);
      }
    }
    geo.computeVertexNormals();
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }

  /* 2. WARM MATTE DRAWN STEEL STIRRUP (BESI POLOS — Cozy Blender Feel) */
  function createStirrupSteelMaterial(opts = {}) {
    const W = 256, H = 256;
    const n1 = makeTileNoise(12, 201), n2 = makeTileNoise(48, 202);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const iAlb = gAlb.createImageData(W, H);
    const rgb = opts.rgb || [164, 158, 150];
    for (let y = 0; y < H; y++) {
      const v = y / H;
      for (let x = 0; x < W; x++) {
        const u = x / W;
        const streak = n1(u * 2.5, v * 0.4) * 0.65 + n2(u * 4.0, v * 0.8) * 0.35;
        const sh = 0.90 + (streak - 0.5) * 0.18;
        const p = (y * W + x) * 4;
        iAlb.data[p] = Math.min(255, Math.round(rgb[0] * sh));
        iAlb.data[p + 1] = Math.min(255, Math.round(rgb[1] * sh));
        iAlb.data[p + 2] = Math.min(255, Math.round(rgb[2] * sh));
        iAlb.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(iAlb, 0, 0);

    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, 1, 5, !!opts.srgb),
      metalness: opts.metalness != null ? opts.metalness : 0.18,
      roughness: opts.roughness != null ? opts.roughness : 0.60,
      emissive: new THREE.Color(opts.emissive || 0x141210),
      emissiveIntensity: opts.emissiveInt != null ? opts.emissiveInt : 0.06,
      envMapIntensity: opts.envInt != null ? opts.envInt : 0.18,
    });
  }

  /* 3. CREAMY LOW-CONTRAST VORONOI AGGREGATE CONCRETE (Natural Limestone/Gravel — Never Harsh or Blown Out!) */
  function createConcreteSectionMaterial(opts = {}) {
    const W = 512, H = 512;
    const r = mulberry32(opts.seed || 401);
    const n1 = makeTileNoise(10, 415), n2 = makeTileNoise(36, 416), n3 = makeTileNoise(96, 417);
    const G = opts.density || 13;
    const pts = [];
    for (let gy = 0; gy < G; gy++) {
      for (let gx = 0; gx < G; gx++) {
        pts.push({
          x: (gx + 0.18 + r() * 0.64) / G,
          y: (gy + 0.18 + r() * 0.64) / G,
          tone: r(),
          warm: r(),
          isStone: r() < 0.84,
        });
      }
    }

    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const iAlb = gAlb.createImageData(W, H);
    const height = new Float32Array(W * H);

    // Creamy warm limestone concrete base (calibrated NOT to blow out under daylight!)
    const mortarRGB = opts.mortarRGB || [210, 205, 196];
    const tintRGB = opts.tintRGB || null;
    const tintAmt = opts.tintAmt || 0;

    for (let y = 0; y < H; y++) {
      const v = y / H;
      const gy0 = Math.floor(v * G);
      for (let x = 0; x < W; x++) {
        const u = x / W;
        const gx0 = Math.floor(u * G);
        let d1 = 99, d2 = 99, best = null;
        for (let oy = -1; oy <= 1; oy++) {
          const gy = (gy0 + oy + G) % G;
          for (let ox = -1; ox <= 1; ox++) {
            const gx = (gx0 + ox + G) % G;
            const pt = pts[gy * G + gx];
            let dx = pt.x - u, dy = pt.y - v;
            if (dx > 0.5) dx -= 1; if (dx < -0.5) dx += 1;
            if (dy > 0.5) dy -= 1; if (dy < -0.5) dy += 1;
            const d = Math.hypot(dx, dy);
            if (d < d1) { d2 = d1; d1 = d; best = pt; }
            else if (d < d2) { d2 = d; }
          }
        }
        const edgeGap = (d2 - d1) * G;
        const micro = fbm(u, v, [n1, n2, n3]);
        const smoothStone = best.isStone ? Math.min(1, Math.max(0, (edgeGap - 0.08) / 0.11)) : 0;

        // Rich creamy limestone chips vs clean light mortar (clearly visible like reference!)
        const mK = 1.00 + (micro - 0.5) * 0.06;
        const mr = mortarRGB[0] * mK, mg = mortarRGB[1] * mK, mb = mortarRGB[2] * mK;
        const sK = 0.80 + best.tone * 0.17 + (micro - 0.5) * 0.05;
        const sr = mortarRGB[0] * sK + (best.warm - 0.5) * 14;
        const sg = mortarRGB[1] * sK + (best.warm - 0.5) * 8;
        const sb = mortarRGB[2] * sK - (best.warm - 0.5) * 6;

        let rr = mr + (sr - mr) * smoothStone;
        let gg = mg + (sg - mg) * smoothStone;
        let bb = mb + (sb - mb) * smoothStone;

        if (tintRGB && tintAmt > 0) {
          rr = rr * (1 - tintAmt) + tintRGB[0] * tintAmt;
          gg = gg * (1 - tintAmt) + tintRGB[1] * tintAmt;
          bb = bb * (1 - tintAmt) + tintRGB[2] * tintAmt;
        }
        height[y * W + x] = 0.46 + smoothStone * 0.10 + (micro - 0.5) * 0.10;
        const p = (y * W + x) * 4;
        iAlb.data[p] = Math.min(255, Math.max(0, Math.round(rr)));
        iAlb.data[p + 1] = Math.min(255, Math.max(0, Math.round(gg)));
        iAlb.data[p + 2] = Math.min(255, Math.max(0, Math.round(bb)));
        iAlb.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(iAlb, 0, 0);

    const rep = opts.rep || 1.25;
    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, rep, rep, !!opts.srgb),
      normalMap: heightToNormalTex(height, W, H, 0.70, rep, rep),
      metalness: 0.0,
      roughness: 0.92,
      envMapIntensity: 0.0,
    });
  }

  /* 4. SMOOTH CAST CONCRETE SIDE WALLS */
  function createCastConcreteMaterial(opts = {}) {
    const W = 512, H = 512;
    const n1 = makeTileNoise(8, 301), n2 = makeTileNoise(24, 302), n3 = makeTileNoise(64, 303);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const iAlb = gAlb.createImageData(W, H);
    const base = opts.rgb || [208, 203, 194];
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const m = fbm(x / W, y / H, [n1, n2, n3]);
        const sh = 0.93 + (m - 0.5) * 0.14;
        const p = (y * W + x) * 4;
        iAlb.data[p] = Math.min(255, Math.round(base[0] * sh));
        iAlb.data[p + 1] = Math.min(255, Math.round(base[1] * sh));
        iAlb.data[p + 2] = Math.min(255, Math.round(base[2] * sh));
        iAlb.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(iAlb, 0, 0);
    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, opts.rep || 1.2, opts.rep || 1.2, !!opts.srgb),
      metalness: 0.0,
      roughness: 0.92,
      transparent: !!opts.transparent,
      opacity: opts.opacity != null ? opts.opacity : 1.0,
      envMapIntensity: 0.0,
    });
  }

  /* 5. ORGANIC FRACTURED CONCRETE RUBBLE CHUNK (Real Broken Concrete Piece — Never Square Dice!) */
  function buildFracturedChunk(radius, mat, seed = 1) {
    const r = mulberry32(seed);
    const geo = new THREE.IcosahedronGeometry(radius, 1);
    const pos = geo.attributes.position;
    const sx = 0.85 + r() * 0.45, sy = 0.55 + r() * 0.35, sz = 0.75 + r() * 0.45;
    // Deterministic vertex perturbation keyed by snapped position so shared vertices stay watertight!
    const cache = {};
    for (let i = 0; i < pos.count; i++) {
      const vx = pos.getX(i), vy = pos.getY(i), vz = pos.getZ(i);
      const key = `${Math.round(vx * 100)},${Math.round(vy * 100)},${Math.round(vz * 100)}`;
      if (!(key in cache)) cache[key] = 0.76 + r() * 0.42;
      const k = cache[key];
      pos.setXYZ(i, vx * sx * k, vy * sy * k, vz * sz * k);
    }
    geo.computeVertexNormals();
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }

  /* 6. REAL 3D TWISTED TIE WIRE (KAWAT BENDRAT) */
  function buildTieWire(x, y, z, rMain, rS, mat) {
    const grp = new THREE.Group();
    grp.position.set(x, y, z);
    const wireMat = mat || new THREE.MeshStandardMaterial({ color: 0x32353b, metalness: 0.45, roughness: 0.52 });
    const rad = rMain + rS * 0.92;
    for (const rotZ of [0.58, -0.58]) {
      const loop = new THREE.Mesh(new THREE.TorusGeometry(rad * 0.94, 0.011, 8, 22), wireMat);
      loop.rotation.set(Math.PI * 0.35, Math.PI * 0.25, rotZ);
      grp.add(loop);
    }
    const tailPts = [];
    for (let i = 0; i <= 10; i++) {
      const u = i / 10, a = u * Math.PI * 4;
      tailPts.push(new THREE.Vector3(rad * 0.78 + u * 0.14, Math.sin(a) * 0.016, rad * 0.78 + u * 0.14 + Math.cos(a) * 0.016));
    }
    grp.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(tailPts), 16, 0.0085, 6, false), wireMat));
    return grp;
  }

  global.RevaPBR = {
    createRebarMaterial,
    buildSculptedRebarCylinder,
    buildSculptedRebarTube,
    createStirrupSteelMaterial,
    createConcreteSectionMaterial,
    createCastConcreteMaterial,
    buildFracturedChunk,
    buildTieWire,
  };
})(window);
