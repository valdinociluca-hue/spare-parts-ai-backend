import base from './index.js';

export default [
  ...base,
  {
    files: ['**/*.{ts,tsx}'],
    rules: {
      // Next.js-specific overrides go here
    },
  },
];
