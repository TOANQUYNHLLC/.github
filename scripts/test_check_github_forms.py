"""Test tự động cho scripts/check-github-forms.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import http.client
import io
import json
import unittest
import urllib.error
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class GithubFormsTest(unittest.TestCase):
	def testTemplateErrorsCollectFormAndFieldMessages(self):
		# Lỗi cấp biểu mẫu (bỏ thẻ HTML) và lỗi từng trường đều được báo; trường không có input bị bỏ qua.
		module = loadScript('check-github-forms')
		template = {
			'valid': False,
			'errors': [{'message': '<code>type</code> is not a permitted key'}],
			'inputs': [{'input': None}, {'input': {'errors': {'label': 'is required'}}}, {}],
		}
		self.assertEqual(
			module.templateErrors(template),
			['type is not a permitted key', 'label: is required'],
		)
		self.assertEqual(
			module.templateErrors({'valid': True, 'errors': [], 'inputs': [{'input': {}}]}), []
		)
		for broken in (
			{'errors': [{'message': 42}], 'inputs': []},
			{'errors': [], 'inputs': ['x']},
			{'errors': [], 'inputs': [{'input': {'errors': ['x']}}]},
		):
			with self.subTest(broken=broken), self.assertRaises(TypeError):
				module.templateErrors(broken)

	def testMalformedValidFlagCannotReportSuccess(self):
		module = loadScript('check-github-forms')
		for value in (None, 0, 1, 'false', [], {}):
			with self.subTest(valid=value):
				with (
					mock.patch.object(
						module,
						'templateData',
						return_value={'errors': [], 'inputs': [], 'valid': value},
					),
					contextlib.redirect_stdout(io.StringIO()) as output,
				):
					self.assertEqual(module.main(), 1)
				self.assertIn('không đọc được biểu mẫu', output.getvalue())
				self.assertNotIn('✅', output.getvalue())

	def testNoFormsCannotReportSuccess(self):
		module = loadScript('check-github-forms')
		with (
			mock.patch.object(module, 'formPaths', return_value=[]),
			mock.patch.object(module, 'fetchPage') as fetch,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(module.main(), 1)
		fetch.assert_not_called()

	def testInvalidFlagCannotReportSuccess(self):
		module = loadScript('check-github-forms')
		with (
			mock.patch.object(
				module, 'templateData', return_value={'errors': [], 'inputs': [], 'valid': False}
			),
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(module.main(), 1)

	def testMalformedPageDataFailsPerForm(self):
		module = loadScript('check-github-forms')
		forms = module.formPaths()
		valid = {
			'payload': {
				'codeViewBlobRoute': {
					'issueTemplate': {'errors': [], 'inputs': []},
					'discussionTemplate': {'errors': [], 'inputs': []},
				}
			}
		}
		for malformed in (
			[],
			{'payload': []},
			{'payload': {'codeViewBlobRoute': []}},
			{'payload': {'codeViewBlobRoute': {'issueTemplate': []}}},
			{'payload': {'codeViewBlobRoute': {'issueTemplate': {'errors': [42]}}}},
			{
				'payload': {
					'codeViewBlobRoute': {'issueTemplate': {'inputs': [{'input': {'errors': []}}]}}
				}
			},
		):
			with self.subTest(data=malformed):

				def fetchPage(url, malformed=malformed):
					data = (
						malformed
						if url.endswith(forms[0].relative_to(module.ROOT).as_posix())
						else valid
					)
					if isinstance(data, dict) and isinstance(data.get('payload'), dict):
						data['payload']['codeViewLayoutRoute'] = {'repo': {'defaultBranch': 'main'}}
						data['payload']['codeViewBlobLayoutRoute'] = {
							'refInfo': {'name': 'main', 'refType': 'branch'}
						}
					return (
						'<script type="application/json" data-target="react-app.embeddedData">'
						+ json.dumps(data)
						+ '</script>'
					)

				output = io.StringIO()
				with (
					mock.patch.object(module, 'fetchPage', fetchPage),
					contextlib.redirect_stdout(output),
				):
					self.assertEqual(module.main(), 1)
				self.assertIn(
					'❌ ' + forms[0].relative_to(module.ROOT).as_posix(), output.getvalue()
				)
				self.assertIn(
					'✅ ' + forms[1].relative_to(module.ROOT).as_posix(), output.getvalue()
				)

	def testEmptyTemplateIsNotAccepted(self):
		module = loadScript('check-github-forms')
		output = io.StringIO()
		with (
			mock.patch.object(module, 'templateData', return_value={}),
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(module.main(), 1)
		self.assertNotIn('✅', output.getvalue())

	def testRefAndPathAreUrlEncoded(self):
		# Tên branch có # hay % (git cho phép) không được cắt URL hay đổi nghĩa: mỗi ký tự được mã hoá, giữ dấu /.
		module = loadScript('check-github-forms')
		urls = []

		def fetchPage(url):
			urls.append(url)
			return ''

		with mock.patch.object(module, 'fetchPage', fetchPage):
			module.templateData('fix/#12_50%', '.github/ISSUE_TEMPLATE/bug report.yml')
		self.assertEqual(
			urls,
			[
				(
					'https://github.com/TOANQUYNHLLC/.github/blob/fix/%2312_50%25/'
					'.github/ISSUE_TEMPLATE/bug%20report.yml'
				)
			],
		)

	def testDiscussionRejectsRenderedDefaultDataForOtherRefs(self):
		module = loadScript('check-github-forms')
		for name, refType, defaultBranch in (
			('feature/forms', 'branch', 'main'),
			('abc123', 'commit', 'main'),
			('main', 'tag', 'main'),
		):
			page = self.discussionPage(name, refType, defaultBranch)
			with (
				self.subTest(name=name, refType=refType),
				mock.patch.object(module, 'fetchPage', return_value=page),
			):
				with self.assertRaises(module.UnverifiedDiscussion):
					module.templateData(name, '.github/DISCUSSION_TEMPLATE/ideas.yml')
				# Issue vẫn được kiểm tra theo ref của trang.
				self.assertEqual(
					module.templateData(name, '.github/ISSUE_TEMPLATE/feature-request.yml'),
					{'errors': [], 'inputs': [], 'valid': True},
				)

	def testDiscussionAcceptsActualDefaultBranchAndRequiresMetadata(self):
		module = loadScript('check-github-forms')
		with mock.patch.object(
			module, 'fetchPage', return_value=self.discussionPage('develop', 'branch', 'develop')
		):
			self.assertEqual(
				module.templateData('develop', '.github/DISCUSSION_TEMPLATE/ideas.yml')['valid'],
				True,
			)
		with (
			mock.patch.object(
				module, 'fetchPage', return_value=self.discussionPage('main', 'branch', '')
			),
			self.assertRaises(TypeError),
		):
			module.templateData('main', '.github/DISCUSSION_TEMPLATE/ideas.yml')

	def testUnverifiedDiscussionCannotReportCompleteSuccess(self):
		module = loadScript('check-github-forms')
		with (
			mock.patch.object(
				module,
				'fetchPage',
				return_value=self.discussionPage('feature/forms', 'branch', 'main'),
			),
			mock.patch.object(module.sys, 'argv', ['check-github-forms.py', 'feature/forms']),
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(module.main(), 1)
		self.assertIn('Discussion chưa xác minh', output.getvalue())
		self.assertIn('✅ .github/ISSUE_TEMPLATE/', output.getvalue())
		self.assertNotIn('GitHub chấp nhận mọi biểu mẫu', output.getvalue())

	@staticmethod
	def discussionPage(name, refType, defaultBranch):
		template = {'errors': [], 'inputs': [], 'valid': True}
		payload = {
			'codeViewBlobRoute': {'discussionTemplate': template, 'issueTemplate': template},
			'codeViewLayoutRoute': {'repo': {'defaultBranch': defaultBranch}},
			'codeViewBlobLayoutRoute': {'refInfo': {'name': name, 'refType': refType}},
		}
		return (
			'<script type="application/json" data-target="react-app.embeddedData">'
			+ json.dumps({'payload': payload})
			+ '</script>'
		)

	def testTransientErrorIsRetried(self):
		# GitHub trả 503 khi bị gọi dồn: thử lại rồi đọc được; lỗi 404 thì báo ngay, không thử lại.
		module = loadScript('check-github-forms')
		module.RETRY_DELAY = 0
		unavailable = urllib.error.HTTPError(
			'https://github.com', 503, 'Service Unavailable', {}, None
		)
		missing = urllib.error.HTTPError('https://github.com', 404, 'Not Found', {}, None)
		responses = [unavailable, io.BytesIO(b'trang')]

		def urlopen(request, timeout):
			response = responses.pop(0)
			if isinstance(response, Exception):
				raise response
			return response

		with mock.patch.object(module.urllib.request, 'urlopen', urlopen):
			self.assertEqual(module.fetchPage('https://github.com'), 'trang')
			responses[:] = [missing, io.BytesIO(b'')]
			with self.assertRaises(urllib.error.HTTPError) as raised:
				module.fetchPage('https://github.com')
			raised.exception.close()
			self.assertEqual(len(responses), 1)

	def testBrokenResponseIsReportedPerForm(self):
		# Máy chủ ngắt kết nối hoặc trả trang không phải UTF-8 (lỗi lúc đọc, urllib không gói thành URLError): báo
		# biểu mẫu đó lỗi, các biểu mẫu khác vẫn được kiểm tra.
		module = loadScript('check-github-forms')
		forms = [path.relative_to(module.ROOT).as_posix() for path in module.formPaths()]
		failures = {
			forms[0]: http.client.RemoteDisconnected('đóng kết nối'),
			forms[1]: UnicodeDecodeError('utf-8', b'', 0, 1, 'x'),
		}

		def fetchPage(url):
			failure = next((exc for form, exc in failures.items() if url.endswith(form)), None)
			if failure:
				raise failure
			return '<html></html>'

		output = io.StringIO()
		with (
			mock.patch.object(module, 'fetchPage', fetchPage),
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(module.main(), 1)
		lines = output.getvalue().splitlines()
		self.assertIn(f'❌ {forms[0]}: không đọc được trang (đóng kết nối)', lines)
		self.assertTrue(lines[1].startswith(f'❌ {forms[1]}: không đọc được trang'))
		# Biểu mẫu còn lại vẫn được kiểm tra (trang giả không có dữ liệu biểu mẫu).
		self.assertEqual(len(lines), len(forms) + 1)

	def testMissingRefIsReportedOnce(self):
		# Branch chưa đẩy lên GitHub: mọi trang 404 — báo một dòng, không báo từng biểu mẫu lỗi.
		module = loadScript('check-github-forms')

		def missing(url):
			raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)

		output = io.StringIO()
		with (
			mock.patch.object(module, 'fetchPage', missing),
			mock.patch.object(module.sys, 'argv', ['check-github-forms.py', 'feature/x']),
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(module.main(), 1)
		self.assertEqual(
			output.getvalue().strip(),
			'❌ Không có "feature/x" trên GitHub — đẩy branch trước: git push -u origin feature/x',
		)


if __name__ == '__main__':
	unittest.main()
