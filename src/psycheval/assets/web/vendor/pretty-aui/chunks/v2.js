globalThis.__zod_globalConfig ??= {}, globalThis.__zod_globalConfig.jitless = !0;
import { A as e, B as t, D as n, E as r, F as i, H as a, I as o, L as s, M as c, N as l, O as u, P as d, R as f, T as p, V as m, W as h, a as ee, b as te, d as ne, f as re, h as ie, i as ae, j as g, k as _, l as oe, o as se, p as ce, r as le, s as ue, t as de, v as fe, x as v, y, z as b } from "./types.js";
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/v2/schema/index.js
var x = {
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
}, S = {
	session_request_permission: "session/request_permission",
	session_update: "session/update",
	mcp_connect: "mcp/connect",
	mcp_message: "mcp/message",
	mcp_disconnect: "mcp/disconnect",
	elicitation_create: "elicitation/create",
	elicitation_complete: "elicitation/complete"
}, C = { cancel_request: "$/cancel_request" }, w = b([i(), f()]).nullable(), T = f(), E = f(), pe = b([
	d("read"),
	d("edit"),
	d("delete"),
	d("move"),
	d("search"),
	d("execute"),
	d("think"),
	d("fetch"),
	d("switch_mode"),
	d("other"),
	f()
]), me = b([
	d("pending"),
	d("in_progress"),
	d("completed"),
	d("failed"),
	d("cancelled"),
	f()
]), he = b([
	d("assistant"),
	d("user"),
	f()
]), D = o({
	audience: p(_(he).nullish(), () => void 0),
	lastModified: p(a({ offset: !0 }).nullish(), () => void 0),
	priority: p(i().gte(0).lte(1).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ge = o({
	text: f(),
	annotations: p(D.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), O = f(), _e = o({
	data: f(),
	mimeType: O,
	uri: p(m().nullish(), () => void 0),
	annotations: p(D.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ve = o({
	data: f(),
	mimeType: O,
	annotations: p(D.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ye = b([
	d("light"),
	d("dark"),
	f()
]), be = o({
	src: m(),
	mimeType: p(O.nullish(), () => void 0),
	sizes: p(_(f()).nullish(), () => void 0),
	theme: p(ye.nullish(), () => void 0)
}), xe = o({
	name: f(),
	uri: m(),
	title: p(f().nullish(), () => void 0),
	description: p(f().nullish(), () => void 0),
	icons: p(_(be).nullish(), () => void 0),
	mimeType: p(O.nullish(), () => void 0),
	size: p(i().nullish(), () => void 0),
	annotations: p(D.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Se = o({
	text: f(),
	uri: m(),
	mimeType: p(O.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ce = o({
	blob: f(),
	uri: m(),
	mimeType: p(O.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), we = b([Se, Ce]), Te = o({
	resource: we,
	annotations: p(D.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), k = n(b([
	ge.and(o({ type: d("text") })),
	_e.and(o({ type: d("image") })),
	ve.and(o({ type: d("audio") })),
	xe.and(o({ type: d("resource_link") })),
	Te.and(o({ type: d("resource") })),
	r(o({ type: f() }), "type", [
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
]), Ee = o({
	content: k,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), De = b([
	d("text"),
	d("binary"),
	d("directory"),
	d("symlink"),
	f()
]), A = f(), j = o({ path: A }), M = o({
	oldPath: A,
	path: A
}), Oe = n(l(b([
	j.and(o({ operation: d("add") })),
	j.and(o({ operation: d("delete") })),
	j.and(o({ operation: d("modify") })),
	M.and(o({ operation: d("move") })),
	M.and(o({ operation: d("copy") })),
	r(o({ operation: f() }), "operation", [
		"add",
		"copy",
		"delete",
		"modify",
		"move"
	])
]), o({
	fileType: p(De.nullish(), () => void 0),
	mimeType: p(O.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
})), "operation", [
	"add",
	"copy",
	"delete",
	"modify",
	"move"
]), ke = b([d("git_patch"), f()]), Ae = o({
	format: ke,
	text: f()
}), je = o({
	changes: _(Oe),
	patch: p(Ae.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), N = f(), Me = o({
	terminalId: N,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ne = n(b([
	Ee.and(o({ type: d("content") })),
	je.and(o({ type: d("diff") })),
	Me.and(o({ type: d("terminal") })),
	r(o({ type: f() }), "type", [
		"content",
		"diff",
		"terminal"
	])
]), "type", [
	"content",
	"diff",
	"terminal"
]), Pe = o({
	path: A,
	line: p(c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Fe = o({
	toolCallId: E,
	name: p(f().nullish(), () => void 0),
	title: p(f().nullish(), () => void 0),
	kind: p(pe.nullish(), () => void 0),
	status: p(me.nullish(), () => void 0),
	content: p(_(Ne).nullish(), () => void 0),
	locations: p(_(Pe).nullish(), () => void 0),
	rawInput: p(t().optional(), () => void 0),
	rawOutput: p(t().optional(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ie = o({ toolCall: Fe }), Le = o({
	command: f(),
	cwd: A,
	toolCallId: p(E.nullish(), () => void 0),
	terminalId: p(N.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Re = n(b([
	Ie.and(o({ type: d("tool_call") })),
	Le.and(o({ type: d("command") })),
	r(o({ type: f() }), "type", ["command", "tool_call"])
]), "type", ["command", "tool_call"]), ze = f(), Be = b([
	d("allow_once"),
	d("allow_always"),
	d("reject_once"),
	d("reject_always"),
	f()
]), Ve = o({
	optionId: ze,
	name: f(),
	kind: Be,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), He = o({
	sessionId: T,
	title: f(),
	description: p(f().nullish(), () => void 0),
	subject: Re.nullish(),
	options: e(Ve).min(1),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ue = o({
	sessionId: T,
	toolCallId: p(E.nullish(), () => void 0)
}), We = o({ requestId: w }), Ge = d("object"), Ke = b([
	d("email"),
	d("uri"),
	d("date"),
	d("date-time"),
	f()
]), qe = o({
	const: f(),
	title: f(),
	description: p(f().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Je = o({
	title: p(f().nullish(), () => void 0),
	description: p(f().nullish(), () => void 0),
	minLength: c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	maxLength: c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	pattern: f().nullish(),
	format: Ke.nullish(),
	default: p(f().nullish(), () => void 0),
	enum: e(f()).min(1).nullish(),
	oneOf: e(qe).min(1).nullish(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ye = o({
	title: p(f().nullish(), () => void 0),
	description: p(f().nullish(), () => void 0),
	minimum: i().nullish(),
	maximum: i().nullish(),
	default: p(i().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Xe = o({
	title: p(f().nullish(), () => void 0),
	description: p(f().nullish(), () => void 0),
	minimum: i().nullish(),
	maximum: i().nullish(),
	default: p(i().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ze = o({
	title: p(f().nullish(), () => void 0),
	description: p(f().nullish(), () => void 0),
	default: p(g().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Qe = o({
	enum: e(f()).min(1),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), $e = o({
	anyOf: e(qe).min(1),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), et = n(b([
	Qe.and(o({ type: d("string") })),
	r(o({ type: f() }), "type", ["string"]),
	$e
]), "type", ["string"]), tt = o({
	title: p(f().nullish(), () => void 0),
	description: p(f().nullish(), () => void 0),
	minItems: i().nullish(),
	maxItems: i().nullish(),
	items: et,
	default: p(_(f()).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), nt = n(b([
	Je.and(o({ type: d("string") })),
	Ye.and(o({ type: d("number") })),
	Xe.and(o({ type: d("integer") })),
	Ze.and(o({ type: d("boolean") })),
	tt.and(o({ type: d("array") })),
	r(o({ type: f() }), "type", [
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
]), rt = o({
	type: p(Ge.optional().default("object"), () => "object"),
	title: p(f().nullish(), () => void 0),
	properties: s(f(), nt).optional().default({}),
	required: e(f()).nullish(),
	description: p(f().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), it = l(b([Ue, We]), o({ requestedSchema: rt })), at = f(), ot = l(b([Ue, We]), o({
	elicitationId: at,
	url: m()
})), st = n(l(b([
	it.and(o({ mode: d("form") })),
	ot.and(o({ mode: d("url") })),
	r(l(b([Ue, We]), o({ mode: f() })), "mode", ["form", "url"])
]), o({
	message: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
})), "mode", ["form", "url"]), ct = f(), lt = o({
	serverId: ct,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ut = f(), dt = o({
	connectionId: ut,
	method: f(),
	params: s(f(), t()).nullish(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ft = o({
	connectionId: ut,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), pt = t();
o({
	id: w,
	method: f(),
	params: b([
		He,
		st,
		lt,
		dt,
		ft,
		pt
	]).nullish()
});
var mt = c().gte(0).lte(65535), ht = o({
	name: f(),
	title: p(f().nullish(), () => void 0),
	version: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), gt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), _t = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), vt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), yt = o({
	image: p(gt.nullish(), () => void 0),
	audio: p(_t.nullish(), () => void 0),
	embeddedContext: p(vt.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), bt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), xt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), St = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Ct = o({
	stdio: p(bt.nullish(), () => void 0),
	http: p(xt.nullish(), () => void 0),
	acp: p(St.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), wt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Tt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Et = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Dt = o({
	prompt: p(yt.nullish(), () => void 0),
	mcp: p(Ct.nullish(), () => void 0),
	delete: p(wt.nullish(), () => void 0),
	additionalDirectories: p(Tt.nullish(), () => void 0),
	fork: p(Et.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ot = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), kt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), At = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), jt = b([d("full"), d("incremental")]), Mt = o({
	syncKind: jt,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Nt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Pt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Ft = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), It = o({
	didOpen: p(At.nullish(), () => void 0),
	didChange: p(Mt.nullish(), () => void 0),
	didClose: p(Nt.nullish(), () => void 0),
	didSave: p(Pt.nullish(), () => void 0),
	didFocus: p(Ft.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Lt = o({
	document: p(It.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Rt = o({
	maxCount: p(c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), zt = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Bt = o({
	maxCount: p(c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Vt = o({
	maxCount: p(c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ht = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Ut = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Wt = o({
	recentFiles: p(Rt.nullish(), () => void 0),
	relatedSnippets: p(zt.nullish(), () => void 0),
	editHistory: p(Bt.nullish(), () => void 0),
	userActions: p(Vt.nullish(), () => void 0),
	openFiles: p(Ht.nullish(), () => void 0),
	diagnostics: p(Ut.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Gt = o({
	events: p(Lt.nullish(), () => void 0),
	context: p(Wt.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Kt = b([
	d("utf-16"),
	d("utf-32"),
	d("utf-8")
]), qt = o({
	session: p(Dt.nullish(), () => void 0),
	auth: p(Ot.nullish(), () => void 0),
	providers: p(kt.nullish(), () => void 0),
	nes: p(Gt.nullish(), () => void 0),
	positionEncoding: p(Kt.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), P = f(), Jt = o({
	name: f(),
	value: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Yt = o({
	methodId: P,
	name: f(),
	description: p(f().nullish(), () => void 0),
	args: p(_(f()).optional(), () => []),
	env: p(_(Jt).optional(), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Xt = o({
	methodId: P,
	name: f(),
	description: p(f().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Zt = n(b([
	Yt.and(o({ type: d("terminal") })),
	Xt.and(o({ type: d("agent") })),
	r(o({
		type: f(),
		methodId: P,
		name: f(),
		description: p(f().nullish(), () => void 0),
		_meta: p(s(f(), t()).nullish(), () => void 0)
	}), "type", ["agent", "terminal"])
]), "type", ["agent", "terminal"]), Qt = o({
	protocolVersion: mt,
	info: ht,
	capabilities: p(qt.optional().default({}), () => ({})),
	authMethods: p(_(Zt).optional(), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), $t = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), en = f(), tn = b([
	d("anthropic"),
	d("openai"),
	d("azure"),
	d("vertex"),
	d("bedrock"),
	f()
]), nn = o({
	apiType: tn,
	baseUrl: m(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), rn = o({
	providerId: en,
	supported: u(_(tn), () => []),
	required: g(),
	current: nn.nullish(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), an = o({
	providers: e(rn),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), on = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), sn = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), cn = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), F = f(), ln = b([
	d("mode"),
	d("model"),
	d("model_config"),
	d("thought_level"),
	f()
]), I = f(), un = o({
	value: I,
	name: f(),
	description: p(f().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), dn = f(), fn = o({
	groupId: dn,
	name: f(),
	options: u(_(un), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), pn = b([e(un), e(fn)]), mn = o({
	currentValue: I,
	options: pn
}), hn = o({ currentValue: g() }), L = n(l(b([
	mn.and(o({ type: d("select") })),
	hn.and(o({ type: d("boolean") })),
	r(o({ type: f() }), "type", ["boolean", "select"])
]), o({
	configId: F,
	name: f(),
	description: p(f().nullish(), () => void 0),
	category: p(ln.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
})), "type", ["boolean", "select"]), gn = o({
	sessionId: T,
	configOptions: p(_(L).optional(), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), _n = o({
	sessionId: T,
	cwd: A,
	additionalDirectories: p(_(A).optional(), () => []),
	title: p(f().nullish(), () => void 0),
	updatedAt: p(a({ offset: !0 }).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), vn = f(), yn = o({
	sessions: u(_(_n), () => []),
	nextCursor: p(vn.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), bn = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), xn = o({
	sessionId: T,
	configOptions: p(_(L).optional(), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Sn = o({
	configOptions: p(_(L).optional(), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Cn = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), wn = o({
	configOptions: u(_(L), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Tn = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), En = o({
	sessionId: T,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), R = f(), z = o({
	line: c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	character: c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), B = o({
	start: z,
	end: z,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Dn = o({
	range: B,
	newText: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), On = o({
	suggestionId: R,
	uri: m(),
	edits: e(Dn).min(1),
	cursorPosition: p(z.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), kn = o({
	suggestionId: R,
	uri: m(),
	position: z,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), An = o({
	suggestionId: R,
	uri: m(),
	position: z,
	newName: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), jn = o({
	suggestionId: R,
	uri: m(),
	search: f(),
	replace: f(),
	isRegex: g().nullish(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Mn = n(b([
	On.and(o({ kind: d("edit") })),
	kn.and(o({ kind: d("jump") })),
	An.and(o({ kind: d("rename") })),
	jn.and(o({ kind: d("searchAndReplace") })),
	r(o({
		kind: f(),
		suggestionId: R
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
]), Nn = o({
	suggestions: e(Mn),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Pn = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Fn = t(), V = t(), In = b([
	d(-32700),
	d(-32600),
	d(-32601),
	d(-32602),
	d(-32603),
	d(-32800),
	d(-32e3),
	d(-32002),
	c().min(-2147483648, { error: "Invalid value: Expected int32 to be >= -2147483648" }).max(2147483647, { error: "Invalid value: Expected int32 to be <= 2147483647" })
]), Ln = o({
	code: In,
	message: f(),
	data: p(t().optional(), () => void 0)
});
b([o({
	id: w,
	result: b([
		Qt,
		$t,
		an,
		on,
		sn,
		cn,
		gn,
		yn,
		bn,
		xn,
		Sn,
		Cn,
		wn,
		Tn,
		En,
		Nn,
		Pn,
		Fn,
		V
	])
}), o({
	id: w,
	error: Ln
})]);
var H = f(), U = o({
	messageId: H,
	content: k,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Rn = o({
	messageId: H,
	content: p(_(k).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), zn = o({
	messageId: H,
	content: p(_(k).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Bn = o({
	messageId: H,
	content: p(_(k).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Vn = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Hn = b([
	d("end_turn"),
	d("max_tokens"),
	d("max_turn_requests"),
	d("refusal"),
	d("cancelled"),
	f()
]), Un = o({
	totalTokens: i(),
	inputTokens: i(),
	outputTokens: i(),
	thoughtTokens: p(i().nullish(), () => void 0),
	cachedReadTokens: p(i().nullish(), () => void 0),
	cachedWriteTokens: p(i().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Wn = o({
	stopReason: p(Hn.nullish(), () => void 0),
	usage: p(Un.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Gn = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Kn = n(b([
	Vn.and(o({ state: d("running") })),
	Wn.and(o({ state: d("idle") })),
	Gn.and(o({ state: d("requires_action") })),
	r(o({ state: f() }), "state", [
		"idle",
		"requires_action",
		"running"
	])
]), "state", [
	"idle",
	"requires_action",
	"running"
]), qn = o({
	toolCallId: E,
	content: Ne,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Jn = o({
	data: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Yn = o({
	exitCode: p(c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: p(f().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Xn = o({
	terminalId: N,
	command: p(f().nullish(), () => void 0),
	cwd: p(A.nullish(), () => void 0),
	output: p(Jn.nullish(), () => void 0),
	exitStatus: p(Yn.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Zn = o({
	terminalId: N,
	data: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), W = f(), Qn = b([
	d("high"),
	d("medium"),
	d("low"),
	f()
]), $n = b([
	d("pending"),
	d("in_progress"),
	d("completed"),
	d("cancelled"),
	f()
]), er = o({
	content: f(),
	priority: Qn,
	status: $n,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), tr = o({
	planId: W,
	entries: u(_(er), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), nr = o({
	planId: W,
	uri: m(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), rr = o({
	planId: W,
	content: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ir = n(b([
	tr.and(o({ type: d("items") })),
	nr.and(o({ type: d("file") })),
	rr.and(o({ type: d("markdown") })),
	r(o({
		type: f(),
		planId: W
	}), "type", [
		"file",
		"items",
		"markdown"
	])
]), "type", [
	"file",
	"items",
	"markdown"
]), ar = o({
	plan: ir,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), or = o({
	planId: W,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), sr = o({
	hint: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), cr = n(b([sr.and(o({ type: d("text") })), r(o({ type: f() }), "type", ["text"])]), "type", ["text"]), lr = o({
	name: f(),
	description: f(),
	input: p(cr.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ur = o({
	availableCommands: u(_(lr), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), dr = o({
	configOptions: u(_(L), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), fr = o({
	title: p(f().nullish(), () => void 0),
	updatedAt: p(a({ offset: !0 }).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), pr = o({
	amount: i(),
	currency: f().regex(/^[A-Z]{3}$/),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), mr = o({
	used: i(),
	size: i(),
	cost: p(pr.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), hr = f(), gr = b([
	d("in_progress"),
	d("completed"),
	d("failed"),
	d("cancelled"),
	f()
]), _r = o({
	compactionId: hr,
	status: gr,
	summary: p(_(k).nullish(), () => void 0),
	error: p(f().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), vr = o({
	compactionId: hr,
	content: k,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), yr = n(b([
	U.and(o({ sessionUpdate: d("user_message_chunk") })),
	Rn.and(o({ sessionUpdate: d("user_message") })),
	U.and(o({ sessionUpdate: d("agent_message_chunk") })),
	zn.and(o({ sessionUpdate: d("agent_message") })),
	U.and(o({ sessionUpdate: d("agent_thought_chunk") })),
	Bn.and(o({ sessionUpdate: d("agent_thought") })),
	Kn.and(o({ sessionUpdate: d("state_update") })),
	qn.and(o({ sessionUpdate: d("tool_call_content_chunk") })),
	Fe.and(o({ sessionUpdate: d("tool_call_update") })),
	Xn.and(o({ sessionUpdate: d("terminal_update") })),
	Zn.and(o({ sessionUpdate: d("terminal_output_chunk") })),
	ar.and(o({ sessionUpdate: d("plan_update") })),
	or.and(o({ sessionUpdate: d("plan_removed") })),
	ur.and(o({ sessionUpdate: d("available_commands_update") })),
	dr.and(o({ sessionUpdate: d("config_option_update") })),
	fr.and(o({ sessionUpdate: d("session_info_update") })),
	mr.and(o({ sessionUpdate: d("usage_update") })),
	_r.and(o({ sessionUpdate: d("compaction_update") })),
	vr.and(o({ sessionUpdate: d("compaction_summary_chunk") })),
	r(o({ sessionUpdate: f() }), "sessionUpdate", [
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
]), br = o({
	sessionId: T,
	update: yr,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), xr = o({
	elicitationId: at,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Sr = o({
	connectionId: ut,
	method: f(),
	params: p(s(f(), t()).nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Cr = t();
o({
	method: f(),
	params: b([
		br,
		xr,
		Sr,
		Cr
	]).nullish()
});
var wr = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Tr = o({
	terminal: p(wr.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Er = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Dr = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Or = o({
	form: p(Er.nullish(), () => void 0),
	url: p(Dr.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), kr = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Ar = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), jr = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Mr = o({
	jump: p(kr.nullish(), () => void 0),
	rename: p(Ar.nullish(), () => void 0),
	searchAndReplace: p(jr.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Nr = o({
	auth: p(Tr.nullish(), () => void 0),
	elicitation: p(Or.nullish(), () => void 0),
	nes: p(Mr.nullish(), () => void 0),
	positionEncodings: p(_(Kt).optional(), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Pr = o({
	protocolVersion: mt,
	info: ht,
	capabilities: p(Nr.optional().default({}), () => ({})),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Fr = o({
	methodId: P,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ir = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Lr = o({
	providerId: en,
	apiType: tn,
	baseUrl: m(),
	headers: s(f(), f()).optional(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Rr = o({
	providerId: en,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), zr = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Br = o({
	name: f(),
	value: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Vr = o({
	name: f(),
	url: m(),
	headers: e(Br).optional(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Hr = o({
	name: f(),
	serverId: ct,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ur = o({
	name: f(),
	command: A,
	args: e(f()).optional(),
	env: e(Jt).optional(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Wr = n(b([
	Vr.and(o({ type: d("http") })),
	Hr.and(o({ type: d("acp") })),
	Ur.and(o({ type: d("stdio") })),
	r(o({ type: f() }), "type", [
		"acp",
		"http",
		"stdio"
	])
]), "type", [
	"acp",
	"http",
	"stdio"
]), Gr = o({
	cwd: A,
	additionalDirectories: p(_(A).optional(), () => []),
	mcpServers: p(_(Wr).optional(), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Kr = o({
	cwd: A.nullish(),
	cursor: vn.nullish(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), qr = o({
	sessionId: T,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Jr = o({
	sessionId: T,
	cwd: A,
	additionalDirectories: p(_(A).optional(), () => []),
	mcpServers: p(_(Wr).optional(), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Yr = o({ _meta: p(s(f(), t()).nullish(), () => void 0) }), Xr = n(b([Yr.and(o({ type: d("start") })), r(o({
	type: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), "type", ["start"])]), "type", ["start"]), Zr = o({
	sessionId: T,
	cwd: A,
	additionalDirectories: p(_(A).optional(), () => []),
	mcpServers: p(_(Wr).optional(), () => []),
	replayFrom: p(Xr.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Qr = o({
	sessionId: T,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), $r = n(l(b([
	o({
		value: I,
		type: d("id")
	}),
	o({
		value: g(),
		type: d("boolean")
	}),
	r(o({
		type: f(),
		value: t()
	}), "type", ["boolean", "id"])
]), o({
	sessionId: T,
	configId: F,
	_meta: p(s(f(), t()).nullish(), () => void 0)
})), "type", ["boolean", "id"]), ei = o({
	sessionId: T,
	prompt: e(k),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ti = o({
	uri: m(),
	name: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ni = o({
	name: f(),
	owner: f(),
	remoteUrl: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ri = o({
	workspaceUri: p(m().nullish(), () => void 0),
	workspaceFolders: e(ti).nullish(),
	repository: p(ni.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ii = b([
	d("automatic"),
	d("diagnostic"),
	d("manual"),
	f()
]), ai = o({
	uri: m(),
	languageId: f(),
	text: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), oi = o({
	startLine: c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	endLine: c().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	text: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), si = o({
	uri: m(),
	excerpts: e(oi),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ci = o({
	uri: m(),
	diff: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), li = o({
	action: f(),
	uri: m(),
	position: z,
	timestampMs: i(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ui = o({
	uri: m(),
	languageId: f(),
	visibleRange: p(B.nullish(), () => void 0),
	lastFocusedMs: p(i().nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), di = b([
	d("error"),
	d("warning"),
	d("information"),
	d("hint"),
	f()
]), fi = o({
	uri: m(),
	range: B,
	severity: di,
	message: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), pi = o({
	recentFiles: e(ai).nullish(),
	relatedSnippets: e(si).nullish(),
	editHistory: e(ci).nullish(),
	userActions: e(li).nullish(),
	openFiles: e(ui).nullish(),
	diagnostics: e(fi).nullish(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), mi = o({
	sessionId: T,
	uri: m(),
	version: i(),
	position: z,
	selection: B.nullish(),
	triggerKind: ii,
	context: pi.nullish(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), hi = o({
	sessionId: T,
	_meta: p(s(f(), t()).nullish(), () => void 0)
});
o({
	id: w,
	method: f(),
	params: b([
		Pr,
		Fr,
		Ir,
		Lr,
		Rr,
		zr,
		Gr,
		Kr,
		qr,
		Jr,
		Zr,
		Qr,
		$r,
		ei,
		ri,
		mi,
		hi,
		dt,
		pt
	]).nullish()
});
var gi = o({
	optionId: ze,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), _i = n(b([
	o({ outcome: d("cancelled") }),
	gi.and(o({ outcome: d("selected") })),
	r(o({ outcome: f() }), "outcome", ["cancelled", "selected"])
]), "outcome", ["cancelled", "selected"]), vi = o({
	outcome: _i,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), yi = b([
	f(),
	i(),
	i(),
	g(),
	e(f())
]), bi = o({ content: s(f(), yi).nullish() }), xi = n(l(b([
	bi.and(o({ action: d("accept") })),
	o({ action: d("decline") }),
	o({ action: d("cancel") }),
	r(o({ action: f() }), "action", [
		"accept",
		"cancel",
		"decline"
	])
]), o({ _meta: p(s(f(), t()).nullish(), () => void 0) })), "action", [
	"accept",
	"cancel",
	"decline"
]), Si = o({
	connectionId: ut,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ci = o({ _meta: p(s(f(), t()).nullish(), () => void 0) });
b([o({
	id: w,
	result: b([
		vi,
		xi,
		Si,
		Ci,
		V,
		Fn
	])
}), o({
	id: w,
	error: Ln
})]);
var wi = o({
	sessionId: T,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ti = o({
	sessionId: T,
	uri: m(),
	languageId: f(),
	version: i(),
	text: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ei = o({
	range: B.nullish(),
	text: f(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Di = o({
	sessionId: T,
	uri: m(),
	version: i(),
	contentChanges: u(_(Ei), () => []),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Oi = o({
	sessionId: T,
	uri: m(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ki = o({
	sessionId: T,
	uri: m(),
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Ai = o({
	sessionId: T,
	uri: m(),
	version: i(),
	position: z,
	visibleRange: B,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), ji = o({
	sessionId: T,
	suggestionId: R,
	_meta: p(s(f(), t()).nullish(), () => void 0)
}), Mi = b([
	d("rejected"),
	d("ignored"),
	d("replaced"),
	d("cancelled"),
	f()
]), Ni = o({
	sessionId: T,
	suggestionId: R,
	reason: p(Mi.nullish(), () => void 0),
	_meta: p(s(f(), t()).nullish(), () => void 0)
});
o({
	method: f(),
	params: b([
		wi,
		Ti,
		Di,
		Oi,
		ki,
		Ai,
		ji,
		Ni,
		Sr,
		Cr
	]).nullish()
});
var Pi = o({
	requestId: w,
	_meta: p(s(f(), t()).nullish(), () => void 0)
});
o({
	method: f(),
	params: Pi.nullish()
});
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/v2/schema/guards.gen.js
function G(e, t) {
	return typeof e == "object" && e ? e[t] : void 0;
}
Ie.and(o({ type: d("tool_call") })), Le.and(o({ type: d("command") })), Ee.and(o({ type: d("content") })), je.and(o({ type: d("diff") })), Me.and(o({ type: d("terminal") }));
var Fi = ge.and(o({ type: d("text") })), Ii = _e.and(o({ type: d("image") })), Li = ve.and(o({ type: d("audio") })), Ri = xe.and(o({ type: d("resource_link") })), zi = Te.and(o({ type: d("resource") }));
j.and(o({ operation: d("add") })), j.and(o({ operation: d("delete") })), j.and(o({ operation: d("modify") })), M.and(o({ operation: d("move") })), M.and(o({ operation: d("copy") })), it.and(o({ mode: d("form") })).and(o({ message: f() })), ot.and(o({ mode: d("url") })).and(o({ message: f() })), b([Ue, We]).and(o({ message: f() })), Je.and(o({ type: d("string") })), Ye.and(o({ type: d("number") })), Xe.and(o({ type: d("integer") })), Ze.and(o({ type: d("boolean") })), tt.and(o({ type: d("array") })), Qe.and(o({ type: d("string") })), Yt.and(o({ type: d("terminal") })), Xt.and(o({ type: d("agent") })), o({
	methodId: P,
	name: f()
}), mn.and(o({ type: d("select") })).and(o({
	configId: F,
	name: f()
})), hn.and(o({ type: d("boolean") })).and(o({
	configId: F,
	name: f()
})), o({
	configId: F,
	name: f()
}), On.and(o({ kind: d("edit") })), kn.and(o({ kind: d("jump") })), An.and(o({ kind: d("rename") })), jn.and(o({ kind: d("searchAndReplace") })), o({ suggestionId: R });
var Bi = U.and(o({ sessionUpdate: d("user_message_chunk") })), Vi = Rn.and(o({ sessionUpdate: d("user_message") })), Hi = U.and(o({ sessionUpdate: d("agent_message_chunk") })), Ui = zn.and(o({ sessionUpdate: d("agent_message") })), Wi = U.and(o({ sessionUpdate: d("agent_thought_chunk") })), Gi = Bn.and(o({ sessionUpdate: d("agent_thought") })), Ki = Kn.and(o({ sessionUpdate: d("state_update") })), qi = qn.and(o({ sessionUpdate: d("tool_call_content_chunk") })), Ji = Fe.and(o({ sessionUpdate: d("tool_call_update") })), Yi = Xn.and(o({ sessionUpdate: d("terminal_update") })), Xi = Zn.and(o({ sessionUpdate: d("terminal_output_chunk") })), Zi = ar.and(o({ sessionUpdate: d("plan_update") })), Qi = or.and(o({ sessionUpdate: d("plan_removed") })), $i = ur.and(o({ sessionUpdate: d("available_commands_update") })), ea = dr.and(o({ sessionUpdate: d("config_option_update") })), ta = fr.and(o({ sessionUpdate: d("session_info_update") })), na = mr.and(o({ sessionUpdate: d("usage_update") })), ra = _r.and(o({ sessionUpdate: d("compaction_update") })), ia = vr.and(o({ sessionUpdate: d("compaction_summary_chunk") })), aa = Vn.and(o({ state: d("running") })), oa = Wn.and(o({ state: d("idle") })), sa = Gn.and(o({ state: d("requires_action") }));
tr.and(o({ type: d("items") })), nr.and(o({ type: d("file") })), rr.and(o({ type: d("markdown") })), o({ planId: W }), sr.and(o({ type: d("text") })), Vr.and(o({ type: d("http") })), Hr.and(o({ type: d("acp") })), Ur.and(o({ type: d("stdio") })), Yr.and(o({ type: d("start") })), o({ type: d("id") }).and(o({ value: I })).and(o({
	sessionId: T,
	configId: F
})), o({ type: d("boolean") }).and(o({ value: g() })).and(o({
	sessionId: T,
	configId: F
})), o({ value: t() }).and(o({
	sessionId: T,
	configId: F
})), o({ outcome: d("cancelled") }), gi.and(o({ outcome: d("selected") })), bi.and(o({ action: d("accept") })), o({ action: d("decline") }), o({ action: d("cancel") });
var ca = {
	isText(e) {
		return G(e, "type") === "text" && Fi.safeParse(e).success;
	},
	isImage(e) {
		return G(e, "type") === "image" && Ii.safeParse(e).success;
	},
	isAudio(e) {
		return G(e, "type") === "audio" && Li.safeParse(e).success;
	},
	isResourceLink(e) {
		return G(e, "type") === "resource_link" && Ri.safeParse(e).success;
	},
	isResource(e) {
		return G(e, "type") === "resource" && zi.safeParse(e).success;
	},
	isCustom(e) {
		let t = G(e, "type");
		return typeof t == "string" && ![
			"audio",
			"image",
			"resource",
			"resource_link",
			"text"
		].includes(t);
	}
}, la = {
	isUserMessageChunk(e) {
		return G(e, "sessionUpdate") === "user_message_chunk" && Bi.safeParse(e).success;
	},
	isUserMessage(e) {
		return G(e, "sessionUpdate") === "user_message" && Vi.safeParse(e).success;
	},
	isAgentMessageChunk(e) {
		return G(e, "sessionUpdate") === "agent_message_chunk" && Hi.safeParse(e).success;
	},
	isAgentMessage(e) {
		return G(e, "sessionUpdate") === "agent_message" && Ui.safeParse(e).success;
	},
	isAgentThoughtChunk(e) {
		return G(e, "sessionUpdate") === "agent_thought_chunk" && Wi.safeParse(e).success;
	},
	isAgentThought(e) {
		return G(e, "sessionUpdate") === "agent_thought" && Gi.safeParse(e).success;
	},
	isStateUpdate(e) {
		return G(e, "sessionUpdate") === "state_update" && Ki.safeParse(e).success;
	},
	isToolCallContentChunk(e) {
		return G(e, "sessionUpdate") === "tool_call_content_chunk" && qi.safeParse(e).success;
	},
	isToolCallUpdate(e) {
		return G(e, "sessionUpdate") === "tool_call_update" && Ji.safeParse(e).success;
	},
	isTerminalUpdate(e) {
		return G(e, "sessionUpdate") === "terminal_update" && Yi.safeParse(e).success;
	},
	isTerminalOutputChunk(e) {
		return G(e, "sessionUpdate") === "terminal_output_chunk" && Xi.safeParse(e).success;
	},
	isPlanUpdate(e) {
		return G(e, "sessionUpdate") === "plan_update" && Zi.safeParse(e).success;
	},
	isPlanRemoved(e) {
		return G(e, "sessionUpdate") === "plan_removed" && Qi.safeParse(e).success;
	},
	isAvailableCommandsUpdate(e) {
		return G(e, "sessionUpdate") === "available_commands_update" && $i.safeParse(e).success;
	},
	isConfigOptionUpdate(e) {
		return G(e, "sessionUpdate") === "config_option_update" && ea.safeParse(e).success;
	},
	isSessionInfoUpdate(e) {
		return G(e, "sessionUpdate") === "session_info_update" && ta.safeParse(e).success;
	},
	isUsageUpdate(e) {
		return G(e, "sessionUpdate") === "usage_update" && na.safeParse(e).success;
	},
	isCompactionUpdate(e) {
		return G(e, "sessionUpdate") === "compaction_update" && ra.safeParse(e).success;
	},
	isCompactionSummaryChunk(e) {
		return G(e, "sessionUpdate") === "compaction_summary_chunk" && ia.safeParse(e).success;
	},
	isCustom(e) {
		let t = G(e, "sessionUpdate");
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
}, ua = {
	isRunning(e) {
		return G(e, "state") === "running" && aa.safeParse(e).success;
	},
	isIdle(e) {
		return G(e, "state") === "idle" && oa.safeParse(e).success;
	},
	isRequiresAction(e) {
		return G(e, "state") === "requires_action" && sa.safeParse(e).success;
	},
	isCustom(e) {
		let t = G(e, "state");
		return typeof t == "string" && ![
			"idle",
			"requires_action",
			"running"
		].includes(t);
	}
};
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/v2/acp.js
function K(e) {
	return e ?? {};
}
var da = /* @__PURE__ */ new Set([
	...Object.values(x),
	...Object.values(S),
	...Object.values(C)
]);
function q(e, t, n, r = !1) {
	if (!(Object.hasOwn(t, e) || r && e === C.cancel_request) && da.has(e)) throw TypeError(`ACP v2 ${n} method '${e}' is not valid in this direction`);
}
function fa(e, t) {
	if (da.has(e)) throw TypeError(`Cannot replace the built-in ACP v2 ${t} parser for '${e}'`);
}
function pa(e, t, n) {
	for (let r of e) q(r.method, r.kind === "request" ? t : n, r.kind, r.kind === "notification");
}
function ma(e) {
	let t = Pr.parse(e);
	if (t.protocolVersion !== 2) throw v.invalidParams({
		expectedProtocolVersion: 2,
		receivedProtocolVersion: t.protocolVersion
	}, "The v2 API only supports protocol version 2");
	return structuredClone(t);
}
function ha(e) {
	return ma({
		...typeof e == "object" && e && !Array.isArray(e) ? e : {},
		protocolVersion: 2
	});
}
function ga(e) {
	let t = Qt.parse(e);
	if (t.protocolVersion !== 2) throw v.invalidRequest({
		expectedProtocolVersion: 2,
		receivedProtocolVersion: t.protocolVersion
	}, "The v2 API only supports protocol version 2");
	return structuredClone(t);
}
function _a(e) {
	return structuredClone(e);
}
function va() {
	let e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var ya = class {
	phase = "uninitialized";
	request;
	barrier = va();
	constructor() {
		this.barrier.promise.catch(() => {});
	}
	get status() {
		return this.phase;
	}
	get initialized() {
		return this.barrier.promise.then(_a);
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
		return this.phase === "initialized" ? Promise.resolve() : this.phase === "initializing" ? this.barrier.promise.then(() => {}) : Promise.reject(xa(e));
	}
}, ba = /* @__PURE__ */ new WeakMap();
function J(e) {
	let t = ba.get(e);
	return t || (t = new ya(), ba.set(e, t), e.signal.aborted ? t.fail(e.signal.reason) : e.signal.addEventListener("abort", () => t?.fail(e.signal.reason), { once: !0 })), t;
}
function xa(e) {
	return v.invalidRequest(`ACP v2 connection must be initialized before '${e}'`);
}
async function Sa(e, t) {
	let n = xa(e.method);
	return t.fail(n), Ca(e, n);
}
async function Ca(e, t) {
	return e.kind === "request" && await e.responder.respondWithError(t), y.yes();
}
function wa() {
	return {
		async handleMessage(e, t) {
			let n = J(t);
			return e.kind === "notification" && e.method === C.cancel_request ? n.status === "initializing" || n.status === "initialized" ? y.yes() : Sa(e, n) : n.status === "initialized" ? y.no(e) : n.status === "initializing" ? (await n.waitUntilInitialized(e.method), y.no(e)) : Sa(e, n);
		},
		describe: () => "client-initialization"
	};
}
function Ta(e, t) {
	return Ha(e.response, t);
}
function Ea(e, t, n) {
	return e.map((e) => {
		if (e.kind !== "request") return e;
		let r = t[e.method], i = e.mapResponse;
		return {
			...e,
			mapResponse: r ? (t) => {
				let a = Ta(r, t);
				return n && e.method === x.initialize && n(a), i ? i(a) : a;
			} : i
		};
	});
}
function Da(e) {
	return typeof e == "object" && !!e && "readable" in e && "writable" in e;
}
function Oa() {
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
		initialize: x.initialize,
		auth: {
			login: x.auth_login,
			logout: x.auth_logout
		},
		providers: {
			list: x.providers_list,
			set: x.providers_set,
			disable: x.providers_disable
		},
		session: {
			new: x.session_new,
			list: x.session_list,
			delete: x.session_delete,
			fork: x.session_fork,
			resume: x.session_resume,
			close: x.session_close,
			setConfigOption: x.session_set_config_option,
			prompt: x.session_prompt,
			cancel: x.session_cancel
		},
		mcp: { message: x.mcp_message },
		nes: {
			start: x.nes_start,
			suggest: x.nes_suggest,
			accept: x.nes_accept,
			reject: x.nes_reject,
			close: x.nes_close
		},
		document: {
			didOpen: x.document_did_open,
			didChange: x.document_did_change,
			didClose: x.document_did_close,
			didSave: x.document_did_save,
			didFocus: x.document_did_focus
		}
	},
	client: {
		session: {
			requestPermission: S.session_request_permission,
			update: S.session_update
		},
		mcp: {
			connect: S.mcp_connect,
			message: S.mcp_message,
			disconnect: S.mcp_disconnect
		},
		elicitation: {
			create: S.elicitation_create,
			complete: S.elicitation_complete
		}
	},
	protocol: { cancelRequest: C.cancel_request }
}, ka = Symbol("startActiveSession"), Aa = class {
	cx;
	currentRequestId;
	constructor(e, t) {
		this.cx = e, this.currentRequestId = t;
	}
	get initialized() {
		return J(this.cx).initialized;
	}
	get initializationLifecycle() {
		return J(this.cx);
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
}, ja = class e extends Aa {
	constructor(e, t) {
		super(e, t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	request(e, t, n) {
		q(e, $, "request");
		let r = $[e];
		return this.initializationLifecycle.waitUntilInitialized(e).then(() => this.sendRequest(e, t, r ? (e) => Ta(r, e) : void 0, n));
	}
	notify(e, t) {
		return q(e, Za, "notification", !0), this.initializationLifecycle.waitUntilInitialized(e).then(() => this.sendNotification(e, t));
	}
	batch(e) {
		return pa(e, $, Za), this.initializationLifecycle.waitUntilInitialized("batch").then(() => this.sendBatch(Ea(e, $)));
	}
}, Ma = class e extends Aa {
	closeOnInitializationFailure;
	constructor(e, t, n) {
		super(e, t), this.closeOnInitializationFailure = n;
	}
	static create(t, n, r) {
		return new e(t, n, r);
	}
	[ka](e, t) {
		return this.request(x.session_new, e, t).then((e) => this.attachSession(e));
	}
	buildSession(e) {
		return typeof e == "string" ? Ba.create(this, {
			cwd: e,
			mcpServers: []
		}) : Ba.create(this, e);
	}
	attachSession(e) {
		let t = new Ra(), n = /* @__PURE__ */ new Set(), r = {
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
		let o = no(this.connectionContext).attach(e, r), s = new te(() => {
			i.removeEventListener("abort", a);
		});
		return Va.create(this, e, r, [o, s]);
	}
	request(e, t, n) {
		q(e, Q, "request");
		let r = Q[e], i = this.initializationLifecycle;
		if (e === x.initialize) {
			let a = ha(t);
			i.begin(a);
			let o;
			try {
				o = this.sendRequest(e, a, (e) => {
					let t = Ta(r, e);
					return i.complete(t), t;
				}, n);
			} catch (e) {
				throw i.fail(e), this.closeOnInitializationFailure?.(e), e;
			}
			return o.catch((e) => {
				i.status !== "initialized" && (i.fail(e), this.closeOnInitializationFailure?.(e));
			}), o;
		}
		return i.waitUntilInitialized(e).then(() => this.sendRequest(e, t, r ? (e) => Ta(r, e) : void 0, n));
	}
	notify(e, t) {
		return q(e, Xa, "notification", !0), this.initializationLifecycle.waitUntilInitialized(e).then(() => this.sendNotification(e, t));
	}
	batch(e) {
		pa(e, Q, Xa);
		let t = e.filter((e) => e.kind === "request" && e.method === x.initialize);
		if (t.length > 0) {
			if (e.length !== 1 || t.length !== 1) return Promise.reject(v.invalidRequest("ACP v2 initialize must be the only entry in its batch"));
			let n = this.initializationLifecycle, r = ha(t[0].params);
			n.begin(r);
			let i = [{
				...t[0],
				params: r
			}], a;
			try {
				a = this.sendBatch(Ea(i, Q, (e) => n.complete(e)));
			} catch (e) {
				throw n.fail(e), this.closeOnInitializationFailure?.(e), e;
			}
			return a.catch((e) => {
				n.status !== "initialized" && (n.fail(e), this.closeOnInitializationFailure?.(e));
			}), a;
		}
		return this.initializationLifecycle.waitUntilInitialized("batch").then(() => this.sendBatch(Ea(e, Q)));
	}
}, Na = class {
	connection;
	constructor(e) {
		this.connection = e;
	}
	get initialized() {
		return J(this.connection.getContext()).initialized;
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
}, Pa = class extends Na {
	connectHandlers;
	client;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.client = ja.create(e.getContext());
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, ro(this, this.connectHandlers));
	}
}, Fa = class extends Na {
	connectHandlers;
	agent;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.agent = Ma.create(e.getContext(), void 0, (t) => e.close(t));
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, ro(this, this.connectHandlers));
	}
};
function Ia(e, t = []) {
	return new Pa(e, t);
}
function La(e, t = []) {
	return new Fa(e, t);
}
var Ra = class {
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
function za(e) {
	return structuredClone(e);
}
var Ba = class e {
	cx;
	request;
	constructor(e, t) {
		this.cx = e, this.request = za(t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	toRequest() {
		return za(this.request);
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
		return this.cx[ka](this.toRequest(), e);
	}
	async withSession(e) {
		let t = await this.start();
		try {
			return await e(t);
		} finally {
			t.dispose();
		}
	}
}, Va = class e {
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
		let r = this.cx.request(x.session_prompt, {
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
			if (a.kind === "stop") return n.flatMap((e) => r.get(e) ?? []).filter(ca.isText).map((e) => e.text).join("");
			let { update: o } = a;
			la.isAgentMessage(o) ? (i(o.messageId), o.content !== void 0 && r.set(o.messageId, o.content ?? [])) : la.isAgentMessageChunk(o) && i(o.messageId).push(o.content);
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
function Ha(e, t) {
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
function Ua(e, t, n, r, i) {
	e.onReceiveRequest(t.method, (e) => Ha(t.params, e), async (e, a, o) => {
		try {
			let s = await r(n(e, o, a.signal, a.id)), c = t.serializeResponse ? t.serializeResponse(s) : s;
			await a.respond(c), i?.afterResponse(e, c, o);
		} catch (e) {
			throw i?.onError(o, e), e;
		}
	});
}
function Wa(e, t, n, r) {
	e.onReceiveNotification(t.method, (e) => Ha(t.params, e), (e, t) => r(n(e, t, t.signal)));
}
function Ga(e) {
	let t = Object.create(null);
	for (let n of Object.values(e)) t[n.method] = n;
	return t;
}
var Ka = {
	initialize: X(x.initialize, ma, ga, ga),
	loginAuth: X(x.auth_login, Fr, $t, K),
	unstable_listProviders: X(x.providers_list, Ir, an),
	unstable_setProvider: X(x.providers_set, Lr, on, K),
	unstable_disableProvider: X(x.providers_disable, Rr, sn, K),
	newSession: X(x.session_new, Gr, gn),
	setSessionConfigOption: X(x.session_set_config_option, $r, wn),
	prompt: X(x.session_prompt, ei, Tn, K),
	unstable_messageMcp: X(x.mcp_message, dt, V),
	listSessions: X(x.session_list, Kr, yn),
	deleteSession: X(x.session_delete, qr, bn, K),
	unstable_forkSession: X(x.session_fork, Jr, xn),
	resumeSession: X(x.session_resume, Zr, Sn),
	closeSession: X(x.session_close, Qr, Cn, K),
	logoutAuth: X(x.auth_logout, zr, cn, K),
	unstable_startNes: X(x.nes_start, ri, En),
	unstable_suggestNes: X(x.nes_suggest, mi, Nn),
	unstable_closeNes: X(x.nes_close, hi, Pn, K)
}, qa = {
	cancelSession: Z(x.session_cancel, wi),
	unstable_messageMcp: Z(x.mcp_message, Sr),
	unstable_didOpenDocument: Z(x.document_did_open, Ti),
	unstable_didChangeDocument: Z(x.document_did_change, Di),
	unstable_didCloseDocument: Z(x.document_did_close, Oi),
	unstable_didSaveDocument: Z(x.document_did_save, ki),
	unstable_didFocusDocument: Z(x.document_did_focus, Ai),
	unstable_acceptNes: Z(x.nes_accept, ji),
	unstable_rejectNes: Z(x.nes_reject, Ni)
}, Ja = {
	requestPermission: X(S.session_request_permission, He, vi),
	unstable_connectMcp: X(S.mcp_connect, lt, Si),
	unstable_messageMcp: X(S.mcp_message, dt, V),
	unstable_disconnectMcp: X(S.mcp_disconnect, ft, Ci, K),
	createElicitation: X(S.elicitation_create, st, xi)
}, Ya = {
	sessionUpdate: Z(S.session_update, br),
	unstable_messageMcp: Z(S.mcp_message, Sr),
	completeElicitation: Z(S.elicitation_complete, xr)
}, Q = Ga(Ka), Xa = Ga(qa), $ = Ga(Ja), Za = Ga(Ya);
function Qa(e, t, n, r) {
	return {
		params: e,
		requestId: r,
		signal: n,
		agent: t
	};
}
function $a(e, t, n) {
	return {
		params: e,
		signal: n,
		agent: t
	};
}
var eo = class {
	activeSessions = /* @__PURE__ */ new Map();
	handleMessage(e) {
		if (e.kind !== "notification" || e.method !== S.session_update) return y.no(e);
		let t = br.parse(e.params), { update: n } = t, r = la.isStateUpdate(n) && ua.isIdle(n), i = this.activeSessions.get(t.sessionId);
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
		return y.no(e);
	}
	attach(e, t) {
		let n = this.activeSessions.get(e.sessionId) ?? /* @__PURE__ */ new Set();
		return n.add(t), this.activeSessions.set(e.sessionId, n), new te(() => {
			n.delete(t), n.size === 0 && this.activeSessions.delete(e.sessionId);
		});
	}
}, to = /* @__PURE__ */ new WeakMap();
function no(e) {
	let t = to.get(e);
	return t || (t = new eo(), to.set(e, t)), t;
}
function ro(e, t) {
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
var io = Symbol("appBuilder"), ao = Symbol("runAgentConnectHandlers"), oo = Symbol("runClientConnectHandlers");
function so(e, t) {
	e.closed.then(async () => {
		J(e.getContext()).status === "initialized" && await t.initialized.catch(() => {}), t.close(e.signal.reason);
	});
}
function co(e) {
	return new lo(e);
}
var lo = class {
	builder = fe.builder();
	connectHandlers = [];
	constructor(e = {}) {
		e.name && this.builder.name(e.name), this.builder.withHandler(wa()), this.builder.withHandler({
			handleMessage: (e, t) => no(t).handleMessage(e),
			describe: () => "client-session-update-router"
		});
	}
	[io]() {
		return this.builder;
	}
	[oo](e) {
		ro(e, this.connectHandlers);
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
		if (n) return fa(e, "request"), this.request({
			method: e,
			params: t
		}, n);
		let r = $[e];
		if (!r) throw Error(`Unknown ACP request method '${e}'. Pass a params parser for custom methods.`);
		return this.request(r, t);
	}
	onNotification(e, t, n) {
		if (n) return fa(e, "notification"), this.notification({
			method: e,
			params: t
		}, n);
		let r = Za[e];
		if (!r) throw Error(`Unknown ACP notification method '${e}'. Pass a params parser for custom methods.`);
		return this.notification(r, t);
	}
	request(e, t) {
		return Ua(this.builder, e, (e, t, n, r) => Qa(e, Ma.create(t, r), n, r), t), this;
	}
	notification(e, t) {
		return Wa(this.builder, e, (e, t, n) => $a(e, Ma.create(t), n), t), this;
	}
	connectConnection(e) {
		if (Da(e)) {
			let t = this.openStreamConnection(e);
			return this[oo](t.connection), t;
		}
		let [t, n] = Oa(), r = e[io]().connect(n), i = Ia(r), a = this.openStreamConnection(t);
		so(a.rawConnection, i), so(r, a.connection);
		try {
			e[ao](i), this[oo](a.connection);
		} catch (e) {
			throw i.close(e), a.connection.close(e), e;
		}
		return a;
	}
	openStreamConnection(e) {
		let t = this.builder.connect(e);
		return {
			rawConnection: t,
			connection: La(t, this.connectHandlers)
		};
	}
};
//#endregion
//#region src/core/protocol/v2.ts
async function uo(e) {
	let { sink: t } = e, n, r = co({ name: e.clientInfo.name }).onRequest(Y.client.session.requestPermission, async ({ params: e }) => {
		let n = e, r = await t.onPermission(e.sessionId, ho(n), n);
		return ue(r);
	}).onRequest(Y.client.elicitation.create, async ({ params: e }) => {
		let n = e, r = await t.onElicitation("sessionId" in e && typeof e.sessionId == "string" ? e.sessionId : void 0, ee(n), n);
		return ae(r);
	}).onNotification(Y.client.session.update, ({ params: e }) => {
		t.onProtocol(Y.client.session.update, e), t.onUpdate(e.sessionId, e.update), n?.handleUpdate(e.sessionId, e.update);
	}).onNotification(Y.client.elicitation.complete, ({ params: e }) => {
		t.onProtocol(Y.client.elicitation.complete, e), t.onElicitationComplete(e.elicitationId);
	}).connect(e.stream), i = !1;
	r.closed.then(() => {
		n?.handleClose(), i || t.onDisconnect();
	});
	let a;
	try {
		a = await r.agent.request(Y.agent.initialize, {
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
		});
	} catch (e) {
		throw r.close(e), new h("INITIALIZE_REJECTED", "ACP v2 initialization failed", {
			cause: e,
			protocol: 2,
			phase: "initialize",
			retryable: !0
		});
	}
	if (a.protocolVersion !== 2) throw r.close(), new h("PROTOCOL_VERSION_MISMATCH", `Requested ACP v2 but agent selected v${a.protocolVersion}`, {
		protocol: 2,
		phase: "initialize"
	});
	if (a.capabilities?.session == null) throw r.close(), new h("CAPABILITY_REQUIRED", "The ACP v2 agent does not advertise the session surface", {
		protocol: 2,
		phase: "initialize"
	});
	let o = a.capabilities.session;
	return n = new fo(r, {
		protocolVersion: 2,
		agentName: a.info.title ?? a.info.name,
		authMethods: re(a.authMethods),
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
		i = !0;
	}), n;
}
var fo = class {
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
		le(e, this.initialized, 2, "session/new");
		let t = await de(() => this.connection.agent.request(Y.agent.session.new, po(e)), 2, "session/new");
		return {
			sessionId: t.sessionId,
			configOptions: ce(t.configOptions)
		};
	}
	async openSession(e, t, n) {
		le(t, this.initialized, 2, "session/open");
		let r = await de(() => this.connection.agent.request(Y.agent.session.resume, {
			...po(t),
			sessionId: e,
			...n === "all" ? { replayFrom: { type: "start" } } : {}
		}), 2, "session/open");
		return {
			sessionId: e,
			configOptions: ce(r.configOptions)
		};
	}
	async listSessions(e, t) {
		let n = await this.connection.agent.request(Y.agent.session.list, {
			cwd: e,
			...t ? { cursor: t } : {}
		});
		return ie(n);
	}
	async deleteSession(e) {
		if (!this.initialized.capabilities.deleteSession) throw new h("CAPABILITY_REQUIRED", "The agent does not support session/delete", { protocol: 2 });
		await this.connection.agent.request(Y.agent.session.delete, { sessionId: e });
	}
	async closeSession(e) {
		await this.connection.agent.request(Y.agent.session.close, { sessionId: e });
	}
	promptReady(e) {
		return !this.#t.has(e);
	}
	async prompt(e, t, n) {
		if (this.#e.has(e)) throw new h("SESSION_BUSY", `Session '${e}' already has a foreground turn`, { protocol: 2 });
		let r, i, a = new Promise((e, t) => {
			r = e, i = t;
		}), o = {
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
			throw this.#e.get(e) === o && this.#e.delete(e), t;
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
		return ce(r.configOptions);
	}
	async authenticate(e) {
		if (e.type === "terminal") {
			if (!this.host?.terminalAuth) throw new h("CAPABILITY_REQUIRED", "Terminal authentication needs a host handler", { protocol: 2 });
			await this.host.terminalAuth(e);
			return;
		}
		await this.connection.agent.request(Y.agent.auth.login, { methodId: e.id });
	}
	async logout() {
		await this.connection.agent.request(Y.agent.auth.logout, {});
	}
	handleUpdate(e, t) {
		if (!ne(t) || t.sessionUpdate !== "state_update" || t.state !== "idle" || this.#t.delete(e) || !this.#e.has(e)) return;
		let n = this.#e.get(e);
		n && (this.#e.delete(e), n.resolve(oe(t.stopReason) ?? "end_turn"));
	}
	handleClose() {
		for (let e of this.#e.values()) e.reject(new h("TURN_INTERRUPTED", "Connection closed before the turn completed", {
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
function po(e) {
	return {
		cwd: e.cwd,
		...e.additionalDirectories?.length ? { additionalDirectories: [...e.additionalDirectories] } : {},
		...e.mcpServers?.length ? { mcpServers: e.mcpServers.map(mo) } : {}
	};
}
function mo(e) {
	if (e.type === "sse") throw new h("INVALID_CONFIGURATION", "SSE MCP servers are not part of ACP v2", { protocol: 2 });
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
function ho(e) {
	let t = ne(e) ? e : {}, n = oe(t.description);
	return {
		type: "permission",
		title: oe(t.title) ?? "Permission required",
		...n ? { description: n } : {},
		options: se(t.options)
	};
}
//#endregion
export { uo as connectV2 };

//# sourceMappingURL=v2.js.map