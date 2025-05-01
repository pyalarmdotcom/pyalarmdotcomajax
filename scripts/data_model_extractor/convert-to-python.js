#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// ─── Config ───────────────────────────────────────────────────────────────────

const MODELS_DIR = path.resolve(__dirname, 'ember_modules_dump', 'customer-site', 'models');
const OUTPUT_DIR = path.resolve(__dirname, 'python_definitions');

// ─── Helpers ──────────────────────────────────────────────────────────────────

function walk(dir, cb) {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) {
      walk(full, cb);
    } else if (name.endsWith('.js')) {
      cb(full);
    }
  }
}

function toSnake(name) {
  return name
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/[\-\.]/g, '_')
    .toLowerCase();
}

function toPascal(name) {
  return name
    .split(/[\-_\/]/)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join('');
}

function extractInheritanceComments(src) {
  const lines = src.split('\n');
  const out = [];
  let capture = false;
  for (const line of lines) {
    if (line.trim().startsWith('// Inheritance:')) capture = true;
    if (capture && line.trim().startsWith('//')) out.push(line);
    else if (capture) break;
  }
  return out;
}

const TYPE_MAP = {
  string: 'str',
  number: 'int',
  boolean: 'bool',
  array: 'list',
  object: 'dict',
  'icon-data': 'str',
};

// ─── Script ───────────────────────────────────────────────────────────────────

if (fs.existsSync(OUTPUT_DIR)) {
  fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
}
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

walk(MODELS_DIR, filePath => {
  const rel = path.relative(MODELS_DIR, filePath).replace(/\\/g, '/');
  const moduleName = `customer-site/${rel.replace(/\.js$/, '')}`;
  const pythonRel = rel.replace(/\.js$/, '.py');
  const outPath = path.join(OUTPUT_DIR, pythonRel);

  const src = fs.readFileSync(filePath, 'utf-8');

  const m = src.match(/export const attributes = \{([\s\S]*?)\};/);
  if (!m) return;

  const attrsBlock = '{' + m[1] + '}';
  let attrs;
  try {
    attrs = Function(`"use strict"; return (${attrsBlock});`)();
  } catch (err) {
    console.error(`\n⚠️  Failed to parse attributes in ${moduleName}:`, err.message);
    return;
  }

  const own = Object.entries(attrs)
    .filter(([, meta]) => meta.definedOn === moduleName)
    .map(([k, meta]) => [k, meta]);

  fs.mkdirSync(path.dirname(outPath), { recursive: true });

  const className = toPascal(path.basename(rel, '.js')) + 'Attributes';
  const lines = [];

  // Inheritance comments
  const inheritanceComments = extractInheritanceComments(src);
  lines.push(...inheritanceComments, '');

  lines.push('from dataclasses import dataclass');
  lines.push('from typing import Optional, Any');
  lines.push('');

  lines.push('@dataclass');
  lines.push(`class ${className}:`);
  lines.push(`    """Attributes of ${path.basename(rel, '.js')}."""`);

  if (own.length === 0) {
    lines.push('    pass');
  } else {
    for (const [attrName, meta] of own) {
      const pyName = toSnake(attrName);
      const baseType = TYPE_MAP[meta.type] || 'Any';
      const hasDefault = Object.prototype.hasOwnProperty.call(meta.options, 'defaultValue');
      const defaultVal = meta.options.defaultValue;
      let typeHint = baseType;
      let defaultStr = '';

      if (!hasDefault) {
        typeHint = `Optional[${baseType}]`;
        defaultStr = ' = None';
      } else {
        let lit;
        if (typeof defaultVal === 'string') lit = `'${defaultVal}'`;
        else if (defaultVal === null) lit = 'None';
        else lit = String(defaultVal);
        defaultStr = ` = ${lit}`;
      }

      lines.push(`    ${pyName}: ${typeHint}${defaultStr}`);
    }
  }

  const methodsSection = src.split(/\/\/ —+ Methods —+/)[1];
  const stubLines = [];
  if (methodsSection) {
    stubLines.push('');
    stubLines.push('# ————— Methods (stubs) —————');
    for (const line of methodsSection.split('\n')) {
      const sig = line.trim().match(/^([A-Za-z0-9_]+)\s*\(([^)]*)\)/);
      if (sig) {
        const [, name, argsRaw] = sig;
        const args = argsRaw
          .split(',')
          .map(a => a.trim())
          .filter(a => a.length > 0);
        const pyArgs = ['self', ...args.map(a => `${toSnake(a)}: Any`)].join(', ');
        stubLines.push(`    def ${name}(${pyArgs}) -> Any:`);
        stubLines.push('        pass');
        stubLines.push('');
      }
    }
    lines.push(...stubLines);
  }

  fs.writeFileSync(outPath, lines.join('\n') + '\n');
  console.log(`⎘ Wrote ${outPath}`);
});

console.log('\nDone! python_definitions generated.\n');
