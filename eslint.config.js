// ESLint cho mã JavaScript của repository .github — CÔNG TY TNHH TOÀN QUỲNH.
// Định dạng (thụt lề bằng tab, dấu chấm phẩy, dấu nháy…) do Prettier đảm nhận;
// eslint-config-prettier tắt mọi quy tắc định dạng của ESLint để hai công cụ không xung đột.
import { fileURLToPath } from 'node:url';
import js from '@eslint/js';
import { defineConfig, includeIgnoreFile } from 'eslint/config';
import prettier from 'eslint-config-prettier';
import globals from 'globals';

export default defineConfig([
	// Bỏ qua đúng những gì .gitignore bỏ qua (.history/…), không chép lại danh sách; node_modules/ mặc định đã bỏ qua.
	includeIgnoreFile(fileURLToPath(new URL('.gitignore', import.meta.url))),
	js.configs.recommended,
	{
		files: ['**/*.{js,mjs,cjs}'],
		// ecmaVersion 'latest' và sourceType theo đuôi tệp (.cjs là commonjs) là mặc định của flat config.
		languageOptions: {
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
]);
