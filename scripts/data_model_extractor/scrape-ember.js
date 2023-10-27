const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const TARGET_URL = 'https://www.alarm.com/web/system/home';
const OUTPUT_DIR = path.resolve(__dirname, 'ember_modules_dump');

function resetOutputDir() {
  if (fs.existsSync(OUTPUT_DIR)) {
    fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function main() {
  resetOutputDir();

  const browser = await puppeteer.connect({
    browserURL: 'http://localhost:9222',
    defaultViewport: null
  });

  const pages = await browser.pages();
  const page = pages.find(p => p.url().startsWith(TARGET_URL));

  if (!page) {
    console.error(`No page found with URL: ${TARGET_URL}`);
    await browser.disconnect();
    return;
  }

  console.log(`Using existing page: ${page.url()}`);

  const entries = await page.evaluate(() => Object.keys(window.require.entries));
  console.log(`Found ${entries.length} modules.`);

  const failedModules = [];

  for (const name of entries) {
    try {
      const content = await page.evaluate((allEntries, moduleName) => {
        const constructorModuleMap = new Map();
        const attributeMap = new Map();
        const relationshipMap = new Map();

        for (const modName of allEntries) {
          try {
            const m = window.require(modName);
            if (m && m.default && m.default.isModel) {
              const cls = m.default;
              constructorModuleMap.set(cls, modName);
              const attrs = new Set();
              const rels = new Set();
              try { cls.eachAttribute(n => attrs.add(n)); } catch {}
              try { cls.eachRelationship(n => rels.add(n)); } catch {}
              attributeMap.set(modName, attrs);
              relationshipMap.set(modName, rels);
            }
          } catch {}
        }

        function extractEmberModel(modelClass) {
          const chain = [];
          let cls = modelClass;
          while (constructorModuleMap.has(cls)) {
            chain.push(constructorModuleMap.get(cls));
            const proto = Object.getPrototypeOf(cls.prototype);
            if (!proto || !proto.constructor) break;
            cls = proto.constructor;
          }
          const inheritanceChain = chain.slice().reverse();
          const schema = { inheritanceChain, attributes: {}, relationships: {}, methods: [] };

          try {
            modelClass.eachAttribute((name, meta) => {
              for (const modName of inheritanceChain) {
                const set = attributeMap.get(modName);
                if (set && set.has(name)) {
                  schema.attributes[name] = { type: meta.type, options: meta.options || {}, definedOn: modName };
                  break;
                }
              }
            });
          } catch {}

          try {
            modelClass.eachRelationship((name, meta) => {
              for (const modName of inheritanceChain) {
                const set = relationshipMap.get(modName);
                if (set && set.has(name)) {
                  schema.relationships[name] = { kind: meta.kind, type: meta.type, options: meta.options || {}, definedOn: modName };
                  break;
                }
              }
            });
          } catch {}

          try {
            const proto = modelClass.prototype;
            Object.getOwnPropertyNames(proto).forEach(fnName => {
              if (fnName === 'constructor') return;
              const fn = proto[fnName];
              if (typeof fn === 'function') {
                schema.methods.push({ name: fnName, raw: fn.toString() });
              }
            });
          } catch {}

          return schema;
        }

        try {
          const mod = window.require(moduleName);
          if (mod && mod.default && mod.default.isModel) {
            return { type: 'ember-data-model', schema: extractEmberModel(mod.default) };
          }
        } catch (e) {
          return { error: e.message };
        }

        try {
          const mod = window.require(moduleName);
          const t = typeof mod;
          if (t === 'function') {
            const src = mod.toString();
            const isClass = /^class\s/.test(src.trim());
            return { type: isClass ? 'class' : 'function', source: src };
          } else if (t === 'object' && mod !== null) {
            return { type: 'object', source: JSON.stringify(mod, null, 2) };
          } else {
            return { type: 'primitive', source: JSON.stringify(mod) };
          }
        } catch (e) {
          return { error: e.message };
        }
      }, entries, name);

      if (content.error) {
        console.warn(`Skipped ${name}: ${content.error}`);
        failedModules.push({ name, error: content.error });
        continue;
      }

      const safePath = name.replace(/^@/, '').replace(/:/g, '/');
      const filePath = path.join(OUTPUT_DIR, `${safePath}.js`);
      fs.mkdirSync(path.dirname(filePath), { recursive: true });

      let fileContent;
      if (content.type === 'ember-data-model') {
        const { inheritanceChain, attributes, relationships, methods } = content.schema;

        const tree = ['// Inheritance:'];
        if (inheritanceChain.length) {
          tree.push(`// ${inheritanceChain[0]}`);
          for (let i = 1; i < inheritanceChain.length; i++) {
            const indent = '    '.repeat(i - 1);
            tree.push(`// ${indent}└─ ${inheritanceChain[i]}`);
          }
        }
        const inheritanceBlock = tree.join('\n');

        const groupedAttrs = {};
        Object.entries(attributes).forEach(([k,v]) => {
          groupedAttrs[v.definedOn] = groupedAttrs[v.definedOn] || {};
          groupedAttrs[v.definedOn][k] = v;
        });
        let attrsCode = 'export const attributes = {\n';
        inheritanceChain.forEach(modName => {
          const grp = groupedAttrs[modName];
          if (grp) {
            attrsCode += `  // ${modName}\n`;
            Object.entries(grp).forEach(([attr,meta]) => {
              const metaStr = JSON.stringify(meta, null, 2).split('\n').map((l,i)=>i? '    '+l : l).join('\n');
              attrsCode += `  ${attr}: ${metaStr},\n`;
            });
          }
        });
        attrsCode += '};\n';

        const groupedRels = {};
        Object.entries(relationships).forEach(([k,v]) => {
          groupedRels[v.definedOn] = groupedRels[v.definedOn] || {};
          groupedRels[v.definedOn][k] = v;
        });
        let relsCode = 'export const relationships = {\n';
        inheritanceChain.forEach(modName => {
          const grp = groupedRels[modName];
          if (grp) {
            relsCode += `  // ${modName}\n`;
            Object.entries(grp).forEach(([rel,meta]) => {
              const metaStr = JSON.stringify(meta, null, 2).split('\n').map((l,i)=>i? '    '+l : l).join('\n');
              relsCode += `  ${rel}: ${metaStr},\n`;
            });
          }
        });
        relsCode += '};\n';

        const methodsStr = methods.map(m=>`// Method: ${m.name}\n${m.raw}`).join('\n\n');

        fileContent =
          `// Module: ${name}\n` +
          `${inheritanceBlock}\n\n` +
          `// ————— Attributes —————\n` +
          `${attrsCode}\n` +
          `// ————— Relationships —————\n` +
          `${relsCode}\n` +
          `// ————— Methods —————\n` +
          `${methodsStr}\n`;
      } else if (content.type === 'function'||content.type==='class') {
        fileContent = `// Module: ${name}\n${content.source}\n`;
      } else {
        fileContent = `// Module: ${name}\nexport default ${content.source};\n`;
      }

      fs.writeFileSync(filePath, fileContent);
      console.log(`Saved ${name}`);
    } catch (e) {
      console.error(`Error dumping ${name}:`, e.message);
      failedModules.push({ name, error: e.message });
    }
  }

  if (failedModules.length) {
    fs.writeFileSync(
      path.join(OUTPUT_DIR, 'failed_modules.json'),
      JSON.stringify(failedModules, null, 2)
    );
    console.log(`Failed to dump ${failedModules.length} modules.`);
  }

  await browser.disconnect();
  console.log('Done!');
}

main().catch(err => { console.error(err); process.exit(1); });
