/* threejs_canvas.js - REVA Lab "Blender-Style Cozy Matte + Depth SSAO + Silhouette Ink" Three.js Engine.
 *
 * Self-contained pipeline (requires ONLY three.min.js; zero external W3 dependency):
 *   1. Soft warm daylight sky-to-horizon cyclorama gradient + PMREM sky-dome env reflections
 *   2. Self-contained 2x SSAA post-process:
 *        - 8-tap Depth Contact AO (SSAO) for automatic Blender-like crevice/under-bar grounding
 *        - Silhouette-Only Warm Charcoal Ink Contour (depth + normal edges; skips obj.userData.noInk)
 *        - ACES Filmic Tone Mapping + sRGB gamma output
 *   3. Procedural Crevice Contact AO Ribbons & Discs under stirrups and bars
 *   4. Fresh Spring-Meadow Grass Diorama + Tapered V-Cluster Grass Tufts + Optional Soil Slab
 *   5. Auto-injected Reference-Style Floating Pill Header, Bottom Caption Pill, HUD Tags & Calipers
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

  function markNoInk(obj, flag = true) {
    if (!obj) return obj;
    obj.traverse((ch) => {
      ch.userData = ch.userData || {};
      ch.userData.noInk = flag;
    });
    return obj;
  }

  function _ensureStyles() {
    if (document.getElementById("reva-canvas-style")) return;
    const st = document.createElement("style");
    st.id = "reva-canvas-style";
    st.textContent = `
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body {
        width: 100%; height: 100%; overflow: hidden;
        background: #dce5ec;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
      }
      #stage, canvas, svg#lines, #hud-host {
        position: fixed; inset: 0; width: 100%; height: 100%;
        display: block; pointer-events: none;
      }
      #rc-header {
        position: fixed; top: 124px; left: 50%; transform: translateX(-50%);
        z-index: 30; pointer-events: none;
      }
      #rc-pill {
        display: inline-flex; align-items: center; gap: 18px;
        padding: 12px 34px 12px 14px; border-radius: 999px;
        background: rgba(255, 255, 255, 0.97);
        box-shadow: 0 10px 28px rgba(18, 28, 42, 0.14);
        font-weight: 800; font-size: 38px; line-height: 1.1;
        color: #14171c; white-space: nowrap;
      }
      #rc-pill .rc-num {
        width: 54px; height: 54px; border-radius: 50%;
        background: #1e88e5; color: #ffffff;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 31px; font-weight: 800; flex: 0 0 auto;
      }
      #rc-caption {
        position: fixed; bottom: 190px; left: 50%; transform: translateX(-50%);
        z-index: 30; pointer-events: none;
        padding: 15px 30px; border-radius: 18px;
        background: rgba(24, 28, 34, 0.92);
        box-shadow: 0 10px 26px rgba(10, 14, 20, 0.24);
        color: #ffffff; font-weight: 700; font-size: 34px; line-height: 1.25;
        white-space: nowrap; text-align: center;
      }
      .rtag {
        position: absolute; padding: 9px 22px; border-radius: 14px;
        font-weight: 800; font-size: 28px; line-height: 1.18;
        color: #ffffff; background: #1e293b;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.22);
        white-space: pre-line; text-align: center; letter-spacing: -0.01em;
      }
      .rtag.green { background: #12985d; }
      .rtag.blue  { background: #248bf0; }
      .rtag.red   { background: #e13b33; }
      .rtag.gray, .rtag.muted { background: #96989c; }
      .rtag.amber { background: #d97706; }
      .rtag.num-badge {
        width: 34px; height: 34px; padding: 0; border-radius: 50%;
        background: #ffffff; color: #1e88e5; border: 3px solid #1e88e5;
        font-size: 20px; font-weight: 800;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.20);
      }
    `;
    document.head.appendChild(st);
  }

  /* Soft vertical sky-to-horizon cyclorama background texture */
  function buildSkyBackdropTex(topHex = "#b8cad8", midHex = "#dae4ec", botHex = "#eef2f5") {
    const c = document.createElement("canvas");
    c.width = 16; c.height = 512;
    const g = c.getContext("2d");
    const gr = g.createLinearGradient(0, 0, 0, 512);
    gr.addColorStop(0.0, topHex);
    gr.addColorStop(0.55, midHex);
    gr.addColorStop(1.0, botHex);
    g.fillStyle = gr;
    g.fillRect(0, 0, 16, 512);
    const tex = new THREE.CanvasTexture(c);
    if (THREE.sRGBEncoding) tex.encoding = THREE.sRGBEncoding;
    return tex;
  }

  /* Procedural Soft Daylight Sky-Dome Environment Map (gives satin steel highlights without chrome glare) */
  function buildDaylightEnv(renderer) {
    const c = document.createElement("canvas");
    c.width = 256; c.height = 128;
    const g = c.getContext("2d");
    const gr = g.createLinearGradient(0, 0, 0, 128);
    gr.addColorStop(0.0, "#eef5fc");
    gr.addColorStop(0.45, "#f9f7f1");
    gr.addColorStop(0.55, "#c5d9b2");
    gr.addColorStop(1.0, "#8ba66e");
    g.fillStyle = gr;
    g.fillRect(0, 0, 256, 128);
    // Warm soft sun-key highlight blob for satin cylindrical rebar/stirrup specular
    const sunGrad = g.createRadialGradient(78, 34, 4, 78, 34, 42);
    sunGrad.addColorStop(0.0, "rgba(255, 253, 244, 0.96)");
    sunGrad.addColorStop(1.0, "rgba(255, 253, 244, 0.0)");
    g.fillStyle = sunGrad;
    g.fillRect(28, 0, 100, 84);
    const tex = new THREE.CanvasTexture(c);
    tex.mapping = THREE.EquirectangularReflectionMapping;
    if (THREE.sRGBEncoding) tex.encoding = THREE.sRGBEncoding;
    const pmrem = new THREE.PMREMGenerator(renderer);
    const env = pmrem.fromEquirectangular(tex).texture;
    tex.dispose();
    pmrem.dispose();
    return env;
  }

  /* Soft Radial Contact AO Disc (Grounds Vertical Rebars & Posts like Real Blender GTAO) */
  function makeAoDisc(radius, opacity = 0.36) {
    const c = document.createElement("canvas");
    c.width = 128; c.height = 128;
    const g = c.getContext("2d");
    const gr = g.createRadialGradient(64, 64, 12, 64, 64, 60);
    gr.addColorStop(0.0, `rgba(26, 22, 18, ${opacity})`);
    gr.addColorStop(0.55, `rgba(26, 22, 18, ${(opacity * 0.42).toFixed(3)})`);
    gr.addColorStop(1.0, "rgba(26, 22, 18, 0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(c);
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(radius * 2, radius * 2),
      new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false })
    );
    m.rotation.x = -Math.PI / 2;
    markNoInk(m, true);
    return m;
  }

  /* Soft Contact AO Shadow Ribbon Underneath a Horizontal Stirrup Loop */
  function makeStirrupAoShadow(c, rMain, rS, extFactor = 6.0, ySurf = 1.028, opacity = 0.30) {
    const d = rS * 2.0;
    const R = Math.max(rMain + rS, 2.5 * d);
    const lExt = extFactor * d;
    const half = c + R + rS * 2.6;
    const sz = 512;
    const cv = document.createElement("canvas");
    cv.width = sz; cv.height = sz;
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
    g.strokeStyle = `rgba(30, 24, 18, ${opacity})`;
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

    const tex = new THREE.CanvasTexture(cv);
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(half * 2, half * 2),
      new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false })
    );
    m.rotation.x = -Math.PI / 2;
    m.position.set(0.05, ySurf, 0.05);
    markNoInk(m, true);
    return m;
  }

  /* Fresh Spring-Meadow Grass Diorama + Crisp V-Cluster Tufts + Optional Soil Cutaway Base */
  function buildCozyGrassDiorama(clearHalf, noInkArr, opts = {}) {
    const grp = new THREE.Group();
    const lawnSize = opts.size || 18;
    const tuftRadius = opts.tuftArea || 11.2;
    const tuftCount = opts.tuftCount || 220;
    const withSoil = opts.withSoil !== false;

    const cv = document.createElement("canvas");
    cv.width = 512; cv.height = 512;
    const g = cv.getContext("2d");
    // Fresh spring meadow green calibrated to land on #9fcc70 after ACES + sRGB output
    g.fillStyle = "#88bd57";
    g.fillRect(0, 0, 512, 512);
    const rng = mulberry32(77);
    for (let i = 0; i < 200; i++) {
      g.fillStyle = rng() > 0.5 ? "rgba(152, 204, 102, 0.24)" : "rgba(116, 168, 70, 0.18)";
      g.beginPath();
      g.arc(rng() * 512, rng() * 512, 16 + rng() * 44, 0, Math.PI * 2);
      g.fill();
    }
    const lawnTex = new THREE.CanvasTexture(cv);
    lawnTex.wrapS = lawnTex.wrapT = THREE.RepeatWrapping;
    lawnTex.repeat.set(3, 3);
    if (THREE.sRGBEncoding) lawnTex.encoding = THREE.sRGBEncoding;

    const lawnH = withSoil ? 0.16 : 0.30;
    const lawn = new THREE.Mesh(
      new THREE.BoxGeometry(lawnSize, lawnH, lawnSize),
      new THREE.MeshStandardMaterial({ map: lawnTex, roughness: 0.90, metalness: 0.0, envMapIntensity: 0.12 })
    );
    lawn.position.y = -lawnH * 0.5;
    lawn.receiveShadow = true;
    grp.add(lawn);
    markNoInk(lawn, true);
    if (noInkArr) noInkArr.push(lawn);

    if (withSoil) {
      const soilH = opts.soilHeight || 0.72;
      const soilMat = (global.RevaPBR && global.RevaPBR.createSoilCutawayMaterial)
        ? global.RevaPBR.createSoilCutawayMaterial({ rep: 2 })
        : new THREE.MeshStandardMaterial({ color: 0x9a744b, roughness: 0.92, metalness: 0.0, envMapIntensity: 0.08 });
      const soil = new THREE.Mesh(new THREE.BoxGeometry(lawnSize, soilH, lawnSize), soilMat);
      soil.position.y = -lawnH - soilH * 0.5;
      soil.receiveShadow = true;
      grp.add(soil);
      markNoInk(soil, true);
      if (noInkArr) noInkArr.push(soil);
    }

    // Merged V-cluster tapered grass blades with vertex color gradient (#457322 base -> #83bd4d tip)
    const pos = [];
    const col = [];
    const rng2 = mulberry32(42);
    const cBase = new THREE.Color(0x457322);
    const cTip = new THREE.Color(0x83bd4d);
    if (cBase.convertSRGBToLinear) { cBase.convertSRGBToLinear(); cTip.convertSRGBToLinear(); }

    for (let t = 0; t < tuftCount; t++) {
      const gx = (rng2() - 0.5) * tuftRadius;
      const gz = (rng2() - 0.5) * tuftRadius;
      if (clearHalf > 0 && Math.abs(gx) < clearHalf + 0.24 && Math.abs(gz) < clearHalf + 0.24) continue;
      const blades = 3 + Math.floor(rng2() * 3);
      for (let b = 0; b < blades; b++) {
        const ang = (b / blades) * Math.PI * 2 + (rng2() - 0.5) * 0.6;
        const h = 0.19 + rng2() * 0.18;
        const w = 0.024 + rng2() * 0.010;
        const lean = 0.07 + rng2() * 0.09;
        const ca = Math.cos(ang), sa = Math.sin(ang);
        const bx = gx + ca * 0.025, bz = gz + sa * 0.025;
        const p0 = [bx - sa * w, 0.0, bz + ca * w];
        const p1 = [bx + sa * w, 0.0, bz - ca * w];
        const p2 = [bx + ca * lean * 0.45 + sa * w * 0.48, h * 0.56, bz + sa * lean * 0.45 - ca * w * 0.48];
        const p3 = [bx + ca * lean * 0.45 - sa * w * 0.48, h * 0.56, bz + sa * lean * 0.45 + ca * w * 0.48];
        const p4 = [bx + ca * lean, h, bz + sa * lean];
        const tris = [
          [[p0, cBase], [p1, cBase], [p2, cTip]],
          [[p0, cBase], [p2, cTip], [p3, cTip]],
          [[p3, cTip], [p2, cTip], [p4, cTip]],
        ];
        for (const tri of tris) {
          for (const [pt, vc] of tri) {
            pos.push(pt[0], pt[1], pt[2]);
            col.push(vc.r, vc.g, vc.b);
          }
        }
      }
    }

    const tuftGeo = new THREE.BufferGeometry();
    tuftGeo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    tuftGeo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    tuftGeo.computeVertexNormals();
    const tufts = new THREE.Mesh(
      tuftGeo,
      new THREE.MeshStandardMaterial({
        vertexColors: true, roughness: 0.88, metalness: 0.0, envMapIntensity: 0.10, side: THREE.DoubleSide,
      })
    );
    tufts.castShadow = true;
    tufts.receiveShadow = true;
    grp.add(tufts);
    markNoInk(tufts, true);
    if (noInkArr) noInkArr.push(tufts);
    return grp;
  }

  /* Post-Processing GLSL Shader: 8-tap Depth Contact AO + Silhouette Ink + ACES Filmic + sRGB */
  function _buildPostPass(rtW, rtH, camera, opts) {
    const postScene = new THREE.Scene();
    const postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const inkCol = new THREE.Color(opts.ink != null ? opts.ink : 0x2e2925);
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        tColor: { value: null },
        tDepth: { value: null },
        tNorm: { value: null },
        uTexel: { value: new THREE.Vector2(1 / rtW, 1 / rtH) },
        uNear: { value: camera.near },
        uFar: { value: camera.far },
        uAoStrength: { value: opts.aoStrength != null ? opts.aoStrength : 0.56 },
        uAoRadius: { value: opts.aoRadius != null ? opts.aoRadius : 14.0 },
        uDepthK: { value: opts.depthK != null ? opts.depthK : 0.010 },
        uNormK: { value: opts.normK != null ? opts.normK : 0.54 },
        uLine: { value: opts.line != null ? opts.line : 1.45 },
        inkK: { value: opts.inkK != null ? opts.inkK : 0.54 },
        uInkColor: { value: inkCol },
        uOutline: { value: opts.outline !== false ? 1.0 : 0.0 },
        uExposure: { value: opts.exposure != null ? opts.exposure : 0.92 },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        precision highp float;
        varying vec2 vUv;
        uniform sampler2D tColor;
        uniform sampler2D tDepth;
        uniform sampler2D tNorm;
        uniform vec2 uTexel;
        uniform float uNear;
        uniform float uFar;
        uniform float uAoStrength;
        uniform float uAoRadius;
        uniform float uDepthK;
        uniform float uNormK;
        uniform float uLine;
        uniform float inkK;
        uniform vec3 uInkColor;
        uniform float uOutline;
        uniform float uExposure;

        float linDepth(vec2 uv) {
          float z = texture2D(tDepth, clamp(uv, vec2(0.0), vec2(1.0))).x;
          float ndc = z * 2.0 - 1.0;
          return (2.0 * uNear * uFar) / max(0.0001, (uFar + uNear - ndc * (uFar - uNear)));
        }

        vec3 acesFilm(vec3 x) {
          float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
          return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
        }

        void main() {
          vec4 base = texture2D(tColor, vUv);
          vec3 rgb = base.rgb;
          float dc = linDepth(vUv);
          float isGeo = step(dc, uFar * 0.94);

          // 1. 2-Ring 16-Tap Multi-Scale Depth GTAO (tight contact crevices + wide architectural corners)
          if (uAoStrength > 0.001 && isGeo > 0.5) {
            vec2 dirs[8];
            dirs[0] = vec2( 0.924,  0.383);
            dirs[1] = vec2(-0.383,  0.924);
            dirs[2] = vec2(-0.924, -0.383);
            dirs[3] = vec2( 0.383, -0.924);
            dirs[4] = vec2( 0.707, -0.707);
            dirs[5] = vec2(-0.707,  0.707);
            dirs[6] = vec2( 0.707,  0.707);
            dirs[7] = vec2(-0.707, -0.707);

            float occTight = 0.0;
            float occWide = 0.0;
            float r1 = uAoRadius * 0.45;
            float r2 = uAoRadius * 1.90;
            for (int i = 0; i < 8; i++) {
              float d1 = linDepth(vUv + dirs[i] * uTexel * r1);
              float df1 = dc - d1;
              occTight += smoothstep(0.65, 0.02, abs(df1)) * smoothstep(0.008, 0.14, df1);

              float d2 = linDepth(vUv + dirs[i] * uTexel * r2);
              float df2 = dc - d2;
              occWide += smoothstep(2.00, 0.08, abs(df2)) * smoothstep(0.030, 0.55, df2);
            }
            float occ = (occTight * 0.65 + occWide * 0.50) / 8.0;
            float ao = 1.0 - clamp(occ * uAoStrength, 0.0, 0.60);
            rgb *= ao;
          }

          // 2. Silhouette-Only Warm Charcoal Ink Contour Pass
          if (uOutline > 0.5 && inkK > 0.001) {
            vec2 s = uTexel * uLine;
            float dN = linDepth(vUv + vec2(0.0,  s.y));
            float dS = linDepth(vUv + vec2(0.0, -s.y));
            float dE = linDepth(vUv + vec2( s.x, 0.0));
            float dW = linDepth(vUv + vec2(-s.x, 0.0));
            float dEdge = (abs(dN - dc) + abs(dS - dc) + abs(dE - dc) + abs(dW - dc)) / max(1.0, dc);
            float inkD = smoothstep(uDepthK * 0.8, uDepthK * 2.4, dEdge);

            vec4 nc = texture2D(tNorm, vUv);
            vec4 nN = texture2D(tNorm, vUv + vec2(0.0,  s.y));
            vec4 nS = texture2D(tNorm, vUv + vec2(0.0, -s.y));
            vec4 nE = texture2D(tNorm, vUv + vec2( s.x, 0.0));
            vec4 nW = texture2D(tNorm, vUv + vec2(-s.x, 0.0));
            float mask = nc.a * nN.a * nS.a * nE.a * nW.a;
            float nDiff = length(nN.rgb - nc.rgb) + length(nS.rgb - nc.rgb) + length(nE.rgb - nc.rgb) + length(nW.rgb - nc.rgb);
            float inkN = mask * smoothstep(uNormK * 0.7, uNormK * 1.6, nDiff);

            float ink = clamp(max(inkD, inkN * 0.72), 0.0, 1.0) * inkK;
            rgb = mix(rgb, uInkColor, ink);
          }

          // 3. ACES Filmic Tone Mapping + sRGB Gamma
          rgb = acesFilm(rgb * uExposure);
          rgb = pow(rgb, vec3(1.0 / 2.2));
          gl_FragColor = vec4(rgb, 1.0);
        }
      `,
      depthTest: false,
      depthWrite: false,
    });
    postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
    return { scene: postScene, camera: postCam, material: mat, uniforms: mat.uniforms };
  }

  /* Boot Self-Contained REVA Cozy Blender-Style Three.js Canvas */
  function boot(opts = {}) {
    _ensureStyles();
    const qs = new URLSearchParams(location.search);
    const W = parseInt(opts.W || opts.w || qs.get("w") || "1080", 10);
    const H = parseInt(opts.H || opts.h || qs.get("h") || "1920", 10);
    const ssaa = Math.max(1, Math.min(2, opts.ssaa || 2));
    const tInit = parseFloat(qs.get("t") || "0") || 0;

    let stage = opts.host || document.getElementById("stage");
    if (!stage) {
      stage = document.createElement("div");
      stage.id = "stage";
      document.body.appendChild(stage);
    }

    let svg = document.getElementById("lines");
    if (!svg) {
      svg = document.createElementNS(NS, "svg");
      svg.id = "lines";
      document.body.appendChild(svg);
    }
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("preserveAspectRatio", "none");

    let hudHost = document.getElementById("hud-host") || document.getElementById("chips");
    if (!hudHost) {
      hudHost = document.createElement("div");
      hudHost.id = "hud-host";
      document.body.appendChild(hudHost);
    }

    // Header pill + Bottom caption DOM
    let hdr = document.getElementById("rc-header");
    if (!hdr) {
      hdr = document.createElement("div");
      hdr.id = "rc-header";
      const pill = document.createElement("div");
      pill.id = "rc-pill";
      const numEl = document.createElement("span");
      numEl.className = "rc-num";
      numEl.id = "rc-num";
      const titleEl = document.createElement("span");
      titleEl.id = "rc-title";
      pill.append(numEl, titleEl);
      hdr.appendChild(pill);
      document.body.appendChild(hdr);
    }
    let cap = document.getElementById("rc-caption");
    if (!cap) {
      cap = document.createElement("div");
      cap.id = "rc-caption";
      document.body.appendChild(cap);
    }

    function setHeader(num, title) {
      const nEl = document.getElementById("rc-num");
      const tEl = document.getElementById("rc-title");
      const hEl = document.getElementById("rc-header");
      if (nEl) nEl.textContent = num != null ? String(num) : "";
      if (nEl) nEl.style.display = (num === "" || num == null) ? "none" : "inline-flex";
      if (tEl) tEl.textContent = title || "";
      if (hEl) hEl.style.display = (title || num != null) ? "block" : "none";
    }
    function setCaption(txt) {
      const cEl = document.getElementById("rc-caption");
      if (!cEl) return;
      cEl.textContent = txt || "";
      cEl.style.display = txt ? "block" : "none";
    }
    setHeader(opts.headerNum, opts.headerTitle);
    setCaption(opts.caption || "");

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(W, H, false);
    renderer.shadowMap.enabled = opts.shadows !== false;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.NoToneMapping;
    stage.innerHTML = "";
    stage.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const skyBg = opts.sky != null ? new THREE.Color(opts.sky) : buildSkyBackdropTex();
    scene.background = skyBg;
    if (opts.fog !== false) {
      scene.fog = new THREE.Fog(opts.fogColor != null ? opts.fogColor : 0xdde6ed, 42, 165);
    }
    scene.environment = buildDaylightEnv(renderer);

    const camera = new THREE.PerspectiveCamera(opts.fov || 32, W / H, opts.near || 0.2, opts.far || 190);
    camera.position.set(3.4, 3.8, 4.2);
    camera.lookAt(0, 1.0, 0);

    const hemiSpec = opts.hemi || [0xfdfaf4, 0x8ea67c, 0.36];
    const hemi = new THREE.HemisphereLight(hemiSpec[0], hemiSpec[1], hemiSpec[2]);
    scene.add(hemi);

    const sunDir = opts.sunDir || [28, 34, 22];
    const sun = new THREE.DirectionalLight(0xfff9ee, opts.sunK != null ? opts.sunK : 1.12);
    sun.position.set(sunDir[0], sunDir[1], sunDir[2]);
    sun.castShadow = opts.shadows !== false;
    const smSz = opts.shadowMap || 2048;
    sun.shadow.mapSize.set(smSz, smSz);
    const sExt = opts.shadowExtent || 5.8;
    sun.shadow.camera.left = -sExt;
    sun.shadow.camera.right = sExt;
    sun.shadow.camera.top = sExt * 1.25;
    sun.shadow.camera.bottom = -sExt;
    sun.shadow.camera.near = 1;
    sun.shadow.camera.far = 140;
    sun.shadow.radius = 5.0;
    sun.shadow.bias = -0.0003;
    sun.shadow.normalBias = 0.008;
    scene.add(sun);

    const fill = new THREE.DirectionalLight(0xcfe2f5, opts.fillK != null ? opts.fillK : 0.14);
    fill.position.set(-45, 38, -42);
    scene.add(fill);

    // Setup 2x SSAA RenderTargets + DepthTexture when supported
    const rtW = W * ssaa, rtH = H * ssaa;
    const hasDepth = !!(renderer.capabilities.isWebGL2 || renderer.extensions.get("WEBGL_depth_texture"));
    let colorRT = null, normalRT = null, post = null;
    const normMat = new THREE.MeshNormalMaterial();

    if (hasDepth && opts.post !== false) {
      const depthType = renderer.capabilities.isWebGL2 ? THREE.UnsignedIntType : THREE.UnsignedShortType;
      colorRT = new THREE.WebGLRenderTarget(rtW, rtH, {
        minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, format: THREE.RGBAFormat, depthBuffer: true,
      });
      colorRT.depthTexture = new THREE.DepthTexture(rtW, rtH, depthType);
      normalRT = new THREE.WebGLRenderTarget(rtW, rtH, {
        minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, format: THREE.RGBAFormat, depthBuffer: true,
      });
      post = _buildPostPass(rtW, rtH, camera, opts);
      post.uniforms.tColor.value = colorRT.texture;
      post.uniforms.tDepth.value = colorRT.depthTexture;
      post.uniforms.tNorm.value = normalRT.texture;
    } else {
      if (THREE.sRGBEncoding) renderer.outputEncoding = THREE.sRGBEncoding;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.02;
    }

    function render(customScene, customCam) {
      const sc = customScene || scene;
      const cm = customCam || camera;
      if (!post || !colorRT || !normalRT) {
        renderer.render(sc, cm);
        return;
      }

      post.uniforms.uNear.value = cm.near;
      post.uniforms.uFar.value = cm.far;

      // Pass 1: Color + Depth into SSAA target
      renderer.setRenderTarget(colorRT);
      renderer.setClearColor(0x000000, 1.0);
      renderer.clear(true, true, true);
      renderer.render(sc, cm);

      // Pass 2: Normal buffer (temporarily skip noInk & transparent meshes + sky background)
      const hidden = [];
      sc.traverse((o) => {
        if (!o.visible) return;
        const isTrans = !!(o.material && o.material.transparent);
        const skip = !!(o.userData && o.userData.noInk);
        if (o.isMesh && (isTrans || skip)) {
          o.visible = false;
          hidden.push(o);
        }
      });
      const prevBg = sc.background, prevFog = sc.fog, prevOv = sc.overrideMaterial;
      sc.background = null;
      sc.fog = null;
      sc.overrideMaterial = normMat;
      renderer.setRenderTarget(normalRT);
      renderer.setClearColor(0x000000, 0.0);
      renderer.clear(true, true, true);
      renderer.render(sc, cm);

      sc.overrideMaterial = prevOv;
      sc.background = prevBg;
      sc.fog = prevFog;
      for (const o of hidden) o.visible = true;

      // Pass 3: Composite AO + Silhouette Ink + ACES + sRGB to canvas
      renderer.setRenderTarget(null);
      renderer.render(post.scene, post.camera);
    }

    return {
      W, H, tInit, renderer, scene, camera, sun, fill, hemi, post, render,
      svg, host: hudHost,
      setHeader, setCaption, markNoInk,
      makeAoDisc, makeStirrupAoShadow, buildCozyGrassDiorama, createMinimalHud,
      hud: createMinimalHud(camera, svg, hudHost, W, H),
    };
  }

  /* Clean Minimal Reference-Style Floating HUD (Tags, Number Badges & Exact Calipers) */
  function createMinimalHud(camera, svg, host, W = 1080, H = 1920) {
    _ensureStyles();
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
      const ty = Math.max(220, Math.min(H - 270, s.y + dy));
      el.style.transform = `translate(-50%, -50%) translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px)`;
      if (withLine) {
        mk("line", { x1: s.x, y1: s.y, x2: tx, y2: ty, stroke: "#22262c", "stroke-width": 3.0, "stroke-linecap": "round" });
        const strokeCol = cls === "red" ? "#e13b33" : (cls === "blue" ? "#248bf0" : (cls === "gray" || cls === "muted" ? "#ffffff" : "#12985d"));
        const fillCol = cls === "blue" ? "#248bf0" : (cls === "gray" || cls === "muted" ? "#7a7e85" : "#ffffff");
        mk("circle", { cx: s.x, cy: s.y, r: 6.0, fill: fillCol, stroke: cls === "blue" ? "#ffffff" : strokeCol, "stroke-width": 3.0 });
      }
      return el;
    }

    function numBadge(pt, n, dx = 0, dy = 0) {
      const s = proj(pt);
      const el = document.createElement("div");
      el.className = "rtag num-badge";
      el.textContent = String(n);
      host.appendChild(el);
      el.style.transform = `translate(-50%, -50%) translate(${(s.x + dx).toFixed(1)}px, ${(s.y + dy).toFixed(1)}px)`;
      return el;
    }

    function caliper(p1, p2, label, cls = "green", colorHex = "#12985d", offX = 0, offY = 0, tagDx = 0, tagDy = 0) {
      const a = proj(p1), b = proj(p2);
      const ax = a.x + offX, ay = a.y + offY, bx = b.x + offX, by = b.y + offY;
      const d = Math.hypot(bx - ax, by - ay) || 1;
      const nx = -(by - ay) / d * 11, ny = (bx - ax) / d * 11;
      mk("line", { x1: ax, y1: ay, x2: bx, y2: by, stroke: colorHex, "stroke-width": 3.5, "stroke-linecap": "round" });
      mk("line", { x1: ax - nx, y1: ay - ny, x2: ax + nx, y2: ay + ny, stroke: colorHex, "stroke-width": 3.2, "stroke-linecap": "round" });
      mk("line", { x1: bx - nx, y1: by - ny, x2: bx + nx, y2: by + ny, stroke: colorHex, "stroke-width": 3.2, "stroke-linecap": "round" });
      const el = document.createElement("div");
      el.className = "rtag " + cls;
      el.textContent = label;
      host.appendChild(el);
      const hw = (el.offsetWidth || 90) / 2;
      const mx = Math.max(32 + hw, Math.min(W - 32 - hw, (ax + bx) / 2 + tagDx));
      const my = Math.max(220, Math.min(H - 270, (ay + by) / 2 + tagDy));
      el.style.transform = `translate(-50%, -50%) translate(${mx.toFixed(1)}px, ${my.toFixed(1)}px)`;
      return el;
    }

    return { proj, mk, clear, tag, numBadge, caliper };
  }

  global.RevaCanvas = {
    boot, createMinimalHud, makeAoDisc, makeStirrupAoShadow, buildCozyGrassDiorama, markNoInk,
  };
})(window);
