const pptx = require('pptxgenjs');
const p = new pptx();
p.layout = 'LAYOUT_WIDE';                       // 13.333 x 7.5
const W = 13.333, H = 7.5;

const INK='14181A', INK2='43504F', INK3='6E7B79', RULE='D2D8D3';
const NEG='D2622A', OK='2E9E68', SEN='2C8FBF', OBS='7A55B5';
const BLUE='006FBF', TINT='F4F6F3';
const SERIF='Cambria', SANS='Calibri';
const LOGO='deckbuild/sih_logo.png';

function chrome(s, title, n){
  s.background = { color:'FFFFFF' };
  s.addShape(p.ShapeType.ellipse, { x:0.28, y:0.16, w:1.32, h:0.62,
    fill:{color:'FFFFFF'}, line:{color:'7A6FA8', width:1.2} });
  s.addText('Raysense', { x:0.28, y:0.16, w:1.32, h:0.62, align:'center',
    valign:'middle', fontSize:13, fontFace:SANS, color:INK, isTextBox:true, margin:0 });
  s.addImage({ path:LOGO, x:11.35, y:0.10, w:1.72, h:0.86 });
  if(title) s.addText(title, { x:1.8, y:0.16, w:9.4, h:0.72, align:'center',
    fontSize:31, bold:true, fontFace:SERIF, color:INK, isTextBox:true, margin:0 });
  s.addShape(p.ShapeType.rect, { x:0, y:H-0.46, w:W, h:0.46, fill:{color:BLUE} });
  s.addText('@SIH Idea submission- Template', { x:0, y:H-0.46, w:W, h:0.46,
    align:'center', valign:'middle', fontSize:12, fontFace:SANS, color:'FFFFFF', isTextBox:true });
  s.addText(String(n), { x:W-1.0, y:H-0.46, w:0.6, h:0.46, align:'right', valign:'middle',
    fontSize:12, bold:true, fontFace:SANS, color:'FFFFFF', isTextBox:true });
}
function card(s,x,y,w,h,fill){ s.addShape(p.ShapeType.roundRect,{x,y,w,h,rectRadius:0.04,
  fill:{color:fill||TINT}, line:{color:RULE,width:0.75}}); }
function label(s,t,x,y,w,c){ s.addText(t,{x,y,w,h:0.28,fontSize:11,bold:true,fontFace:SANS,
  color:c||INK3,charSpacing:1.2,isTextBox:true,margin:0}); }
function body(s,t,x,y,w,h,sz){ s.addText(t,{x,y,w,h,fontSize:sz||13,fontFace:SANS,
  color:INK2,isTextBox:true,margin:0,lineSpacingMultiple:1.12}); }

/* ---------------- 1 · TITLE ---------------- */
let s = p.addSlide(); chrome(s,null,1);
s.addText('SMART INDIA HACKATHON 2026', { x:1.6, y:1.35, w:10.1, h:0.5, align:'center',
  fontSize:22, bold:true, fontFace:SERIF, color:INK, isTextBox:true });
s.addText('Adaptive Variable Resolution 2.5D Lidar Mapping\nfor Dynamic Environment Perception',
  { x:1.2, y:2.15, w:10.9, h:1.5, align:'center', fontSize:30, bold:true, fontFace:SERIF,
    color:BLUE, isTextBox:true, lineSpacingMultiple:1.08 });
const meta=[['Problem Statement ID','SIH26053'],['Theme','Smart Vehicles'],
            ['PS Category','Software'],['Team Name','Raysense']];
meta.forEach((m,i)=>{ const x=0.95+i*3.0;
  card(s,x,4.15,2.8,1.15);
  s.addText(m[0],{x:x+0.16,y:4.32,w:2.5,h:0.3,fontSize:10.5,bold:true,fontFace:SANS,
    color:INK3,charSpacing:1.1,isTextBox:true,margin:0});
  s.addText(m[1],{x:x+0.16,y:4.66,w:2.5,h:0.42,fontSize:16,bold:true,fontFace:SANS,
    color:INK,isTextBox:true,margin:0}); });
s.addText('Organisation: Defence Research and Development Organisation (DRDO)',
  { x:1.2, y:5.7, w:10.9, h:0.4, align:'center', fontSize:14, fontFace:SANS,
    color:INK3, isTextBox:true });
