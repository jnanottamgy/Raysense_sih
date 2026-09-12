const pptx = require('pptxgenjs');
const p = new pptx();
p.layout = 'LAYOUT_WIDE';
const W = 13.333, H = 7.5;

const INK='14181A', INK2='43504F', INK3='6E7B79', RULE='D9DED6';
const NEG='D2622A', OK='2E9E68', SEN='2C8FBF', OBS='7A55B5';
const BLUE='006FBF', TINT='F6F8F5';
const SERIF='Cambria', SANS='Calibri';
const D='deckbuild/';

function chrome(s, title, n){
  s.background = { color:'FFFFFF' };
  s.addShape(p.ShapeType.ellipse, { x:0.26, y:0.14, w:1.26, h:0.58,
    fill:{color:'FFFFFF'}, line:{color:'7A6FA8', width:1.2} });
  s.addText('Raysense', { x:0.26, y:0.14, w:1.26, h:0.58, align:'center', valign:'middle',
    fontSize:12.5, fontFace:SANS, color:INK, isTextBox:true, margin:0 });
  s.addImage({ path:D+'sih_logo.png', x:11.42, y:0.10, w:1.66, h:1.66/2.0895 });
  if(title) s.addText(title, { x:1.7, y:0.13, w:9.6, h:0.62, align:'center',
    fontSize:29, bold:true, fontFace:SERIF, color:INK, isTextBox:true, margin:0 });
  s.addShape(p.ShapeType.rect, { x:0, y:H-0.42, w:W, h:0.42, fill:{color:BLUE} });
  s.addText('@SIH Idea submission- Template', { x:0, y:H-0.42, w:W, h:0.42, align:'center',
    valign:'middle', fontSize:11, fontFace:SANS, color:'FFFFFF', isTextBox:true });
  s.addText(String(n), { x:W-0.95, y:H-0.42, w:0.55, h:0.42, align:'right', valign:'middle',
    fontSize:11, bold:true, fontFace:SANS, color:'FFFFFF', isTextBox:true });
}
// short caption under / beside a visual — never a paragraph
function cap(s,t,x,y,w,c,sz){ s.addText(t,{x,y,w,h:0.30,fontSize:sz||12,bold:true,
  fontFace:SANS,color:c||INK3,charSpacing:0.8,isTextBox:true,margin:0,align:'center'}); }
function chip(s,x,y,w,h,fill,line){ s.addShape(p.ShapeType.roundRect,{x,y,w,h,rectRadius:0.05,
  fill:{color:fill||TINT},line:{color:line||RULE,width:1}}); }

/* ============ 1 · TITLE ============ */
/* Official SIH 2026 idea-submission title page: carries all six required
   fields with the template's own labels. Like the template's slide 1 it
   takes no footer bar, no slide number and no team oval — those start on
   slide 2. */
let s = p.addSlide();
s.background = { color:'FFFFFF' };
s.addShape(p.ShapeType.ellipse, { x:0.44, y:0.36, w:1.46, h:0.68,
  fill:{color:'FFFFFF'}, line:{color:'7A6FA8', width:1.3} });
s.addText('Raysense', { x:0.44, y:0.36, w:1.46, h:0.68, align:'center', valign:'middle',
  fontSize:13.5, fontFace:SANS, color:INK, isTextBox:true, margin:0 });
s.addImage({ path:D+'sih_logo.png', x:10.30, y:0.30, w:2.60, h:2.60/2.0895 });

s.addText('SMART INDIA HACKATHON 2026', { x:0.90, y:1.88, w:11.53, h:0.40, align:'center',
  fontSize:18, bold:true, fontFace:SERIF, color:INK3, charSpacing:2.6, isTextBox:true });
s.addText('PROBLEM STATEMENT TITLE', { x:0.90, y:2.32, w:11.53, h:0.28, align:'center',
  fontSize:10.5, bold:true, fontFace:SANS, color:BLUE, charSpacing:1.8, isTextBox:true });
/* one box, two explicit lines — so a wrap can never shunt the second line
   into the chips below; the box has 0.5in of slack under the text it holds */
