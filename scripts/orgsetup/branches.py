"""Bản khôi phục bảo vệ nhánh kiểu cũ qua GraphQL, giữ pattern và ràng buộc GitHub Apps."""

import copy

from orgsetup import enterprise, github

BOOLEAN_FIELDS = (
	'allowsDeletions',
	'allowsForcePushes',
	'blocksCreations',
	'dismissesStaleReviews',
	'isAdminEnforced',
	'lockAllowsFetchAndMerge',
	'lockBranch',
	'requireLastPushApproval',
	'requiresApprovingReviews',
	'requiresCodeOwnerReviews',
	'requiresCommitSignatures',
	'requiresConversationResolution',
	'requiresDeployments',
	'requiresLinearHistory',
	'requiresStatusChecks',
	'requiresStrictStatusChecks',
	'restrictsPushes',
	'restrictsReviewDismissals',
)
ACTOR_FIELDS = {
	'reviewDismissalActorIds': 'reviewDismissalAllowances',
	'bypassPullRequestActorIds': 'bypassPullRequestAllowances',
	'bypassForcePushActorIds': 'bypassForcePushAllowances',
	'pushActorIds': 'pushAllowances',
}
ACTOR_CONNECTION = """{totalCount nodes{actor{__typename ... on Node{id}}}
	pageInfo{hasNextPage endCursor}}"""
RULE_FIELDS = (
	'pattern',
	'requiredApprovingReviewCount',
	'requiredDeploymentEnvironments',
	'requiredStatusChecks',
	*BOOLEAN_FIELDS,
	*ACTOR_FIELDS,
)
RULE_QUERY = (
	' '.join(BOOLEAN_FIELDS)
	+ """ id pattern requiredApprovingReviewCount
	requiredDeploymentEnvironments requiredStatusChecks{context app{id}}
	"""
	+ ' '.join(f'{field}(first:100){ACTOR_CONNECTION}' for field in ACTOR_FIELDS.values())
)
QUERY = (
	"""query($owner:String!,$name:String!,$after:String){repository(owner:$owner,name:$name){
	id nameWithOwner branchProtectionRules(first:100,after:$after){totalCount
	nodes{"""
	+ RULE_QUERY
	+ """} pageInfo{hasNextPage endCursor}}}}"""
)


def validateGroup(items):
	if not isinstance(items, list):
		raise TypeError('Bảo vệ nhánh phải là danh sách')
	patterns = set()
	for item in items:
		if not isinstance(item, dict) or set(item) != set(RULE_FIELDS):
			raise ValueError('Bảo vệ nhánh thiếu trường hoặc chứa metadata')
		if (
			not isinstance(item['pattern'], str)
			or not item['pattern']
			or item['pattern'] in patterns
		):
			raise ValueError('Bảo vệ nhánh có pattern không hợp lệ hoặc trùng')
		patterns.add(item['pattern'])
		if any(type(item[field]) is not bool for field in BOOLEAN_FIELDS):
			raise ValueError('Bảo vệ nhánh có cờ sai kiểu')
		count = item['requiredApprovingReviewCount']
		if type(count) is not int or not 0 <= count <= 6:
			raise ValueError('Bảo vệ nhánh có số phê duyệt không hợp lệ')
		for field in ('requiredDeploymentEnvironments', *ACTOR_FIELDS):
			values = item[field]
			if (
				not isinstance(values, list)
				or any(not isinstance(value, str) or not value for value in values)
				or len(values) != len(set(values))
			):
				raise ValueError('Bảo vệ nhánh có danh sách môi trường hoặc actor không hợp lệ')
		checks = item['requiredStatusChecks']
		if not isinstance(checks, list):
			raise TypeError('Bảo vệ nhánh cần danh sách status checks')
		contexts = set()
		for check in checks:
			if (
				not isinstance(check, dict)
				or set(check) != {'context', 'appId'}
				or not isinstance(check['context'], str)
				or not check['context']
				or (
					check['appId'] is not None
					and (not isinstance(check['appId'], str) or not check['appId'])
				)
				or (check['context'], check['appId']) in contexts
			):
				raise ValueError('Bảo vệ nhánh có status check hoặc GitHub App không hợp lệ')
			contexts.add((check['context'], check['appId']))
	return items


def connectionPage(connection):
	if (
		not isinstance(connection, dict)
		or type(connection.get('totalCount')) is not int
		or connection['totalCount'] < 0
		or not isinstance(connection.get('nodes'), list)
	):
		raise ValueError('Bảo vệ nhánh thiếu trang hoặc tổng dữ liệu')
	page = connection.get('pageInfo')
	if not isinstance(page, dict) or type(page.get('hasNextPage')) is not bool:
		raise ValueError('Bảo vệ nhánh thiếu thông tin phân trang')
	cursor = page.get('endCursor')
	if page['hasNextPage'] and (not isinstance(cursor, str) or not cursor):
		raise ValueError('Bảo vệ nhánh có cursor không hợp lệ')
	return connection['nodes'], connection['totalCount'], cursor if page['hasNextPage'] else None


