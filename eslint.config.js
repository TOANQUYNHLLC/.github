// ESLint cho mã JavaScript của repository .github — CÔNG TY TNHH TOÀN QUỲNH.
// Định dạng (thụt lề bằng tab, dấu chấm phẩy, dấu nháy…) do Prettier đảm nhận;
// eslint-config-prettier tắt mọi quy tắc định dạng của ESLint để hai công cụ không xung đột.
import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import globals from 'globals';

export default [
	{
		// node_modules/ đã được ESLint bỏ qua mặc định.
		ignores: ['.history/'],
	},
	js.configs.recommended,
	{
		files: ['**/*.{js,mjs,cjs}'],
		languageOptions: {
			ecmaVersion: 'latest',
			sourceType: 'module',
			globals: {
				...globals.node,
			},
		},
		rules: {
			// Chất lượng mã theo quy ước của dự án — không có quy tắc định dạng.
			eqeqeq: ['error', 'always'],
			curly: ['error', 'all'],
			'no-var': 'error',
			'prefer-const': 'error',
			'no-console': 'off',
			'no-unused-vars': ['error', { argsIgnorePattern: '^_', caughtErrors: 'none' }],
		},
	},
	prettier,
];
