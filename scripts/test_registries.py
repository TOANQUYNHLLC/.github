"""Kiểm tra khôi phục registry, OIDC, credentials riêng và danh sách repository theo tên."""

import base64
import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from unittest import mock

try:
	from testsupport import ROOT
except ModuleNotFoundError:
	from scripts.testsupport import ROOT

from orgsetup import catalog, configuration, github, localdata, patterns, registries, resources

BASE = 'orgs/TOANQUYNHLLC'


def apiRegistry(**changes):
	return dict(
		{
			'name': 'REGISTRY_SECRET',
			'registry_type': 'docker_registry',
			'url': 'https://registry.example.test',
			'auth_type': 'oidc_azure',
			'tenant_id': 'TENANT',
			'client_id': 'CLIENT',
			'visibility': 'all',
			'created_at': 'METADATA',
		},
		**changes,
	)


class RegistrySettingsTest(unittest.TestCase):
	def setUp(self):
		self.temporary = tempfile.TemporaryDirectory()
		self.addCleanup(self.temporary.cleanup)
		patcher = mock.patch.dict(os.environ, ORGSETUP_PRIVATE_DIR=self.temporary.name)
		patcher.start()
		self.addCleanup(patcher.stop)
		localdata.resetCapture()
		self.addCleanup(localdata.resetCapture)

	def capture(self, api):
		with (
			mock.patch.object(resources, 'readCollection', return_value=[{'name': api['name']}]),
			mock.patch.object(github, 'ghJson', return_value=api),
		):
			return registries.readDetails(BASE)[0]

	def save(self, items, credential=None):
		config = {
			'organization': {'collections': {'private_registries': items}},
			'repositories': {},
		}
		with contextlib.redirect_stdout(io.StringIO()):
			localdata.saveCapturedValues(config)
		if credential is not None:
			values = localdata.readValues()
			values[items[0]['credential_source']] = json.dumps(credential)
			localdata.dataPath().write_text(json.dumps(values), encoding='utf-8')

	def testReadFiltersPrivateDefinitionAndDoesNotInventHiddenSecret(self):
		items = self.capture(
			apiRegistry(
				username='PRIVATE_USERNAME', encrypted_value='DO_NOT_CAPTURE', key_id='OLD_KEY'
			)
		)
		self.save(items)
		self.assertNotIn('PRIVATE_USERNAME', json.dumps(items))
		self.assertNotIn('TENANT', json.dumps(items))
		values = localdata.readValues()
		self.assertNotIn(items[0]['credential_source'], values)
		self.assertNotIn('DO_NOT_CAPTURE', json.dumps(values))
		self.assertNotIn('created_at', json.dumps(values))
		self.assertEqual(
			registries.privateDefinition(items[0]['definition_source'])['username'],
			'PRIVATE_USERNAME',
		)

	def testOidcCreateWithoutCredentialsAndNoopWithServerAssignedName(self):
		items = self.capture(apiRegistry())
		self.save(items)
		plan = []
		with mock.patch.object(resources, 'readCollection', return_value=[]):
			registries.collectionChanges(plan, BASE, [], items, {})
		self.assertEqual(plan[0][1], 'POST')
		self.assertNotIn('CLIENT', json.dumps(plan))
		body = patterns.resolvePlanBody(plan[0][0], plan[0][2])
		self.assertNotIn('name', body)
		self.assertNotIn('encrypted_value', body)
		self.assertEqual(body['auth_type'], 'oidc_azure')
		live = self.capture(apiRegistry(name='SERVER_ASSIGNED'))
		plan = []
		registries.collectionChanges(plan, BASE, live, items, {})
		self.assertEqual(plan, [])

	def testSecretRegistryCannotCreateWithoutEncryptedCredentials(self):
		api = apiRegistry(auth_type='token')
		api.pop('tenant_id')
		api.pop('client_id')
		items = self.capture(api)
		self.save(items)
		with self.assertRaisesRegex(ValueError, 'credentials'):
			registries.collectionChanges([], BASE, [], items, {})
		credential = {
			'encrypted_value': base64.b64encode(b'x' * 64).decode(),
			'key_id': 'CURRENT_KEY',
		}
		self.save(items, credential)
		with (
			mock.patch.object(resources, 'readCollection', return_value=[]),
			mock.patch.object(github, 'ghJson', return_value={'key_id': 'CURRENT_KEY'}),
		):
			plan = []
			registries.collectionChanges(plan, BASE, [], items, {})
		self.assertNotIn(credential['encrypted_value'], json.dumps(plan))
		self.assertEqual(
			patterns.resolvePlanBody(plan[0][0], plan[0][2])['encrypted_value'],
			credential['encrypted_value'],
		)

	def testStalePublicKeyAndPlaintextCredentialAreRejectedWithoutLeak(self):
		reference = BASE + '/private-registries/definition#' + 'a' * 32 + '/credential'
		for value in (
			{'encrypted_value': 'PRIVATE_VALUE', 'key_id': 'CURRENT'},
			{'encrypted_value': base64.b64encode(b'x' * 64).decode(), 'key_id': 'OLD'},
		):
			with (
				mock.patch.object(localdata, 'privateValue', return_value=json.dumps(value)),
				mock.patch.object(github, 'ghJson', return_value={'key_id': 'CURRENT'}),
				self.assertRaises(ValueError) as caught,
			):
				registries.credentials(BASE, reference)
			self.assertNotIn('PRIVATE_VALUE', str(caught.exception))

	def testSelectedRepositoryIdsAreCapturedAsNamesAndResolvedFresh(self):
		api = apiRegistry(visibility='selected', selected_repository_ids=[4])
		with (
			mock.patch.object(resources, 'readCollection', return_value=[{'name': api['name']}]),
			mock.patch.object(
				github, 'ghJson', side_effect=[api, {'id': 4, 'full_name': 'TOANQUYNHLLC/.github'}]
			),
		):
			items, _ = registries.readDetails(BASE)
		self.assertEqual(items[0]['selected_repositories'], ['TOANQUYNHLLC/.github'])
		self.save(items)
		with (
			mock.patch.object(resources, 'readCollection', return_value=[]),
			mock.patch.object(resources, 'repositoryIds', return_value=[95]) as resolve,
		):
			plan = []
			registries.collectionChanges(plan, BASE, [], items, {})
		self.assertEqual(
			patterns.resolvePlanBody(plan[0][0], plan[0][2])['selected_repository_ids'], [95]
		)
		resolve.assert_called_once_with(['TOANQUYNHLLC/.github'], {})

	def testVisibilityUpdatePreservesExistingHiddenSecret(self):
		api = apiRegistry(auth_type='token')
		api.pop('tenant_id')
		api.pop('client_id')
		current = self.capture(api)
		self.save(current)
		wanted = copy.deepcopy(current)
		wanted[0]['visibility'] = 'private'
		with mock.patch.object(registries, 'readDetails', return_value=(current, {})):
			plan = []
			registries.collectionChanges(plan, BASE, current, wanted, {})
		body = patterns.resolvePlanBody(plan[0][0], plan[0][2])
		self.assertNotIn('encrypted_value', body)
		self.assertEqual(body['visibility'], 'private')

	def testMissingApiFieldsWrongIdentityAndAuthTypeChangeBlock(self):
		bad = apiRegistry()
		bad.pop('url')
		with self.assertRaises(ValueError):
			self.capture(bad)
		with (
			mock.patch.object(resources, 'readCollection', return_value=[{'name': 'EXPECTED'}]),
			mock.patch.object(github, 'ghJson', return_value=apiRegistry()),
			self.assertRaisesRegex(ValueError, 'xác minh'),
		):
			registries.readDetails(BASE)
		current = self.capture(apiRegistry())
		wanted = copy.deepcopy(current)
		self.save(wanted)
		value = registries.definition(
			{
				'registry_type': 'docker_registry',
				'url': 'https://registry.example.test',
				'auth_type': 'oidc_gcp',
				'workload_identity_provider': 'projects/1/providers/test',
			}
		)
		with (
			mock.patch.object(
				registries,
				'privateDefinition',
				side_effect=lambda reference, captured=False: (
					registries.definition(
						{
							field: apiRegistry()[field]
							for field in registries.DEFINITION_FIELDS
							if field in apiRegistry()
						}
					)
					if captured
					else value
				),
			),
			self.assertRaisesRegex(ValueError, 'auth_type'),
		):
			registries.collectionChanges([], BASE, current, wanted, {})

	def testEmptyRegistryIsVerifiedAndReferencesMustMatchScope(self):
		with mock.patch.object(resources, 'readCollection', return_value=[]):
			self.assertEqual(
				catalog.readCollections(BASE, ['private_registries']),
				({'private_registries': []}, {}, {}),
			)
		items = self.capture(apiRegistry())
		with self.assertRaises(ValueError):
			catalog.validateReferenceScope('orgs/OTHER', 'private_registries', items)
		with self.assertRaises(ValueError):
			registries.readDetails('repos/TOANQUYNHLLC/.github')

	def testRotatedKeyAndWrongWriteResultCannotBeReportedAsSuccess(self):
		body = {'encrypted_value': 'PRIVATE_CIPHERTEXT', 'key_id': 'OLD'}
		with (
			mock.patch.object(github, 'ghJson', return_value={'key_id': 'NEW'}),
			self.assertRaises(ValueError),
		):
			registries.validatePlanBody(BASE + '/private-registries', body)
		body = registries.definition(
			{
				field: apiRegistry()[field]
				for field in registries.DEFINITION_FIELDS
				if field in apiRegistry()
			}
		)
		body['visibility'] = 'all'
		for response in (
			'{}',
			json.dumps(apiRegistry(url='https://other.example.test')),
			json.dumps(apiRegistry(visibility='private')),
		):
			with self.subTest(response=response), self.assertRaises(ValueError):
				registries.validateResponse(response, body)
		registries.validateResponse(json.dumps(apiRegistry()), body)

	def testRemovingOidcFieldBlocksBeforeWritesInsteadOfKeepingOldValue(self):
		api = apiRegistry(
			auth_type='oidc_jfrog',
			jfrog_oidc_provider_name='PROVIDER',
			identity_mapping_name='MAPPING',
		)
		api.pop('tenant_id')
		api.pop('client_id')
		current = self.capture(api)
		wanted = copy.deepcopy(current)
		self.save(wanted)
		previous = registries.privateDefinition(wanted[0]['definition_source'])
		desired = dict(previous)
		desired.pop('identity_mapping_name')
		with (
			mock.patch.object(
				registries,
				'privateDefinition',
				side_effect=lambda reference, captured=False: previous if captured else desired,
			),
			self.assertRaisesRegex(ValueError, 'xóa tham số'),
		):
			registries.collectionChanges([], BASE, current, wanted, {})

	def testOidcRoundtripReadsBackAndSecondApplyDoesNotWrite(self):
		items = self.capture(apiRegistry())
		self.save(items)
		wanted = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'collections': {'private_registries': items},
		}
		live = []
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}

		def readScopes(source):
			for item in live:
				localdata.captureValue(
					BASE + '/private-registries/definition',
					localdata.privateValue(item['definition_source']),
				)
			return [
				(
					None,
					wanted,
					(dict(wanted, collections={'private_registries': copy.deepcopy(live)}), {}),
				)
			]

		def write(*args, stdin):
			body = json.loads(stdin)
			self.assertEqual(args[3], BASE + '/private-registries')
			created = dict(body, name='SERVER_ASSIGNED')
			live.append(dict(items[0], name='SERVER_ASSIGNED'))
			return json.dumps(created)

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'configuredScopes', side_effect=readScopes),
			mock.patch.object(
				registries, 'readDetails', side_effect=lambda base: (copy.deepcopy(live), {})
			),
			mock.patch.object(github, 'gh', side_effect=write) as mutation,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		mutation.assert_called_once()


if __name__ == '__main__':
	unittest.main()