def readActors(connection, identity, field):
	actors, total, cursors = [], None, set()
	while True:
		nodes, count, cursor = connectionPage(connection)
		if total is not None and count != total:
			raise ValueError('Actor bảo vệ nhánh thay đổi trong lúc đọc')
		total = count
		for node in nodes:
			actor = node.get('actor') if isinstance(node, dict) else None
			if (
				not isinstance(actor, dict)
				or actor.get('__typename') not in ('User', 'Team', 'App')
				or not isinstance(actor.get('id'), str)
				or not actor['id']
				or actor['id'] in actors
			):
				raise ValueError('Bảo vệ nhánh có actor chưa xác minh được')
			actors.append(actor['id'])
		if cursor is None:
			break
		if cursor in cursors:
			raise ValueError('Actor bảo vệ nhánh lặp cursor')
		cursors.add(cursor)
		query = (
			'query($id:ID!,$after:String){node(id:$id){... on BranchProtectionRule{'
			+ f'{field}(first:100,after:$after){ACTOR_CONNECTION}'
			+ '}}}'
		)
		data = enterprise.graphqlResult(
			github.ghJson(
				'api',
				'graphql',
				'-f',
				f'query={query}',
				'-f',
				f'id={identity}',
				'-f',
				f'after={cursor}',
			)
		)
		connection = (data.get('node') or {}).get(field)
	if len(actors) != total:
		raise ValueError('Chưa đọc đủ actor bảo vệ nhánh')
	return sorted(actors)


def readDetails(base):
	parts = base.split('/')
	if len(parts) != 3 or parts[0] != 'repos' or parts[1].casefold() != github.ORG.casefold():
		raise ValueError('Bảo vệ nhánh cần repository thuộc tổ chức')
	result, ids, total, identity, cursor, cursors = [], {}, None, None, None, set()
	while True:
		args = [
			'api',
			'graphql',
			'-f',
			f'query={QUERY}',
			'-f',
			f'owner={parts[1]}',
			'-f',
			f'name={parts[2]}',
		]
		if cursor is not None:
			args.extend(['-f', f'after={cursor}'])
		repo = enterprise.graphqlResult(github.ghJson(*args)).get('repository')
		if (
			not isinstance(repo, dict)
			or not isinstance(repo.get('nameWithOwner'), str)
			or repo['nameWithOwner'].casefold() != '/'.join(parts[1:]).casefold()
			or not isinstance(repo.get('id'), str)
			or not repo['id']
		):
			raise ValueError('Không xác minh được repository bảo vệ nhánh')
		nodes, count, cursor = connectionPage(repo.get('branchProtectionRules'))
		if identity is not None and (identity != repo['id'] or total != count):
			raise ValueError('Bảo vệ nhánh thay đổi trong lúc đọc')
		identity, total = repo['id'], count
		for rule in nodes:
			if (
				not isinstance(rule, dict)
				or not isinstance(rule.get('id'), str)
				or not rule['id']
				or not isinstance(rule.get('pattern'), str)
				or rule['pattern'] in ids
				or rule['id'] in ids.values()
			):
				raise ValueError('Bảo vệ nhánh thiếu hoặc trùng pattern/ID')
			value = {field: rule[field] for field in BOOLEAN_FIELDS}
			if rule['requiredApprovingReviewCount'] is None and rule['requiresApprovingReviews']:
				raise ValueError('Bảo vệ nhánh bật phê duyệt nhưng thiếu số lượng')
			value.update(
				pattern=rule['pattern'],
				requiredApprovingReviewCount=rule['requiredApprovingReviewCount']
				if rule['requiredApprovingReviewCount'] is not None
				else 0,
				requiredDeploymentEnvironments=rule['requiredDeploymentEnvironments'] or [],
				requiredStatusChecks=[],
			)
			checks = rule['requiredStatusChecks']
			if checks is not None and not isinstance(checks, list):
				raise ValueError('API status checks bảo vệ nhánh sai kiểu')
			for check in checks or []:
				app = check.get('app') if isinstance(check, dict) else None
				if (
					not isinstance(check, dict)
					or 'context' not in check
					or (
						app is not None
						and (
							not isinstance(app, dict)
							or not isinstance(app.get('id'), str)
							or not app['id']
						)
					)
				):
					raise ValueError('Không xác minh được GitHub App của status check')
				value['requiredStatusChecks'].append(
					{'context': check['context'], 'appId': app['id'] if app else None}
				)
			for target, field in ACTOR_FIELDS.items():
				value[target] = readActors(rule[field], rule['id'], field)
			ids[rule['pattern']] = rule['id']
			result.append(value)
		if cursor is None:
			break
		if cursor in cursors:
			raise ValueError('Bảo vệ nhánh lặp cursor')
		cursors.add(cursor)
	if len(result) != total:
		raise ValueError('Chưa đọc đủ bảo vệ nhánh')
	ids[None] = identity
	return validateGroup(result), ids


def summary(item):
	result = copy.deepcopy(item)
	for field in ('requiredDeploymentEnvironments', *ACTOR_FIELDS):
		result[field].sort()
	result['requiredStatusChecks'].sort(key=lambda check: (check['context'], check['appId'] or ''))
	return result


def collectionChanges(plan, base, live, targets):
	validateGroup(targets)
	present = {item['pattern']: item for item in live}
	changed = [
		item
		for item in targets
		if item['pattern'] not in present or summary(item) != summary(present[item['pattern']])
	]
	if not changed:
		return
	details, ids = readDetails(base)
	if {item['pattern']: summary(item) for item in details} != {
		pattern: summary(item) for pattern, item in present.items()
	}:
		raise ValueError('Bảo vệ nhánh thay đổi trong lúc lập kế hoạch')
	for target in changed:
		body = copy.deepcopy(target)
		if target['pattern'] in present:
			body['branchProtectionRuleId'] = ids[target['pattern']]
			name, inputType = 'updateBranchProtectionRule', 'UpdateBranchProtectionRuleInput'
		else:
			body['repositoryId'] = ids[None]
			name, inputType = 'createBranchProtectionRule', 'CreateBranchProtectionRuleInput'
		plan.append(
			enterprise.mutationStep(name, inputType, body, {'branch_protection': target['pattern']})
		)
