/* threejs_pbr_materials.js - REVA Lab Shared Physical-Stylized Material & 3D Geometry Engine (Three.js 0.149).
 *
 * Calibrated against the SNI 2847 Blender reference stills:
 *   - 3D Vertex-Sculpted Helical Deformed Rebar (rich oxidized iron-brown + localized burnt-orange rust pockets)
 *   - Satin Warm Pewter Steel Stirrups (cylindrical specular highlight) + 3D Twisted Tie Wire
 *   - Crisp Polygonal Voronoi Aggregate Concrete Cross-Section (mortar + gravel chips + normal relief)
 *   - Speckled Cast Concrete (warm light grey + scattered aggregate flecks & air-void pinholes)
 *   - Faceted Angular Fractured Concrete Shards (flat-shaded spall fragments)
 *   - Running-Bond Terracotta Brick Wall + Warm Grey Mortar (with height-to-normal mortar grooves)
 *   - Honey-Pine Timber Formwork Planks & Clamps + Translucent Frosted Sky-Blue Concrete Cover Glass
 *   - Ochre River-Pebble Soil Cutaway Slab + Beveled Spacer Cube with Wire Arch + Minimalist Scale Worker
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

  function makeCanvasTex(c, repX = 1, repY = 1, useSRGB = true) {
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(repX, repY);
    tex.anisotropy = 8;
    if (THREE.sRGBEncoding) {
      tex.encoding = useSRGB !== false ? THREE.sRGBEncoding : THREE.LinearEncoding;
    }
    return tex;
  }

  function _linColor(hex) {
    const c = new THREE.Color(hex);
    if (c.convertSRGBToLinear) c.convertSRGBToLinear();
    return c;
  }

  /* 1. OXIDIZED IRON-BROWN DEFORMED REBAR + SUBTLE DAPPLED EARTHY RUST */
  function createRebarMaterial(opts = {}) {
    const W = 512, H = 512;
    const height = new Float32Array(W * H);
    const n1 = makeTileNoise(6, 111), n2 = makeTileNoise(18, 112), n3 = makeTileNoise(64, 113);
    const rustPatchA = makeTileNoise(5, 151), rustPatchB = makeTileNoise(12, 152);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const cRgh = document.createElement("canvas"); cRgh.width = W; cRgh.height = H;
    const gAlb = cAlb.getContext("2d"), gRgh = cRgh.getContext("2d");
    const iAlb = gAlb.createImageData(W, H), iRgh = gRgh.createImageData(W, H);

    // Rich oxidized dark iron-brown matching FB reference rebar (#5c4e43)
    const base = opts.rgb || [92, 78, 67];
    const srgb = opts.srgb !== false;
    const smooth = (edge0, edge1, x) => {
      const t = Math.min(1, Math.max(0, (x - edge0) / (edge1 - edge0)));
      return t * t * (3 - 2 * t);
    };
    for (let y = 0; y < H; y++) {
      const v = y / H;
      for (let x = 0; x < W; x++) {
        const u = x / W;
        const m = fbm(u, v, [n1, n2, n3]);
        const rField = rustPatchA(u * 1.4, v * 2.2) * 0.55 + rustPatchB(u * 2.6, v * 3.8) * 0.45;
        // Natural dappled oxidation broken up with fine high-frequency grain (zero tiger stripes)
        const grain = 0.45 + 0.55 * n3(u * 2.0, v * 4.0);
        const rust = smooth(0.66, 0.80, rField) * grain;
        height[y * W + x] = m * 0.75 + rust * 0.25;
        const sh = 0.84 + (m - 0.5) * 0.30;
        const p = (y * W + x) * 4;
        const rr = base[0] * sh + rust * 56;
        const gg = base[1] * sh + rust * 18;
        const bb = base[2] * sh - rust * 8;
        iAlb.data[p] = Math.min(255, Math.max(0, Math.round(rr)));
        iAlb.data[p + 1] = Math.min(255, Math.max(0, Math.round(gg)));
        iAlb.data[p + 2] = Math.min(255, Math.max(0, Math.round(bb)));
        iAlb.data[p + 3] = 255;

        const rgh = Math.round((0.60 + (m - 0.5) * 0.22 + rust * 0.24) * 255);
        iRgh.data[p] = iRgh.data[p + 1] = iRgh.data[p + 2] = Math.min(242, Math.max(128, rgh));
        iRgh.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(iAlb, 0, 0);
    gRgh.putImageData(iRgh, 0, 0);

    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, 1, 3, srgb),
      normalMap: heightToNormalTex(height, W, H, 1.25, 1, 3),
      roughnessMap: makeCanvasTex(cRgh, 1, 3, false),
      metalness: opts.metalness != null ? opts.metalness : 0.24,
      roughness: 1.0,
      envMapIntensity: opts.envInt != null ? opts.envInt : 0.35,
    });
  }

  function createRebarCapMaterial(opts = {}) {
    const W = 128, H = 128;
    const n1 = makeTileNoise(16, 171), n2 = makeTileNoise(48, 172);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const iAlb = gAlb.createImageData(W, H);
    const base = opts.rgb || [104, 90, 78];
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const m = n1(x / W, y / H) * 0.6 + n2(x / W, y / H) * 0.4;
        const sh = 0.88 + (m - 0.5) * 0.24;
        const p = (y * W + x) * 4;
        iAlb.data[p] = Math.min(255, Math.round(base[0] * sh));
        iAlb.data[p + 1] = Math.min(255, Math.round(base[1] * sh));
        iAlb.data[p + 2] = Math.min(255, Math.round(base[2] * sh));
        iAlb.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(iAlb, 0, 0);
    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, 1, 1, true),
      metalness: 0.14,
      roughness: 0.78,
      envMapIntensity: 0.18,
    });
  }

  /* Helical Deformed Rebar Rib Profile (Continuous 2-spine ribs + crisp diagonal crescent lugs) */
  function rebarRibDisp(theta, axialPos, ribPitch) {
    const u = ((theta / (Math.PI * 2)) % 1 + 1) % 1;
    const dSeam = Math.min(Math.abs(u), Math.abs(u - 1), Math.abs(u - 0.5));
    const seam = Math.exp(-Math.pow(dSeam / 0.036, 2)) * 0.88;
    const side = u < 0.5 ? 1 : -1;
    const phase = ((axialPos / ribPitch + u * side * 0.70) % 1 + 1) % 1;
    const dRib = Math.abs(phase - 0.5);
    const lugMask = Math.min(1.0, Math.max(0.0, (dSeam - 0.018) / 0.032));
    const lug = Math.exp(-Math.pow(dRib / 0.145, 2.4)) * 1.0 * lugMask;
    return Math.max(seam, lug);
  }

  function _markNoInk(obj, flag) {
    if (!obj) return;
    obj.traverse((ch) => {
      ch.userData = ch.userData || {};
      ch.userData.noInk = flag;
    });
  }

  function buildSculptedRebarCylinder(r, height, mat, ribPitch, opts = {}) {
    const pitch = ribPitch || r * 0.62;
    const radialSegs = 36;
    const heightSegs = Math.max(96, Math.min(240, Math.round((height / pitch) * 4.5)));
    const geo = new THREE.CylinderGeometry(r, r, height, radialSegs, heightSegs, true);
    const pos = geo.attributes.position;
    const amp = r * 0.095;

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

    const cutMat = createRebarCapMaterial();
    const topCap = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.94, r * 1.01, r * 0.08, 28), cutMat);
    topCap.position.y = height / 2 + r * 0.035;
    topCap.castShadow = true;
    grp.add(topCap);
    const botCap = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.01, r * 0.94, r * 0.08, 28), cutMat);
    botCap.position.y = -height / 2 - r * 0.035;
    grp.add(botCap);

    if (opts.noInk !== false) _markNoInk(grp, true);
    return grp;
  }

  function buildSculptedRebarTube(curve, r, mat, ribPitch, opts = {}) {
    const len = curve.getLength();
    const pitch = ribPitch || r * 0.62;
    const tubularSegs = Math.max(96, Math.min(240, Math.round((len / pitch) * 4.5)));
    const radialSegs = 28;
    const geo = new THREE.TubeGeometry(curve, tubularSegs, r, radialSegs, false);
    const pos = geo.attributes.position;
    const uv = geo.attributes.uv;
    const amp = r * 0.095;

    for (let i = 0; i <= tubularSegs; i++) {
      const uT = i / tubularSegs;
      const center = curve.getPointAt(uT);
      const axial = uT * len;
      const endFade = Math.min(1, Math.min(axial, len - axial) / (pitch * 0.32));
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
    if (opts.noInk !== false) _markNoInk(m, true);
    return m;
  }

  /* 2. SATIN WARM PEWTER DRAWN STEEL STIRRUP (Cylindrical Specular Highlight!) */
  function createStirrupSteelMaterial(opts = {}) {
    const W = 256, H = 256;
    const n1 = makeTileNoise(12, 201), n2 = makeTileNoise(48, 202);
    const height = new Float32Array(W * H);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const iAlb = gAlb.createImageData(W, H);
    const rgb = opts.rgb || [120, 113, 106];
    const srgb = opts.srgb !== false;
    for (let y = 0; y < H; y++) {
      const v = y / H;
      for (let x = 0; x < W; x++) {
        const u = x / W;
        const streak = n1(u * 2.5, v * 0.4) * 0.65 + n2(u * 4.0, v * 0.8) * 0.35;
        height[y * W + x] = streak;
        const sh = 0.91 + (streak - 0.5) * 0.16;
        const p = (y * W + x) * 4;
        iAlb.data[p] = Math.min(255, Math.round(rgb[0] * sh));
        iAlb.data[p + 1] = Math.min(255, Math.round(rgb[1] * sh));
        iAlb.data[p + 2] = Math.min(255, Math.round(rgb[2] * sh));
        iAlb.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(iAlb, 0, 0);

    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, 1, 5, srgb),
      normalMap: heightToNormalTex(height, W, H, 0.35, 1, 5),
      metalness: opts.metalness != null ? opts.metalness : 0.36,
      roughness: opts.roughness != null ? opts.roughness : 0.38,
      envMapIntensity: opts.envInt != null ? opts.envInt : 0.65,
    });
  }

  /* 3. CRISP POLYGONAL VORONOI AGGREGATE CONCRETE CROSS-SECTION */
  function createConcreteSectionMaterial(opts = {}) {
    const W = 512, H = 512;
    const r = mulberry32(opts.seed || 401);
    const n1 = makeTileNoise(10, 415), n2 = makeTileNoise(36, 416), n3 = makeTileNoise(96, 417);
    const G = opts.density || 12;
    const pts = [];
    for (let gy = 0; gy < G; gy++) {
      for (let gx = 0; gx < G; gx++) {
        pts.push({
          x: (gx + 0.14 + r() * 0.72) / G,
          y: (gy + 0.14 + r() * 0.72) / G,
          tone: r(),
          warm: r(),
          isStone: r() < 0.82,
        });
      }
    }

    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const iAlb = gAlb.createImageData(W, H);
    const height = new Float32Array(W * H);

    const mortarRGB = opts.mortarRGB || [218, 214, 206];
    const tintRGB = opts.tintRGB || null;
    const tintAmt = opts.tintAmt || 0;
    const srgb = opts.srgb !== false;

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
        const sand = n3(u * 2.5, v * 2.5);
        // Crisp polygonal gravel facet transition matching full_29.png
        const smoothStone = best.isStone ? Math.min(1, Math.max(0, (edgeGap - 0.045) / 0.05)) : 0;

        const mK = 1.00 + (micro - 0.5) * 0.06;
        const mr = mortarRGB[0] * mK, mg = mortarRGB[1] * mK, mb = mortarRGB[2] * mK;
        const sK = 0.68 + best.tone * 0.25 + (micro - 0.5) * 0.05 + (sand - 0.5) * 0.04;
        const sr = mortarRGB[0] * sK + (best.warm - 0.5) * 26;
        const sg = mortarRGB[1] * sK + (best.warm - 0.5) * 14;
        const sb = mortarRGB[2] * sK - (best.warm - 0.5) * 10;

        let rr = mr + (sr - mr) * smoothStone;
        let gg = mg + (sg - mg) * smoothStone;
        let bb = mb + (sb - mb) * smoothStone;
        if (tintRGB && tintAmt > 0) {
          rr = rr * (1 - tintAmt) + tintRGB[0] * tintAmt;
          gg = gg * (1 - tintAmt) + tintRGB[1] * tintAmt;
          bb = bb * (1 - tintAmt) + tintRGB[2] * tintAmt;
        }
        height[y * W + x] = 0.44 + smoothStone * 0.16 + (micro - 0.5) * 0.10;
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
      map: makeCanvasTex(cAlb, rep, rep, srgb),
      normalMap: heightToNormalTex(height, W, H, 1.05, rep, rep),
      metalness: 0.0,
      roughness: 0.90,
      envMapIntensity: 0.12,
    });
  }

  /* 4. SPECKLED CAST CONCRETE (Warm Light Grey + Angular Dark Flecks & Air-Void Pinholes) */
  function createCastConcreteMaterial(opts = {}) {
    const W = 512, H = 512;
    const n1 = makeTileNoise(8, 301), n2 = makeTileNoise(24, 302), n3 = makeTileNoise(64, 303);
    const r = mulberry32(opts.seed || 309);
    const height = new Float32Array(W * H);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const iAlb = gAlb.createImageData(W, H);
    const base = opts.rgb || [206, 203, 196];
    const srgb = opts.srgb !== false;

    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const m = fbm(x / W, y / H, [n1, n2, n3]);
        height[y * W + x] = 0.5 + (m - 0.5) * 0.25;
        const sh = 0.94 + (m - 0.5) * 0.12;
        const p = (y * W + x) * 4;
        iAlb.data[p] = Math.min(255, Math.round(base[0] * sh));
        iAlb.data[p + 1] = Math.min(255, Math.round(base[1] * sh));
        iAlb.data[p + 2] = Math.min(255, Math.round(base[2] * sh));
        iAlb.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(iAlb, 0, 0);

    // Paint crisp scattered angular dark aggregate flecks & pinholes (tiled across wrap boundaries)
    const drawWrappedPoly = (cx, cy, rad, verts, col) => {
      for (const ox of [-W, 0, W]) {
        for (const oy of [-H, 0, H]) {
          gAlb.fillStyle = col;
          gAlb.beginPath();
          verts.forEach(([vx, vy], idx) => {
            const px = cx + ox + vx * rad, py = cy + oy + vy * rad;
            if (idx === 0) gAlb.moveTo(px, py);
            else gAlb.lineTo(px, py);
          });
          gAlb.closePath();
          gAlb.fill();
        }
      }
    };
    for (let i = 0; i < 260; i++) {
      const cx = r() * W, cy = r() * H;
      const rad = 2.0 + r() * 3.8;
      const nV = 4 + Math.floor(r() * 3);
      const verts = [];
      for (let k = 0; k < nV; k++) {
        const a = (k / nV) * Math.PI * 2 + r() * 0.4;
        const rr = 0.55 + r() * 0.45;
        verts.push([Math.cos(a) * rr, Math.sin(a) * rr]);
      }
      const shade = Math.round(128 + r() * 34);
      drawWrappedPoly(cx, cy, rad, verts, `rgba(${shade}, ${shade - 3}, ${shade - 7}, 0.82)`);
    }
    for (let i = 0; i < 140; i++) {
      const cx = r() * W, cy = r() * H, pr = 0.9 + r() * 1.5;
      for (const ox of [-W, 0, W]) {
        for (const oy of [-H, 0, H]) {
          gAlb.fillStyle = "rgba(112, 108, 102, 0.82)";
          gAlb.beginPath();
          gAlb.arc(cx + ox, cy + oy, pr, 0, Math.PI * 2);
          gAlb.fill();
        }
      }
    }

    const rep = opts.rep || 1.4;
    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, rep, rep, srgb),
      normalMap: heightToNormalTex(height, W, H, 0.45, rep, rep),
      metalness: 0.0,
      roughness: 0.90,
      transparent: !!opts.transparent,
      opacity: opts.opacity != null ? opts.opacity : 1.0,
      envMapIntensity: 0.12,
    });
  }

  /* 5. SHARP ANGULAR FACETED CONCRETE SHARDS (Matches Shattered Column in full_38.png!) */
  function buildFracturedChunk(radius, mat, seed = 1) {
    const r = mulberry32(seed);
    const base = new THREE.IcosahedronGeometry(radius, 0);
    const pos = base.attributes.position;
    const sx = 0.75 + r() * 0.55, sy = 0.55 + r() * 0.45, sz = 0.70 + r() * 0.50;
    const cache = {};
    for (let i = 0; i < pos.count; i++) {
      const vx = pos.getX(i), vy = pos.getY(i), vz = pos.getZ(i);
      const key = `${Math.round(vx * 100)},${Math.round(vy * 100)},${Math.round(vz * 100)}`;
      if (!(key in cache)) cache[key] = 0.68 + r() * 0.58;
      const k = cache[key];
      pos.setXYZ(i, vx * sx * k, vy * sy * k, vz * sz * k);
    }
    const geo = base.toNonIndexed ? base.toNonIndexed() : base;
    geo.computeVertexNormals();
    const useMat = mat || createCastConcreteMaterial({ seed: seed + 100 });
    const m = new THREE.Mesh(geo, useMat);
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }

  /* 6. REAL 3D TWISTED TIE WIRE (KAWAT BENDRAT) */
  function buildTieWire(x, y, z, rMain, rS, mat) {
    const grp = new THREE.Group();
    grp.position.set(x, y, z);
    const wireMat = mat || new THREE.MeshStandardMaterial({ color: _linColor(0x32363c), metalness: 0.42, roughness: 0.52 });
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

  /* 7. SLEEK 1024px RUNNING-BOND TERRACOTTA BRICK WALL + DROP-SHADOW MORTAR (Matches full_83.png!) */
  function createBrickWallMaterial(opts = {}) {
    const W = 1024, H = 1024;
    const rows = opts.rows || 10, cols = opts.cols || 3;
    const mortarPx = opts.mortarPx || 8;
    const r = mulberry32(opts.seed || 501);
    const nGrain = makeTileNoise(64, 502);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const height = new Float32Array(W * H);

    // Recessed warm grey mortar (#b8b4ac)
    gAlb.fillStyle = "#b8b4ac";
    gAlb.fillRect(0, 0, W, H);
    height.fill(0.16);

    const rowH = H / rows, colW = W / cols;
    const halfM = mortarPx * 0.5;
    for (let row = 0; row < rows; row++) {
      const stagger = (row % 2 === 1) ? colW * 0.5 : 0;
      for (let col = -1; col <= cols; col++) {
        const bx = col * colW + stagger + halfM;
        const by = row * rowH + halfM;
        const bw = colW - mortarPx;
        const bh = rowH - mortarPx;
        const tone = (r() - 0.5) * 12;
        const cr = Math.min(245, Math.round(196 + tone));
        const cg = Math.min(200, Math.round(86 + tone * 0.55));
        const cb = Math.min(160, Math.round(36 + tone * 0.35));

        // Crisp 4px directional bottom & right mortar drop-shadow strip beneath each brick
        gAlb.fillStyle = "rgba(86, 72, 62, 0.38)";
        gAlb.fillRect(bx + 2, by + bh, bw + 2, Math.min(4, halfM + 1));
        gAlb.fillRect(bx + bw, by + 2, Math.min(4, halfM + 1), bh);

        // Subtle inner rim bevel + matte terracotta face
        gAlb.fillStyle = `rgb(${Math.max(0, cr - 20)},${Math.max(0, cg - 12)},${Math.max(0, cb - 7)})`;
        gAlb.fillRect(bx, by, bw, bh);
        gAlb.fillStyle = `rgb(${cr},${cg},${cb})`;
        gAlb.fillRect(bx + 2, by + 2, Math.max(1, bw - 4), Math.max(1, bh - 4));

        const x0 = Math.max(0, Math.floor(bx)), x1 = Math.min(W, Math.ceil(bx + bw));
        const y0 = Math.max(0, Math.floor(by)), y1 = Math.min(H, Math.ceil(by + bh));
        for (let py = y0; py < y1; py++) {
          for (let px = x0; px < x1; px++) {
            const edge = Math.min(px - x0, x1 - 1 - px, py - y0, y1 - 1 - py) < 3 ? 0.65 : 0.88;
            height[py * W + px] = edge + (nGrain(px / W, py / H) - 0.5) * 0.16;
          }
        }
      }
    }
    const img = gAlb.getImageData(0, 0, W, H);
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const p = (y * W + x) * 4;
        const gn = (nGrain(x / W, y / H) - 0.5) * 16;
        img.data[p] = Math.min(255, Math.max(0, img.data[p] + gn));
        img.data[p + 1] = Math.min(255, Math.max(0, img.data[p + 1] + gn * 0.8));
        img.data[p + 2] = Math.min(255, Math.max(0, img.data[p + 2] + gn * 0.6));
      }
    }
    gAlb.putImageData(img, 0, 0);

    const repX = opts.repX || 1.5, repY = opts.repY || 1.5;
    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, repX, repY, opts.srgb !== false),
      normalMap: heightToNormalTex(height, W, H, 1.5, repX, repY),
      metalness: 0.0,
      roughness: 0.86,
      envMapIntensity: 0.12,
    });
  }

  /* 8. COZY SATIN-MATTE HONEY-PINE TIMBER FORMWORK (Subtle Natural Grain, Zero Harsh Sine Rings) */
  function createTimberFormworkMaterial(opts = {}) {
    const W = 512, H = 512;
    const isClamp = opts.tone === "clamp";
    const base = opts.rgb || (isClamp ? [208, 138, 54] : [220, 178, 102]);
    const nLong = makeTileNoise(8, isClamp ? 611 : 601);
    const nFine = makeTileNoise(48, isClamp ? 612 : 602);
    const height = new Float32Array(W * H);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const img = gAlb.createImageData(W, H);

    for (let y = 0; y < H; y++) {
      const v = y / H;
      for (let x = 0; x < W; x++) {
        const u = x / W;
        const streak = nLong(u * 5.0, v * 0.25) * 0.68 + nFine(u * 3.5, v * 0.45) * 0.32;
        const wood = 0.94 + (streak - 0.5) * 0.12;
        height[y * W + x] = 0.5 + (streak - 0.5) * 0.16;
        const p = (y * W + x) * 4;
        img.data[p] = Math.min(255, Math.round(base[0] * wood));
        img.data[p + 1] = Math.min(255, Math.round(base[1] * wood));
        img.data[p + 2] = Math.min(255, Math.round(base[2] * wood));
        img.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(img, 0, 0);

    const rep = opts.rep || 1.0;
    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, rep, rep, opts.srgb !== false),
      normalMap: heightToNormalTex(height, W, H, 0.30, rep, rep),
      metalness: 0.0,
      roughness: 0.72,
      envMapIntensity: 0.16,
    });
  }

  /* 9. FRESNEL FROSTED SKY-BLUE CONCRETE COVER GLASS SHELL (Crystal Center + Frosted Edges!) */
  function createConcreteCoverGlassMaterial(opts = {}) {
    const W = 256, H = 256;
    const n1 = makeTileNoise(10, 701), n2 = makeTileNoise(32, 702);
    const cFrost = document.createElement("canvas"); cFrost.width = W; cFrost.height = H;
    const gFrost = cFrost.getContext("2d");
    const img = gFrost.createImageData(W, H);
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const v = Math.round(fbm(x / W, y / H, [n1, n2]) * 255);
        const p = (y * W + x) * 4;
        img.data[p] = img.data[p + 1] = img.data[p + 2] = v;
        img.data[p + 3] = 255;
      }
    }
    gFrost.putImageData(img, 0, 0);

    return new THREE.ShaderMaterial({
      uniforms: {
        uColor: { value: _linColor(opts.color || 0x6fb4e2) },
        uRimColor: { value: _linColor(opts.rimColor || 0x9fd0ee) },
        uMap: { value: makeCanvasTex(cFrost, 1, 2, false) },
        uCenterAlpha: { value: opts.centerAlpha != null ? opts.centerAlpha : 0.16 },
        uEdgeAlpha: { value: opts.edgeAlpha != null ? opts.edgeAlpha : 0.58 },
      },
      vertexShader: `
        varying vec2 vUv;
        varying vec3 vNormalW;
        varying vec3 vViewPos;
        void main() {
          vUv = uv;
          vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
          vViewPos = -mvPos.xyz;
          vNormalW = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * mvPos;
        }
      `,
      fragmentShader: `
        varying vec2 vUv;
        varying vec3 vNormalW;
        varying vec3 vViewPos;
        uniform vec3 uColor;
        uniform vec3 uRimColor;
        uniform sampler2D uMap;
        uniform float uCenterAlpha;
        uniform float uEdgeAlpha;
        void main() {
          vec3 N = normalize(vNormalW);
          if (!gl_FrontFacing) N = -N;
          vec3 V = normalize(vViewPos);
          float ndv = clamp(abs(dot(N, V)), 0.0, 1.0);
          float fresnel = pow(1.0 - ndv, 1.7);
          float frost = texture2D(uMap, vUv * vec2(1.0, 2.2)).r;
          vec3 col = mix(uColor, uRimColor, fresnel * 0.65) * (0.90 + frost * 0.22);
          float alpha = mix(uCenterAlpha, uEdgeAlpha, fresnel) * (0.85 + frost * 0.28);
          gl_FragColor = vec4(col, clamp(alpha, 0.12, 0.68));
        }
      `,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
  }

  /* 10. OCHRE CLAY SOIL WITH PALE RIVER PEBBLES (Matches full_46.png cutaway base!) */
  function createSoilCutawayMaterial(opts = {}) {
    const W = 512, H = 512;
    const n1 = makeTileNoise(8, 801), n2 = makeTileNoise(24, 802);
    const r = mulberry32(opts.seed || 803);
    const cAlb = document.createElement("canvas"); cAlb.width = W; cAlb.height = H;
    const gAlb = cAlb.getContext("2d");
    const img = gAlb.createImageData(W, H);
    const base = opts.rgb || [156, 118, 76];
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const m = fbm(x / W, y / H, [n1, n2]);
        const sh = 0.90 + (m - 0.5) * 0.20;
        const p = (y * W + x) * 4;
        img.data[p] = Math.min(255, Math.round(base[0] * sh));
        img.data[p + 1] = Math.min(255, Math.round(base[1] * sh));
        img.data[p + 2] = Math.min(255, Math.round(base[2] * sh));
        img.data[p + 3] = 255;
      }
    }
    gAlb.putImageData(img, 0, 0);
    for (let i = 0; i < 48; i++) {
      const px = r() * W, py = r() * H;
      const rx = 5 + r() * 14, ry = 3 + r() * 9;
      const ang = r() * Math.PI;
      const tone = 186 + Math.round(r() * 34);
      gAlb.save();
      gAlb.translate(px, py);
      gAlb.rotate(ang);
      gAlb.fillStyle = `rgb(${tone}, ${tone - 10}, ${tone - 24})`;
      gAlb.beginPath();
      gAlb.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
      gAlb.fill();
      gAlb.restore();
    }
    const rep = opts.rep || 1.5;
    return new THREE.MeshStandardMaterial({
      map: makeCanvasTex(cAlb, rep, rep, opts.srgb !== false),
      metalness: 0.0,
      roughness: 0.94,
      envMapIntensity: 0.08,
    });
  }

  /* 11. BEVELED BOX & CONCRETE DECKING SPACER WITH WIRE ARCH (Matches full_95.png!) */
  function buildBeveledBox(w, h, d, bevel = 0.04, mat) {
    const b = Math.min(bevel, w * 0.24, h * 0.24, d * 0.24);
    const iw = w - 2 * b, ih = h - 2 * b, id = d - 2 * b;
    const hw = iw / 2, hh = ih / 2;
    const s = new THREE.Shape();
    s.moveTo(-hw, -hh);
    s.lineTo(hw, -hh);
    s.lineTo(hw, hh);
    s.lineTo(-hw, hh);
    s.closePath();
    const geo = new THREE.ExtrudeGeometry(s, {
      depth: id, bevelEnabled: true, bevelThickness: b, bevelSize: b, bevelSegments: 2,
    });
    geo.translate(0, 0, -id / 2);
    geo.computeVertexNormals();
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }

  function buildDeckingSpacerPBR(size = 0.22, concreteMat, wireMat) {
    const grp = new THREE.Group();
    const cMat = concreteMat || createCastConcreteMaterial({ rgb: [212, 210, 206], seed: 910 });
    const wMat = wireMat || new THREE.MeshStandardMaterial({ color: _linColor(0x3b4048), metalness: 0.48, roughness: 0.45 });
    grp.add(buildBeveledBox(size, size * 0.88, size, size * 0.14, cMat));
    const archCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-size * 0.30, size * 0.40, 0),
      new THREE.Vector3(-size * 0.22, size * 0.70, 0),
      new THREE.Vector3(0, size * 0.78, 0),
      new THREE.Vector3(size * 0.22, size * 0.70, 0),
      new THREE.Vector3(size * 0.30, size * 0.40, 0),
    ]);
    const arch = new THREE.Mesh(new THREE.TubeGeometry(archCurve, 20, size * 0.042, 8, false), wMat);
    arch.castShadow = true;
    grp.add(arch);
    return grp;
  }

  /* 12. MINIMALIST SCALE SITE WORKER FIGURE (Matches full_46.png!) */
  function buildWorkerFigure(opts = {}) {
    const scale = opts.scale || 1.0;
    const grp = new THREE.Group();
    const pantsMat = new THREE.MeshStandardMaterial({ color: _linColor(0x1f3c6e), roughness: 0.82, metalness: 0.0 });
    const shirtMat = new THREE.MeshStandardMaterial({ color: _linColor(0xe67122), roughness: 0.72, metalness: 0.0 });
    const skinMat  = new THREE.MeshStandardMaterial({ color: _linColor(0xdfb28b), roughness: 0.76, metalness: 0.0 });
    const helmMat  = new THREE.MeshStandardMaterial({ color: _linColor(0xf4cf3e), roughness: 0.42, metalness: 0.05 });
    for (const lx of [-0.09, 0.09]) {
      const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.070, 0.78, 16), pantsMat);
      leg.position.set(lx, 0.39, 0);
      leg.castShadow = true;
      grp.add(leg);
    }
    const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.17, 0.56, 20), shirtMat);
    torso.position.y = 1.04; torso.scale.set(1.05, 1.0, 0.72); torso.castShadow = true;
    grp.add(torso);
    for (const ax of [-0.22, 0.22]) {
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.050, 0.50, 14), shirtMat);
      arm.position.set(ax, 1.02, 0); arm.castShadow = true;
      grp.add(arm);
    }
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.145, 20, 16), skinMat);
    head.position.y = 1.48; head.castShadow = true;
    grp.add(head);
    const helm = new THREE.Mesh(new THREE.SphereGeometry(0.165, 20, 12, 0, Math.PI * 2, 0, Math.PI * 0.55), helmMat);
    helm.position.y = 1.50; helm.castShadow = true;
    grp.add(helm);
    const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.19, 0.025, 20), helmMat);
    brim.position.set(0, 1.50, 0.03);
    grp.add(brim);
    grp.scale.setScalar(scale);
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
    createBrickWallMaterial,
    createTimberFormworkMaterial,
    createConcreteCoverGlassMaterial,
    createSoilCutawayMaterial,
    buildBeveledBox,
    buildDeckingSpacerPBR,
    buildWorkerFigure,
  };
})(window);