s.addNotes('PRANAVI — 55s. Open with the PS ID and DRDO. Then the 93% / 11% contrast. Pause 3s after "eleven percent".');

/* ---------------- 2 · IDEA / SOLUTION ---------------- */
s = p.addSlide(); chrome(s,'Adaptive Point-Budget Lidar Perception for UGVs',2);
s.addImage({ path:'deckbuild/fig_gap.png', x:0.42, y:1.15, w:4.35, h:2.92 });
label(s,'THE FINDING',0.42,4.16,4.35);
body(s,'A full scan — every ray, forty times — finds 92.9% of obstacles that stick up and 11.5% of the ones you fall into. Spending more rays cannot fix it: at full scan you are already spending everything.',
  0.42,4.46,4.35,1.3,12.5);
s.addImage({ path:'deckbuild/absence.png', x:5.05, y:1.22, w:7.9, h:2.6 });
label(s,'WHY — THE AMBIGUITY NOBODY RESOLVES',5.05,3.95,7.9,NEG);
body(s,'A ditch is detected by what does NOT come back. A narrow trench is never entered by the beams — it is stepped over. To the sensor, a ditch and a patch you never looked at give the identical signal.',
  5.05,4.25,7.9,0.75,12.5);
card(s,5.05,5.12,7.9,1.62,'F0F5F1');
label(s,'OUR SOLUTION  ·  A THREE-STATE MAP',5.25,5.28,7.5,OK);
body(s,'OBSERVED  ·  UNKNOWN  ·  CANDIDATE_NEGATIVE  —  unknown is a real answer, never silently treated as safe.\nNovelty: adaptive lidar sampling exists (AEye, NEC) but only for urban driving. Negative-obstacle work exists but assumes dense scanning. We are the first to put the two together for off-road terrain.',
  5.25,5.6,7.5,1.05,12.5);
s.addNotes('JEEVIKA — 96s. Walk the three regions A / B / C. Land on "B and C are identical". Then the three-state map and the novelty claim.');

/* ---------------- 3 · TECHNICAL APPROACH ---------------- */
s = p.addSlide(); chrome(s,'TECHNICAL APPROACH',3);
s.addImage({ path:'deckbuild/fig_quadratic.png', x:0.42, y:1.12, w:5.5, h:3.58 });
label(s,'THE SAFETY FLOOR — CORRECTED GEOMETRY',0.42,4.80,5.5,NEG);
s.addText([{text:'Δθ ≤ w · h',options:{bold:true}},{text:'sensor',options:{subscript:true,bold:true}},
           {text:' / r²',options:{bold:true}},
           {text:'      ditches bind quadratically; bumps only linearly. A floor sized with h/r is comfortably met while ditches stay invisible.',options:{bold:false}}],
  { x:0.42, y:5.12, w:5.5, h:1.0, fontSize:13, fontFace:SANS, color:INK2, isTextBox:true,
    margin:0, lineSpacingMultiple:1.12 });
label(s,'PIPELINE  —  SINGLE PASS, PER FRAME',6.25,1.12,6.7,SEN);
const steps=[['1  Predict','warp the previous map forward using ego-motion; age every cell'],
 ['2  Safety floor','hard geometric constraint allocated BEFORE anything adaptive — never traded away'],
 ['3  Need map','score every angular bin: gradient, staleness, moving objects, frontier, unresolved candidates'],
 ['4  Acquire','one of three backends — steerable MEMS/OPA, fixed-pattern Ouster/Velodyne, or replay'],
 ['5  Disambiguate','track RAYS, not points: a cell is empty only if a ray traversed it and returned from beyond'],
 ['6  Output','three-valued traversability — traversable / blocked / unknown']];
steps.forEach((st,i)=>{ const y=1.48+i*0.62;
  s.addText(st[0],{x:6.25,y,w:1.55,h:0.3,fontSize:12.5,bold:true,fontFace:SANS,color:INK,isTextBox:true,margin:0});
  s.addText(st[1],{x:7.85,y:y-0.02,w:5.1,h:0.56,fontSize:11.5,fontFace:SANS,color:INK2,isTextBox:true,margin:0,lineSpacingMultiple:1.05}); });
