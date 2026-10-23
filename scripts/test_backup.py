"""Kiểm tra gói sao lưu cài đặt: chuyển máy, dữ liệu thiếu, checksum và bảo vệ dữ liệu riêng."""

import base64
import contextlib
import copy
import io
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript

from orgsetup import backup, catalog, configuration, github, inventory, localdata


def completeConfig():
	"""Phạm vi tổ chức đã khai báo đủ; dữ liệu riêng chỉ là fixture, không đọc tệp riêng của máy."""
	config = configuration.readConfig(ROOT)
	config['repositories'] = {}
	config['unavailable'] = {}
	scope = config['organization']
	scope.pop('pending_settings', None)
	scope.pop('observed', None)
	# Tài nguyên fixture độc lập với cài đặt đang nhập; không lấy định nghĩa riêng từ nguồn thật.
	scope['collections'] = {key: [] for key in catalog.ORG_GROUPS}
	scope['runner_groups'] = []
	scope['security_configurations'] = []
	scope['web_settings']['installed_apps'] = []
	scope['collections']['dependabot_access'] = [{'default_level': 'public', 'repositories': []}]
	scope['manual_settings'] = {
		key: {'status': 'not_applicable', 'configuration_source': None}
		for key in inventory.MANUAL_GROUPS
	}
	return configuration.validateConfig(config)