s.addText([{ text:'Adaptive Variable Resolution 2.5D Lidar Mapping',
             options:{ fontSize:31, bold:true, color:INK, breakLine:true } },
           { text:'for Dynamic Environment Perception',
             options:{ fontSize:23, color:INK2 } }],
  { x:0.90, y:2.62, w:11.53, h:1.40, align:'center', fontFace:SERIF, isTextBox:true });

/* the six fields the template asks for, in its own order */
const meta=[['PROBLEM STATEMENT ID','SIH26053',SEN,INK],
            ['ORGANISATION','DRDO',NEG,INK],
            ['THEME','Smart Automation',OBS,INK],
            ['PS CATEGORY','Software',OK,INK],
            ['TEAM ID','ADD FROM PORTAL',NEG,NEG],
            ['TEAM NAME','Raysense',BLUE,INK]];
meta.forEach((m,i)=>{
  const x = 0.772 + (i%3)*4.03, y = 4.46 + Math.floor(i/3)*1.16;
  chip(s,x,y,3.73,1.02);
  s.addShape(p.ShapeType.ellipse,{x:x+0.22,y:y+0.40,w:0.22,h:0.22,fill:{color:m[2]}});
  s.addText(m[0],{x:x+0.56,y:y+0.17,w:2.95,h:0.26,fontSize:9,bold:true,fontFace:SANS,
    color:INK3,charSpacing:1,isTextBox:true,margin:0});
  s.addText(m[1],{x:x+0.56,y:y+0.43,w:2.95,h:0.34,fontSize:14.5,bold:true,fontFace:SANS,
    color:m[3],isTextBox:true,margin:0}); });
s.addNotes('PRANAVI — 55s. PS ID + DRDO. Then 93% / 11%. PAUSE 3s after "eleven percent".');

/* ============ 2 · THE PROBLEM & THE IDEA ============ */
s = p.addSlide(); chrome(s,'Adaptive Point-Budget Lidar Perception for UGVs',2);
s.addImage({ path:D+'fig_donuts.png', x:0.40, y:1.00, w:4.55, h:4.55/1.795 });
cap(s,'A FULL SCAN ALREADY MISSES 9 IN 10 DITCHES',0.40,3.62,4.55,NEG,11.5);
s.addImage({ path:D+'absence.png', x:5.35, y:1.12, w:7.55, h:7.55/1.855 });
cap(s,'A DITCH AND A PATCH YOU NEVER LOOKED AT GIVE THE SAME SIGNAL',
  5.35,5.42,7.55,NEG,11.5);
chip(s,0.40,4.10,4.55,2.62,'F0F5F1',OK);
s.addText('OUR ANSWER',{x:0.62,y:4.28,w:4.1,h:0.3,fontSize:11.5,bold:true,fontFace:SANS,
  color:OK,charSpacing:1.2,isTextBox:true,margin:0});
s.addText('A three-state map',{x:0.62,y:4.58,w:4.1,h:0.42,fontSize:20,bold:true,fontFace:SERIF,
  color:INK,isTextBox:true,margin:0});
[['OBSERVED',OK],['UNKNOWN','9A6F0E'],['CANDIDATE_NEGATIVE',NEG]].forEach((c,i)=>{
  const y=5.10+i*0.42;
  s.addShape(p.ShapeType.ellipse,{x:0.66,y:y+0.07,w:0.18,h:0.18,fill:{color:c[1]}});
  s.addText(c[0],{x:0.96,y,w:3.8,h:0.32,fontSize:12.5,bold:true,fontFace:SANS,color:c[1],
    isTextBox:true,margin:0}); });
s.addText('Unknown is never upgraded to “safe”.',{x:0.62,y:6.34,w:4.1,h:0.3,fontSize:11.5,
  italic:true,fontFace:SANS,color:INK2,isTextBox:true,margin:0});
s.addNotes('JEEVIKA — 96s. Walk A / B / C. Land on "B and C are identical". Then the three states, then novelty.');