card(s,6.25,5.35,6.7,0.82);
body(s,'Python · NumPy · Numba · Open3D · quadtree elevation map.  Detector cost: 43 ms per frame.',
  6.45,5.58,6.3,0.4,12.5);
s.addNotes('NIKITA — 84s. Lead with the quadratic: 0.7 m spacing at 10 m, 9 m at 30 m. That is why a 6 m ditch at 30 m is invisible. Then walk the pipeline.');

/* ---------------- 4 · FEASIBILITY ---------------- */
s = p.addSlide(); chrome(s,'FEASIBILITY AND VIABILITY',4);
const feas=[['NO NEW HARDWARE',OK,'Software on data a deployed vehicle already produces, running on the lidar that platform already carries. Sensor-agnostic across three backends.'],
 ['EVIDENCE BASE',SEN,'A controlled off-road testbed where ground truth is KNOWN rather than inferred. Deliberate: public off-road datasets contain almost no labelled ditches, so scoring against them means scoring against the sensor’s own blind spots.'],
 ['REPRODUCIBLE',OBS,'103 automated tests. Every figure generated from a committed CSV. Verified to rebuild bit-identically from a clean environment.']];
feas.forEach((f,i)=>{ const x=0.42+i*4.27;
  card(s,x,1.2,4.05,2.5);
  label(s,f[0],x+0.22,1.42,3.6,f[1]);
  body(s,f[2],x+0.22,1.76,3.6,1.8,12); });
label(s,'HONEST RISKS, AND WHAT WE DO ABOUT THEM',0.42,4.0,12.5,NEG);
const risks=[['Precision is 73%, not 100%','Crest occlusions produce genuine range gaps. Threshold chosen by sweep against terrain with the ditches removed — 2.0 gives 94% recall at 46% precision, 3.0 gives 88% at 73%.'],
 ['RELLIS-3D corroboration is outstanding','Real-data validation has NOT yet been run. The loader is written and it is the next step.'],
 ['No embedded-hardware benchmark','43 ms/frame measured on a laptop CPU. We do not quote a Jetson figure we have not measured.']];
risks.forEach((r,i)=>{ const y=4.36+i*0.78;
  s.addShape(p.ShapeType.roundRect,{x:0.42,y,w:3.75,h:0.66,rectRadius:0.05,
    fill:{color:'F8EDE7'},line:{color:'E4C4B2',width:0.75}});
  s.addText(r[0],{x:0.6,y:y+0.06,w:3.45,h:0.54,fontSize:11.5,bold:true,fontFace:SANS,
    color:NEG,isTextBox:true,margin:0,valign:'middle',lineSpacingMultiple:1.0});
  s.addText(r[1],{x:4.35,y:y+0.02,w:8.6,h:0.62,fontSize:11.5,fontFace:SANS,color:INK2,
    isTextBox:true,margin:0,valign:'middle',lineSpacingMultiple:1.05}); });
s.addNotes('NIKITA — 48s. No new hardware. Ground truth is known not inferred. Then volunteer all three risks before being asked — especially that RELLIS has NOT been run.');

/* ---------------- 5 · IMPACT ---------------- */
s = p.addSlide(); chrome(s,'IMPACT AND BENEFITS',5);
s.addImage({ path:'deckbuild/fig_detection.png', x:0.42, y:1.15, w:5.75, h:3.74 });
label(s,'20× FEWER POINTS, SEVEN TIMES THE DETECTION',0.42,4.98,5.75,OK);
body(s,'91% of negative obstacles at a 5% budget. A full scan with no absence reasoning finds 12%.',
  0.42,5.30,5.75,0.6,12.5);
card(s,6.5,1.15,6.45,2.02,'FDF1EA');
s.addText('23 km/h',{x:6.7,y:1.3,w:3.0,h:0.95,fontSize:46,bold:true,fontFace:SANS,
  color:NEG,isTextBox:true,margin:0});
s.addText('the speed limit nobody published',{x:6.7,y:2.22,w:6.0,h:0.32,fontSize:13,bold:true,
  fontFace:SANS,color:NEG,isTextBox:true,margin:0});
body(s,'Run the geometry backwards and it states how fast a vehicle may safely drive. For a stock OS1-64 that must never enter a 1 m ditch, the honest answer is 23 km/h — and the sensor gives no indication of it.',
  6.7,2.54,6.05,0.62,11.5);
