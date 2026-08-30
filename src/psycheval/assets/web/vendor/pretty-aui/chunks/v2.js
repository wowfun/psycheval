globalThis.__zod_globalConfig ??= {}, globalThis.__zod_globalConfig.jitless = !0;
import { A as e, B as t, D as n, E as r, F as i, H as a, I as o, K as s, L as c, M as l, N as u, O as d, P as f, R as p, T as m, V as h, a as ee, b as te, d as ne, f as re, h as ie, i as ae, j as g, k as _, l as oe, o as se, p as ce, r as le, s as ue, t as de, v as fe, x as v, y, z as b } from "./types.js";
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
}, C = { cancel_request: "$/cancel_request" }, w = b([i(), p()]).nullable(), T = p(), E = p(), pe = b([
	f("read"),
	f("edit"),
	f("delete"),
	f("move"),
	f("search"),
	f("execute"),
	f("think"),
	f("fetch"),
	f("switch_mode"),
	f("other"),
	p()
]), me = b([
	f("pending"),
	f("in_progress"),
	f("completed"),
	f("failed"),
	f("cancelled"),
	p()
]), he = b([
	f("assistant"),
	f("user"),
	p()
]), D = o({
	audience: m(_(he).nullish(), () => void 0),
	lastModified: m(a({ offset: !0 }).nullish(), () => void 0),
	priority: m(i().gte(0).lte(1).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ge = o({
	text: p(),
	annotations: m(D.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), O = p(), _e = o({
	data: p(),
	mimeType: O,
	uri: m(h().nullish(), () => void 0),
	annotations: m(D.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ve = o({
	data: p(),
	mimeType: O,
	annotations: m(D.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ye = b([
	f("light"),
	f("dark"),
	p()
]), be = o({
	src: h(),
	mimeType: m(O.nullish(), () => void 0),
	sizes: m(_(p()).nullish(), () => void 0),
	theme: m(ye.nullish(), () => void 0)
}), xe = o({
	name: p(),
	uri: h(),
	title: m(p().nullish(), () => void 0),
	description: m(p().nullish(), () => void 0),
	icons: m(_(be).nullish(), () => void 0),
	mimeType: m(O.nullish(), () => void 0),
	size: m(i().nullish(), () => void 0),
	annotations: m(D.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Se = o({
	text: p(),
	uri: h(),
	mimeType: m(O.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ce = o({
	blob: p(),
	uri: h(),
	mimeType: m(O.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), we = b([Se, Ce]), Te = o({
	resource: we,
	annotations: m(D.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), k = n(b([
	ge.and(o({ type: f("text") })),
	_e.and(o({ type: f("image") })),
	ve.and(o({ type: f("audio") })),
	xe.and(o({ type: f("resource_link") })),
	Te.and(o({ type: f("resource") })),
	r(o({ type: p() }), "type", [
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
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), De = b([
	f("text"),
	f("binary"),
	f("directory"),
	f("symlink"),
	p()
]), A = p(), j = o({ path: A }), M = o({
	oldPath: A,
	path: A
}), Oe = n(u(b([
	j.and(o({ operation: f("add") })),
	j.and(o({ operation: f("delete") })),
	j.and(o({ operation: f("modify") })),
	M.and(o({ operation: f("move") })),
	M.and(o({ operation: f("copy") })),
	r(o({ operation: p() }), "operation", [
		"add",
		"copy",
		"delete",
		"modify",
		"move"
	])
]), o({
	fileType: m(De.nullish(), () => void 0),
	mimeType: m(O.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
})), "operation", [
	"add",
	"copy",
	"delete",
	"modify",
	"move"
]), ke = b([f("git_patch"), p()]), Ae = o({
	format: ke,
	text: p()
}), je = o({
	changes: _(Oe),
	patch: m(Ae.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), N = p(), Me = o({
	terminalId: N,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ne = n(b([
	Ee.and(o({ type: f("content") })),
	je.and(o({ type: f("diff") })),
	Me.and(o({ type: f("terminal") })),
	r(o({ type: p() }), "type", [
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
	line: m(l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Fe = o({
	toolCallId: E,
	name: m(p().nullish(), () => void 0),
	title: m(p().nullish(), () => void 0),
	kind: m(pe.nullish(), () => void 0),
	status: m(me.nullish(), () => void 0),
	content: m(_(Ne).nullish(), () => void 0),
	locations: m(_(Pe).nullish(), () => void 0),
	rawInput: m(t().optional(), () => void 0),
	rawOutput: m(t().optional(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ie = o({ toolCall: Fe }), Le = o({
	command: p(),
	cwd: A,
	toolCallId: m(E.nullish(), () => void 0),
	terminalId: m(N.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Re = n(b([
	Ie.and(o({ type: f("tool_call") })),
	Le.and(o({ type: f("command") })),
	r(o({ type: p() }), "type", ["command", "tool_call"])
]), "type", ["command", "tool_call"]), ze = p(), Be = b([
	f("allow_once"),
	f("allow_always"),
	f("reject_once"),
	f("reject_always"),
	p()
]), Ve = o({
	optionId: ze,
	name: p(),
	kind: Be,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), He = o({
	sessionId: T,
	title: p(),
	description: m(p().nullish(), () => void 0),
	subject: Re.nullish(),
	options: e(Ve).min(1),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ue = o({
	sessionId: T,
	toolCallId: m(E.nullish(), () => void 0)
}), We = o({ requestId: w }), Ge = f("object"), Ke = b([
	f("email"),
	f("uri"),
	f("date"),
	f("date-time"),
	p()
]), qe = o({
	const: p(),
	title: p(),
	description: m(p().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Je = o({
	title: m(p().nullish(), () => void 0),
	description: m(p().nullish(), () => void 0),
	minLength: l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	maxLength: l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	pattern: p().nullish(),
	format: Ke.nullish(),
	default: m(p().nullish(), () => void 0),
	enum: e(p()).min(1).nullish(),
	oneOf: e(qe).min(1).nullish(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ye = o({
	title: m(p().nullish(), () => void 0),
	description: m(p().nullish(), () => void 0),
	minimum: i().nullish(),
	maximum: i().nullish(),
	default: m(i().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Xe = o({
	title: m(p().nullish(), () => void 0),
	description: m(p().nullish(), () => void 0),
	minimum: i().nullish(),
	maximum: i().nullish(),
	default: m(i().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ze = o({
	title: m(p().nullish(), () => void 0),
	description: m(p().nullish(), () => void 0),
	default: m(g().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Qe = o({
	enum: e(p()).min(1),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), $e = o({
	anyOf: e(qe).min(1),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), et = n(b([
	Qe.and(o({ type: f("string") })),
	r(o({ type: p() }), "type", ["string"]),
	$e
]), "type", ["string"]), tt = o({
	title: m(p().nullish(), () => void 0),
	description: m(p().nullish(), () => void 0),
	minItems: i().nullish(),
	maxItems: i().nullish(),
	items: et,
	default: m(_(p()).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), nt = n(b([
	Je.and(o({ type: f("string") })),
	Ye.and(o({ type: f("number") })),
	Xe.and(o({ type: f("integer") })),
	Ze.and(o({ type: f("boolean") })),
	tt.and(o({ type: f("array") })),
	r(o({ type: p() }), "type", [
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
	type: m(Ge.optional().default("object"), () => "object"),
	title: m(p().nullish(), () => void 0),
	properties: c(p(), nt).optional().default({}),
	required: e(p()).nullish(),
	description: m(p().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), it = u(b([Ue, We]), o({ requestedSchema: rt })), at = p(), ot = u(b([Ue, We]), o({
	elicitationId: at,
	url: h()
})), st = n(u(b([
	it.and(o({ mode: f("form") })),
	ot.and(o({ mode: f("url") })),
	r(u(b([Ue, We]), o({ mode: p() })), "mode", ["form", "url"])
]), o({
	message: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
})), "mode", ["form", "url"]), ct = p(), lt = o({
	serverId: ct,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ut = p(), dt = o({
	connectionId: ut,
	method: p(),
	params: c(p(), t()).nullish(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ft = o({
	connectionId: ut,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), pt = t();
o({
	id: w,
	method: p(),
	params: b([
		He,
		st,
		lt,
		dt,
		ft,
		pt
	]).nullish()
});
var mt = l().gte(0).lte(65535), ht = o({
	name: p(),
	title: m(p().nullish(), () => void 0),
	version: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), gt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), _t = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), vt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), yt = o({
	image: m(gt.nullish(), () => void 0),
	audio: m(_t.nullish(), () => void 0),
	embeddedContext: m(vt.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), bt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), xt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), St = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Ct = o({
	stdio: m(bt.nullish(), () => void 0),
	http: m(xt.nullish(), () => void 0),
	acp: m(St.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), wt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Tt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Et = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Dt = o({
	prompt: m(yt.nullish(), () => void 0),
	mcp: m(Ct.nullish(), () => void 0),
	delete: m(wt.nullish(), () => void 0),
	additionalDirectories: m(Tt.nullish(), () => void 0),
	fork: m(Et.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ot = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), kt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), At = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), jt = b([f("full"), f("incremental")]), Mt = o({
	syncKind: jt,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Nt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Pt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Ft = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), It = o({
	didOpen: m(At.nullish(), () => void 0),
	didChange: m(Mt.nullish(), () => void 0),
	didClose: m(Nt.nullish(), () => void 0),
	didSave: m(Pt.nullish(), () => void 0),
	didFocus: m(Ft.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Lt = o({
	document: m(It.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Rt = o({
	maxCount: m(l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), zt = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Bt = o({
	maxCount: m(l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Vt = o({
	maxCount: m(l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ht = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Ut = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Wt = o({
	recentFiles: m(Rt.nullish(), () => void 0),
	relatedSnippets: m(zt.nullish(), () => void 0),
	editHistory: m(Bt.nullish(), () => void 0),
	userActions: m(Vt.nullish(), () => void 0),
	openFiles: m(Ht.nullish(), () => void 0),
	diagnostics: m(Ut.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Gt = o({
	events: m(Lt.nullish(), () => void 0),
	context: m(Wt.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Kt = b([
	f("utf-16"),
	f("utf-32"),
	f("utf-8")
]), qt = o({
	session: m(Dt.nullish(), () => void 0),
	auth: m(Ot.nullish(), () => void 0),
	providers: m(kt.nullish(), () => void 0),
	nes: m(Gt.nullish(), () => void 0),
	positionEncoding: m(Kt.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), P = p(), Jt = o({
	name: p(),
	value: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Yt = o({
	methodId: P,
	name: p(),
	description: m(p().nullish(), () => void 0),
	args: m(_(p()).optional(), () => []),
	env: m(_(Jt).optional(), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Xt = o({
	methodId: P,
	name: p(),
	description: m(p().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Zt = n(b([
	Yt.and(o({ type: f("terminal") })),
	Xt.and(o({ type: f("agent") })),
	r(o({
		type: p(),
		methodId: P,
		name: p(),
		description: m(p().nullish(), () => void 0),
		_meta: m(c(p(), t()).nullish(), () => void 0)
	}), "type", ["agent", "terminal"])
]), "type", ["agent", "terminal"]), Qt = o({
	protocolVersion: mt,
	info: ht,
	capabilities: m(qt.optional().default({}), () => ({})),
	authMethods: m(_(Zt).optional(), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), $t = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), en = p(), tn = b([
	f("anthropic"),
	f("openai"),
	f("azure"),
	f("vertex"),
	f("bedrock"),
	p()
]), nn = o({
	apiType: tn,
	baseUrl: h(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), rn = o({
	providerId: en,
	supported: d(_(tn), () => []),
	required: g(),
	current: nn.nullish(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), an = o({
	providers: e(rn),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), on = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), sn = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), cn = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), F = p(), ln = b([
	f("mode"),
	f("model"),
	f("model_config"),
	f("thought_level"),
	p()
]), I = p(), un = o({
	value: I,
	name: p(),
	description: m(p().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), dn = p(), fn = o({
	groupId: dn,
	name: p(),
	options: d(_(un), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), pn = b([e(un), e(fn)]), mn = o({
	currentValue: I,
	options: pn
}), hn = o({ currentValue: g() }), L = n(u(b([
	mn.and(o({ type: f("select") })),
	hn.and(o({ type: f("boolean") })),
	r(o({ type: p() }), "type", ["boolean", "select"])
]), o({
	configId: F,
	name: p(),
	description: m(p().nullish(), () => void 0),
	category: m(ln.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
})), "type", ["boolean", "select"]), gn = o({
	sessionId: T,
	configOptions: m(_(L).optional(), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), _n = o({
	sessionId: T,
	cwd: A,
	additionalDirectories: m(_(A).optional(), () => []),
	title: m(p().nullish(), () => void 0),
	updatedAt: m(a({ offset: !0 }).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), vn = p(), yn = o({
	sessions: d(_(_n), () => []),
	nextCursor: m(vn.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), bn = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), xn = o({
	sessionId: T,
	configOptions: m(_(L).optional(), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Sn = o({
	configOptions: m(_(L).optional(), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Cn = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), wn = o({
	configOptions: d(_(L), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Tn = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), En = o({
	sessionId: T,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), R = p(), z = o({
	line: l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	character: l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), B = o({
	start: z,
	end: z,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Dn = o({
	range: B,
	newText: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), On = o({
	suggestionId: R,
	uri: h(),
	edits: e(Dn).min(1),
	cursorPosition: m(z.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), kn = o({
	suggestionId: R,
	uri: h(),
	position: z,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), An = o({
	suggestionId: R,
	uri: h(),
	position: z,
	newName: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), jn = o({
	suggestionId: R,
	uri: h(),
	search: p(),
	replace: p(),
	isRegex: g().nullish(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Mn = n(b([
	On.and(o({ kind: f("edit") })),
	kn.and(o({ kind: f("jump") })),
	An.and(o({ kind: f("rename") })),
	jn.and(o({ kind: f("searchAndReplace") })),
	r(o({
		kind: p(),
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
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Pn = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Fn = t(), V = t(), In = b([
	f(-32700),
	f(-32600),
	f(-32601),
	f(-32602),
	f(-32603),
	f(-32800),
	f(-32e3),
	f(-32002),
	l().min(-2147483648, { error: "Invalid value: Expected int32 to be >= -2147483648" }).max(2147483647, { error: "Invalid value: Expected int32 to be <= 2147483647" })
]), Ln = o({
	code: In,
	message: p(),
	data: m(t().optional(), () => void 0)
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
var H = p(), U = o({
	messageId: H,
	content: k,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Rn = o({
	messageId: H,
	content: m(_(k).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), zn = o({
	messageId: H,
	content: m(_(k).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Bn = o({
	messageId: H,
	content: m(_(k).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Vn = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Hn = b([
	f("end_turn"),
	f("max_tokens"),
	f("max_turn_requests"),
	f("refusal"),
	f("cancelled"),
	p()
]), Un = o({
	totalTokens: i(),
	inputTokens: i(),
	outputTokens: i(),
	thoughtTokens: m(i().nullish(), () => void 0),
	cachedReadTokens: m(i().nullish(), () => void 0),
	cachedWriteTokens: m(i().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Wn = o({
	stopReason: m(Hn.nullish(), () => void 0),
	usage: m(Un.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Gn = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Kn = n(b([
	Vn.and(o({ state: f("running") })),
	Wn.and(o({ state: f("idle") })),
	Gn.and(o({ state: f("requires_action") })),
	r(o({ state: p() }), "state", [
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
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Jn = o({
	data: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Yn = o({
	exitCode: m(l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: m(p().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Xn = o({
	terminalId: N,
	command: m(p().nullish(), () => void 0),
	cwd: m(A.nullish(), () => void 0),
	output: m(Jn.nullish(), () => void 0),
	exitStatus: m(Yn.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Zn = o({
	terminalId: N,
	data: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), W = p(), Qn = b([
	f("high"),
	f("medium"),
	f("low"),
	p()
]), $n = b([
	f("pending"),
	f("in_progress"),
	f("completed"),
	f("cancelled"),
	p()
]), er = o({
	content: p(),
	priority: Qn,
	status: $n,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), tr = o({
	planId: W,
	entries: d(_(er), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), nr = o({
	planId: W,
	uri: h(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), rr = o({
	planId: W,
	content: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ir = n(b([
	tr.and(o({ type: f("items") })),
	nr.and(o({ type: f("file") })),
	rr.and(o({ type: f("markdown") })),
	r(o({
		type: p(),
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
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), or = o({
	planId: W,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), sr = o({
	hint: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), cr = n(b([sr.and(o({ type: f("text") })), r(o({ type: p() }), "type", ["text"])]), "type", ["text"]), lr = o({
	name: p(),
	description: p(),
	input: m(cr.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ur = o({
	availableCommands: d(_(lr), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), dr = o({
	configOptions: d(_(L), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), fr = o({
	title: m(p().nullish(), () => void 0),
	updatedAt: m(a({ offset: !0 }).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), pr = o({
	amount: i(),
	currency: p().regex(/^[A-Z]{3}$/),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), mr = o({
	used: i(),
	size: i(),
	cost: m(pr.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), hr = p(), gr = b([
	f("in_progress"),
	f("completed"),
	f("failed"),
	f("cancelled"),
	p()
]), _r = o({
	compactionId: hr,
	status: gr,
	summary: m(_(k).nullish(), () => void 0),
	error: m(p().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), vr = o({
	compactionId: hr,
	content: k,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), yr = n(b([
	U.and(o({ sessionUpdate: f("user_message_chunk") })),
	Rn.and(o({ sessionUpdate: f("user_message") })),
	U.and(o({ sessionUpdate: f("agent_message_chunk") })),
	zn.and(o({ sessionUpdate: f("agent_message") })),
	U.and(o({ sessionUpdate: f("agent_thought_chunk") })),
	Bn.and(o({ sessionUpdate: f("agent_thought") })),
	Kn.and(o({ sessionUpdate: f("state_update") })),
	qn.and(o({ sessionUpdate: f("tool_call_content_chunk") })),
	Fe.and(o({ sessionUpdate: f("tool_call_update") })),
	Xn.and(o({ sessionUpdate: f("terminal_update") })),
	Zn.and(o({ sessionUpdate: f("terminal_output_chunk") })),
	ar.and(o({ sessionUpdate: f("plan_update") })),
	or.and(o({ sessionUpdate: f("plan_removed") })),
	ur.and(o({ sessionUpdate: f("available_commands_update") })),
	dr.and(o({ sessionUpdate: f("config_option_update") })),
	fr.and(o({ sessionUpdate: f("session_info_update") })),
	mr.and(o({ sessionUpdate: f("usage_update") })),
	_r.and(o({ sessionUpdate: f("compaction_update") })),
	vr.and(o({ sessionUpdate: f("compaction_summary_chunk") })),
	r(o({ sessionUpdate: p() }), "sessionUpdate", [
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
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), xr = o({
	elicitationId: at,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Sr = o({
	connectionId: ut,
	method: p(),
	params: m(c(p(), t()).nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Cr = t();
o({
	method: p(),
	params: b([
		br,
		xr,
		Sr,
		Cr
	]).nullish()
});
var wr = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Tr = o({
	terminal: m(wr.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Er = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Dr = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Or = o({
	form: m(Er.nullish(), () => void 0),
	url: m(Dr.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), kr = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Ar = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), jr = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Mr = o({
	jump: m(kr.nullish(), () => void 0),
	rename: m(Ar.nullish(), () => void 0),
	searchAndReplace: m(jr.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Nr = o({
	auth: m(Tr.nullish(), () => void 0),
	elicitation: m(Or.nullish(), () => void 0),
	nes: m(Mr.nullish(), () => void 0),
	positionEncodings: m(_(Kt).optional(), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Pr = o({
	protocolVersion: mt,
	info: ht,
	capabilities: m(Nr.optional().default({}), () => ({})),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Fr = o({
	methodId: P,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ir = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Lr = o({
	providerId: en,
	apiType: tn,
	baseUrl: h(),
	headers: c(p(), p()).optional(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Rr = o({
	providerId: en,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), zr = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Br = o({
	name: p(),
	value: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Vr = o({
	name: p(),
	url: h(),
	headers: e(Br).optional(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Hr = o({
	name: p(),
	serverId: ct,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ur = o({
	name: p(),
	command: A,
	args: e(p()).optional(),
	env: e(Jt).optional(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Wr = n(b([
	Vr.and(o({ type: f("http") })),
	Hr.and(o({ type: f("acp") })),
	Ur.and(o({ type: f("stdio") })),
	r(o({ type: p() }), "type", [
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
	additionalDirectories: m(_(A).optional(), () => []),
	mcpServers: m(_(Wr).optional(), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Kr = o({
	cwd: A.nullish(),
	cursor: vn.nullish(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), qr = o({
	sessionId: T,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Jr = o({
	sessionId: T,
	cwd: A,
	additionalDirectories: m(_(A).optional(), () => []),
	mcpServers: m(_(Wr).optional(), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Yr = o({ _meta: m(c(p(), t()).nullish(), () => void 0) }), Xr = n(b([Yr.and(o({ type: f("start") })), r(o({
	type: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), "type", ["start"])]), "type", ["start"]), Zr = o({
	sessionId: T,
	cwd: A,
	additionalDirectories: m(_(A).optional(), () => []),
	mcpServers: m(_(Wr).optional(), () => []),
	replayFrom: m(Xr.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Qr = o({
	sessionId: T,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), $r = n(u(b([
	o({
		value: I,
		type: f("id")
	}),
	o({
		value: g(),
		type: f("boolean")
	}),
	r(o({
		type: p(),
		value: t()
	}), "type", ["boolean", "id"])
]), o({
	sessionId: T,
	configId: F,
	_meta: m(c(p(), t()).nullish(), () => void 0)
})), "type", ["boolean", "id"]), ei = o({
	sessionId: T,
	prompt: e(k),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ti = o({
	uri: h(),
	name: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ni = o({
	name: p(),
	owner: p(),
	remoteUrl: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ri = o({
	workspaceUri: m(h().nullish(), () => void 0),
	workspaceFolders: e(ti).nullish(),
	repository: m(ni.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ii = b([
	f("automatic"),
	f("diagnostic"),
	f("manual"),
	p()
]), ai = o({
	uri: h(),
	languageId: p(),
	text: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), oi = o({
	startLine: l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	endLine: l().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	text: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), si = o({
	uri: h(),
	excerpts: e(oi),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ci = o({
	uri: h(),
	diff: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), li = o({
	action: p(),
	uri: h(),
	position: z,
	timestampMs: i(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ui = o({
	uri: h(),
	languageId: p(),
	visibleRange: m(B.nullish(), () => void 0),
	lastFocusedMs: m(i().nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), di = b([
	f("error"),
	f("warning"),
	f("information"),
	f("hint"),
	p()
]), fi = o({
	uri: h(),
	range: B,
	severity: di,
	message: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), pi = o({
	recentFiles: e(ai).nullish(),
	relatedSnippets: e(si).nullish(),
	editHistory: e(ci).nullish(),
	userActions: e(li).nullish(),
	openFiles: e(ui).nullish(),
	diagnostics: e(fi).nullish(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), mi = o({
	sessionId: T,
	uri: h(),
	version: i(),
	position: z,
	selection: B.nullish(),
	triggerKind: ii,
	context: pi.nullish(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), hi = o({
	sessionId: T,
	_meta: m(c(p(), t()).nullish(), () => void 0)
});
o({
	id: w,
	method: p(),
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
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), _i = n(b([
	o({ outcome: f("cancelled") }),
	gi.and(o({ outcome: f("selected") })),
	r(o({ outcome: p() }), "outcome", ["cancelled", "selected"])
]), "outcome", ["cancelled", "selected"]), vi = o({
	outcome: _i,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), yi = b([
	p(),
	i(),
	i(),
	g(),
	e(p())
]), bi = o({ content: c(p(), yi).nullish() }), xi = n(u(b([
	bi.and(o({ action: f("accept") })),
	o({ action: f("decline") }),
	o({ action: f("cancel") }),
	r(o({ action: p() }), "action", [
		"accept",
		"cancel",
		"decline"
	])
]), o({ _meta: m(c(p(), t()).nullish(), () => void 0) })), "action", [
	"accept",
	"cancel",
	"decline"
]), Si = o({
	connectionId: ut,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ci = o({ _meta: m(c(p(), t()).nullish(), () => void 0) });
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
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ti = o({
	sessionId: T,
	uri: h(),
	languageId: p(),
	version: i(),
	text: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ei = o({
	range: B.nullish(),
	text: p(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Di = o({
	sessionId: T,
	uri: h(),
	version: i(),
	contentChanges: d(_(Ei), () => []),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Oi = o({
	sessionId: T,
	uri: h(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ki = o({
	sessionId: T,
	uri: h(),
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Ai = o({
	sessionId: T,
	uri: h(),
	version: i(),
	position: z,
	visibleRange: B,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), ji = o({
	sessionId: T,
	suggestionId: R,
	_meta: m(c(p(), t()).nullish(), () => void 0)
}), Mi = b([
	f("rejected"),
	f("ignored"),
	f("replaced"),
	f("cancelled"),
	p()
]), Ni = o({
	sessionId: T,
	suggestionId: R,
	reason: m(Mi.nullish(), () => void 0),
	_meta: m(c(p(), t()).nullish(), () => void 0)
});
o({
	method: p(),
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
	_meta: m(c(p(), t()).nullish(), () => void 0)
});
o({
	method: p(),
	params: Pi.nullish()
});
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/v2/schema/guards.gen.js
function G(e, t) {
	return typeof e == "object" && e ? e[t] : void 0;
}
Ie.and(o({ type: f("tool_call") })), Le.and(o({ type: f("command") })), Ee.and(o({ type: f("content") })), je.and(o({ type: f("diff") })), Me.and(o({ type: f("terminal") }));
var Fi = ge.and(o({ type: f("text") })), Ii = _e.and(o({ type: f("image") })), Li = ve.and(o({ type: f("audio") })), Ri = xe.and(o({ type: f("resource_link") })), zi = Te.and(o({ type: f("resource") }));
j.and(o({ operation: f("add") })), j.and(o({ operation: f("delete") })), j.and(o({ operation: f("modify") })), M.and(o({ operation: f("move") })), M.and(o({ operation: f("copy") })), it.and(o({ mode: f("form") })).and(o({ message: p() })), ot.and(o({ mode: f("url") })).and(o({ message: p() })), b([Ue, We]).and(o({ message: p() })), Je.and(o({ type: f("string") })), Ye.and(o({ type: f("number") })), Xe.and(o({ type: f("integer") })), Ze.and(o({ type: f("boolean") })), tt.and(o({ type: f("array") })), Qe.and(o({ type: f("string") })), Yt.and(o({ type: f("terminal") })), Xt.and(o({ type: f("agent") })), o({
	methodId: P,
	name: p()
}), mn.and(o({ type: f("select") })).and(o({
	configId: F,
	name: p()
})), hn.and(o({ type: f("boolean") })).and(o({
	configId: F,
	name: p()
})), o({
	configId: F,
	name: p()
}), On.and(o({ kind: f("edit") })), kn.and(o({ kind: f("jump") })), An.and(o({ kind: f("rename") })), jn.and(o({ kind: f("searchAndReplace") })), o({ suggestionId: R });
var Bi = U.and(o({ sessionUpdate: f("user_message_chunk") })), Vi = Rn.and(o({ sessionUpdate: f("user_message") })), Hi = U.and(o({ sessionUpdate: f("agent_message_chunk") })), Ui = zn.and(o({ sessionUpdate: f("agent_message") })), Wi = U.and(o({ sessionUpdate: f("agent_thought_chunk") })), Gi = Bn.and(o({ sessionUpdate: f("agent_thought") })), Ki = Kn.and(o({ sessionUpdate: f("state_update") })), qi = qn.and(o({ sessionUpdate: f("tool_call_content_chunk") })), Ji = Fe.and(o({ sessionUpdate: f("tool_call_update") })), Yi = Xn.and(o({ sessionUpdate: f("terminal_update") })), Xi = Zn.and(o({ sessionUpdate: f("terminal_output_chunk") })), Zi = ar.and(o({ sessionUpdate: f("plan_update") })), Qi = or.and(o({ sessionUpdate: f("plan_removed") })), $i = ur.and(o({ sessionUpdate: f("available_commands_update") })), ea = dr.and(o({ sessionUpdate: f("config_option_update") })), ta = fr.and(o({ sessionUpdate: f("session_info_update") })), na = mr.and(o({ sessionUpdate: f("usage_update") })), ra = _r.and(o({ sessionUpdate: f("compaction_update") })), ia = vr.and(o({ sessionUpdate: f("compaction_summary_chunk") })), aa = Vn.and(o({ state: f("running") })), oa = Wn.and(o({ state: f("idle") })), sa = Gn.and(o({ state: f("requires_action") }));
tr.and(o({ type: f("items") })), nr.and(o({ type: f("file") })), rr.and(o({ type: f("markdown") })), o({ planId: W }), sr.and(o({ type: f("text") })), Vr.and(o({ type: f("http") })), Hr.and(o({ type: f("acp") })), Ur.and(o({ type: f("stdio") })), Yr.and(o({ type: f("start") })), o({ type: f("id") }).and(o({ value: I })).and(o({
	sessionId: T,
	configId: F
})), o({ type: f("boolean") }).and(o({ value: g() })).and(o({
	sessionId: T,
	configId: F
})), o({ value: t() }).and(o({
	sessionId: T,
	configId: F
})), o({ outcome: f("cancelled") }), gi.and(o({ outcome: f("selected") })), bi.and(o({ action: f("accept") })), o({ action: f("decline") }), o({ action: f("cancel") });
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
		throw r.close(e), new s("INITIALIZE_REJECTED", "ACP v2 initialization failed", {
			cause: e,
			protocol: 2,
			phase: "initialize",
			retryable: !0
		});
	}
	if (a.protocolVersion !== 2) throw r.close(), new s("PROTOCOL_VERSION_MISMATCH", `Requested ACP v2 but agent selected v${a.protocolVersion}`, {
		protocol: 2,
		phase: "initialize"
	});
	if (a.capabilities?.session == null) throw r.close(), new s("CAPABILITY_REQUIRED", "The ACP v2 agent does not advertise the session surface", {
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
		if (!this.initialized.capabilities.deleteSession) throw new s("CAPABILITY_REQUIRED", "The agent does not support session/delete", { protocol: 2 });
		await this.connection.agent.request(Y.agent.session.delete, { sessionId: e });
	}
	async closeSession(e) {
		await this.connection.agent.request(Y.agent.session.close, { sessionId: e });
	}
	promptReady(e) {
		return !this.#t.has(e);
	}
	async prompt(e, t, n) {
		if (this.#e.has(e)) throw new s("SESSION_BUSY", `Session '${e}' already has a foreground turn`, { protocol: 2 });
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
			if (!this.host?.terminalAuth) throw new s("CAPABILITY_REQUIRED", "Terminal authentication needs a host handler", { protocol: 2 });
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
		for (let e of this.#e.values()) e.reject(new s("TURN_INTERRUPTED", "Connection closed before the turn completed", {
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
	if (e.type === "sse") throw new s("INVALID_CONFIGURATION", "SSE MCP servers are not part of ACP v2", { protocol: 2 });
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