/* ============ 3 · TECHNICAL APPROACH ============ */
s = p.addSlide(); chrome(s,'TECHNICAL APPROACH',3);
s.addImage({ path:D+'fig_pipeline.png', x:0.40, y:1.13, w:5.95, h:5.95/1.594 });
s.addImage({ path:D+'fig_quadratic.png', x:6.72, y:0.95, w:6.2, h:6.2/1.535 });
cap(s,'DITCHES DEGRADE QUADRATICALLY · BUMPS ONLY LINEARLY',6.72,5.03,6.2,NEG,11.5);
chip(s,6.72,5.42,6.2,0.86,'FDF1EA',NEG);
s.addText([{text:'Δθ  ≤  w · h',options:{bold:true,fontSize:21}},
           {text:'sensor',options:{subscript:true,bold:true,fontSize:21}},
           {text:'  /  r²',options:{bold:true,fontSize:21}}],
  { x:6.72, y:5.55, w:6.2, h:0.6, align:'center', fontFace:SANS, color:NEG, isTextBox:true });
const tech=[['Python · NumPy · Numba',SEN],['Open3D · quadtree map',OBS],
            ['3 sensor backends',OK],['43 ms / frame',NEG]];
tech.forEach((t,i)=>{ const x=6.72+(i%2)*3.18, y=6.44+Math.floor(i/2)*0.0;
  chip(s,x,y,3.02,0.46);
  s.addShape(p.ShapeType.ellipse,{x:x+0.14,y:y+0.14,w:0.18,h:0.18,fill:{color:t[1]}});
  s.addText(t[0],{x:x+0.42,y,w:2.5,h:0.46,fontSize:11,bold:true,fontFace:SANS,color:INK2,
    valign:'middle',isTextBox:true,margin:0}); });
s.addNotes('NIKITA — 84s. 0.7 m spacing at 10 m, 9 m at 30 m. That is why a 6 m ditch at 30 m is invisible. Then the six steps.');

/* ============ 4 · FEASIBILITY ============ */
s = p.addSlide(); chrome(s,'FEASIBILITY AND VIABILITY',4);
s.addImage({ path:D+'fig_threshold.png', x:0.40, y:0.98, w:6.0, h:6.0/1.600 });
cap(s,'EVERY PARAMETER CHOSEN BY SWEEP, NOT BY EYE',0.40,4.78,6.0,INK3,11.5);
s.addImage({ path:D+'demo_frame.png', x:6.70, y:0.98, w:6.22, h:6.22/2.344 });
cap(s,'IT RUNS TODAY — 103 TESTS, REPRODUCIBLE BIT-FOR-BIT',6.70,3.64,6.22,OK,11.5);
const feas=[['NO NEW HARDWARE',OK],['GROUND TRUTH KNOWN',SEN],['103 TESTS PASS',OBS]];
feas.forEach((f,i)=>{ const x=6.70+i*2.11;
  chip(s,x,4.06,1.96,0.72,'F0F5F1',f[1]);
  s.addText(f[0],{x:x+0.1,y:4.06,w:1.76,h:0.72,fontSize:10.5,bold:true,fontFace:SANS,
    color:f[1],align:'center',valign:'middle',isTextBox:true,margin:0}); });
s.addText('HONEST RISKS',{x:0.40,y:5.24,w:12.5,h:0.32,fontSize:12,bold:true,fontFace:SANS,
  color:NEG,charSpacing:1.4,isTextBox:true,margin:0});
const risks=[['73%','precision, not 100% — crest occlusions'],
             ['0','frames of RELLIS-3D run so far — next step'],
             ['no','Jetson benchmark — we will not quote one']];
risks.forEach((r,i)=>{ const x=0.40+i*4.22;
  chip(s,x,5.58,4.0,1.05,'FBF3EE','E4C4B2');
  s.addText(r[0],{x:x+0.18,y:5.70,w:1.05,h:0.6,fontSize:26,bold:true,fontFace:SANS,
    color:NEG,isTextBox:true,margin:0,valign:'middle'});
  s.addText(r[1],{x:x+1.32,y:5.66,w:2.5,h:0.9,fontSize:11.5,fontFace:SANS,color:INK2,
    isTextBox:true,margin:0,valign:'middle'}); });
s.addNotes('NIKITA — 48s. No new hardware, ground truth known. Volunteer all three risks — especially that RELLIS has NOT been run.');

