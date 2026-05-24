import { build } from 'esbuild';

await build({
  entryPoints: ['src/widget.ts'],
  bundle: true,
  minify: true,
  format: 'iife',
  target: ['es2020'],
  outfile: 'dist/widget.js',
  sourcemap: true,
  logLevel: 'info',
});
