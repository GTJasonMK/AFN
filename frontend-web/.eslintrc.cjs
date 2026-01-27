module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
  },
  parser: '@typescript-eslint/parser',
  plugins: ['react-hooks', 'react-refresh'],
  ignorePatterns: ['dist', 'node_modules'],
  rules: {
    ...require('eslint-plugin-react-hooks').configs.recommended.rules,
    // 项目目前未对“导出组件”做严格约束，避免在 WebUI 快速迭代期引入大量告警
    'react-refresh/only-export-components': 'off',
  },
};

