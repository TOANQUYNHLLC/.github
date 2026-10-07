"""Kiểm tra tính nhất quán của repository .github — điểm chạy; các nhóm kiểm tra nằm trong gói
scripts/validation/.

Chạy: python3 scripts/validate.py  (cần Python ≥ 3.11 — tomllib, datetime.UTC — và Ruby để đọc YAML;
cả hai có sẵn trên runner GitHub; trên máy dùng Python do mise cài, không dùng Python 3.9 của macOS).
"""

import json
import sys

# Gói validation cần Python ≥ 3.11 (tomllib, datetime.UTC) — chặn sớm, báo rõ khi chạy bằng bản cũ.
try:
	import tomllib  # noqa: F401
except ModuleNotFoundError:
	sys.exit(
		f'Cần Python ≥ 3.11 (đang dùng {sys.version.split()[0]}) — chạy mise install, mở terminal có mise.'
	)

from validation.common import (
	ROOT,
	anchorsCache,
	bytesCache,
	error,
	errors,
	jsonCache,
	loadYaml,
	readText,
	textCache,
	trackedCache,
	trackedFiles,
	yamlCache,
)
from validation.docs import (
	checkAbsoluteLinks,
	checkAdrIndex,
	checkBadges,
	checkChangelog,
	checkDocsMatchCode,
	checkEmails,
	checkHeadings,
	checkLinks,
	checkRequiredFiles,
	checkSecurityMailto,
	checkSecurityTxt,
)
from validation.formatting import (
	BINARY_SUFFIXES,
	KEEP_TRAILING_SPACE_SUFFIXES,
	SPACE_SUFFIXES,
	TWO_SPACE_SUFFIXES,
	checkSpaceOnly,
	checkSuffixLists,
	checkTabOnly,
	checkText,
)
from validation.forms import FORM_LABELS, checkForm, checkIssueConfig
from validation.repository import (
	checkConventions,
	checkDependabotCooldown,
	checkGitHubSettings,
	checkLabelUsage,
	checkMaintainers,
	checkRulesets,
)
from validation.sources import SCRIPT_SUFFIXES, checkNames, checkScriptLanguage, checkShell
from validation.tooling import (
	checkDevcontainerPins,
	checkEditorExtensions,
	checkFormatConfig,
	checkLintIgnoreConfig,
	checkToolVersions,
)
from validation.workflows import checkWorkflow, checkWorkflowTemplate


def checkFile(file):
	"""Kiểm tra từng tệp: vị trí, ngôn ngữ script, định dạng, mã hóa, nội dung theo loại tệp."""
	# GitHub chỉ nhận biểu mẫu Issue, Discussion, báo cáo lỗ hổng và FUNDING.yml trong thư mục .github/.
	if (
		file.parent.name in ('ISSUE_TEMPLATE', 'DISCUSSION_TEMPLATE')
		and file.parent.parent != ROOT / '.github'
	) or (
		file.name in ('FUNDING.yml', 'VULNERABILITY_REPORT.yml', 'VULNERABILITY_REPORT.yaml')
		and file.parent != ROOT / '.github'
	):
		error(file, 'phải nằm trong thư mục .github/ để GitHub nhận diện')
	# Script ưu tiên Python; ngôn ngữ khác chỉ khi xử lý việc đó tốt hơn, ghi lý do ở đầu tệp (ADR 0009).
	if (file.parent == ROOT / 'scripts' and file.suffix != '.py') or file.suffix in SCRIPT_SUFFIXES:
		checkScriptLanguage(file)
	if file.suffix in BINARY_SUFFIXES:
		return
	content = checkText(file)
	if content is None:
		return
	if file.suffix == '.sh':
		checkShell(file)
	if file.suffix == '.py':
		checkNames(file, readText(file))
	if file.suffix in SPACE_SUFFIXES + TWO_SPACE_SUFFIXES:
		checkSpaceOnly(file, readText(file))
	if not file.name.endswith(SPACE_SUFFIXES + TWO_SPACE_SUFFIXES + KEEP_TRAILING_SPACE_SUFFIXES):
		checkTabOnly(file, content)
	# .mailmap ánh xạ email tác giả commit (kể cả địa chỉ noreply của GitHub), không phải email liên hệ.
	if file.name != '.mailmap':
		checkEmails(file, content)
	if file.name == 'security.txt':
		checkSecurityTxt(file, content)
	if file.name == 'CHANGELOG.md':
		checkChangelog(file, content)
	if (
		file.suffix in ('.sh', '.svg', '.txt', '.js', '.toml')
		or file.suffix == ''
		or file.name.startswith('.')
	):
		return
	if file.suffix == '.md':
		checkLinks(file, content)
		checkHeadings(file, content)
		checkBadges(file, content)
	if file.name == 'SECURITY.md':
		checkSecurityMailto(file, content)
	if file.suffix == '.md' and (
		file.stem.upper() == 'PULL_REQUEST_TEMPLATE'
		or file.parent.name.upper() == 'PULL_REQUEST_TEMPLATE'
	):
		checkAbsoluteLinks(file, content)
	if file.parent.name == 'ISSUE_TEMPLATE' and file.suffix in ('.yml', '.yaml'):
		if file.stem == 'config':
			checkIssueConfig(file)
		else:
			checkForm(file)
	elif file.parent.name == 'DISCUSSION_TEMPLATE' and file.suffix in ('.yml', '.yaml'):
		checkForm(file, required=('body',))
	elif file.name in ('VULNERABILITY_REPORT.yml', 'VULNERABILITY_REPORT.yaml'):
		checkForm(file)
	elif file.suffix in ('.yml', '.yaml') and (
		file.parent.name == 'workflow-templates'
		or file.parent.parts[-2:] == ('.github', 'workflows')
	):
		checkWorkflow(file, content)
		if file.parent.name == 'workflow-templates':
			checkWorkflowTemplate(file)
	elif file.suffix in ('.yml', '.yaml') and file != ROOT / 'labels.yml':
		loadYaml(file)
	elif file.suffix == '.json':
		try:
			json.loads(content)
		except json.JSONDecodeError as exc:
			error(file, f'JSON không hợp lệ: {exc}')


def runChecks():
	"""Chạy mọi kiểm tra, trả danh sách lỗi."""
	errors.clear()
	FORM_LABELS.clear()
	yamlCache.clear()
	jsonCache.clear()
	trackedCache.clear()
	bytesCache.clear()
	textCache.clear()
	anchorsCache.clear()
	for file in trackedFiles():
		checkFile(file)
	for check in (
		checkFormatConfig,
		checkLintIgnoreConfig,
		checkDependabotCooldown,
		checkToolVersions,
		checkSuffixLists,
		checkEditorExtensions,
		checkDevcontainerPins,
		checkConventions,
		checkRulesets,
		checkGitHubSettings,
		checkMaintainers,
		checkDocsMatchCode,
		checkAdrIndex,
		checkRequiredFiles,
		checkLabelUsage,
	):
		check()
	return list(errors)


def main():
	found = runChecks()
	for message in found:
		print(f'❌ {message}')
	print(f'{"✅ Không có lỗi" if not found else f"❌ {len(found)} lỗi"}.')
	return 1 if found else 0


if __name__ == '__main__':
	sys.exit(main())