class SettingsBackupTest(unittest.TestCase):
	def setUp(self):
		self.directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		self.path = Path(self.directory.name) / 'backup.tar.gz'
		self.config = completeConfig()
		self.values = dict.fromkeys(localdata.valueReferences(self.config), 'PRIVATE_FIXTURE')

	def write(self):
		with (
			mock.patch.object(configuration, 'readConfig', return_value=self.config),
			mock.patch.object(localdata, 'readValues', return_value=self.values),
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			result = backup.writeBackup(self.path)
		self.assertNotIn('PRIVATE_FIXTURE', output.getvalue())
		return result

	def rewrite(self, transform):
		with tarfile.open(self.path, 'r:gz') as archive:
			entries = [(member, archive.extractfile(member).read()) for member in archive]
		entries = transform(entries)
		with tarfile.open(self.path, 'w:gz') as archive:
			for member, data in entries:
				member.size = len(data)
				archive.addfile(member, io.BytesIO(data))

	def testCompleteBackupChecksOnAnotherMachineWithoutSourceValues(self):
		self.values['unrelated/secret'] = 'MUST_NOT_COPY'
		self.assertEqual(self.write(), 0)
		self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
		with (
			mock.patch.object(
				localdata, 'readValues', side_effect=AssertionError('không đọc tại máy')
			),
			mock.patch.object(github, 'gh', side_effect=AssertionError('không gọi GitHub')),
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(backup.checkBackup(self.path), 0)
			config, values, problems = backup.readBackup(self.path)
		self.assertEqual(config, self.config)
		self.assertEqual(
			values, dict.fromkeys(localdata.valueReferences(config), 'PRIVATE_FIXTURE')
		)
		self.assertEqual(problems, [])
		self.assertNotIn('PRIVATE_FIXTURE', output.getvalue())

	def testIncompleteBackupPreservesAvailableDataAndCannotClaimCompleteness(self):
		self.config['organization']['manual_settings']['secrets']['status'] = 'unverified'
		self.values.clear()
		self.assertEqual(self.write(), 1)
		with contextlib.redirect_stdout(io.StringIO()):
			self.assertEqual(backup.checkBackup(self.path), 1)
		config, values, problems = backup.readBackup(self.path)
		self.assertEqual(config, self.config)
		self.assertEqual(values, {})
		self.assertTrue(any('manual_settings/secrets' in item for item in problems))
		self.assertTrue(any('private_values' in item for item in problems))

	def testDeletedManualAndCollectionGroupsRemainIncomplete(self):
		self.config['organization']['manual_settings'].pop('secrets')
		self.config['organization']['collections'].pop('rulesets')
		self.assertEqual(self.write(), 1)
		_, _, problems = backup.readBackup(self.path)
		self.assertTrue(any('manual_settings/secrets' in item for item in problems))
		self.assertTrue(any('collections/rulesets' in item for item in problems))

	def testExistingBackupNeverOverwritten(self):
		self.assertEqual(self.write(), 0)
		before = self.path.read_bytes()
		with self.assertRaises(ValueError):
			self.write()
		self.assertEqual(self.path.read_bytes(), before)

	def testRecoveryExportResolvesPrivateDataOfflineAndPreservesUnknowns(self):
		ref = 'manual/settings-pages'
		self.config['organization']['manual_settings']['settings_pages'] = {
			'status': 'pending',
			'configuration_source': ref,
		}
		self.values[ref] = json.dumps(
			{
				'pages': [
					{
						'url': 'https://github.com/organizations/TOANQUYNHLLC/settings/security',
						'fields': [{'name': 'policy', 'value': 'PRIVATE_FIXTURE'}],
					}
				],
				'excluded_groups': ['secrets'],
			}
		)
		self.config['organization']['collections'].pop('network_configurations')
		self.config['organization']['pending_settings'] = {
			'collections': {'network_configurations': None}
		}
		self.config['unavailable'] = {
			'orgs/TOANQUYNHLLC/settings/network-configurations': 'HTTP 404'
		}
		self.assertEqual(self.write(), 1)
		destination = Path(self.directory.name) / 'recovery.json'
		with (
			mock.patch.object(
				localdata, 'readValues', side_effect=AssertionError('Không đọc tệp riêng tại máy')
			),
			mock.patch.object(github, 'gh', side_effect=AssertionError('Không gọi GitHub')),
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(backup.exportRecovery(self.path, destination), 1)
		self.assertNotIn('PRIVATE_FIXTURE', output.getvalue())
		self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
		data = json.loads(destination.read_text())
		self.assertFalse(data['complete'])
		scope = data['scopes']['orgs/TOANQUYNHLLC']
		item = scope['manual_settings']['settings_pages']
		self.assertEqual(item['status'], 'pending')
		self.assertEqual(
			item['configuration_source']['saved_value']['pages'][0]['fields'][0]['value'],
			'PRIVATE_FIXTURE',
		)
		self.assertIsNone(scope['pending_settings']['collections']['network_configurations'])
		self.assertEqual(data['unavailable'], self.config['unavailable'])
		before = destination.read_bytes()
		with self.assertRaises(ValueError):
			backup.exportRecovery(self.path, destination)
		self.assertEqual(destination.read_bytes(), before)
		with self.assertRaises(ValueError):
			backup.exportRecovery(self.path, ROOT / 'private-recovery.json')

	def testRecoveryExportKeepsIpAddressAndEntryNameOffline(self):
		base = f'orgs/{github.ORG}/ip-allow-list'
		addressReference = base + '/value#' + 'a' * 32
		nameReference = base + '/name#' + 'b' * 32
		self.config['organization']['collections']['ip_allow_list'] = [
			{
				'enabled': False,
				'apps_enabled': False,
				'entries': [
					{
						'value_source': addressReference,
						'name_source': nameReference,
						'is_active': True,
					}
				],
			}
		]
		self.values.update({addressReference: '198.51.100.0/24', nameReference: '001'})
		self.assertEqual(self.write(), 0)
		destination = Path(self.directory.name) / 'recovery.json'
		with (
			mock.patch.object(
				localdata, 'readValues', side_effect=AssertionError('Không đọc tệp gốc')
			),
			mock.patch.object(github, 'gh', side_effect=AssertionError('Không gọi GitHub')),
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(backup.exportRecovery(self.path, destination), 0)
		data = json.loads(destination.read_text())
		policy = data['scopes'][f'orgs/{github.ORG}']['collections']['ip_allow_list'][0]
		entry = policy['entries'][0]
		self.assertFalse(policy['enabled'])
		self.assertTrue(entry['is_active'])
		self.assertEqual(entry['value_source']['saved_value'], '198.51.100.0/24')
		self.assertEqual(
			entry['name_source'],
			{'reference': nameReference, 'available': True, 'saved_value': '001'},
		)

	def testRecoveryReferencesPreserveStringsAndReportMissingValues(self):
		data = {
			'value_source': 'variable/ref',
			'pattern_source': 'missing/ref',
			'nested': [{'definition_source': 'definition/ref'}],
		}
		values = {'variable/ref': '001', 'definition/ref': '{"pattern":"^fixture$"}'}
		exported = backup.expandReferences(data, values)
		self.assertEqual(exported['value_source']['saved_value'], '001')
		self.assertFalse(exported['pattern_source']['available'])
		self.assertNotIn('saved_value', exported['pattern_source'])
		self.assertEqual(
			exported['nested'][0]['definition_source']['saved_value'], {'pattern': '^fixture$'}
		)
		self.assertEqual(data['value_source'], 'variable/ref')

	def testRecoveryCliWorksOfflineAndRejectsWriteOptions(self):
		self.assertEqual(self.write(), 0)
		module = loadScript('org-setup')
		destination = Path(self.directory.name) / 'recovery.json'
		args = [
			'org-setup.py',
			'settings-backup-export',
			'--backup-file',
			str(self.path),
			'--recovery-file',
			str(destination),
		]
		with (
			mock.patch.object(module.sys, 'argv', args),
			mock.patch.object(module, 'signedIn') as login,
			mock.patch.object(github, 'gh') as request,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(module.main(), 0)
		login.assert_not_called()
		request.assert_not_called()
		for extra in (['--apply'], ['--repo', 'app'], ['--complete'], ['--only', 'labels']):
			with (
				mock.patch.object(module.sys, 'argv', [*args, *extra]),
				contextlib.redirect_stderr(io.StringIO()),
				self.assertRaises(SystemExit),
			):
				module.main()

	def testRepositoryAndSymlinkDestinationsAreRejected(self):
		for path in (ROOT / '.cache' / 'backup.tar.gz',):
			with self.assertRaises(ValueError):
				backup.writeBackup(path)
		self.path.symlink_to(ROOT / 'github-settings.json')
		with self.assertRaises(ValueError):
			backup.writeBackup(self.path)

	def testCorruptedContentNeverPassesChecksum(self):
		self.assertEqual(self.write(), 0)
		self.rewrite(
			lambda entries: [
				(member, data + b' ' if member.name == 'values.json' else data)
				for member, data in entries
			]
		)
		with self.assertRaises(ValueError):
			backup.checkBackup(self.path)

	def testDuplicatedNamesAndNonRegularMembersCannotBeExtracted(self):
		self.assertEqual(self.write(), 0)
		self.rewrite(lambda entries: [*entries, entries[0]])
		with self.assertRaises(ValueError):
			backup.readBackup(self.path)
		self.path.unlink()
		self.assertEqual(self.write(), 0)

		def symlink(entries):
			member = tarfile.TarInfo('values.json')
			member.type = tarfile.SYMTYPE
			member.linkname = '../../private'
			return [
				(member, b'') if item.name == 'values.json' else (item, data)
				for item, data in entries
			]

		self.rewrite(symlink)
		with self.assertRaises(ValueError):
			backup.readBackup(self.path)

	def testWorldReadableBackupRejected(self):
		self.assertEqual(self.write(), 0)
		for mode in (0o644, 0o400, 0o700):
			with self.subTest(mode=mode):
				os.chmod(self.path, mode)
				with self.assertRaises(ValueError):
					backup.readBackup(self.path)

	def testWorldReadableArchiveMemberAndBrokenGzipAreRejected(self):
		self.assertEqual(self.write(), 0)

		def publicMember(entries):
			entries[0][0].mode = 0o644
			return entries

		self.rewrite(publicMember)
		with self.assertRaises(ValueError):
			backup.readBackup(self.path)
		self.path.write_bytes(b'\x1f\x8b\x08\x00')
		with self.assertRaises(ValueError):
			backup.readBackup(self.path)

	def testManualSnapshotIsIncludedButNeverPrinted(self):
		self.config['organization']['manual_settings']['secrets'] = {
			'status': 'verified',
			'configuration_source': 'manual/secrets',
		}
		self.values['manual/secrets'] = 'PRIVATE_FIXTURE'
		self.assertEqual(self.write(), 0)
		_, values, _ = backup.readBackup(self.path)
		self.assertEqual(values['manual/secrets'], 'PRIVATE_FIXTURE')

	def testCliCommandsWorkOfflineAndRejectMutationOptions(self):
		self.assertEqual(self.write(), 0)
		module = loadScript('org-setup')
		with (
			mock.patch.object(
				module.sys,
				'argv',
				['org-setup.py', 'settings-backup-check', '--backup-file', str(self.path)],
			),
			mock.patch.object(module, 'signedIn') as login,
			mock.patch.object(github, 'gh') as request,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(module.main(), 0)
		login.assert_not_called()
		request.assert_not_called()
		for extra in (['--apply'], ['--repo', 'app'], ['--complete'], ['--only', 'labels']):
			with (
				self.subTest(extra=extra),
				mock.patch.object(
					module.sys,
					'argv',
					[
						'org-setup.py',
						'settings-backup-check',
						'--backup-file',
						str(self.path),
						*extra,
					],
				),
				contextlib.redirect_stderr(io.StringIO()),
				self.assertRaises(SystemExit),
			):
				module.main()

	def testCollectionAndNestedPendingPrivateReferencesAreRequired(self):
		scope = {
			'collections': {'variables': [{'name': 'SETTING', 'value_source': 'variable/ref'}]},
			'pending_settings': {
				'collections': {
					'webhooks': [{'url_source': 'hook/url', 'secret_source': 'hook/secret'}]
				}
			},
		}
		problems = inventory.scopeProblems(scope, 'orgs/TOANQUYNHLLC', privateValues={})
		for reference in ('variable/ref', 'hook/url', 'hook/secret'):
			self.assertTrue(any(reference in item for item in problems))
		before = copy.deepcopy(scope)
		inventory.scopeProblems(scope, 'orgs/TOANQUYNHLLC', privateValues={})
		self.assertEqual(scope, before)

	def testRegistryTokenRequiresCredentialButOidcDoesNot(self):
		item = {
			'name': 'registry',
			'definition_source': 'registry/definition',
			'credential_source': 'registry/definition/credential',
		}
		scope = {'collections': {'private_registries': [item]}}
		for authType, fields, missing in (
			('token', {}, True),
			('oidc_azure', {'tenant_id': 'tenant', 'client_id': 'client'}, False),
		):
			with self.subTest(authType=authType):
				values = {
					'registry/definition': json.dumps(
						{
							'registry_type': 'npm_registry',
							'url': 'https://registry.example.test',
							'auth_type': authType,
							**fields,
						}
					)
				}
				problems = inventory.scopeProblems(scope, 'orgs/TOANQUYNHLLC', privateValues=values)
				self.assertEqual(any('credential' in problem for problem in problems), missing)

	def testIncompleteDependabotPolicyCannotClaimFullCoverage(self):
		self.config['organization']['collections']['dependabot_access'][0].pop('default_level')
		self.assertEqual(self.write(), 1)
		_, _, problems = backup.readBackup(self.path)
		self.assertTrue(any('dependabot_access/default_level' in problem for problem in problems))

	def testManualExclusionCannotHideMissingApiValueWithSharedReference(self):
		reference = self.config['organization']['private_settings']['billing_email']['value_source']
		self.config['organization']['manual_settings']['billing'] = {
			'status': 'not_applicable',
			'configuration_source': reference,
		}
		self.values.clear()
		self.assertEqual(self.write(), 1)
		_, _, problems = backup.readBackup(self.path)
		self.assertTrue(any(reference in problem for problem in problems))

	def testMissingUnusedManualReferenceDoesNotRequireApiValue(self):
		self.config['organization']['manual_settings']['billing'] = {
			'status': 'not_applicable',
			'configuration_source': 'manual/old-billing',
		}
		self.assertEqual(self.write(), 0)
		_, values, problems = backup.readBackup(self.path)
		self.assertNotIn('manual/old-billing', values)
		self.assertEqual(problems, [])

	def testMalformedPrivateDefinitionsAndCredentialsRemainIncompleteWithoutLeaks(self):
		base = f'orgs/{github.ORG}'
		patternReference = f'{base}/secret-scanning/custom-patterns/definition#' + 'a' * 32
		registryReference = f'{base}/private-registries/definition#' + 'b' * 32
		for case in ('pattern', 'registry', 'credential'):
			with self.subTest(case=case):
				config = completeConfig()
				values = dict.fromkeys(localdata.valueReferences(config), 'PRIVATE_FIXTURE')
				if case == 'pattern':
					config['organization']['collections']['custom_patterns'] = [
						{
							'name': 'Example',
							'slug': 'example',
							'state': 'unpublished',
							'push_protection_enabled': False,
							'definition_source': patternReference,
						}
					]
					values[patternReference] = json.dumps({'pattern': ['PRIVATE_FIXTURE']})
				else:
					config['organization']['collections']['private_registries'] = [
						{
							'name': 'example',
							'definition_source': registryReference,
							'credential_source': registryReference + '/credential',
							'visibility': 'all',
							'selected_repositories': [],
						}
					]
					values[registryReference] = json.dumps(
						{
							'registry_type': 'npm_registry',
							'url': 'PRIVATE_FIXTURE'
							if case == 'registry'
							else 'https://registry.example.test',
						}
					)
					values[registryReference + '/credential'] = 'PRIVATE_FIXTURE'
				self.config, self.values = configuration.validateConfig(config), values
				self.assertEqual(self.write(), 1)
				_, _, problems = backup.readBackup(self.path)
				self.assertTrue(any('thiếu hoặc sai' in problem for problem in problems))
				self.assertNotIn('PRIVATE_FIXTURE', str(problems))
				self.path.unlink()

	def testRegistryCredentialShapeChecksOfflineAndAcceptsSealedBoxStructure(self):
		from orgsetup import registries

		valid = {
			'key_id': 'example-key',
			'encrypted_value': base64.b64encode(b'x' * 48).decode('ascii'),
		}
		self.assertEqual(registries.credentialDefinition(valid), valid)
		for invalid in (
			[],
			{},
			dict(valid, key_id=''),
			dict(valid, encrypted_value='PRIVATE_FIXTURE'),
			dict(valid, encrypted_value=base64.b64encode(b'x' * 47).decode('ascii')),
		):
			with self.subTest(invalid=invalid), self.assertRaises(ValueError) as failure:
				registries.credentialDefinition(invalid)
			self.assertNotIn('PRIVATE_FIXTURE', str(failure.exception))

	def testSelectedSecurityBindingKeepsCaptureFailureAndStopsBeforeApiReads(self):
		self.config['repositories']['app'] = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'security_configuration': None,
			'collections': {'labels': []},
		}
		path = f'repos/{github.ORG}/app/code-security'
		self.config['unavailable'][path] = 'HTTP 403'
		before = copy.deepcopy(self.config)
		with (
			mock.patch.object(configuration, 'readConfig', return_value=self.config),
			mock.patch.object(configuration, 'configuredScopes') as read,
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(ValueError, 'có mục chưa nhập'),
		):
			configuration.syncConfiguredSettings(True, only=['security_configuration', 'labels'])
		read.assert_not_called()
		write.assert_not_called()
		self.assertEqual(self.config, before)

	def testMalformedManifestAndFalseCompletenessCannotPassValidation(self):
		for change in (
			{'format_version': True},
			{'organization_name': 'OTHER'},
			{'created_at': None},
			{'created_at': '2026-10-13'},
			{'created_at': 'invalid'},
			{'complete': False},
			{'problems': [{}]},
			{'sha256': []},
			{'unexpected': 'PRIVATE_FIXTURE'},
		):
			with self.subTest(change=change):
				self.assertEqual(self.write(), 0)

				def update(entries, change=change):
					return [
						(member, backup.jsonBytes(dict(json.loads(data), **change)))
						if member.name == 'manifest.json'
						else (member, data)
						for member, data in entries
					]

				self.rewrite(update)
				with self.assertRaises(ValueError) as failure:
					backup.readBackup(self.path)
				self.assertNotIn('PRIVATE_FIXTURE', str(failure.exception))
				self.path.unlink()


if __name__ == '__main__':
	unittest.main()