const aud=[['Defence UGVs / AUGVs',OK,'Unmapped ground becomes navigable, without waiting for a human to survey it first.'],
 ['Field operators',SEN,'Fewer platforms stranded or destroyed. A negative obstacle does not damage a vehicle — it ends it.'],
 ['Platform designers',OBS,'A quantified speed ceiling for a given sensor and point budget. This does not exist today.']];
aud.forEach((a,i)=>{ const y=3.47+i*1.12;
  card(s,6.5,y,6.45,1.02);
  s.addShape(p.ShapeType.ellipse,{x:6.72,y:y+0.32,w:0.34,h:0.34,fill:{color:a[1]}});
  s.addText(a[0],{x:7.22,y:y+0.12,w:5.5,h:0.3,fontSize:13,bold:true,fontFace:SANS,
    color:INK,isTextBox:true,margin:0});
  s.addText(a[2],{x:7.22,y:y+0.42,w:5.55,h:0.52,fontSize:11.5,fontFace:SANS,color:INK2,
    isTextBox:true,margin:0,lineSpacingMultiple:1.05}); });
s.addNotes('ANUJ — 66s. Warmest delivery. Three audiences, then land hard on 23 km/h and pause.');

/* ---------------- 6 · RESEARCH ---------------- */
s = p.addSlide(); chrome(s,'RESEARCH AND REFERENCES',6);
card(s,0.42,1.15,6.15,2.55,'F0F5F1');
label(s,'THE RESEARCH GAP',0.62,1.35,5.7,OK);
body(s,'Adaptive lidar sampling is established — AEye ships it, NEC Labs published it, and a 2025 paper uses temporal cues. All of it targets urban driving, where negative obstacles are essentially absent.\n\nThe negative-obstacle literature is equally established — and all of it assumes dense, uniform scanning.\n\nThose two fields have never been put in the same room.',
  0.62,1.68,5.72,1.9,12.5);
card(s,0.42,3.88,6.15,2.9,'FDF1EA');
label(s,'WHAT IS OURS',0.62,4.08,5.7,NEG);
body(s,'1.   Adaptive sampling creates exactly the absences that hide a ditch — measured, not asserted.\n\n2.   A three-state map (OBSERVED / UNKNOWN / CANDIDATE_NEGATIVE) that never turns "I did not look there" into "safe to drive".\n\n3.   A corrected safety floor, Δθ ≤ w·h/r², showing ditches bind quadratically where bumps bind linearly.\n\n4.   A range-normalised gap test: 91% detection at a twentieth of the budget.',
  0.62,4.42,5.72,2.25,12);
label(s,'REFERENCES',6.85,1.15,6.1,SEN);
const refs=[['RELLIS-3D','Off-road multimodal dataset, Ouster OS1-64, ICRA 2021 · github.com/unmannedlab/RELLIS-3D'],
 ['NEC Labs','Pittaluga et al. — A MEMS-based foveating lidar for real-time adaptive depth sensing'],
 ['Adaptive LiDAR Scanning','Harnessing Temporal Cues for Efficient 3D Object Detection, 2025'],
 ['AEye iDAR / 4Sight','US 11675053 · 11782136 · 11860313 — foveated scanning, regions of interest'],
 ['Larson & Trivedi','Lidar-based off-road negative obstacle detection — DTIC ADA561293'],
 ['IEEE ROBIO 2024','Negative obstacle detection in off-road environments using sparse 3D lidar']];
refs.forEach((r,i)=>{ const y=1.5+i*0.86;
  s.addText(r[0],{x:6.85,y,w:6.1,h:0.28,fontSize:12.5,bold:true,fontFace:SANS,color:INK,isTextBox:true,margin:0});
  s.addText(r[1],{x:6.85,y:y+0.27,w:6.1,h:0.5,fontSize:11,fontFace:SANS,color:INK3,
    isTextBox:true,margin:0,lineSpacingMultiple:1.05}); });
s.addNotes('PRANAVI — 41s. We cite these BECAUSE the field exists — we did not invent adaptive lidar. Close on the three numbers, then stop.');

p.writeFile({ fileName:'SIH2026_Raysense_CORRECTED.pptx' }).then(f=>console.log('wrote',f));
