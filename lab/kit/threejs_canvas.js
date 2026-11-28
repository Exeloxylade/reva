/* threejs_canvas.js - REVA Lab "Blender-Style Cozy Matte + Silhouette Ink" Three.js Canvas Engine.
 *
 * Bridges the gap between fast Three.js WebGL (~5 min full video render) and cozy Blender EEVEE aesthetics:
 *   1. Soft warm daylight sky-to-horizon cyclorama gradient + subtle procedural sky-dome env reflections
 *   2. Silhouette-Only Ink Contour Pass (depth + sharp silhouette edges ONLY; never smudges rebar ribs!)
 *   3. Procedural Crevice Contact AO Ribbons & Discs (fakes Blender GTAO under stirrups, bars, and slabs in 0.1 ms!)
 *   4. Organic Muted-Sage Lawn + Curved Ribbon Grass Tufts (zero spiky cones or neon yellow-green!)
 *   5. Minimal Reference-Style Floating Tags + Crisp 3D-Projected Calipers (generous breathing room!)
 */
(function (global) {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const V = (x, y, z) => new THREE.Vector3(x, y, z);

  function mulberry32(seed) {
    let a = seed | 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* Procedural Soft Daylight Sky-Dome Environment Map (gives warm matte bounce without chrome glare!) */
  function buildDaylightEnv(renderer) {
    const c = document.createElement("canvas");
    c.width = 256; c.height = 128;
    const g = c.getContext("2d");
    const gr = g.createLinearGradient(0, 0, 0, 128);
    gr.addColorStop(0.0, "#eef5fa");
    gr.addColorStop(0.45, "#f7f5ee");
    gr.addColorStop(0.55, "#c5d1b8");
    gr.addColorStop(1.0, "#8fa07e");
    g.fillStyle = gr; g.fillRect(0, 0, 256, 128);
    g.fillStyle = "rgba(255,252,240,0.85)";
    g.fillRect(36, 18, 68, 32);
    const tex = new THREE.CanvasTexture(c);
    tex.mapping = THREE.EquirectangularReflectionMapping;
    const pmrem = new THREE.PMREMGenerator(renderer);
    const env = pmrem.fromEquirectangular(tex).texture;
    tex.dispose(); pmrem.dispose();
    return env;
  }

  /* Soft Radial Contact AO Disc (Grounds Vertical Rebars & Posts like Real Blender GTAO!) */
  function makeAoDisc(radius, opacity = 0.34) {
    const c = document.createElement("canvas"); c.width = 128; c.height = 128;
    const g = c.getContext("2d");
    const gr = g.createRadialGradient(64, 64, 14, 64, 64, 60);
    gr.addColorStop(0.0, `rgba(28, 24, 20, ${opacity})`);
    gr.addColorStop(0.55, `rgba(28, 24, 20, ${(opacity * 0.42).toFixed(3)})`);
    gr.addColorStop(1.0, "rgba(28, 24, 20, 0)");
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(radius * 2, radius * 2),
      new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false })
    );
    m.rotation.x = -Math.PI / 2;
    return m;
  }

  /* Soft Contact AO Shadow Ribbon Underneath a Horizontal Stirrup Loop (The #1 Blender Visual Cue!) */
  function makeStirrupAoShadow(c, rMain, rS, extFactor = 6.0, ySurf = 1.028, opacity = 0.28) {
    const d = rS * 2.0;
    const R = Math.max(rMain + rS, 2.5 * d);
    const lExt = extFactor * d;
    const half = c + R + rS * 2.6;
    const sz = 512;
    const cv = document.createElement("canvas"); cv.width = sz; cv.height = sz;
    const g = cv.getContext("2d");
    const toPx = (v) => (v / (half * 2) + 0.5) * sz;

    const pts = [];
    function arc(cx, cz, a0, a1, n) {
      for (let i = 0; i <= n; i++) {
        const a = a0 + (a1 - a0) * (i / n);
        pts.push([cx + Math.cos(a) * R, cz + Math.sin(a) * R]);
      }
    }
    const dir = -Math.SQRT1_2;
    const tanA = [c + Math.cos(-Math.PI * 0.25) * R, c + Math.sin(-Math.PI * 0.25) * R];
    pts.push([tanA[0] + dir * lExt, tanA[1] + dir * lExt], tanA);
    arc(c, c, -Math.PI * 0.25, Math.PI * 0.5, 10);
    arc(-c, c, Math.PI * 0.5, Math.PI, 8);
    arc(-c, -c, Math.PI, Math.PI * 1.5, 8);
    arc(c, -c, -Math.PI * 0.5, 0, 8);
    arc(c, c, 0, Math.PI * 0.75, 10);
    const tanB = [c + Math.cos(Math.PI * 0.75) * R, c + Math.sin(Math.PI * 0.75) * R];
    pts.push([tanB[0] + dir * lExt, tanB[1] + dir * lExt]);

    g.save();
    g.filter = "blur(10px)";
    g.strokeStyle = `rgba(34, 28, 22, ${opacity})`;
    g.lineWidth = Math.max(14, (rS * 3.8 / (half * 2)) * sz);
    g.lineCap = "round";
    g.lineJoin = "round";
    g.beginPath();
    pts.forEach(([px, pz], idx) => {
      if (idx === 0) g.moveTo(toPx(px), toPx(pz));
      else g.lineTo(toPx(px), toPx(pz));
    });
    g.stroke();
    g.restore();

    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(half * 2, half * 2),
      new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(cv), transparent: true, depthWrite: false })
    );
    m.rotation.x = -Math.PI / 2;
    m.position.set(0.05, ySurf, 0.05); // Slight warm sun-angle offset + soft blur under the entire hoop!
    return m;
  }

  /* Organic Muted-Sage Lawn + Graceful Curved Ribbon Grass Tufts (Matches Cozy Blender Diorama!) */
  function buildCozyGrassDiorama(clearHalf, noInkArr) {
    const grp = new THREE.Group();

    // Subtle organic mottled cozy meadow-green lawn texture (calibrated to match viral reference, zero washout!)
    const cv = document.createElement("canvas"); cv.width = 512; cv.height = 512;
    const g = cv.getContext("2d");
    g.fillStyle = "#76a84c"; g.fillRect(0, 0, 512, 512);
    const rng = mulberry32(77);
    for (let i = 0; i < 180; i++) {
      g.fillStyle = rng() > 0.5 ? "rgba(136, 184, 86, 0.20)" : "rgba(82, 124, 48, 0.18)";
      g.beginPath(); g.arc(rng() * 512, rng() * 512, 18 + rng() * 44, 0, Math.PI * 2); g.fill();
    }
    const lawnTex = new THREE.CanvasTexture(cv);
    lawnTex.wrapS = lawnTex.wrapT = THREE.RepeatWrapping;
    lawnTex.repeat.set(3, 3);
    const lawn = new THREE.Mesh(
      new THREE.BoxGeometry(18, 0.3, 18),
      new THREE.MeshStandardMaterial({ map: lawnTex, roughness: 0.94, metalness: 0.0, envMapIntensity: 0.0 })
    );
    lawn.position.y = -0.15;
    lawn.receiveShadow = true;
    grp.add(lawn);
    if (noInkArr) noInkArr.push(lawn);

    // Build ONE merged curved-ribbon grass tuft BufferGeometry (graceful thin blades, zero ugly cones!)
    const pos = [], nor = [];
    const rng2 = mulberry32(42);
    for (let t = 0; t < 130; t++) {
      const gx = (rng2() - 0.5) * 10.2, gz = (rng2() - 0.5) * 10.2;
      if (Math.abs(gx) < clearHalf + 0.24 && Math.abs(gz) < clearHalf + 0.24) continue;
      const blades = 2 + Math.floor(rng2() * 3);
      for (let b = 0; b < blades; b++) {
        const ang = rng2() * Math.PI * 2;
        const h = 0.16 + rng2() * 0.18;
        const w = 0.026 + rng2() * 0.012;
        const lean = 0.06 + rng2() * 0.10;
        const bx = gx + (rng2() - 0.5) * 0.14;
        const bz = gz + (rng2() - 0.5) * 0.14;
        const ca = Math.cos(ang), sa = Math.sin(ang);
        const p0 = [bx - sa * w, 0.0, bz + ca * w];
        const p1 = [bx + sa * w, 0.0, bz - ca * w];
        const p2 = [bx + ca * lean * 0.42 + sa * w * 0.52, h * 0.54, bz + sa * lean * 0.42 - ca * w * 0.52];
        const p3 = [bx + ca * lean * 0.42 - sa * w * 0.52, h * 0.54, bz + sa * lean * 0.42 + ca * w * 0.52];
        const p4 = [bx + ca * lean, h, bz + sa * lean];
        const tris = [[p0, p1, p2], [p0, p2, p3], [p3, p2, p4]];
        for (const tri of tris) {
          for (const pt of tri) {
            pos.push(pt[0], pt[1], pt[2]);
            nor.push(0, 1, 0);
          }
        }
      }
    }
    const tuftGeo = new THREE.BufferGeometry();
    tuftGeo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    tuftGeo.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    tuftGeo.computeVertexNormals();
    const tufts = new THREE.Mesh(
      tuftGeo,
      new THREE.MeshStandardMaterial({ color: 0x548232, roughness: 0.90, metalness: 0.0, envMapIntensity: 0.0, side: THREE.DoubleSide })
    );
    tufts.castShadow = true;
    grp.add(tufts);
    if (noInkArr) noInkArr.push(tufts);
    return grp;
  }

  /* Boot REVA Cozy Blender-Style Three.js Canvas (2x SSAA + Silhouette-Only Subtle Ink Pass + Calibrated Daylight) */
  function boot(opts = {}) {
    const W = opts.W || 1080, H = opts.H || 1920;
    const bootW3 = W3.boot({
      host: opts.host || document.getElementById("stage"),
      W, H,
      ssaa: opts.ssaa || 2,
      sky: opts.sky != null ? opts.sky : 0xcfe0ec,
      outline: opts.outline !== false,
      ink: opts.ink != null ? opts.ink : 0x352e28,
      line: opts.line != null ? opts.line : 1.35,
      // SILHOUETTE-ONLY TUNING: depthK catches clean silhouette contours; high normK (0.78) avoids smudging rebar ribs!
      depthK: opts.depthK != null ? opts.depthK : 0.017,
      normK: opts.normK != null ? opts.normK : 0.78,
      shadows: true,
      shadowMap: 2048,
      sunDir: opts.sunDir || [44, 88, 56],
      // Calibrated total irradiance (~1.05 max) so creamy concrete & pastel grass NEVER blow out to white!
      hemi: opts.hemi || [0xfdfaf3, 0x9eb098, 0.56],
      sunK: opts.sunK != null ? opts.sunK : 0.44,
      fov: opts.fov || 32,
    });
    const { renderer, scene, post } = bootW3;
    post.uniforms.inkK.value = opts.inkK != null ? opts.inkK : 0.58; // Crisp thin warm charcoal contour!
    scene.fog = new THREE.Fog(opts.sky != null ? opts.sky : 0xcfe0ec, 48, 190);
    if (renderer) {
      scene.environment = buildDaylightEnv(renderer);
    }

    // Subtle cool sky bounce light opposite key sun (creamy Blender-like soft shadows!)
    const fill = new THREE.DirectionalLight(0xd4e6f5, 0.14);
    fill.position.set(-45, 38, -42);
    scene.add(fill);

    return Object.assign(bootW3, {
      makeAoDisc,
      makeStirrupAoShadow,
      buildCozyGrassDiorama,
    });
  }

  /* Clean Minimal Reference-Style Floating HUD (Compact Tags + Exact Calipers, Maximum Breathing Room!) */
  function createMinimalHud(camera, svg, host, W = 1080, H = 1920) {
    function proj(pt) {
      const p = pt.clone().project(camera);
      return { x: (p.x * 0.5 + 0.5) * W, y: (-p.y * 0.5 + 0.5) * H };
    }
    function mk(tag, attrs) {
      const el = document.createElementNS(NS, tag);
      for (const k in attrs) el.setAttribute(k, attrs[k]);
      svg.appendChild(el);
      return el;
    }
    function clear() { svg.innerHTML = ""; host.innerHTML = ""; }

    function tag(pt, text, cls = "green", dx = 0, dy = 0, withLine = false) {
      const s = proj(pt);
      const el = document.createElement("div");
      el.className = "rtag " + cls;
      el.textContent = text;
      host.appendChild(el);
      const hw = (el.offsetWidth || 120) / 2;
      const tx = Math.max(32 + hw, Math.min(W - 32 - hw, s.x + dx));
      const ty = Math.max(220, Math.min(1610, s.y + dy));
      el.style.transform = `translate(-50%, -50%) translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px)`;
      if (withLine) {
        mk("line", { x1: s.x, y1: s.y, x2: tx, y2: ty, stroke: "#262a30", "stroke-width": 2.8, "stroke-linecap": "round" });
        mk("circle", { cx: s.x, cy: s.y, r: 5.5, fill: "#ffffff", stroke: cls === "red" ? "#dc2626" : "#15803d", "stroke-width": 3 });
      }
      return el;
    }

    function caliper(p1, p2, label, cls = "green", colorHex = "#16a34a", offX = 0, offY = 0, tagDx = 0, tagDy = 0) {
      const a = proj(p1), b = proj(p2);
      const ax = a.x + offX, ay = a.y + offY, bx = b.x + offX, by = b.y + offY;
      const d = Math.hypot(bx - ax, by - ay) || 1;
      const nx = -(by - ay) / d * 10, ny = (bx - ax) / d * 10;
      mk("line", { x1: ax, y1: ay, x2: bx, y2: by, stroke: colorHex, "stroke-width": 3.5, "stroke-linecap": "round" });
      mk("line", { x1: ax - nx, y1: ay - ny, x2: ax + nx, y2: ay + ny, stroke: colorHex, "stroke-width": 3, "stroke-linecap": "round" });
      mk("line", { x1: bx - nx, y1: by - ny, x2: bx + nx, y2: by + ny, stroke: colorHex, "stroke-width": 3, "stroke-linecap": "round" });
      const el = document.createElement("div");
      el.className = "rtag " + cls;
      el.textContent = label;
      host.appendChild(el);
      const hw = (el.offsetWidth || 90) / 2;
      const mx = Math.max(32 + hw, Math.min(W - 32 - hw, (ax + bx) / 2 + tagDx));
      const my = Math.max(220, Math.min(1610, (ay + by) / 2 + tagDy));
      el.style.transform = `translate(-50%, -50%) translate(${mx.toFixed(1)}px, ${my.toFixed(1)}px)`;
      return el;
    }

    return { proj, mk, clear, tag, caliper };
  }

  global.RevaCanvas = { boot, createMinimalHud, makeAoDisc, makeStirrupAoShadow, buildCozyGrassDiorama };
})(window);