/* ============ 5 · IMPACT ============ */
s = p.addSlide(); chrome(s,'IMPACT AND BENEFITS',5);
s.addImage({ path:D+'fig_detection.png', x:0.40, y:1.00, w:6.05, h:6.05/1.535 });
cap(s,'91% OF DITCHES AT 5% OF THE POINTS · 20× FEWER',0.40,5.02,6.05,OK,11.5);
s.addImage({ path:D+'fig_speedo.png', x:7.15, y:0.98, w:5.1, h:5.1/1.429 });
cap(s,'THE SPEED LIMIT NOBODY PUBLISHED',7.15,4.58,5.1,NEG,11.5);
const aud=[['Defence UGVs',OK,'unmapped ground becomes navigable'],
           ['Field operators',SEN,'a ditch does not damage a vehicle — it ends it'],
           ['Platform designers',OBS,'a quantified speed ceiling, per sensor']];
aud.forEach((a,i)=>{ const y=5.08+i*0.63;
  chip(s,6.72,y,6.2,0.55);
  s.addShape(p.ShapeType.ellipse,{x:6.90,y:y+0.17,w:0.21,h:0.21,fill:{color:a[1]}});
  s.addText(a[0],{x:7.22,y,w:2.15,h:0.55,fontSize:12,bold:true,fontFace:SANS,color:INK,
    valign:'middle',isTextBox:true,margin:0});
  s.addText(a[2],{x:9.35,y,w:3.45,h:0.55,fontSize:10.5,fontFace:SANS,color:INK2,
    valign:'middle',isTextBox:true,margin:0}); });
s.addNotes('ANUJ — 66s. Warmest delivery. Three audiences, then land on 23 km/h and PAUSE.');

/* ============ 6 · RESEARCH ============ */
s = p.addSlide(); chrome(s,'RESEARCH AND REFERENCES',6);
s.addImage({ path:D+'fig_venn.png', x:0.40, y:0.96, w:7.85, h:7.85/1.721 });
cap(s,'WE DID NOT INVENT ADAPTIVE LIDAR — WE FOUND WHERE IT BREAKS',
  0.40,5.58,7.85,OK,11.5);
chip(s,0.40,6.00,7.85,0.80,'F0F5F1',OK);
s.addText('Ours: a three-state map · the corrected quadratic floor · a range-normalised gap test',
  {x:0.60,y:6.00,w:7.45,h:0.80,fontSize:12.5,fontFace:SANS,color:INK2,valign:'middle',
   isTextBox:true,margin:0});
s.addText('REFERENCES',{x:8.62,y:0.96,w:4.3,h:0.3,fontSize:11.5,bold:true,fontFace:SANS,
  color:SEN,charSpacing:1.3,isTextBox:true,margin:0});
const refs=[['RELLIS-3D','ICRA 2021 · off-road, Ouster OS1-64'],
            ['NEC Labs','MEMS foveating lidar — Pittaluga et al.'],
            ['Adaptive LiDAR Scanning','temporal cues, 2025'],
            ['AEye iDAR / 4Sight','US 11675053 · 11782136 · 11860313'],
            ['Larson & Trivedi','DTIC ADA561293 — negative obstacles'],
            ['IEEE ROBIO 2024','sparse 3D lidar, off-road ditches']];
refs.forEach((r,i)=>{ const y=1.36+i*0.86;
  s.addShape(p.ShapeType.ellipse,{x:8.62,y:y+0.08,w:0.15,h:0.15,fill:{color:SEN}});
  s.addText(r[0],{x:8.90,y,w:4.0,h:0.3,fontSize:12,bold:true,fontFace:SANS,color:INK,
    isTextBox:true,margin:0});
  s.addText(r[1],{x:8.90,y:y+0.28,w:4.0,h:0.44,fontSize:10.5,fontFace:SANS,color:INK3,
    isTextBox:true,margin:0}); });
s.addNotes('PRANAVI — 41s. We cite these BECAUSE the field exists. Close on the three numbers and stop.');

p.writeFile({ fileName:'SIH2026_Raysense_CORRECTED.pptx' }).then(f=>console.log('wrote',f));
