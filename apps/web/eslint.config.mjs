import next from 'eslint-config-next';
import shared from '@partsai/eslint-config';

export default [
  ...shared,
  ...next,
  {
    ignores: ['.next/**', 'node_modules/**'],
  },
];
