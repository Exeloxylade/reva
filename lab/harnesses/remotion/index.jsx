import React from "react";
import { Composition, registerRoot } from "remotion";
import { BenchComp } from "./BenchComp";

const w = typeof window !== "undefined" && window.remotion_w ? window.remotion_w : 1080;
const h = typeof window !== "undefined" && window.remotion_h ? window.remotion_h : 1920;

export const RemotionRoot = () => (
  <Composition
    id="BenchComp"
    component={BenchComp}
    durationInFrames={150}
    fps={30}
    width={w}
    height={h}
    defaultProps={{ study: "study", technique: "technique" }}
  />
);

registerRoot(RemotionRoot);
