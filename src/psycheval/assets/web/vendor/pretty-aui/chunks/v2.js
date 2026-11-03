globalThis.__zod_globalConfig ??= {}, globalThis.__zod_globalConfig.jitless = !0;
import { A as e, B as t, C as n, D as r, E as i, F as a, H as o, K as ee, M as s, N as c, O as l, P as u, S as d, T as f, U as te, W as ne, Y as p, a as re, b as m, c as ie, d as ae, f as h, i as oe, j as g, k as _, m as v, n as se, o as ce, p as le, r as ue, t as de, v as y, w as b, x, y as S } from "./interactions.js";
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/v2/schema/index.js
var C = {
	initialize: "initialize",
	auth_login: "auth/login",
	providers_list: "providers/list",
	providers_set: "providers/set",
	providers_disable: "providers/disable",
	session_new: "session/new",
	session_set_config_option: "session/set_config_option",
	session_prompt: "session/prompt",
	session_cancel: "session/cancel",
	mcp_message: "mcp/message",
	session_list: "session/list",
	session_delete: "session/delete",
	session_fork: "session/fork",
	session_resume: "session/resume",
	session_close: "session/close",
	auth_logout: "auth/logout",
	nes_start: "nes/start",
	nes_suggest: "nes/suggest",
	nes_accept: "nes/accept",
	nes_reject: "nes/reject",
	nes_close: "nes/close",
	document_did_open: "document/didOpen",
	document_did_change: "document/didChange",
	document_did_close: "document/didClose",
	document_did_save: "document/didSave",
	document_did_focus: "document/didFocus"
}, w = {
	session_request_permission: "session/request_permission",
	session_update: "session/update",
	mcp_connect: "mcp/connect",
	mcp_message: "mcp/message",
	mcp_disconnect: "mcp/disconnect",
	elicitation_create: "elicitation/create",
	elicitation_complete: "elicitation/complete"
}, fe = { cancel_request: "$/cancel_request" }, T = s([l(), g()]).nullable(), E = g(), pe = g(), me = s([
	r("read"),
	r("edit"),
	r("delete"),
	r("move"),
	r("search"),
	r("execute"),
	r("think"),
	r("fetch"),
	r("switch_mode"),
	r("other"),
	g()
]), he = s([
	r("pending"),
	r("in_progress"),
	r("completed"),
	r("failed"),
	r("cancelled"),
	g()
]), ge = s([
	r("assistant"),
	r("user"),
	g()
]), D = _({
	audience: y(d(ge).nullish(), () => void 0),
	lastModified: y(a({ offset: !0 }).nullish(), () => void 0),
	priority: y(l().gte(0).lte(1).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), _e = _({
	text: g(),
	annotations: y(D.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), O = g(), ve = _({
	data: g(),
	mimeType: O,
	uri: y(u().nullish(), () => void 0),
	annotations: y(D.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ye = _({
	data: g(),
	mimeType: O,
	annotations: y(D.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), be = s([
	r("light"),
	r("dark"),
	g()
]), xe = _({
	src: u(),
	mimeType: y(O.nullish(), () => void 0),
	sizes: y(d(g()).nullish(), () => void 0),
	theme: y(be.nullish(), () => void 0)
}), Se = _({
	name: g(),
	uri: u(),
	title: y(g().nullish(), () => void 0),
	description: y(g().nullish(), () => void 0),
	icons: y(d(xe).nullish(), () => void 0),
	mimeType: y(O.nullish(), () => void 0),
	size: y(l().nullish(), () => void 0),
	annotations: y(D.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ce = _({
	text: g(),
	uri: u(),
	mimeType: y(O.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), we = _({
	blob: g(),
	uri: u(),
	mimeType: y(O.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Te = s([Ce, we]), Ee = _({
	resource: Te,
	annotations: y(D.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), k = m(s([
	_e.and(_({ type: r("text") })),
	ve.and(_({ type: r("image") })),
	ye.and(_({ type: r("audio") })),
	Se.and(_({ type: r("resource_link") })),
	Ee.and(_({ type: r("resource") })),
	S(_({ type: g() }), "type", [
		"audio",
		"image",
		"resource",
		"resource_link",
		"text"
	])
]), "type", [
	"audio",
	"image",
	"resource",
	"resource_link",
	"text"
]), De = _({
	content: k,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Oe = s([
	r("text"),
	r("binary"),
	r("directory"),
	r("symlink"),
	g()
]), A = g(), j = _({ path: A }), ke = _({
	oldPath: A,
	path: A
}), Ae = m(i(s([
	j.and(_({ operation: r("add") })),
	j.and(_({ operation: r("delete") })),
	j.and(_({ operation: r("modify") })),
	ke.and(_({ operation: r("move") })),
	ke.and(_({ operation: r("copy") })),
	S(_({ operation: g() }), "operation", [
		"add",
		"copy",
		"delete",
		"modify",
		"move"
	])
]), _({
	fileType: y(Oe.nullish(), () => void 0),
	mimeType: y(O.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
})), "operation", [
	"add",
	"copy",
	"delete",
	"modify",
	"move"
]), je = s([r("git_patch"), g()]), Me = _({
	format: je,
	text: g()
}), Ne = _({
	changes: d(Ae),
	patch: y(Me.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), M = g(), Pe = _({
	terminalId: M,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Fe = m(s([
	De.and(_({ type: r("content") })),
	Ne.and(_({ type: r("diff") })),
	Pe.and(_({ type: r("terminal") })),
	S(_({ type: g() }), "type", [
		"content",
		"diff",
		"terminal"
	])
]), "type", [
	"content",
	"diff",
	"terminal"
]), Ie = _({
	path: A,
	line: y(f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Le = _({
	toolCallId: pe,
	name: y(g().nullish(), () => void 0),
	title: y(g().nullish(), () => void 0),
	kind: y(me.nullish(), () => void 0),
	status: y(he.nullish(), () => void 0),
	content: y(d(Fe).nullish(), () => void 0),
	locations: y(d(Ie).nullish(), () => void 0),
	rawInput: y(c().optional(), () => void 0),
	rawOutput: y(c().optional(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Re = _({ toolCall: Le }), ze = _({
	command: g(),
	cwd: A,
	toolCallId: y(pe.nullish(), () => void 0),
	terminalId: y(M.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Be = m(s([
	Re.and(_({ type: r("tool_call") })),
	ze.and(_({ type: r("command") })),
	S(_({ type: g() }), "type", ["command", "tool_call"])
]), "type", ["command", "tool_call"]), Ve = g(), He = s([
	r("allow_once"),
	r("allow_always"),
	r("reject_once"),
	r("reject_always"),
	g()
]), Ue = _({
	optionId: Ve,
	name: g(),
	kind: He,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), We = _({
	sessionId: E,
	title: g(),
	description: y(g().nullish(), () => void 0),
	subject: Be.nullish(),
	options: n(Ue).min(1),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), N = _({
	sessionId: E,
	toolCallId: y(pe.nullish(), () => void 0)
}), Ge = _({ requestId: T }), Ke = r("object"), qe = s([
	r("email"),
	r("uri"),
	r("date"),
	r("date-time"),
	g()
]), Je = _({
	const: g(),
	title: g(),
	description: y(g().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ye = _({
	title: y(g().nullish(), () => void 0),
	description: y(g().nullish(), () => void 0),
	minLength: f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	maxLength: f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	pattern: g().nullish(),
	format: qe.nullish(),
	default: y(g().nullish(), () => void 0),
	enum: n(g()).min(1).nullish(),
	oneOf: n(Je).min(1).nullish(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Xe = _({
	title: y(g().nullish(), () => void 0),
	description: y(g().nullish(), () => void 0),
	minimum: l().nullish(),
	maximum: l().nullish(),
	default: y(l().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ze = _({
	title: y(g().nullish(), () => void 0),
	description: y(g().nullish(), () => void 0),
	minimum: l().nullish(),
	maximum: l().nullish(),
	default: y(l().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Qe = _({
	title: y(g().nullish(), () => void 0),
	description: y(g().nullish(), () => void 0),
	default: y(b().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), $e = _({
	enum: n(g()).min(1),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), et = _({
	anyOf: n(Je).min(1),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), tt = m(s([
	$e.and(_({ type: r("string") })),
	S(_({ type: g() }), "type", ["string"]),
	et
]), "type", ["string"]), nt = _({
	title: y(g().nullish(), () => void 0),
	description: y(g().nullish(), () => void 0),
	minItems: l().nullish(),
	maxItems: l().nullish(),
	items: tt,
	default: y(d(g()).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), rt = m(s([
	Ye.and(_({ type: r("string") })),
	Xe.and(_({ type: r("number") })),
	Ze.and(_({ type: r("integer") })),
	Qe.and(_({ type: r("boolean") })),
	nt.and(_({ type: r("array") })),
	S(_({ type: g() }), "type", [
		"array",
		"boolean",
		"integer",
		"number",
		"string"
	])
]), "type", [
	"array",
	"boolean",
	"integer",
	"number",
	"string"
]), it = _({
	type: y(Ke.optional().default("object"), () => "object"),
	title: y(g().nullish(), () => void 0),
	properties: e(g(), rt).optional().default({}),
	required: n(g()).nullish(),
	description: y(g().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), at = i(s([N, Ge]), _({ requestedSchema: it })), ot = g(), st = i(s([N, Ge]), _({
	elicitationId: ot,
	url: u()
})), ct = m(i(s([
	at.and(_({ mode: r("form") })),
	st.and(_({ mode: r("url") })),
	S(i(s([N, Ge]), _({ mode: g() })), "mode", ["form", "url"])
]), _({
	message: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
})), "mode", ["form", "url"]), lt = g(), ut = _({
	serverId: lt,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), dt = g(), ft = _({
	connectionId: dt,
	method: g(),
	params: e(g(), c()).nullish(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), pt = _({
	connectionId: dt,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), mt = c();
_({
	id: T,
	method: g(),
	params: s([
		We,
		ct,
		ut,
		ft,
		pt,
		mt
	]).nullish()
});
var ht = f().gte(0).lte(65535), gt = _({
	name: g(),
	title: y(g().nullish(), () => void 0),
	version: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), _t = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), vt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), yt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), bt = _({
	image: y(_t.nullish(), () => void 0),
	audio: y(vt.nullish(), () => void 0),
	embeddedContext: y(yt.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), xt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), St = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Ct = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), wt = _({
	stdio: y(xt.nullish(), () => void 0),
	http: y(St.nullish(), () => void 0),
	acp: y(Ct.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Tt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Et = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Dt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Ot = _({
	prompt: y(bt.nullish(), () => void 0),
	mcp: y(wt.nullish(), () => void 0),
	delete: y(Tt.nullish(), () => void 0),
	additionalDirectories: y(Et.nullish(), () => void 0),
	fork: y(Dt.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), kt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), At = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), jt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Mt = s([r("full"), r("incremental")]), Nt = _({
	syncKind: Mt,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Pt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Ft = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), It = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Lt = _({
	didOpen: y(jt.nullish(), () => void 0),
	didChange: y(Nt.nullish(), () => void 0),
	didClose: y(Pt.nullish(), () => void 0),
	didSave: y(Ft.nullish(), () => void 0),
	didFocus: y(It.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Rt = _({
	document: y(Lt.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), zt = _({
	maxCount: y(f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Bt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Vt = _({
	maxCount: y(f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ht = _({
	maxCount: y(f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ut = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Wt = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Gt = _({
	recentFiles: y(zt.nullish(), () => void 0),
	relatedSnippets: y(Bt.nullish(), () => void 0),
	editHistory: y(Vt.nullish(), () => void 0),
	userActions: y(Ht.nullish(), () => void 0),
	openFiles: y(Ut.nullish(), () => void 0),
	diagnostics: y(Wt.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Kt = _({
	events: y(Rt.nullish(), () => void 0),
	context: y(Gt.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), qt = s([
	r("utf-16"),
	r("utf-32"),
	r("utf-8")
]), Jt = _({
	session: y(Ot.nullish(), () => void 0),
	auth: y(kt.nullish(), () => void 0),
	providers: y(At.nullish(), () => void 0),
	nes: y(Kt.nullish(), () => void 0),
	positionEncoding: y(qt.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), P = g(), Yt = _({
	name: g(),
	value: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Xt = _({
	methodId: P,
	name: g(),
	description: y(g().nullish(), () => void 0),
	args: y(d(g()).optional(), () => []),
	env: y(d(Yt).optional(), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Zt = _({
	methodId: P,
	name: g(),
	description: y(g().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Qt = m(s([
	Xt.and(_({ type: r("terminal") })),
	Zt.and(_({ type: r("agent") })),
	S(_({
		type: g(),
		methodId: P,
		name: g(),
		description: y(g().nullish(), () => void 0),
		_meta: y(e(g(), c()).nullish(), () => void 0)
	}), "type", ["agent", "terminal"])
]), "type", ["agent", "terminal"]), $t = _({
	protocolVersion: ht,
	info: gt,
	capabilities: y(Jt.optional().default({}), () => ({})),
	authMethods: y(d(Qt).optional(), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), en = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), tn = g(), nn = s([
	r("anthropic"),
	r("openai"),
	r("azure"),
	r("vertex"),
	r("bedrock"),
	g()
]), rn = _({
	apiType: nn,
	baseUrl: u(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), an = _({
	providerId: tn,
	supported: x(d(nn), () => []),
	required: b(),
	current: rn.nullish(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), on = _({
	providers: n(an),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), sn = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), cn = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), ln = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), F = g(), un = s([
	r("mode"),
	r("model"),
	r("model_config"),
	r("thought_level"),
	g()
]), dn = g(), fn = _({
	value: dn,
	name: g(),
	description: y(g().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), pn = g(), mn = _({
	groupId: pn,
	name: g(),
	options: x(d(fn), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), hn = s([n(fn), n(mn)]), gn = _({
	currentValue: dn,
	options: hn
}), _n = _({ currentValue: b() }), I = m(i(s([
	gn.and(_({ type: r("select") })),
	_n.and(_({ type: r("boolean") })),
	S(_({ type: g() }), "type", ["boolean", "select"])
]), _({
	configId: F,
	name: g(),
	description: y(g().nullish(), () => void 0),
	category: y(un.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
})), "type", ["boolean", "select"]), vn = _({
	sessionId: E,
	configOptions: y(d(I).optional(), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), yn = _({
	sessionId: E,
	cwd: A,
	additionalDirectories: y(d(A).optional(), () => []),
	title: y(g().nullish(), () => void 0),
	updatedAt: y(a({ offset: !0 }).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), bn = g(), xn = _({
	sessions: x(d(yn), () => []),
	nextCursor: y(bn.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Sn = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Cn = _({
	sessionId: E,
	configOptions: y(d(I).optional(), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), wn = _({
	configOptions: y(d(I).optional(), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Tn = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), En = _({
	configOptions: x(d(I), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Dn = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), On = _({
	sessionId: E,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), L = g(), R = _({
	line: f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	character: f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), z = _({
	start: R,
	end: R,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), kn = _({
	range: z,
	newText: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), An = _({
	suggestionId: L,
	uri: u(),
	edits: n(kn).min(1),
	cursorPosition: y(R.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), jn = _({
	suggestionId: L,
	uri: u(),
	position: R,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Mn = _({
	suggestionId: L,
	uri: u(),
	position: R,
	newName: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Nn = _({
	suggestionId: L,
	uri: u(),
	search: g(),
	replace: g(),
	isRegex: b().nullish(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Pn = m(s([
	An.and(_({ kind: r("edit") })),
	jn.and(_({ kind: r("jump") })),
	Mn.and(_({ kind: r("rename") })),
	Nn.and(_({ kind: r("searchAndReplace") })),
	S(_({
		kind: g(),
		suggestionId: L
	}), "kind", [
		"edit",
		"jump",
		"rename",
		"searchAndReplace"
	])
]), "kind", [
	"edit",
	"jump",
	"rename",
	"searchAndReplace"
]), Fn = _({
	suggestions: n(Pn),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), In = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Ln = c(), B = c(), Rn = s([
	r(-32700),
	r(-32600),
	r(-32601),
	r(-32602),
	r(-32603),
	r(-32800),
	r(-32e3),
	r(-32002),
	f().min(-2147483648, { error: "Invalid value: Expected int32 to be >= -2147483648" }).max(2147483647, { error: "Invalid value: Expected int32 to be <= 2147483647" })
]), zn = _({
	code: Rn,
	message: g(),
	data: y(c().optional(), () => void 0)
});
s([_({
	id: T,
	result: s([
		$t,
		en,
		on,
		sn,
		cn,
		ln,
		vn,
		xn,
		Sn,
		Cn,
		wn,
		Tn,
		En,
		Dn,
		On,
		Fn,
		In,
		Ln,
		B
	])
}), _({
	id: T,
	error: zn
})]);
var V = g(), H = _({
	messageId: V,
	content: k,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Bn = _({
	messageId: V,
	content: y(d(k).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Vn = _({
	messageId: V,
	content: y(d(k).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Hn = _({
	messageId: V,
	content: y(d(k).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Un = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Wn = s([
	r("end_turn"),
	r("max_tokens"),
	r("max_turn_requests"),
	r("refusal"),
	r("cancelled"),
	g()
]), Gn = _({
	totalTokens: l(),
	inputTokens: l(),
	outputTokens: l(),
	thoughtTokens: y(l().nullish(), () => void 0),
	cachedReadTokens: y(l().nullish(), () => void 0),
	cachedWriteTokens: y(l().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Kn = _({
	stopReason: y(Wn.nullish(), () => void 0),
	usage: y(Gn.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), qn = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Jn = m(s([
	Un.and(_({ state: r("running") })),
	Kn.and(_({ state: r("idle") })),
	qn.and(_({ state: r("requires_action") })),
	S(_({ state: g() }), "state", [
		"idle",
		"requires_action",
		"running"
	])
]), "state", [
	"idle",
	"requires_action",
	"running"
]), Yn = _({
	toolCallId: pe,
	content: Fe,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Xn = _({
	data: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Zn = _({
	exitCode: y(f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: y(g().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Qn = _({
	terminalId: M,
	command: y(g().nullish(), () => void 0),
	cwd: y(A.nullish(), () => void 0),
	output: y(Xn.nullish(), () => void 0),
	exitStatus: y(Zn.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), $n = _({
	terminalId: M,
	data: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), U = g(), er = s([
	r("high"),
	r("medium"),
	r("low"),
	g()
]), tr = s([
	r("pending"),
	r("in_progress"),
	r("completed"),
	r("cancelled"),
	g()
]), nr = _({
	content: g(),
	priority: er,
	status: tr,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), rr = _({
	planId: U,
	entries: x(d(nr), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ir = _({
	planId: U,
	uri: u(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ar = _({
	planId: U,
	content: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), or = m(s([
	rr.and(_({ type: r("items") })),
	ir.and(_({ type: r("file") })),
	ar.and(_({ type: r("markdown") })),
	S(_({
		type: g(),
		planId: U
	}), "type", [
		"file",
		"items",
		"markdown"
	])
]), "type", [
	"file",
	"items",
	"markdown"
]), sr = _({
	plan: or,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), cr = _({
	planId: U,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), lr = _({
	hint: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ur = m(s([lr.and(_({ type: r("text") })), S(_({ type: g() }), "type", ["text"])]), "type", ["text"]), dr = _({
	name: g(),
	description: g(),
	input: y(ur.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), fr = _({
	availableCommands: x(d(dr), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), pr = _({
	configOptions: x(d(I), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), mr = _({
	title: y(g().nullish(), () => void 0),
	updatedAt: y(a({ offset: !0 }).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), hr = _({
	amount: l(),
	currency: g().regex(/^[A-Z]{3}$/),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), gr = _({
	used: l(),
	size: l(),
	cost: y(hr.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), _r = g(), vr = s([
	r("in_progress"),
	r("completed"),
	r("failed"),
	r("cancelled"),
	g()
]), yr = _({
	compactionId: _r,
	status: vr,
	summary: y(d(k).nullish(), () => void 0),
	error: y(g().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), br = _({
	compactionId: _r,
	content: k,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), xr = m(s([
	H.and(_({ sessionUpdate: r("user_message_chunk") })),
	Bn.and(_({ sessionUpdate: r("user_message") })),
	H.and(_({ sessionUpdate: r("agent_message_chunk") })),
	Vn.and(_({ sessionUpdate: r("agent_message") })),
	H.and(_({ sessionUpdate: r("agent_thought_chunk") })),
	Hn.and(_({ sessionUpdate: r("agent_thought") })),
	Jn.and(_({ sessionUpdate: r("state_update") })),
	Yn.and(_({ sessionUpdate: r("tool_call_content_chunk") })),
	Le.and(_({ sessionUpdate: r("tool_call_update") })),
	Qn.and(_({ sessionUpdate: r("terminal_update") })),
	$n.and(_({ sessionUpdate: r("terminal_output_chunk") })),
	sr.and(_({ sessionUpdate: r("plan_update") })),
	cr.and(_({ sessionUpdate: r("plan_removed") })),
	fr.and(_({ sessionUpdate: r("available_commands_update") })),
	pr.and(_({ sessionUpdate: r("config_option_update") })),
	mr.and(_({ sessionUpdate: r("session_info_update") })),
	gr.and(_({ sessionUpdate: r("usage_update") })),
	yr.and(_({ sessionUpdate: r("compaction_update") })),
	br.and(_({ sessionUpdate: r("compaction_summary_chunk") })),
	S(_({ sessionUpdate: g() }), "sessionUpdate", [
		"agent_message",
		"agent_message_chunk",
		"agent_thought",
		"agent_thought_chunk",
		"available_commands_update",
		"compaction_summary_chunk",
		"compaction_update",
		"config_option_update",
		"plan_removed",
		"plan_update",
		"session_info_update",
		"state_update",
		"terminal_output_chunk",
		"terminal_update",
		"tool_call_content_chunk",
		"tool_call_update",
		"usage_update",
		"user_message",
		"user_message_chunk"
	])
]), "sessionUpdate", [
	"agent_message",
	"agent_message_chunk",
	"agent_thought",
	"agent_thought_chunk",
	"available_commands_update",
	"compaction_summary_chunk",
	"compaction_update",
	"config_option_update",
	"plan_removed",
	"plan_update",
	"session_info_update",
	"state_update",
	"terminal_output_chunk",
	"terminal_update",
	"tool_call_content_chunk",
	"tool_call_update",
	"usage_update",
	"user_message",
	"user_message_chunk"
]), Sr = _({
	sessionId: E,
	update: xr,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Cr = _({
	elicitationId: ot,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), wr = _({
	connectionId: dt,
	method: g(),
	params: y(e(g(), c()).nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Tr = c();
_({
	method: g(),
	params: s([
		Sr,
		Cr,
		wr,
		Tr
	]).nullish()
});
var Er = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Dr = _({
	terminal: y(Er.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Or = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), kr = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Ar = _({
	form: y(Or.nullish(), () => void 0),
	url: y(kr.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), jr = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Mr = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Nr = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Pr = _({
	jump: y(jr.nullish(), () => void 0),
	rename: y(Mr.nullish(), () => void 0),
	searchAndReplace: y(Nr.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Fr = _({
	auth: y(Dr.nullish(), () => void 0),
	elicitation: y(Ar.nullish(), () => void 0),
	nes: y(Pr.nullish(), () => void 0),
	positionEncodings: y(d(qt).optional(), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ir = _({
	protocolVersion: ht,
	info: gt,
	capabilities: y(Fr.optional().default({}), () => ({})),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Lr = _({
	methodId: P,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Rr = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), zr = _({
	providerId: tn,
	apiType: nn,
	baseUrl: u(),
	headers: e(g(), g()).optional(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Br = _({
	providerId: tn,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Vr = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Hr = _({
	name: g(),
	value: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ur = _({
	name: g(),
	url: u(),
	headers: n(Hr).optional(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Wr = _({
	name: g(),
	serverId: lt,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Gr = _({
	name: g(),
	command: A,
	args: n(g()).optional(),
	env: n(Yt).optional(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Kr = m(s([
	Ur.and(_({ type: r("http") })),
	Wr.and(_({ type: r("acp") })),
	Gr.and(_({ type: r("stdio") })),
	S(_({ type: g() }), "type", [
		"acp",
		"http",
		"stdio"
	])
]), "type", [
	"acp",
	"http",
	"stdio"
]), qr = _({
	cwd: A,
	additionalDirectories: y(d(A).optional(), () => []),
	mcpServers: y(d(Kr).optional(), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Jr = _({
	cwd: A.nullish(),
	cursor: bn.nullish(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Yr = _({
	sessionId: E,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Xr = _({
	sessionId: E,
	cwd: A,
	additionalDirectories: y(d(A).optional(), () => []),
	mcpServers: y(d(Kr).optional(), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Zr = _({ _meta: y(e(g(), c()).nullish(), () => void 0) }), Qr = m(s([Zr.and(_({ type: r("start") })), S(_({
	type: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), "type", ["start"])]), "type", ["start"]), $r = _({
	sessionId: E,
	cwd: A,
	additionalDirectories: y(d(A).optional(), () => []),
	mcpServers: y(d(Kr).optional(), () => []),
	replayFrom: y(Qr.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ei = _({
	sessionId: E,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ti = m(i(s([
	_({
		value: dn,
		type: r("id")
	}),
	_({
		value: b(),
		type: r("boolean")
	}),
	S(_({
		type: g(),
		value: c()
	}), "type", ["boolean", "id"])
]), _({
	sessionId: E,
	configId: F,
	_meta: y(e(g(), c()).nullish(), () => void 0)
})), "type", ["boolean", "id"]), ni = _({
	sessionId: E,
	prompt: n(k),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ri = _({
	uri: u(),
	name: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ii = _({
	name: g(),
	owner: g(),
	remoteUrl: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ai = _({
	workspaceUri: y(u().nullish(), () => void 0),
	workspaceFolders: n(ri).nullish(),
	repository: y(ii.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), oi = s([
	r("automatic"),
	r("diagnostic"),
	r("manual"),
	g()
]), si = _({
	uri: u(),
	languageId: g(),
	text: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ci = _({
	startLine: f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	endLine: f().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	text: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), li = _({
	uri: u(),
	excerpts: n(ci),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ui = _({
	uri: u(),
	diff: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), di = _({
	action: g(),
	uri: u(),
	position: R,
	timestampMs: l(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), fi = _({
	uri: u(),
	languageId: g(),
	visibleRange: y(z.nullish(), () => void 0),
	lastFocusedMs: y(l().nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), pi = s([
	r("error"),
	r("warning"),
	r("information"),
	r("hint"),
	g()
]), mi = _({
	uri: u(),
	range: z,
	severity: pi,
	message: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), hi = _({
	recentFiles: n(si).nullish(),
	relatedSnippets: n(li).nullish(),
	editHistory: n(ui).nullish(),
	userActions: n(di).nullish(),
	openFiles: n(fi).nullish(),
	diagnostics: n(mi).nullish(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), gi = _({
	sessionId: E,
	uri: u(),
	version: l(),
	position: R,
	selection: z.nullish(),
	triggerKind: oi,
	context: hi.nullish(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), _i = _({
	sessionId: E,
	_meta: y(e(g(), c()).nullish(), () => void 0)
});
_({
	id: T,
	method: g(),
	params: s([
		Ir,
		Lr,
		Rr,
		zr,
		Br,
		Vr,
		qr,
		Jr,
		Yr,
		Xr,
		$r,
		ei,
		ti,
		ni,
		ai,
		gi,
		_i,
		ft,
		mt
	]).nullish()
});
var vi = _({
	optionId: Ve,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), yi = m(s([
	_({ outcome: r("cancelled") }),
	vi.and(_({ outcome: r("selected") })),
	S(_({ outcome: g() }), "outcome", ["cancelled", "selected"])
]), "outcome", ["cancelled", "selected"]), bi = _({
	outcome: yi,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), xi = s([
	g(),
	l(),
	l(),
	b(),
	n(g())
]), Si = _({ content: e(g(), xi).nullish() }), Ci = m(i(s([
	Si.and(_({ action: r("accept") })),
	_({ action: r("decline") }),
	_({ action: r("cancel") }),
	S(_({ action: g() }), "action", [
		"accept",
		"cancel",
		"decline"
	])
]), _({ _meta: y(e(g(), c()).nullish(), () => void 0) })), "action", [
	"accept",
	"cancel",
	"decline"
]), wi = _({
	connectionId: dt,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ti = _({ _meta: y(e(g(), c()).nullish(), () => void 0) });
s([_({
	id: T,
	result: s([
		bi,
		Ci,
		wi,
		Ti,
		B,
		Ln
	])
}), _({
	id: T,
	error: zn
})]);
var Ei = _({
	sessionId: E,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Di = _({
	sessionId: E,
	uri: u(),
	languageId: g(),
	version: l(),
	text: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Oi = _({
	range: z.nullish(),
	text: g(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ki = _({
	sessionId: E,
	uri: u(),
	version: l(),
	contentChanges: x(d(Oi), () => []),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ai = _({
	sessionId: E,
	uri: u(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), ji = _({
	sessionId: E,
	uri: u(),
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Mi = _({
	sessionId: E,
	uri: u(),
	version: l(),
	position: R,
	visibleRange: z,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Ni = _({
	sessionId: E,
	suggestionId: L,
	_meta: y(e(g(), c()).nullish(), () => void 0)
}), Pi = s([
	r("rejected"),
	r("ignored"),
	r("replaced"),
	r("cancelled"),
	g()
]), Fi = _({
	sessionId: E,
	suggestionId: L,
	reason: y(Pi.nullish(), () => void 0),
	_meta: y(e(g(), c()).nullish(), () => void 0)
});
_({
	method: g(),
	params: s([
		Ei,
		Di,
		ki,
		Ai,
		ji,
		Mi,
		Ni,
		Fi,
		wr,
		Tr
	]).nullish()
});
var Ii = _({
	requestId: T,
	_meta: y(e(g(), c()).nullish(), () => void 0)
});
_({
	method: g(),
	params: Ii.nullish()
});
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/v2/schema/guards.gen.js
function W(e, t) {
	return typeof e == "object" && e ? e[t] : void 0;
}
Re.and(_({ type: r("tool_call") })), ze.and(_({ type: r("command") })), De.and(_({ type: r("content") })), Ne.and(_({ type: r("diff") })), Pe.and(_({ type: r("terminal") }));
var Li = _e.and(_({ type: r("text") })), Ri = ve.and(_({ type: r("image") })), zi = ye.and(_({ type: r("audio") })), Bi = Se.and(_({ type: r("resource_link") })), Vi = Ee.and(_({ type: r("resource") }));
j.and(_({ operation: r("add") })), j.and(_({ operation: r("delete") })), j.and(_({ operation: r("modify") })), ke.and(_({ operation: r("move") })), ke.and(_({ operation: r("copy") })), at.and(_({ mode: r("form") })).and(_({ message: g() })), st.and(_({ mode: r("url") })).and(_({ message: g() })), s([N, Ge]).and(_({ message: g() })), Ye.and(_({ type: r("string") })), Xe.and(_({ type: r("number") })), Ze.and(_({ type: r("integer") })), Qe.and(_({ type: r("boolean") })), nt.and(_({ type: r("array") })), $e.and(_({ type: r("string") })), Xt.and(_({ type: r("terminal") })), Zt.and(_({ type: r("agent") })), _({
	methodId: P,
	name: g()
}), gn.and(_({ type: r("select") })).and(_({
	configId: F,
	name: g()
})), _n.and(_({ type: r("boolean") })).and(_({
	configId: F,
	name: g()
})), _({
	configId: F,
	name: g()
}), An.and(_({ kind: r("edit") })), jn.and(_({ kind: r("jump") })), Mn.and(_({ kind: r("rename") })), Nn.and(_({ kind: r("searchAndReplace") })), _({ suggestionId: L });
var Hi = H.and(_({ sessionUpdate: r("user_message_chunk") })), Ui = Bn.and(_({ sessionUpdate: r("user_message") })), Wi = H.and(_({ sessionUpdate: r("agent_message_chunk") })), Gi = Vn.and(_({ sessionUpdate: r("agent_message") })), Ki = H.and(_({ sessionUpdate: r("agent_thought_chunk") })), qi = Hn.and(_({ sessionUpdate: r("agent_thought") })), Ji = Jn.and(_({ sessionUpdate: r("state_update") })), Yi = Yn.and(_({ sessionUpdate: r("tool_call_content_chunk") })), Xi = Le.and(_({ sessionUpdate: r("tool_call_update") })), Zi = Qn.and(_({ sessionUpdate: r("terminal_update") })), Qi = $n.and(_({ sessionUpdate: r("terminal_output_chunk") })), $i = sr.and(_({ sessionUpdate: r("plan_update") })), ea = cr.and(_({ sessionUpdate: r("plan_removed") })), ta = fr.and(_({ sessionUpdate: r("available_commands_update") })), na = pr.and(_({ sessionUpdate: r("config_option_update") })), ra = mr.and(_({ sessionUpdate: r("session_info_update") })), ia = gr.and(_({ sessionUpdate: r("usage_update") })), aa = yr.and(_({ sessionUpdate: r("compaction_update") })), oa = br.and(_({ sessionUpdate: r("compaction_summary_chunk") })), sa = Un.and(_({ state: r("running") })), ca = Kn.and(_({ state: r("idle") })), la = qn.and(_({ state: r("requires_action") }));
rr.and(_({ type: r("items") })), ir.and(_({ type: r("file") })), ar.and(_({ type: r("markdown") })), _({ planId: U }), lr.and(_({ type: r("text") })), Ur.and(_({ type: r("http") })), Wr.and(_({ type: r("acp") })), Gr.and(_({ type: r("stdio") })), Zr.and(_({ type: r("start") })), _({ type: r("id") }).and(_({ value: dn })).and(_({
	sessionId: E,
	configId: F
})), _({ type: r("boolean") }).and(_({ value: b() })).and(_({
	sessionId: E,
	configId: F
})), _({ value: c() }).and(_({
	sessionId: E,
	configId: F
})), _({ outcome: r("cancelled") }), vi.and(_({ outcome: r("selected") })), Si.and(_({ action: r("accept") })), _({ action: r("decline") }), _({ action: r("cancel") });
var ua = {
	isText(e) {
		return W(e, "type") === "text" && Li.safeParse(e).success;
	},
	isImage(e) {
		return W(e, "type") === "image" && Ri.safeParse(e).success;
	},
	isAudio(e) {
		return W(e, "type") === "audio" && zi.safeParse(e).success;
	},
	isResourceLink(e) {
		return W(e, "type") === "resource_link" && Bi.safeParse(e).success;
	},
	isResource(e) {
		return W(e, "type") === "resource" && Vi.safeParse(e).success;
	},
	isCustom(e) {
		let t = W(e, "type");
		return typeof t == "string" && ![
			"audio",
			"image",
			"resource",
			"resource_link",
			"text"
		].includes(t);
	}
}, da = {
	isUserMessageChunk(e) {
		return W(e, "sessionUpdate") === "user_message_chunk" && Hi.safeParse(e).success;
	},
	isUserMessage(e) {
		return W(e, "sessionUpdate") === "user_message" && Ui.safeParse(e).success;
	},
	isAgentMessageChunk(e) {
		return W(e, "sessionUpdate") === "agent_message_chunk" && Wi.safeParse(e).success;
	},
	isAgentMessage(e) {
		return W(e, "sessionUpdate") === "agent_message" && Gi.safeParse(e).success;
	},
	isAgentThoughtChunk(e) {
		return W(e, "sessionUpdate") === "agent_thought_chunk" && Ki.safeParse(e).success;
	},
	isAgentThought(e) {
		return W(e, "sessionUpdate") === "agent_thought" && qi.safeParse(e).success;
	},
	isStateUpdate(e) {
		return W(e, "sessionUpdate") === "state_update" && Ji.safeParse(e).success;
	},
	isToolCallContentChunk(e) {
		return W(e, "sessionUpdate") === "tool_call_content_chunk" && Yi.safeParse(e).success;
	},
	isToolCallUpdate(e) {
		return W(e, "sessionUpdate") === "tool_call_update" && Xi.safeParse(e).success;
	},
	isTerminalUpdate(e) {
		return W(e, "sessionUpdate") === "terminal_update" && Zi.safeParse(e).success;
	},
	isTerminalOutputChunk(e) {
		return W(e, "sessionUpdate") === "terminal_output_chunk" && Qi.safeParse(e).success;
	},
	isPlanUpdate(e) {
		return W(e, "sessionUpdate") === "plan_update" && $i.safeParse(e).success;
	},
	isPlanRemoved(e) {
		return W(e, "sessionUpdate") === "plan_removed" && ea.safeParse(e).success;
	},
	isAvailableCommandsUpdate(e) {
		return W(e, "sessionUpdate") === "available_commands_update" && ta.safeParse(e).success;
	},
	isConfigOptionUpdate(e) {
		return W(e, "sessionUpdate") === "config_option_update" && na.safeParse(e).success;
	},
	isSessionInfoUpdate(e) {
		return W(e, "sessionUpdate") === "session_info_update" && ra.safeParse(e).success;
	},
	isUsageUpdate(e) {
		return W(e, "sessionUpdate") === "usage_update" && ia.safeParse(e).success;
	},
	isCompactionUpdate(e) {
		return W(e, "sessionUpdate") === "compaction_update" && aa.safeParse(e).success;
	},
	isCompactionSummaryChunk(e) {
		return W(e, "sessionUpdate") === "compaction_summary_chunk" && oa.safeParse(e).success;
	},
	isCustom(e) {
		let t = W(e, "sessionUpdate");
		return typeof t == "string" && ![
			"agent_message",
			"agent_message_chunk",
			"agent_thought",
			"agent_thought_chunk",
			"available_commands_update",
			"compaction_summary_chunk",
			"compaction_update",
			"config_option_update",
			"plan_removed",
			"plan_update",
			"session_info_update",
			"state_update",
			"terminal_output_chunk",
			"terminal_update",
			"tool_call_content_chunk",
			"tool_call_update",
			"usage_update",
			"user_message",
			"user_message_chunk"
		].includes(t);
	}
}, fa = {
	isRunning(e) {
		return W(e, "state") === "running" && sa.safeParse(e).success;
	},
	isIdle(e) {
		return W(e, "state") === "idle" && ca.safeParse(e).success;
	},
	isRequiresAction(e) {
		return W(e, "state") === "requires_action" && la.safeParse(e).success;
	},
	isCustom(e) {
		let t = W(e, "state");
		return typeof t == "string" && ![
			"idle",
			"requires_action",
			"running"
		].includes(t);
	}
};
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/v2/acp.js
function G(e) {
	return e ?? {};
}
var pa = /* @__PURE__ */ new Set([
	...Object.values(C),
	...Object.values(w),
	...Object.values(fe)
]);
function K(e, t, n, r = !1) {
	if (!(Object.hasOwn(t, e) || r && e === fe.cancel_request) && pa.has(e)) throw TypeError(`ACP v2 ${n} method '${e}' is not valid in this direction`);
}
function ma(e, t) {
	if (pa.has(e)) throw TypeError(`Cannot replace the built-in ACP v2 ${t} parser for '${e}'`);
}
function ha(e, t, n) {
	for (let r of e) K(r.method, r.kind === "request" ? t : n, r.kind, r.kind === "notification");
}
function ga(e) {
	let t = Ir.parse(e);
	if (t.protocolVersion !== 2) throw v.invalidParams({
		expectedProtocolVersion: 2,
		receivedProtocolVersion: t.protocolVersion
	}, "The v2 API only supports protocol version 2");
	return structuredClone(t);
}
function _a(e) {
	return ga({
		...typeof e == "object" && e && !Array.isArray(e) ? e : {},
		protocolVersion: 2
	});
}
function va(e) {
	let t = $t.parse(e);
	if (t.protocolVersion !== 2) throw v.invalidRequest({
		expectedProtocolVersion: 2,
		receivedProtocolVersion: t.protocolVersion
	}, "The v2 API only supports protocol version 2");
	return structuredClone(t);
}
function ya(e) {
	return structuredClone(e);
}
function ba() {
	let e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var xa = class {
	phase = "uninitialized";
	request;
	barrier = ba();
	constructor() {
		this.barrier.promise.catch(() => {});
	}
	get status() {
		return this.phase;
	}
	get initialized() {
		return this.barrier.promise.then(ya);
	}
	begin(e) {
		if (this.phase !== "uninitialized") throw v.invalidRequest("ACP v2 initialize may only be requested once per connection");
		let t = structuredClone(e);
		this.request = t, this.phase = "initializing";
	}
	complete(e) {
		if (this.phase !== "initializing" || !this.request) throw v.invalidRequest("ACP v2 initialization is not in progress");
		let t = {
			request: structuredClone(this.request),
			response: structuredClone(e)
		};
		this.phase = "initialized", this.barrier.resolve(t);
	}
	fail(e) {
		(this.phase === "uninitialized" || this.phase === "initializing") && (this.phase = "failed", this.request = void 0, this.barrier.reject(e ?? v.invalidRequest("ACP v2 connection initialization failed")));
	}
	waitUntilInitialized(e) {
		return this.phase === "initialized" ? Promise.resolve() : this.phase === "initializing" ? this.barrier.promise.then(() => {}) : Promise.reject(Ca(e));
	}
}, Sa = /* @__PURE__ */ new WeakMap();
function q(e) {
	let t = Sa.get(e);
	return t || (t = new xa(), Sa.set(e, t), e.signal.aborted ? t.fail(e.signal.reason) : e.signal.addEventListener("abort", () => t?.fail(e.signal.reason), { once: !0 })), t;
}
function Ca(e) {
	return v.invalidRequest(`ACP v2 connection must be initialized before '${e}'`);
}
async function wa(e, t) {
	let n = Ca(e.method);
	return t.fail(n), Ta(e, n);
}
async function Ta(e, t) {
	return e.kind === "request" && await e.responder.respondWithError(t), h.yes();
}
function Ea() {
	return {
		async handleMessage(e, t) {
			let n = q(t);
			return e.kind === "notification" && e.method === fe.cancel_request ? n.status === "initializing" || n.status === "initialized" ? h.yes() : wa(e, n) : n.status === "initialized" ? h.no(e) : n.status === "initializing" ? (await n.waitUntilInitialized(e.method), h.no(e)) : wa(e, n);
		},
		describe: () => "client-initialization"
	};
}
function J(e, t) {
	return Ua(e.response, t);
}
function Da(e, t, n) {
	return e.map((e) => {
		if (e.kind !== "request") return e;
		let r = t[e.method], i = e.mapResponse;
		return {
			...e,
			mapResponse: r ? (t) => {
				let a = J(r, t);
				return n && e.method === C.initialize && n(a), i ? i(a) : a;
			} : i
		};
	});
}
function Oa(e) {
	return typeof e == "object" && !!e && "readable" in e && "writable" in e;
}
function ka() {
	let e = new TransformStream(), t = new TransformStream();
	return [{
		readable: t.readable,
		writable: e.writable
	}, {
		readable: e.readable,
		writable: t.writable
	}];
}
var Y = {
	agent: {
		initialize: C.initialize,
		auth: {
			login: C.auth_login,
			logout: C.auth_logout
		},
		providers: {
			list: C.providers_list,
			set: C.providers_set,
			disable: C.providers_disable
		},
		session: {
			new: C.session_new,
			list: C.session_list,
			delete: C.session_delete,
			fork: C.session_fork,
			resume: C.session_resume,
			close: C.session_close,
			setConfigOption: C.session_set_config_option,
			prompt: C.session_prompt,
			cancel: C.session_cancel
		},
		mcp: { message: C.mcp_message },
		nes: {
			start: C.nes_start,
			suggest: C.nes_suggest,
			accept: C.nes_accept,
			reject: C.nes_reject,
			close: C.nes_close
		},
		document: {
			didOpen: C.document_did_open,
			didChange: C.document_did_change,
			didClose: C.document_did_close,
			didSave: C.document_did_save,
			didFocus: C.document_did_focus
		}
	},
	client: {
		session: {
			requestPermission: w.session_request_permission,
			update: w.session_update
		},
		mcp: {
			connect: w.mcp_connect,
			message: w.mcp_message,
			disconnect: w.mcp_disconnect
		},
		elicitation: {
			create: w.elicitation_create,
			complete: w.elicitation_complete
		}
	},
	protocol: { cancelRequest: fe.cancel_request }
}, Aa = Symbol("startActiveSession"), ja = class {
	cx;
	currentRequestId;
	constructor(e, t) {
		this.cx = e, this.currentRequestId = t;
	}
	get initialized() {
		return q(this.cx).initialized;
	}
	get initializationLifecycle() {
		return q(this.cx);
	}
	get requestId() {
		return this.currentRequestId;
	}
	get connectionContext() {
		return this.cx;
	}
	sendRequest(e, t, n, r) {
		return this.cx.sendRequest(e, t, n, r);
	}
	sendNotification(e, t) {
		return this.cx.sendNotification(e, t);
	}
	sendBatch(e) {
		return this.cx.sendBatch(e);
	}
	addDynamicHandler(e) {
		return this.cx.addDynamicHandler(e);
	}
}, Ma = class e extends ja {
	constructor(e, t) {
		super(e, t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	request(e, t, n) {
		K(e, $, "request");
		let r = $[e];
		return this.initializationLifecycle.waitUntilInitialized(e).then(() => this.sendRequest(e, t, r ? (e) => J(r, e) : void 0, n));
	}
	notify(e, t) {
		return K(e, Qa, "notification", !0), this.initializationLifecycle.waitUntilInitialized(e).then(() => this.sendNotification(e, t));
	}
	batch(e) {
		return ha(e, $, Qa), this.initializationLifecycle.waitUntilInitialized("batch").then(() => this.sendBatch(Da(e, $)));
	}
}, Na = class e extends ja {
	closeOnInitializationFailure;
	constructor(e, t, n) {
		super(e, t), this.closeOnInitializationFailure = n;
	}
	static create(t, n, r) {
		return new e(t, n, r);
	}
	[Aa](e, t) {
		return this.request(C.session_new, e, t).then((e) => this.attachSession(e));
	}
	buildSession(e) {
		return typeof e == "string" ? Va.create(this, {
			cwd: e,
			mcpServers: []
		}) : Va.create(this, e);
	}
	attachSession(e) {
		let t = new za(), n = /* @__PURE__ */ new Set(), r = {
			enqueue: (e) => t.enqueue(e),
			reject: (e) => t.reject(e),
			clearErrors: () => t.clearErrors(),
			fail: (e) => t.fail(e),
			next: () => t.next(),
			nextAfter: (e, n) => t.nextAfter(e, n),
			beginPrompt: () => {
				let e = {
					updateCursor: t.cursor(),
					overlapController: new AbortController()
				};
				if (n.size > 0) {
					let t = /* @__PURE__ */ Error("readText() cannot attribute updates across overlapping prompts; use nextUpdate() instead");
					for (let e of n) e.overlapController.abort(t);
					e.overlapController.abort(t);
				}
				return n.add(e), e;
			},
			cancelPrompt: (e) => n.delete(e),
			isAwaitingPromptCompletion: () => n.size > 0,
			completePrompt: () => {
				n.clear();
			}
		}, i = this.connectionContext.signal, a = () => {
			t.fail(i.reason ?? /* @__PURE__ */ Error("ACP connection closed"));
		};
		i.aborted ? a() : i.addEventListener("abort", a);
		let o = ro(this.connectionContext).attach(e, r), ee = new le(() => {
			i.removeEventListener("abort", a);
		});
		return Ha.create(this, e, r, [o, ee]);
	}
	request(e, t, n) {
		K(e, Q, "request");
		let r = Q[e], i = this.initializationLifecycle;
		if (e === C.initialize) {
			let a = _a(t);
			i.begin(a);
			let o;
			try {
				o = this.sendRequest(e, a, (e) => {
					let t = J(r, e);
					return i.complete(t), t;
				}, n);
			} catch (e) {
				throw i.fail(e), this.closeOnInitializationFailure?.(e), e;
			}
			return o.catch((e) => {
				i.status !== "initialized" && (i.fail(e), this.closeOnInitializationFailure?.(e));
			}), o;
		}
		return i.waitUntilInitialized(e).then(() => this.sendRequest(e, t, r ? (e) => J(r, e) : void 0, n));
	}
	notify(e, t) {
		return K(e, Za, "notification", !0), this.initializationLifecycle.waitUntilInitialized(e).then(() => this.sendNotification(e, t));
	}
	batch(e) {
		ha(e, Q, Za);
		let t = e.filter((e) => e.kind === "request" && e.method === C.initialize);
		if (t.length > 0) {
			if (e.length !== 1 || t.length !== 1) return Promise.reject(v.invalidRequest("ACP v2 initialize must be the only entry in its batch"));
			let n = this.initializationLifecycle, r = _a(t[0].params);
			n.begin(r);
			let i = [{
				...t[0],
				params: r
			}], a;
			try {
				a = this.sendBatch(Da(i, Q, (e) => n.complete(e)));
			} catch (e) {
				throw n.fail(e), this.closeOnInitializationFailure?.(e), e;
			}
			return a.catch((e) => {
				n.status !== "initialized" && (n.fail(e), this.closeOnInitializationFailure?.(e));
			}), a;
		}
		return this.initializationLifecycle.waitUntilInitialized("batch").then(() => this.sendBatch(Da(e, Q)));
	}
}, Pa = class {
	connection;
	constructor(e) {
		this.connection = e;
	}
	get initialized() {
		return q(this.connection.getContext()).initialized;
	}
	get signal() {
		return this.connection.signal;
	}
	get closed() {
		return this.connection.closed;
	}
	close(e) {
		this.connection.close(e);
	}
}, Fa = class extends Pa {
	connectHandlers;
	client;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.client = Ma.create(e.getContext());
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, io(this, this.connectHandlers));
	}
}, Ia = class extends Pa {
	connectHandlers;
	agent;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.agent = Na.create(e.getContext(), void 0, (t) => e.close(t));
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, io(this, this.connectHandlers));
	}
};
function La(e, t = []) {
	return new Fa(e, t);
}
function Ra(e, t = []) {
	return new Ia(e, t);
}
var za = class {
	values = [];
	waiters = [];
	failed = !1;
	failure;
	nextSequence = 0;
	enqueue(e) {
		if (this.failed) return;
		let t = this.nextSequence++, n = this.waiters.shift();
		n ? n.resolve(e) : this.values.push({
			kind: "value",
			value: e,
			sequence: t
		});
	}
	reject(e) {
		if (this.failed) return;
		let t = this.nextSequence++;
		if (this.waiters.length > 0) {
			for (let t of this.waiters.splice(0)) t.reject(e);
			return;
		}
		this.values.push({
			kind: "error",
			error: e,
			sequence: t
		});
	}
	clearErrors() {
		this.values = this.values.filter((e) => e.kind === "value");
	}
	cursor() {
		return this.nextSequence;
	}
	nextAfter(e, t) {
		if (t?.aborted) return Promise.reject(t.reason);
		for (; this.values[0] && this.values[0].sequence < e;) this.values.shift();
		return this.next(t);
	}
	fail(e) {
		if (!this.failed) {
			this.failed = !0, this.failure = e;
			for (let t of this.waiters.splice(0)) t.reject(e);
		}
	}
	next(e) {
		if (e?.aborted) return Promise.reject(e.reason);
		if (this.values.length > 0) {
			let e = this.values.shift();
			return e.kind === "error" ? Promise.reject(e.error) : Promise.resolve(e.value);
		}
		return this.failed ? Promise.reject(this.failure) : new Promise((t, n) => {
			let r = () => {
				e?.removeEventListener("abort", a);
			}, i = {
				resolve: (e) => {
					r(), t(e);
				},
				reject: (e) => {
					r(), n(e);
				}
			}, a = () => {
				let t = this.waiters.indexOf(i);
				t >= 0 && this.waiters.splice(t, 1), i.reject(e?.reason);
			};
			this.waiters.push(i), e?.addEventListener("abort", a, { once: !0 }), e?.aborted && a();
		});
	}
};
function Ba(e) {
	return structuredClone(e);
}
var Va = class e {
	cx;
	request;
	constructor(e, t) {
		this.cx = e, this.request = Ba(t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	toRequest() {
		return Ba(this.request);
	}
	withAdditionalDirectories(e) {
		return this.request = {
			...this.request,
			additionalDirectories: [...e]
		}, this;
	}
	withMcpServer(e) {
		return this.request = {
			...this.request,
			mcpServers: [...this.request.mcpServers ?? [], structuredClone(e)]
		}, this;
	}
	async start(e) {
		return this.cx[Aa](this.toRequest(), e);
	}
	async withSession(e) {
		let t = await this.start();
		try {
			return await e(t);
		} finally {
			t.dispose();
		}
	}
}, Ha = class e {
	cx;
	sessionResponse;
	updates;
	registrations;
	latestPrompt;
	constructor(e, t, n, r) {
		this.cx = e, this.sessionResponse = t, this.updates = n, this.registrations = r;
	}
	static create(t, n, r, i) {
		return new e(t, n, r, i);
	}
	get sessionId() {
		return this.sessionResponse.sessionId;
	}
	get configOptions() {
		return this.sessionResponse.configOptions;
	}
	get meta() {
		return this.sessionResponse._meta;
	}
	get newSessionResponse() {
		return this.sessionResponse;
	}
	prompt(e, t) {
		this.updates.clearErrors();
		let n = this.updates.beginPrompt();
		this.latestPrompt = n;
		let r = this.cx.request(C.session_prompt, {
			sessionId: this.sessionId,
			prompt: this.promptBlocks(e)
		}, t);
		return r.catch((e) => {
			this.updates.cancelPrompt(n) && this.updates.reject(e);
		}), r;
	}
	nextUpdate() {
		return this.updates.next();
	}
	async readText() {
		let e = this.latestPrompt, t = e?.updateCursor, n = [], r = /* @__PURE__ */ new Map(), i = (e) => {
			let t = r.get(e);
			return t || (t = [], n.push(e), r.set(e, t)), t;
		};
		for (;;) {
			let a = t === void 0 ? await this.nextUpdate() : await this.updates.nextAfter(t, e?.overlapController.signal);
			if (a.kind === "stop") return n.flatMap((e) => r.get(e) ?? []).filter(ua.isText).map((e) => e.text).join("");
			let { update: o } = a;
			da.isAgentMessage(o) ? (i(o.messageId), o.content !== void 0 && r.set(o.messageId, o.content ?? [])) : da.isAgentMessageChunk(o) && i(o.messageId).push(o.content);
		}
	}
	dispose() {
		for (let e of this.registrations.splice(0)) e.dispose();
		this.updates.fail(/* @__PURE__ */ Error("Active session disposed"));
	}
	[Symbol.dispose]() {
		this.dispose();
	}
	promptBlocks(e) {
		return typeof e == "string" ? [{
			type: "text",
			text: e
		}] : Array.isArray(e) ? e : [e];
	}
};
function Ua(e, t) {
	return e ? typeof e == "function" ? e(t) : e.parse(t) : t;
}
function X(e, t, n, r) {
	return {
		method: e,
		params: t,
		response: n,
		serializeResponse: r
	};
}
function Z(e, t) {
	return {
		method: e,
		params: t
	};
}
function Wa(e, t, n, r, i) {
	e.onReceiveRequest(t.method, (e) => Ua(t.params, e), async (e, a, o) => {
		try {
			let ee = await r(n(e, o, a.signal, a.id)), s = t.serializeResponse ? t.serializeResponse(ee) : ee;
			await a.respond(s), i?.afterResponse(e, s, o);
		} catch (e) {
			throw i?.onError(o, e), e;
		}
	});
}
function Ga(e, t, n, r) {
	e.onReceiveNotification(t.method, (e) => Ua(t.params, e), (e, t) => r(n(e, t, t.signal)));
}
function Ka(e) {
	let t = Object.create(null);
	for (let n of Object.values(e)) t[n.method] = n;
	return t;
}
var qa = {
	initialize: X(C.initialize, ga, va, va),
	loginAuth: X(C.auth_login, Lr, en, G),
	unstable_listProviders: X(C.providers_list, Rr, on),
	unstable_setProvider: X(C.providers_set, zr, sn, G),
	unstable_disableProvider: X(C.providers_disable, Br, cn, G),
	newSession: X(C.session_new, qr, vn),
	setSessionConfigOption: X(C.session_set_config_option, ti, En),
	prompt: X(C.session_prompt, ni, Dn, G),
	unstable_messageMcp: X(C.mcp_message, ft, B),
	listSessions: X(C.session_list, Jr, xn),
	deleteSession: X(C.session_delete, Yr, Sn, G),
	unstable_forkSession: X(C.session_fork, Xr, Cn),
	resumeSession: X(C.session_resume, $r, wn),
	closeSession: X(C.session_close, ei, Tn, G),
	logoutAuth: X(C.auth_logout, Vr, ln, G),
	unstable_startNes: X(C.nes_start, ai, On),
	unstable_suggestNes: X(C.nes_suggest, gi, Fn),
	unstable_closeNes: X(C.nes_close, _i, In, G)
}, Ja = {
	cancelSession: Z(C.session_cancel, Ei),
	unstable_messageMcp: Z(C.mcp_message, wr),
	unstable_didOpenDocument: Z(C.document_did_open, Di),
	unstable_didChangeDocument: Z(C.document_did_change, ki),
	unstable_didCloseDocument: Z(C.document_did_close, Ai),
	unstable_didSaveDocument: Z(C.document_did_save, ji),
	unstable_didFocusDocument: Z(C.document_did_focus, Mi),
	unstable_acceptNes: Z(C.nes_accept, Ni),
	unstable_rejectNes: Z(C.nes_reject, Fi)
}, Ya = {
	requestPermission: X(w.session_request_permission, We, bi),
	unstable_connectMcp: X(w.mcp_connect, ut, wi),
	unstable_messageMcp: X(w.mcp_message, ft, B),
	unstable_disconnectMcp: X(w.mcp_disconnect, pt, Ti, G),
	createElicitation: X(w.elicitation_create, ct, Ci)
}, Xa = {
	sessionUpdate: Z(w.session_update, Sr),
	unstable_messageMcp: Z(w.mcp_message, wr),
	completeElicitation: Z(w.elicitation_complete, Cr)
}, Q = Ka(qa), Za = Ka(Ja), $ = Ka(Ya), Qa = Ka(Xa);
function $a(e, t, n, r) {
	return {
		params: e,
		requestId: r,
		signal: n,
		agent: t
	};
}
function eo(e, t, n) {
	return {
		params: e,
		signal: n,
		agent: t
	};
}
var to = class {
	activeSessions = /* @__PURE__ */ new Map();
	handleMessage(e) {
		if (e.kind !== "notification" || e.method !== w.session_update) return h.no(e);
		let t = Sr.parse(e.params), { update: n } = t, r = da.isStateUpdate(n) && fa.isIdle(n), i = this.activeSessions.get(t.sessionId);
		if (i && i.size > 0) for (let e of i) r && e.isAwaitingPromptCompletion() ? (e.completePrompt(), e.enqueue({
			kind: "stop",
			notification: t,
			update: n,
			stopReason: n.stopReason
		})) : e.enqueue({
			kind: "session_update",
			notification: t,
			update: n
		});
		return h.no(e);
	}
	attach(e, t) {
		let n = this.activeSessions.get(e.sessionId) ?? /* @__PURE__ */ new Set();
		return n.add(t), this.activeSessions.set(e.sessionId, n), new le(() => {
			n.delete(t), n.size === 0 && this.activeSessions.delete(e.sessionId);
		});
	}
}, no = /* @__PURE__ */ new WeakMap();
function ro(e) {
	let t = no.get(e);
	return t || (t = new to(), no.set(e, t)), t;
}
function io(e, t) {
	for (let n of t) {
		let t;
		try {
			t = n(e);
		} catch (t) {
			throw e.close(t), t;
		}
		Promise.resolve(t).catch((t) => {
			e.close(t);
		});
	}
}
var ao = Symbol("appBuilder"), oo = Symbol("runAgentConnectHandlers"), so = Symbol("runClientConnectHandlers");
function co(e, t) {
	e.closed.then(async () => {
		q(e.getContext()).status === "initialized" && await t.initialized.catch(() => {}), t.close(e.signal.reason);
	});
}
function lo(e) {
	return new uo(e);
}
var uo = class {
	builder = ae.builder();
	connectHandlers = [];
	constructor(e = {}) {
		e.name && this.builder.name(e.name), this.builder.withHandler(Ea()), this.builder.withHandler({
			handleMessage: (e, t) => ro(t).handleMessage(e),
			describe: () => "client-session-update-router"
		});
	}
	[ao]() {
		return this.builder;
	}
	[so](e) {
		io(e, this.connectHandlers);
	}
	connect(e) {
		return this.connectConnection(e).connection;
	}
	connectWith(e, t) {
		let { rawConnection: n, connection: r } = this.connectConnection(e);
		return n.runUntil(() => t(r.agent));
	}
	onConnect(e) {
		return this.connectHandlers.push(e), this;
	}
	onRequest(e, t, n) {
		if (n) return ma(e, "request"), this.request({
			method: e,
			params: t
		}, n);
		let r = $[e];
		if (!r) throw Error(`Unknown ACP request method '${e}'. Pass a params parser for custom methods.`);
		return this.request(r, t);
	}
	onNotification(e, t, n) {
		if (n) return ma(e, "notification"), this.notification({
			method: e,
			params: t
		}, n);
		let r = Qa[e];
		if (!r) throw Error(`Unknown ACP notification method '${e}'. Pass a params parser for custom methods.`);
		return this.notification(r, t);
	}
	request(e, t) {
		return Wa(this.builder, e, (e, t, n, r) => $a(e, Na.create(t, r), n, r), t), this;
	}
	notification(e, t) {
		return Ga(this.builder, e, (e, t, n) => eo(e, Na.create(t), n), t), this;
	}
	connectConnection(e) {
		if (Oa(e)) {
			let t = this.openStreamConnection(e);
			return this[so](t.connection), t;
		}
		let [t, n] = ka(), r = e[ao]().connect(n), i = La(r), a = this.openStreamConnection(t);
		co(a.rawConnection, i), co(r, a.connection);
		try {
			e[oo](i), this[so](a.connection);
		} catch (e) {
			throw i.close(e), a.connection.close(e), e;
		}
		return a;
	}
	openStreamConnection(e) {
		let t = this.builder.connect(e);
		return {
			rawConnection: t,
			connection: Ra(t, this.connectHandlers)
		};
	}
};
//#endregion
//#region src/core/protocol/v2.ts
async function fo(e) {
	let { sink: t } = e, n, r = lo({ name: e.clientInfo.name }).onRequest(Y.client.session.requestPermission, async ({ params: e }) => {
		let n = e, r = await t.onPermission(e.sessionId, go(n), n);
		return oe(r);
	}).onRequest(Y.client.elicitation.create, async ({ params: e }) => {
		let n = e, r = await t.onElicitation("sessionId" in e && typeof e.sessionId == "string" ? e.sessionId : void 0, se(n), n);
		return de(r);
	}).onNotification(Y.client.session.update, ({ params: e }) => {
		t.onProtocol(Y.client.session.update, e), t.onUpdate(e.sessionId, e.update), n?.handleUpdate(e.sessionId, e.update);
	}).onNotification(Y.client.elicitation.complete, ({ params: e }) => {
		t.onProtocol(Y.client.elicitation.complete, e), t.onElicitationComplete(e.elicitationId);
	}).connect(e.stream), i = !1;
	r.closed.then(() => {
		n?.handleClose(), i && t.onDisconnect();
	});
	let a;
	try {
		if (a = await r.agent.request(Y.agent.initialize, {
			protocolVersion: 2,
			info: {
				name: e.clientInfo.name,
				version: e.clientInfo.version,
				...e.clientInfo.title ? { title: e.clientInfo.title } : {}
			},
			capabilities: {
				auth: { ...e.host?.terminalAuth ? { terminal: {} } : {} },
				elicitation: {
					form: {},
					url: {}
				}
			}
		}), r.signal.aborted) throw r.signal.reason;
	} catch (e) {
		throw r.close(e), new p("INITIALIZE_REJECTED", "ACP v2 initialization failed", {
			cause: e,
			protocol: 2,
			phase: "initialize",
			retryable: !0
		});
	}
	if (a.protocolVersion !== 2) throw r.close(), new p("PROTOCOL_VERSION_MISMATCH", `Requested ACP v2 but agent selected v${a.protocolVersion}`, {
		protocol: 2,
		phase: "initialize"
	});
	if (a.capabilities?.session == null) throw r.close(), new p("CAPABILITY_REQUIRED", "The ACP v2 agent does not advertise the session surface", {
		protocol: 2,
		phase: "initialize"
	});
	let o = a.capabilities.session;
	return n = new po(r, {
		protocolVersion: 2,
		agentName: a.info.title ?? a.info.name,
		authMethods: te(a.authMethods),
		capabilities: {
			listSessions: !0,
			loadSession: !0,
			resumeSession: !0,
			closeSession: !0,
			deleteSession: o.delete != null
		},
		promptCapabilities: {
			image: o.prompt?.image != null,
			audio: o.prompt?.audio != null,
			embeddedContext: o.prompt?.embeddedContext != null
		},
		additionalDirectories: o.additionalDirectories != null,
		mcp: {
			stdio: o.mcp?.stdio != null,
			http: o.mcp?.http != null,
			sse: !1
		}
	}, e.host, () => {
		i = !1;
	}), i = !0, n;
}
var po = class {
	connection;
	initialized;
	host;
	markClosed;
	version = 2;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Set();
	constructor(e, t, n, r) {
		this.connection = e, this.initialized = t, this.host = n, this.markClosed = r;
	}
	async newSession(e) {
		ie(e, this.initialized, 2, "session/new");
		let t = await ce(() => this.connection.agent.request(Y.agent.session.new, mo(e)), 2, "session/new");
		return {
			sessionId: t.sessionId,
			configOptions: ne(t.configOptions)
		};
	}
	async openSession(e, t, n) {
		ie(t, this.initialized, 2, "session/open");
		let r = await ce(() => this.connection.agent.request(Y.agent.session.resume, {
			...mo(t),
			sessionId: e,
			...n === "all" ? { replayFrom: { type: "start" } } : {}
		}), 2, "session/open");
		return {
			sessionId: e,
			configOptions: ne(r.configOptions)
		};
	}
	async listSessions(e, t) {
		let n = await this.connection.agent.request(Y.agent.session.list, {
			cwd: e,
			...t ? { cursor: t } : {}
		});
		return ee(n);
	}
	async deleteSession(e) {
		if (!this.initialized.capabilities.deleteSession) throw new p("CAPABILITY_REQUIRED", "The agent does not support session/delete", { protocol: 2 });
		await this.connection.agent.request(Y.agent.session.delete, { sessionId: e });
	}
	async closeSession(e) {
		await this.connection.agent.request(Y.agent.session.close, { sessionId: e });
	}
	promptReady(e) {
		return !this.#t.has(e);
	}
	async prompt(e, t, n) {
		if (this.#e.has(e)) throw new p("SESSION_BUSY", `Session '${e}' already has a foreground turn`, {
			protocol: 2,
			accepted: !1,
			completionUnknown: !1
		});
		let r, i, a = new Promise((e, t) => {
			r = e, i = t;
		});
		a.catch(() => void 0);
		let o = {
			sessionId: e,
			accepted: !1,
			promise: a,
			resolve: r,
			reject: i
		};
		this.#e.set(e, o);
		try {
			let r = this.connection.agent.request(Y.agent.session.prompt, {
				sessionId: e,
				prompt: t
			});
			return this.#e.get(e) === o && (o.accepted = !0), n(), await r, await a;
		} catch (t) {
			throw this.#e.get(e) === o && this.#e.delete(e), re(t, 2, o.accepted);
		}
	}
	async cancel(e) {
		let t = this.#e.get(e);
		t && this.#t.add(e);
		try {
			await this.connection.agent.notify(Y.agent.session.cancel, { sessionId: e });
		} catch (t) {
			throw this.#t.delete(e), t;
		}
		!t || this.#e.get(e) !== t || (this.#e.delete(e), t.resolve("cancelled"));
	}
	async setConfigOption(e, t, n) {
		let r = await this.connection.agent.request(Y.agent.session.setConfigOption, {
			sessionId: e,
			configId: t,
			type: typeof n == "boolean" ? "boolean" : "id",
			value: n
		});
		return ne(r.configOptions);
	}
	async authenticate(e) {
		if (e.type === "terminal") {
			if (!this.host?.terminalAuth) throw new p("CAPABILITY_REQUIRED", "Terminal authentication needs a host handler", { protocol: 2 });
			await this.host.terminalAuth(e);
			return;
		}
		await this.connection.agent.request(Y.agent.auth.login, { methodId: e.id });
	}
	async logout() {
		await this.connection.agent.request(Y.agent.auth.logout, {});
	}
	handleUpdate(e, n) {
		if (!o(n) || n.sessionUpdate !== "state_update" || n.state !== "idle" || this.#t.delete(e) || !this.#e.has(e)) return;
		let r = this.#e.get(e);
		r && (this.#e.delete(e), r.resolve(t(n.stopReason) ?? "end_turn"));
	}
	handleClose() {
		for (let e of this.#e.values()) e.reject(new p("TURN_INTERRUPTED", "Connection closed before the turn completed", {
			protocol: 2,
			phase: "prompt",
			retryable: !0,
			accepted: e.accepted,
			completionUnknown: e.accepted
		}));
		this.#e.clear(), this.#t.clear();
	}
	async close(e) {
		this.markClosed(), this.handleClose(), this.connection.close(e), await this.connection.closed;
	}
};
function mo(e) {
	return {
		cwd: e.cwd,
		...e.additionalDirectories?.length ? { additionalDirectories: [...e.additionalDirectories] } : {},
		...e.mcpServers?.length ? { mcpServers: e.mcpServers.map(ho) } : {}
	};
}
function ho(e) {
	if (e.type === "sse") throw new p("INVALID_CONFIGURATION", "SSE MCP servers are not part of ACP v2", { protocol: 2 });
	return e.type === "stdio" ? {
		type: "stdio",
		name: e.name,
		command: e.command,
		...e.args?.length ? { args: [...e.args] } : {},
		...e.env?.length ? { env: [...e.env] } : {}
	} : {
		type: "http",
		name: e.name,
		url: e.url,
		...e.headers?.length ? { headers: [...e.headers] } : {}
	};
}
function go(e) {
	let n = o(e) ? e : {}, r = t(n.description);
	return {
		type: "permission",
		title: t(n.title) ?? "Permission required",
		...r ? { description: r } : {},
		options: ue(n.options)
	};
}
//#endregion
export { fo as connectV2 };

//# sourceMappingURL=v2.js.map