import { context } from 'esbuild';

const ctx = await context({
  entryPoints: ['src/widget.ts'],
  bundle: true,
  format: 'iife',
  target: ['es2020'],
  outfile: 'dist/widget.js',
  sourcemap: 'inline',
  logLevel: 'info',
});

await ctx.watch();
const server = await ctx.serve({ servedir: 'dist', port: 3001 });
console.log(`widget dev server on http://${server.host}:${server.port}`);
