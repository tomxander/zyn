/* SVG raster exports. npm install sharp, or point ZYN_NODE_MODULES at a bundle. */
const fs=require('node:fs');
const path=require('node:path');
const {createRequire}=require('node:module');
const req=process.env.ZYN_NODE_MODULES?createRequire(path.join(process.env.ZYN_NODE_MODULES,'_zyn.cjs')):require;
const sharp=req('sharp');
const root=path.resolve(__dirname,'..');
const colors={light:{ink:'#121211',paper:'#FBFAF7',accent:'#1F5FCC'},dark:{ink:'#FBFAF7',paper:'#121211',accent:'#5C9DFF'}};
function vars(source,defaultAccent){
  // Resolve the one custom property for librsvg; preserve nested sheet themes.
  const stack=[defaultAccent];
  return source.replace(/<\/?[^>]+>/g,tag=>{
    if(/^<\//.test(tag)){if(stack.length>1)stack.pop();return tag;}
    const local=/--zyn-accent:([^;"}]+)/.exec(tag);
    let active=local?local[1]:stack[stack.length-1];
    let out=tag.replaceAll('var(--zyn-accent, currentColor)',active);
    if(!/\/>$/.test(tag)&&!/^<\?/.test(tag))stack.push(active);
    return out;
  });
}
function walk(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(dir,e.name)):[path.join(dir,e.name)])}
async function output(source,target,theme,flatten=true){
  let data=fs.readFileSync(source,'utf8');
  if(!data.includes('style="color:'))data=data.replace('<svg ','<svg style="color:'+colors[theme].ink+';--zyn-accent:'+colors[theme].accent+'" ');
  data=vars(data,colors[theme].accent);
  fs.mkdirSync(path.dirname(target),{recursive:true});
  let pipeline=sharp(Buffer.from(data));
  if(flatten)pipeline=pipeline.flatten({background:colors[theme].paper});
  await pipeline.png().toFile(target);
}
(async()=>{
  let jobs=[];
  for(const theme of ['light','dark']){
    for(const file of walk(path.join(root,'logos',theme)).filter(f=>f.endsWith('.svg')))jobs.push([file,file.replace(/\.svg$/,'.png'),theme]);
    for(const size of [24,16])for(const file of walk(path.join(root,'icons',String(size))).filter(f=>f.endsWith('.svg')))jobs.push([file,path.join(root,'raster','icons',theme,String(size),path.basename(file,'.svg')+'.png'),theme]);
  }
  for(const file of walk(path.join(root,'sheets')).filter(f=>f.endsWith('.svg')))jobs.push([file,file.replace(/\.svg$/,'.png'),file.includes('-dark')?'dark':'light']);
  for(let i=0;i<jobs.length;i+=12)await Promise.all(jobs.slice(i,i+12).map(j=>output(...j)));
  console.log(JSON.stringify({png_exports:jobs.length}));
})().catch(e=>{console.error(e);process.exit(1)});
